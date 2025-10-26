#!/usr/bin/env python3
"""
Coletor de Emendas Orçamentárias do Portal da Transparência - VERSÃO CORRIGIDA
Baseado no código validado que funcionou nos testes
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

# Importar modelos
from models.db_utils import get_db_session
from models.politico_models import Deputado
from models.emenda_models import EmendaParlamentar, DetalheEmenda, RankingEmendas

# Importar utilitários
from utils.gcs_utils import get_gcs_manager

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

class ColetorEmendasCorrigido:
    """
    Coletor corrigido baseado no código validado
    """

    def __init__(self):
        """Inicializa o coletor corrigido"""
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
        
        print(f"✅ Coletor de emendas CORRIGIDO inicializado")
        print(f"   🔑 Chave API: {self.api_key[:10]}...")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")

    def fazer_requisicao_api(self, params: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Faz requisição à API com tratamento de erros
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
            elif response.status_code == 429:
                print(f"      ⏳ Rate limit - aguardando 5 segundos...")
                time.sleep(5)
                return self.fazer_requisicao_api(params)
            else:
                print(f"      ❌ Erro HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"      ❌ Erro na requisição: {e}")
            return None

    def limpar_valor_monetario_robusto(self, valor) -> float:
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

    def buscar_deputado_por_nome_robusto(self, nome_autor: str, db: Session) -> Optional[int]:
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

    def salvar_emenda_corrigida(self, emenda_data: Dict, db: Session) -> Optional[EmendaParlamentar]:
        """
        Salva emenda com método corrigido e validado
        """
        try:
            # Verificar se já existe
            existente = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.api_camara_id == str(emenda_data['codigoEmenda'])
            ).first()
            
            if existente:
                print(f"      ⚠️ Emenda já existe: {emenda_data['codigoEmenda']}")
                return existente
            
            # Extrair dados da emenda
            codigo_emenda = emenda_data['codigoEmenda']
            ano = emenda_data['ano']
            tipo_emenda_api = emenda_data['tipoEmenda']
            autor = emenda_data['autor']
            nome_autor = emenda_data.get('nomeAutor', autor)
            
            # Mapear tipo
            tipo_mapeado = self.mapear_tipo_emenda(tipo_emenda_api)
            
            # Extrair valores com método robusto
            valor_empenhado = self.limpar_valor_monetario_robusto(emenda_data.get('valorEmpenhado'))
            valor_liquidado = self.limpar_valor_monetario_robusto(emenda_data.get('valorLiquidado'))
            valor_pago = self.limpar_valor_monetario_robusto(emenda_data.get('valorPago'))
            
            # Usar o maior valor disponível
            valor_emenda = max(valor_empenhado, valor_liquidado, valor_pago)
            
            # Buscar deputado com método robusto
            deputado_id = self.buscar_deputado_por_nome_robusto(nome_autor, db)
            
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
            self._salvar_detalhes_emenda_corrigida(emenda, emenda_data, db)
            
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

    def _salvar_detalhes_emenda_corrigida(self, emenda: EmendaParlamentar, emenda_data: Dict, db: Session):
        """Salva detalhes específicos da emenda"""
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
                    'fonte': 'API Portal da Transparência - VERSÃO CORRIGIDA',
                    'versao': '2.0'
                }
            }
            
            # Fazer upload
            if self.gcs_disponivel:
                gcs_url = self.gcs_manager.upload_emenda(dados_completos, emenda.ano, str(emenda.api_camara_id))
                
                if gcs_url:
                    print(f"      📁 Upload GCS realizado: {emenda.tipo_emenda} {emenda.numero}/{emenda.ano}")
                    return gcs_url
                else:
                    print(f"      ❌ Erro no upload GCS")
                    return None
            else:
                print(f"      ⚠️ GCS não disponível, pulando upload")
                return None
                
        except Exception as e:
            print(f"      ❌ Erro no upload GCS: {e}")
            return None

    def coletar_emendas_deputados_lista(self, lista_deputados: List[str], ano: int, db: Session) -> Dict[str, int]:
        """
        Coleta emendas para uma lista específica de deputados
        """
        print(f"\n💰 COLETANDO EMENDAS - VERSÃO CORRIGIDA")
        print("=" * 60)
        print(f"📅 Ano: {ano}")
        print(f"👥 Deputados: {len(lista_deputados)}")
        
        resultados = {
            'deputados_processados': 0,
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_autor': 0,
            'valor_total': 0.0,
            'erros': 0
        }
        
        for i, nome_deputado in enumerate(lista_deputados, 1):
            print(f"\n🎯 PROCESSANDO DEPUTADO {i}/{len(lista_deputados)}: {nome_deputado}")
            print("-" * 50)
            
            try:
                # Buscar todas as emendas do deputado
                emendas = self.buscar_todas_emendas_deputado(nome_deputado, ano)
                resultados['emendas_encontradas'] += len(emendas)
                
                if not emendas:
                    print(f"   ⚠️ Nenhuma emenda encontrada para {nome_deputado} em {ano}")
                    resultados['deputados_processados'] += 1
                    continue
                
                # Salvar cada emenda
                for j, emenda_data in enumerate(emendas, 1):
                    print(f"   📄 Salvando emenda {j}/{len(emendas)}: {emenda_data.get('codigoEmenda', 'N/A')}")
                    
                    emenda = self.salvar_emenda_corrigida(emenda_data, db)
                    if emenda:
                        resultados['emendas_salvas'] += 1
                        # Converter Decimal para float para evitar erro de tipo
                        valor_emenda = float(emenda.valor_emenda) if emenda.valor_emenda else 0.0
                        resultados['valor_total'] += valor_emenda
                        
                        if emenda.deputado_id:
                            resultados['emendas_com_autor'] += 1
                    
                    # Rate limiting
                    time.sleep(0.3)
                
                resultados['deputados_processados'] += 1
                
            except Exception as e:
                print(f"   ❌ Erro ao processar deputado {nome_deputado}: {e}")
                resultados['erros'] += 1
                continue
        
        return resultados

def main():
    """
    Função principal para teste do coletor corrigido
    """
    print("💰 COLETOR DE EMENDAS - VERSÃO CORRIGIDA")
    print("=" * 60)
    print("🎯 Baseado no código validado que funcionou nos testes")
    print("🔧 Correções aplicadas: tratamento de valores, mapeamento de nomes")
    print("=" * 60)
    
    # Usar sessão do banco
    db_session = get_db_session()
    
    try:
        coletor = ColetorEmendasCorrigido()
        
        # Testar com os deputados do teste anterior
        deputados_teste = [
            "NIKOLAS FERREIRA",
            "TABATA AMARAL", 
            "KIM KATAGUIRI",
            "CARLA ZAMBELLI"
        ]
        
        ano_teste = 2024
        
        print(f"\n🧪 TESTE COM DEPUTADOS CONHECIDOS - {ano_teste}")
        print("=" * 50)
        
        resultados = coletor.coletar_emendas_deputados_lista(deputados_teste, ano_teste, db_session)
        
        print(f"\n📋 RESUMO DO TESTE:")
        print("=" * 30)
        print(f"👥 Deputados processados: {resultados['deputados_processados']}")
        print(f"📄 Emendas encontradas: {resultados['emendas_encontradas']}")
        print(f"💾 Emendas salvas: {resultados['emendas_salvas']}")
        print(f"👥 Com autor identificado: {resultados['emendas_com_autor']}")
        print(f"💰 Valor total: R$ {resultados['valor_total']:,.2f}")
        print(f"❌ Erros: {resultados['erros']}")
        
        if resultados['valor_total'] > 0:
            print(f"\n🎉 SUCESSO! Coletor corrigido funcionando!")
            print(f"💰 Valores reais sendo salvos: R$ {resultados['valor_total']:,.2f}")
        else:
            print(f"\n⚠️ Ainda há problemas a investigar")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTE: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
