#!/usr/bin/env python3
"""
Coletor de Dados de Emendas Parlamentares
Focus em APIs gratuitas da Câmara dos Deputados
Refatorado para usar ETL Utils - elimina redundâncias e padroniza operações
"""

import sys
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações
sys.path.append(str(Path(__file__).parent))
from config import get_config, API_CONFIG, get_coleta_config, get_data_inicio_coleta, deve_respeitar_data_inicio, coleta_habilitada

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.emenda_models import EmendaParlamentar, DetalheEmenda, VotacaoEmenda, RankingEmendas

# Importar utilitários
from utils.gcs_utils import get_gcs_manager

# Importar ETL utils
from etl_utils import ETLBase, DateParser, GCSUploader

class ColetorEmendas(ETLBase):
    """
    Classe responsável por coletar dados de emendas parlamentares
    Herda de ETLBase para usar funcionalidades comuns e eliminar redundâncias
    """

    def __init__(self):
        """Inicializa o coletor usando ETLBase"""
        super().__init__()
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager.is_available()
        
        # Configurações de coleta centralizadas
        self.coleta_config = get_coleta_config()
        self.data_inicio = get_data_inicio_coleta()
        
        print(f"✅ Coletor de emendas inicializado (API gratuita)")
        print(f"📅 Período de coleta: {self.data_inicio} até hoje")
        print(f"🔧 Respeitar data início: {deve_respeitar_data_inicio('emendas')}")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")


    def buscar_emendas_por_tipo(self, tipo_emenda: str, ano: int, limite: int = 100) -> List[Dict]:
        """
        Busca emendas por tipo (EMD, EMP, etc) usando parâmetros da API
        API: /proposicoes?siglaTipo=TIPO&ano=ANO
        """
        print(f"   🔍 Buscando {tipo_emenda}/{ano} (limite: {limite})")
        
        todas_emendas = []
        pagina = 1
        
        # Buscar usando parâmetros da API
        while len(todas_emendas) < limite:
            url = f"{API_CONFIG['base_url']}/proposicoes"
            params = {
                'siglaTipo': tipo_emenda,  # Filtrar por tipo na API
                'ano': ano,  # Filtrar por ano na API
                'pagina': pagina,
                'itens': min(100, limite - len(todas_emendas)),  # Máximo por página
                'ordem': 'DESC',
                'ordenarPor': 'id'
            }
            
            data = self.make_request(url, params)
            if not data:
                break
            
            emendas_pagina = data.get('dados', [])
            if not emendas_pagina:
                break
            
            todas_emendas.extend(emendas_pagina)
            
            # Se não temos mais resultados, parar
            if len(emendas_pagina) < params['itens']:
                break
            
            pagina += 1
            if pagina > 10:  # Limitar páginas para não buscar forever
                break
        
        # Limitar ao número desejado
        emendas = todas_emendas[:limite]
        print(f"      📄 Encontradas {len(emendas)} emendas {tipo_emenda}/{ano}")
        
        return emendas

    def buscar_detalhes_emenda(self, emenda_id: int) -> Optional[Dict]:
        """
        Busca detalhes completos de uma emenda
        API: /proposicoes/{id}
        """
        url = f"{API_CONFIG['base_url']}/proposicoes/{emenda_id}"
        
        data = self.make_request(url)
        if not data:
            return None
        
        return data.get('dados')

    def buscar_autor_emenda(self, autor_uri: str) -> Optional[Dict]:
        """
        Busca detalhes do autor da emenda
        API: /deputados/{id}
        """
        if not autor_uri:
            return None
        
        # Extrair ID do deputado da URI
        try:
            deputado_id = autor_uri.split('/')[-1]
            url = f"{API_CONFIG['base_url']}/deputados/{deputado_id}"
            
            data = self.make_request(url)
            if not data:
                return None
            
            return data.get('dados')
        except:
            return None

    def buscar_votacoes_emenda(self, emenda_id: int) -> List[Dict]:
        """
        Busca votações de uma emenda
        API: /proposicoes/{id}/votacoes
        """
        url = f"{API_CONFIG['base_url']}/proposicoes/{emenda_id}/votacoes"
        params = {'itens': 10}
        
        data = self.make_request(url, params)
        if not data:
            return []
        
        return data.get('dados', [])

    def extrair_valor_emenda(self, descricao: str) -> Optional[float]:
        """
        Extrai valor monetário da descrição da emenda
        """
        if not descricao:
            return None
        
        import re
        
        # Padrões para encontrar valores monetários
        padroes = [
            r'R\$[\s]*([\d.,]+)',
            r'valor[\s]*:[\s]*R\$[\s]*([\d.,]+)',
            r'valor[\s]*de[\s]*([\d.,]+)',
            r'([\d.,]+)\s*reais'
        ]
        
        for padrao in padroes:
            match = re.search(padrao, descricao.lower())
            if match:
                valor_str = match.group(1).replace('.', '').replace(',', '')
                try:
                    return float(valor_str)
                except ValueError:
                    continue
        
        return None

    def extrair_beneficiario(self, descricao: str, ementa: str = '') -> Optional[str]:
        """
        Extrai beneficiário principal da emenda
        """
        texto_completo = f"{descricao} {ementa}".lower()
        
        # Padrões comuns de beneficiários
        padroes_beneficiarios = [
            r'munic[ií]pio\s+de\s+([a-z\s]+)',
            r'estado\s+de\s+([a-z]{2})',
            r'([a-z]{2})\s*-\s*([a-z\s]+)',
            r'para\s+([a-z\s]+)\s*-\s*([a-z]{2})',
            r'beneficia\s+([a-z\s]+)',
            r'favorece\s+([a-z\s]+)'
        ]
        
        for padrao in padroes_beneficiarios:
            match = re.search(padrao, texto_completo)
            if match:
                return match.group(1).strip().title()
        
        return None

    def salvar_emenda(self, emenda_data: Dict, db: Session, resultados: Optional[Dict] = None) -> Optional[EmendaParlamentar]:
        """
        Salva dados completos de uma emenda
        """
        try:
            # Verificar se já existe (converter ID para string)
            existente = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.api_camara_id == str(emenda_data['id'])
            ).first()
            
            if existente:
                return existente
            
            # Buscar autor
            autor_data = self.buscar_autor_emenda(emenda_data.get('uriAutor'))
            deputado_id = None
            
            if autor_data:
                # Buscar deputado no banco
                deputado = db.query(Deputado).filter(
                    Deputado.api_camara_id == autor_data['id']
                ).first()
                if deputado:
                    deputado_id = deputado.id
            
            # Extrair informações da emenda
            numero = emenda_data.get('numero', 0)
            ano = emenda_data.get('ano', 2025)
            tipo = emenda_data.get('siglaTipo', 'EMD')
            
            # Extrair valor e beneficiário
            valor = self.extrair_valor_emenda(emenda_data.get('descricao', ''))
            beneficiario = self.extrair_beneficiario(
                emenda_data.get('descricao', ''),
                emenda_data.get('ementa', '')
            )
            
            # Criar emenda (deputado_id pode ser None para emendas de comissão)
            emenda = EmendaParlamentar(
                api_camara_id=emenda_data['id'],
                deputado_id=deputado_id,  # Pode ser None para emendas de comissão
                tipo_emenda=tipo,
                numero=numero,
                ano=ano,
                emenda=emenda_data.get('descricao', ''),
                local=self._extrair_local(emenda_data.get('descricao', '')),
                natureza=self._extrair_natureza(emenda_data.get('descricao', '')),
                tema=emenda_data.get('tema'),
                valor_emenda=valor,
                beneficiario_principal=beneficiario,
                situacao=emenda_data.get('statusProposicao', {}).get('descricao'),
                data_apresentacao=DateParser.parse_date(emenda_data.get('dataApresentacao')),
                autor=autor_data.get('nome') if autor_data else None,
                partido_autor=autor_data.get('siglaPartido') if autor_data else None,
                uf_autor=autor_data.get('siglaUf') if autor_data else None,
                url_documento=emenda_data.get('urlInteiroTeor')
            )
            
            db.add(emenda)
            db.flush()  # Para obter o ID
            
            # Salvar detalhes
            self._salvar_detalhes_emenda(emenda, emenda_data, db)
            
            # Salvar votações
            votacoes = self.buscar_votacoes_emenda(emenda_data['id'])
            for votacao in votacoes:
                self._salvar_votacao_emenda(emenda, votacao, db)
            
            # Upload para GCS
            gcs_url = self._upload_emenda_gcs(emenda, emenda_data, autor_data, votacoes, db)
            if gcs_url:
                emenda.gcs_url = gcs_url
            
            db.commit()
            print(f"      ✅ Emenda salva: {tipo} {numero}/{ano}")
            return emenda
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar emenda: {e}")
            db.rollback()
            return None

    def _salvar_detalhes_emenda(self, emenda: EmendaParlamentar, emenda_data: Dict, db: Session):
        """Salva detalhes específicos da emenda"""
        try:
            detalhe = DetalheEmenda(
                emenda_id=emenda.id,
                ementa=emenda_data.get('ementa'),
                justificativa=emenda_data.get('justificativa'),
                texto_completo=emenda_data.get('descricao'),
                pdf_url=emenda_data.get('urlInteiroTeor')
            )
            db.add(detalhe)
        except Exception as e:
            print(f"      ⚠️ Erro ao salvar detalhes: {e}")

    def _salvar_votacao_emenda(self, emenda: EmendaParlamentar, votacao_data: Dict, db: Session):
        """Salva dados de votação da emenda"""
        try:
            votacao = VotacaoEmenda(
                emenda_id=emenda.id,
                data_votacao=DateParser.parse_date(votacao_data.get('dataHoraInicio')),
                hora_votacao=votacao_data.get('dataHoraInicio', '').split(' ')[1] if votacao_data.get('dataHoraInicio') else None,
                tipo_votacao=votacao_data.get('descricao'),
                resultado=votacao_data.get('resultado'),
                votos_sim=votacao_data.get('votosSim', 0),
                votos_nao=votacao_data.get('votosNao', 0),
                votos_abstencao=votacao_data.get('votosAbstencao', 0),
                total_votantes=votacao_data.get('totalVotantes', 0),
                orgao_votacao=votacao_data.get('orgao', {}).get('nome'),
                plenario=votacao_data.get('orgao', {}).get('sigla') == 'PLEN',
                api_camara_id=votacao_data.get('id')
            )
            db.add(votacao)
        except Exception as e:
            print(f"      ⚠️ Erro ao salvar votação: {e}")

    def _extrair_local(self, descricao: str) -> Optional[str]:
        """Extrai local da emenda (LOA, LDO, etc)"""
        descricao_lower = descricao.lower()
        if 'loa' in descricao_lower or 'lei orçamentária anual' in descricao_lower:
            return 'LOA'
        elif 'ldo' in descricao_lower or 'lei de diretrizes' in descricao_lower:
            return 'LDO'
        elif 'ppa' in descricao_lower or 'plano plurianual' in descricao_lower:
            return 'PPA'
        return None

    def _extrair_natureza(self, descricao: str) -> Optional[str]:
        """Extrai natureza da emenda"""
        descricao_lower = descricao.lower()
        if 'individual' in descricao_lower:
            return 'Individual'
        elif 'bancada' in descricao_lower:
            return 'Bancada'
        elif 'comissão' in descricao_lower:
            return 'Comissão'
        return 'Individual'  # Default

    def _upload_emenda_gcs(self, emenda: EmendaParlamentar, emenda_data: Dict, autor_data: Optional[Dict], votacoes: List[Dict], db: Session) -> Optional[str]:
        """
        Faz upload dos dados completos da emenda para o GCS
        """
        try:
            # Preparar dados completos da emenda
            dados_completos = {
                'emenda': {
                    'id': emenda.id,
                    'api_camara_id': emenda.api_camara_id,
                    'tipo_emenda': emenda.tipo_emenda,
                    'numero': emenda.numero,
                    'ano': emenda.ano,
                    'emenda': emenda.emenda,
                    'local': emenda.local,
                    'natureza': emenda.natureza,
                    'tema': emenda.tema,
                    'valor_emenda': float(emenda.valor_emenda) if emenda.valor_emenda else None,
                    'beneficiario_principal': emenda.beneficiario_principal,
                    'situacao': emenda.situacao,
                    'data_apresentacao': emenda.data_apresentacao.isoformat() if emenda.data_apresentacao else None,
                    'autor': emenda.autor,
                    'partido_autor': emenda.partido_autor,
                    'uf_autor': emenda.uf_autor,
                    'url_documento': emenda.url_documento,
                    'created_at': emenda.created_at.isoformat() if emenda.created_at else None
                },
                'dados_api': emenda_data,
                'autor': autor_data,
                'votacoes': votacoes,
                'detalhes': {
                    'ementa': emenda_data.get('ementa'),
                    'justificativa': emenda_data.get('justificativa'),
                    'texto_completo': emenda_data.get('descricao'),
                    'pdf_url': emenda_data.get('urlInteiroTeor')
                },
                'metadados': {
                    'data_coleta': datetime.now().isoformat(),
                    'fonte': 'API Câmara dos Deputados',
                    'versao': '1.0'
                }
            }
            
            # Obter GCS Manager
            gcs = get_gcs_manager()
            if not gcs.is_available():
                print(f"      ⚠️ GCS não disponível, pulando upload")
                return None
            
            # Fazer upload
            gcs_url = gcs.upload_emenda(dados_completos, emenda.ano, str(emenda.api_camara_id))
            
            if gcs_url:
                print(f"      📁 Upload GCS realizado: {emenda.tipo_emenda} {emenda.numero}/{emenda.ano}")
                return gcs_url
            else:
                print(f"      ❌ Erro no upload GCS")
                return None
                
        except Exception as e:
            print(f"      ❌ Erro no upload GCS: {e}")
            return None


    def coletar_emendas_ano(self, ano: int, db: Session) -> Dict[str, int]:
        """
        Coleta emendas para um ano específico (método compatível com pipeline)
        """
        # Usar os tipos de emenda mais comuns
        tipos_emenda = ['EMD', 'EMP']  # Emenda e Emenda de Plenário
        return self.coletar_emendas_periodo(ano, tipos_emenda, db)

    def coletar_emendas_periodo(self, ano: int, tipos_emenda: List[str], db: Session) -> Dict[str, int]:
        """
        Coleta emendas para um período específico
        """
        print(f"\n📄 COLETANDO EMENDAS PARLAMENTARES - {ano}")
        print("=" * 60)
        
        resultados = {
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_autor': 0,
            'emendas_com_gcs': 0,
            'votacoes_salvas': 0,
            'erros': 0
        }
        
        for tipo in tipos_emenda:
            print(f"\n🔍 Buscando emendas {tipo}/{ano}")
            
            try:
                # Buscar emendas do tipo
                emendas = self.buscar_emendas_por_tipo(tipo, ano, limite=50)
                resultados['emendas_encontradas'] += len(emendas)
                
                for i, emenda_data in enumerate(emendas, 1):
                    print(f"      📄 Processando {i}/{len(emendas)}: {tipo} {emenda_data.get('numero', '?')}")
                    
                    try:
                        # Salvar emenda completa
                        emenda = self.salvar_emenda(emenda_data, db, resultados)
                        if emenda:
                            resultados['emendas_salvas'] += 1
                            if emenda.deputado_id:
                                resultados['emendas_com_autor'] += 1
                            if emenda.gcs_url:
                                resultados['emendas_com_gcs'] += 1
                            resultados['votacoes_salvas'] += len(emenda.votacoes)
                        
                        # Rate limiting
                        time.sleep(1)  # 1 segundo entre requisições
                        
                    except Exception as e:
                        print(f"      ❌ Erro ao processar emenda: {e}")
                        resultados['erros'] += 1
                        continue
                
            except Exception as e:
                print(f"❌ Erro ao buscar emendas {tipo}: {e}")
                resultados['erros'] += 1
                continue
        
        return resultados

    def gerar_ranking_emendas(self, ano: int, db: Session) -> bool:
        """
        Gera ranking de emendas por deputado
        """
        try:
            print(f"\n🏆 GERANDO RANKING DE EMENDAS - {ano}")
            print("=" * 40)
            
            # Consulta para ranking
            ranking_query = db.query(
                EmendaParlamentar.deputado_id,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_total'),
                func.avg(EmendaParlamentar.valor_emenda).label('valor_medio')
            ).filter(
                EmendaParlamentar.ano == ano,
                EmendaParlamentar.deputado_id.isnot(None)
            ).group_by(EmendaParlamentar.deputado_id).all()
            
            # Salvar ranking
            for i, (deputado_id, quantidade, valor_total, valor_medio) in enumerate(ranking_query, 1):
                ranking = RankingEmendas(
                    deputado_id=deputado_id,
                    ano_referencia=ano,
                    quantidade_emendas=quantidade,
                    valor_total_emendas=valor_total or 0,
                    valor_medio_emenda=valor_medio or 0,
                    ranking_quantidade=i
                )
                db.add(ranking)
            
            db.commit()
            print(f"✅ Ranking gerado com {len(ranking_query)} deputados")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao gerar ranking: {e}")
            db.rollback()
            return False

def main():
    """
    Função principal para execução standalone
    """
    print("📄 COLETA DE DADOS DE EMENDAS PARLAMENTARES")
    print("=" * 60)
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = next(get_db())
    
    try:
        coletor = ColetorEmendas()
        
        # Coletar emendas de 2024 e 2025
        anos = [2024, 2025]
        tipos_emenda = ['EMD', 'EMP']  # Emenda e Emenda de Plenário
        
        for ano in anos:
            resultados = coletor.coletar_emendas_periodo(ano, tipos_emenda, db_session)
            
            print(f"\n📋 RESUMO DA COLETA - {ano}")
            print("=" * 30)
            print(f"📄 Emendas encontradas: {resultados['emendas_encontradas']}")
            print(f"💾 Emendas salvas: {resultados['emendas_salvas']}")
            print(f"👥 Com autor identificado: {resultados['emendas_com_autor']}")
            print(f"🗳️ Votações salvas: {resultados['votacoes_salvas']}")
            print(f"❌ Erros: {resultados['erros']}")
            
            # Gerar ranking
            coletor.gerar_ranking_emendas(ano, db_session)
        
        print(f"\n✅ Coleta de emendas concluída!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
