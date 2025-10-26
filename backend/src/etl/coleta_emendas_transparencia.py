#!/usr/bin/env python3
"""
Coletor de Emendas Orçamentárias do Portal da Transparência
API com valores monetários reais das emendas parlamentares
"""

import sys
import os
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
from config import get_config

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.emenda_models import EmendaParlamentar, DetalheEmenda, VotacaoEmenda, RankingEmendas

# Importar utilitários
from utils.gcs_utils import get_gcs_manager

# Importar ETL utils
from .etl_utils import ETLBase, DateParser, GCSUploader

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

class ColetorEmendasTransparencia(ETLBase):
    """
    Classe responsável por coletar emendas orçamentárias do Portal da Transparência
    Herda de ETLBase para usar funcionalidades comuns
    """

    def __init__(self):
        """Inicializa o coletor usando ETLBase"""
        super().__init__()
        
        # Configurações da API
        self.api_key = os.getenv('CHAVE_API_DADOS')
        if not self.api_key:
            raise ValueError("CHAVE_API_DADOS não encontrada no .env")
        
        self.base_url = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
        self.headers = {
            "chave-api-dados": self.api_key,
            "Accept": "application/json"
        }
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager.is_available()
        
        print(f"✅ Coletor de emendas (Portal da Transparência) inicializado")
        print(f"   🔑 Chave API: {self.api_key[:10]}...")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")

    def fazer_requisicao_api(self, params: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Faz requisição à API com tratamento de erros e rate limiting
        """
        try:
            import requests
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'dados' in data:
                    return data['dados']
                else:
                    return data
            else:
                print(f"      ❌ Erro HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"      ❌ Erro na requisição: {e}")
            return None

    def limpar_valor_monetario(self, valor) -> float:
        """
        Converte valor monetário para float de forma robusta
        Baseado no código validado que funcionou
        """
        if not valor:
            return 0.0
        
        try:
            # Conversão robusta como no código validado
            return float(str(valor).replace('.', '').replace(',', '.') or 0)
        except (ValueError, AttributeError):
            return 0.0

    def buscar_todas_emendas_deputado(self, nome_deputado: str, ano: int) -> List[Dict]:
        """
        Busca TODAS as emendas de um deputado em um ano
        Método validado que funciona
        """
        print(f"   🔍 Buscando emendas de {nome_deputado} - {ano}")
        
        todas_emendas = []
        pagina = 1
        
        while True:
            params = {
                "ano": ano,
                "nomeAutor": nome_deputado,  # Filtro específico por deputado
                "pagina": pagina
            }
            
            print(f"      📄 Página {pagina}...")
            
            emendas_pagina = self.fazer_requisicao_api(params)
            if not emendas_pagina:
                break
            
            if not emendas_pagina:  # Lista vazia = fim dos resultados
                print(f"      ✅ Fim da coleta - página {pagina-1} foi a última")
                break
            
            print(f"      → {len(emendas_pagina)} emendas encontradas")
            todas_emendas.extend(emendas_pagina)
            pagina += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        return todas_emendas

    def buscar_emendas_ano(self, ano: int, limite: int = 1000) -> List[Dict]:
        """
        Busca emendas de um ano específico (método antigo - mantido para compatibilidade)
        """
        print(f"   🔍 Buscando emendas de {ano} (limite: {limite})")
        
        todas_emendas = []
        pagina = 1
        
        while len(todas_emendas) < limite:
            params = {
                'ano': ano,
                'pagina': pagina,
                'itens': min(100, limite - len(todas_emendas))
            }
            
            emendas_pagina = self.fazer_requisicao_api(params)
            if not emendas_pagina:
                break
            
            todas_emendas.extend(emendas_pagina)
            print(f"      📄 Página {pagina}: +{len(emendas_pagina)} emendas")
            
            # Se não tem mais resultados, parar
            if len(emendas_pagina) < params['itens']:
                break
            
            pagina += 1
            if pagina > 100:  # Limite de segurança
                break
            
            # Rate limiting
            time.sleep(0.5)  # 500ms entre requisições
        
        # Limitar ao número desejado
        emendas = todas_emendas[:limite]
        print(f"      ✅ Total encontrado: {len(emendas)} emendas de {ano}")
        
        return emendas

    def mapear_tipo_emenda(self, tipo_emenda: str) -> str:
        """
        Mapeia tipos de emenda da API para o modelo
        """
        tipo_normalizado = tipo_emenda.strip().upper()
        
        mapeamento = {
            'EMENDA INDIVIDUAL': 'EMD',
            'EMENDA DE BANCADA': 'EMB',
            'EMENDA DE COMISSÃO': 'EMC',
            'EMENDA DE RELATOR': 'EMR'
        }
        
        return mapeamento.get(tipo_normalizado, 'EMD')

    def extrair_local_emenda(self, funcao: str, subfuncao: str, localidade: str) -> Optional[str]:
        """
        Extrai local da emenda baseado na função e localidade
        """
        if not funcao:
            return None
        
        funcao_lower = funcao.lower()
        
        # Mapeamento baseado em funções orçamentárias
        if 'saúde' in funcao_lower or 'saude' in funcao_lower:
            return 'SAÚDE'
        elif 'educação' in funcao_lower or 'educacao' in funcao_lower:
            return 'EDUCAÇÃO'
        elif 'urbanismo' in funcao_lower:
            return 'URBANISMO'
        elif 'assistência' in funcao_lower or 'assistencia' in funcao_lower:
            return 'ASSISTÊNCIA SOCIAL'
        elif 'segurança' in funcao_lower or 'seguranca' in funcao_lower:
            return 'SEGURANÇA'
        elif 'infraestrutura' in funcao_lower:
            return 'INFRAESTRUTURA'
        else:
            return funcao.upper()

    def extrair_natureza_emenda(self, tipo_emenda: str, autor: str) -> str:
        """
        Extrai natureza da emenda baseado no tipo e autor
        """
        if 'BANCADA' in tipo_emenda.upper():
            return 'Bancada'
        elif 'INDIVIDUAL' in tipo_emenda.upper():
            return 'Individual'
        elif 'COMISSÃO' in tipo_emenda.upper() or 'COMISSAO' in tipo_emenda.upper():
            return 'Comissão'
        else:
            return 'Individual'  # Default

    def buscar_deputado_por_nome(self, nome_autor: str, db: Session) -> Optional[int]:
        """
        Busca ID do deputado pelo nome com estratégia robusta
        """
        if not nome_autor or 'BANCADA' in nome_autor.upper():
            return None
        
        # Tentar match exato primeiro
        deputado = db.query(Deputado).filter(
            func.upper(Deputado.nome) == func.upper(nome_autor.strip())
        ).first()
        
        if deputado:
            return deputado.id
        
        # Tentar match parcial
        deputado = db.query(Deputado).filter(
            Deputado.nome.ilike(f"%{nome_autor.strip()}%")
        ).first()
        
        if deputado:
            return deputado.id
        
        # Tentar sem sobrenomes (fallback)
        partes_nome = nome_autor.strip().split()
        if len(partes_nome) >= 2:
            primeiro_nome = partes_nome[0]
            deputado = db.query(Deputado).filter(
                Deputado.nome.ilike(f"{primeiro_nome}%")
            ).first()
            
            if deputado:
                return deputado.id
        
        return None

    def salvar_emenda_transparencia(self, emenda_data: Dict, db: Session) -> Optional[EmendaParlamentar]:
        """
        Salva emenda do Portal da Transparência no banco
        """
        try:
            # Verificar se já existe
            existente = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.api_camara_id == str(emenda_data['codigoEmenda'])
            ).first()
            
            if existente:
                return existente
            
            # Extrair dados da emenda
            codigo_emenda = emenda_data['codigoEmenda']
            ano = emenda_data['ano']
            tipo_emenda_api = emenda_data['tipoEmenda']
            autor = emenda_data['autor']
            nome_autor = emenda_data.get('nomeAutor', autor)
            
            # Mapear tipo
            tipo_mapeado = self.mapear_tipo_emenda(tipo_emenda_api)
            
            # Extrair valores
            valor_empenhado = self.limpar_valor_monetario(emenda_data.get('valorEmpenhado', '0'))
            valor_liquidado = self.limpar_valor_monetario(emenda_data.get('valorLiquidado', '0'))
            valor_pago = self.limpar_valor_monetario(emenda_data.get('valorPago', '0'))
            
            # Usar o maior valor disponível
            valor_emenda = max(
                valor_empenhado or 0,
                valor_liquidado or 0,
                valor_pago or 0
            ) or 0
            
            # Buscar deputado
            deputado_id = self.buscar_deputado_por_nome(nome_autor, db)
            
            # Extrair informações adicionais
            funcao = emenda_data.get('funcao', '')
            subfuncao = emenda_data.get('subfuncao', '')
            localidade = emenda_data.get('localidadeDoGasto', '')
            
            # Criar emenda
            emenda = EmendaParlamentar(
                api_camara_id=str(codigo_emenda),
                deputado_id=deputado_id,
                tipo_emenda=tipo_mapeado,
                numero=emenda_data.get('numeroEmenda', 0),
                ano=ano,
                emenda=f"Emenda {tipo_emenda_api} - {funcao} - {localidade}",
                local=self.extrair_local_emenda(funcao, subfuncao, localidade),
                natureza=self.extrair_natureza_emenda(tipo_emenda_api, autor),
                tema=funcao,
                valor_emenda=valor_emenda,
                beneficiario_principal=localidade,
                situacao='Ativa',  # Default pois API não fornece
                data_apresentacao=datetime(ano, 1, 1),  # Default início do ano
                autor=nome_autor,
                partido_autor=None,  # Não disponível nesta API
                uf_autor=localidade.split('(')[-1].replace(')', '') if '(' in localidade else None,
                url_documento=None  # Não disponível nesta API
            )
            
            db.add(emenda)
            db.flush()  # Para obter o ID
            
            # Salvar detalhes específicos
            self._salvar_detalhes_emenda_transparencia(emenda, emenda_data, db)
            
            # Upload para GCS
            gcs_url = self._upload_emenda_gcs(emenda, emenda_data, db)
            if gcs_url:
                emenda.gcs_url = gcs_url
            
            db.commit()
            print(f"      ✅ Emenda salva: {tipo_mapeado} {emenda.numero}/{ano} - R$ {valor_emenda:,.2f}")
            return emenda
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar emenda: {e}")
            db.rollback()
            return None

    def _salvar_detalhes_emenda_transparencia(self, emenda: EmendaParlamentar, emenda_data: Dict, db: Session):
        """Salva detalhes específicos da emenda do Portal da Transparência"""
        try:
            detalhe = DetalheEmenda(
                emenda_id=emenda.id,
                ementa=f"Emenda {emenda_data.get('tipoEmenda')} para {emenda_data.get('funcao', 'função não informada')}",
                justificativa=f"Localidade do gasto: {emenda_data.get('localidadeDoGasto', 'N/A')}",
                texto_completo=f"Função: {emenda_data.get('funcao', 'N/A')}\n"
                               f"Subfunção: {emenda_data.get('subfuncao', 'N/A')}\n"
                               f"Localidade: {emenda_data.get('localidadeDoGasto', 'N/A')}\n"
                               f"Valor Empenhado: {emenda_data.get('valorEmpenhado', '0')}\n"
                               f"Valor Liquidado: {emenda_data.get('valorLiquidado', '0')}\n"
                               f"Valor Pago: {emenda_data.get('valorPago', '0')}",
                pdf_url=None
            )
            db.add(detalhe)
        except Exception as e:
            print(f"      ⚠️ Erro ao salvar detalhes: {e}")

    def _upload_emenda_gcs(self, emenda: EmendaParlamentar, emenda_data: Dict, db: Session) -> Optional[str]:
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
                'dados_api_transparencia': emenda_data,
                'metadados': {
                    'data_coleta': datetime.now().isoformat(),
                    'fonte': 'API Portal da Transparência',
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

    def coletar_emendas_periodo(self, ano: int, limite: int = 500, db: Session = None) -> Dict[str, int]:
        """
        Coleta emendas orçamentárias do Portal da Transparência
        """
        print(f"\n💰 COLETANDO EMENDAS ORÇAMENTÁRIAS - Portal da Transparência")
        print("=" * 70)
        print(f"📅 Ano: {ano}")
        print(f"🎯 Limite: {limite} emendas")
        
        # Usar sessão fornecida ou criar nova
        if not db:
            db = next(get_db())
            fechar_db = True
        else:
            fechar_db = False
        
        resultados = {
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_autor': 0,
            'emendas_com_gcs': 0,
            'valor_total_empenhado': 0.0,
            'valor_total_liquidado': 0.0,
            'valor_total_pago': 0.0,
            'erros': 0
        }
        
        try:
            # Buscar emendas da API
            emendas = self.buscar_emendas_ano(ano, limite)
            resultados['emendas_encontradas'] = len(emendas)
            
            if not emendas:
                print(f"   ⚠️ Nenhuma emenda encontrada para {ano}")
                return resultados
            
            print(f"\n💾 SALVANDO EMENDAS NO BANCO DE DADOS")
            print("-" * 50)
            
            for i, emenda_data in enumerate(emendas, 1):
                print(f"   📄 Processando {i}/{len(emendas)}: {emenda_data.get('codigoEmenda', 'N/A')}")
                
                try:
                    # Salvar emenda
                    emenda = self.salvar_emenda_transparencia(emenda_data, db)
                    if emenda:
                        resultados['emendas_salvas'] += 1
                        
                        if emenda.deputado_id:
                            resultados['emendas_com_autor'] += 1
                        
                        if emenda.gcs_url:
                            resultados['emendas_com_gcs'] += 1
                        
                        # Acumular valores
                        valor_empenhado = self.limpar_valor_monetario(emenda_data.get('valorEmpenhado', '0')) or 0
                        valor_liquidado = self.limpar_valor_monetario(emenda_data.get('valorLiquidado', '0')) or 0
                        valor_pago = self.limpar_valor_monetario(emenda_data.get('valorPago', '0')) or 0
                        
                        resultados['valor_total_empenhado'] += valor_empenhado
                        resultados['valor_total_liquidado'] += valor_liquidado
                        resultados['valor_total_pago'] += valor_pago
                    
                    # Rate limiting
                    time.sleep(0.3)  # 300ms entre registros
                    
                except Exception as e:
                    print(f"      ❌ Erro ao processar emenda: {e}")
                    resultados['erros'] += 1
                    continue
            
            # Gerar ranking
            if resultados['emendas_salvas'] > 0:
                self.gerar_ranking_emendas_transparencia(ano, db)
            
        except Exception as e:
            print(f"❌ Erro geral na coleta: {e}")
            resultados['erros'] += 1
        
        finally:
            if fechar_db:
                db.close()
        
        return resultados

    def gerar_ranking_emendas_transparencia(self, ano: int, db: Session):
        """
        Gera ranking de emendas por deputado (dados do Portal da Transparência)
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
                EmendaParlamentar.deputado_id.isnot(None),
                EmendaParlamentar.valor_emenda > 0
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
            
        except Exception as e:
            print(f"❌ Erro ao gerar ranking: {e}")
            db.rollback()

def main():
    """
    Função principal para execução standalone
    """
    print("💰 COLETA DE EMENDAS ORÇAMENTÁRIAS - Portal da Transparência")
    print("=" * 70)
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = next(get_db())
    
    try:
        coletor = ColetorEmendasTransparencia()
        
        # Coletar emendas dos anos disponíveis (2025 não tem dados na API)
        anos_disponiveis = [2024, 2023, 2022, 2021]  # Anos com dados confirmados
        limite_por_ano = 500  # Limite ampliado para cobertura completa
        
        print(f"\n⚠️  AVISO: API não possui dados de emendas de 2025")
        print(f"📅 Dados disponíveis apenas até 2024")
        print(f"🔍 Coletando dados dos anos disponíveis...")
        
        for ano in anos_disponiveis:
            print(f"\n🎯 COLETANDO EMENDAS DE {ano}")
            print("=" * 40)
            resultados = coletor.coletar_emendas_periodo(ano, limite_por_ano, db_session)
            
            print(f"\n📋 RESUMO DA COLETA - {ano}")
            print("=" * 30)
            print(f"📄 Emendas encontradas: {resultados['emendas_encontradas']}")
            print(f"💾 Emendas salvas: {resultados['emendas_salvas']}")
            print(f"👥 Com autor identificado: {resultados['emendas_com_autor']}")
            print(f"📁 Com upload GCS: {resultados['emendas_com_gcs']}")
            print(f"💰 Valor total empenhado: R$ {resultados['valor_total_empenhado']:,.2f}")
            print(f"💰 Valor total liquidado: R$ {resultados['valor_total_liquidado']:,.2f}")
            print(f"💰 Valor total pago: R$ {resultados['valor_total_pago']:,.2f}")
            print(f"❌ Erros: {resultados['erros']}")
        
        print(f"\n✅ Coleta de emendas orçamentárias concluída!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
