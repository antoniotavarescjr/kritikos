#!/usr/bin/env python3
"""
Script OTIMIZADO para processar PLs 2025
Com timeout reduzido, retry automático e tratamento robusto de erros
"""

import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from models.db_utils import get_db_session
from sqlalchemy import text
from utils.gcs_utils import get_gcs_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProcessadorOtimizadoPLs2025:
    """Processador otimizado com retry e timeout reduzido."""
    
    def __init__(self):
        self.gcs = get_gcs_manager()
        self.session = get_db_session()
        
        # Configurar sessão HTTP com retry
        self.http_session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.http_session.mount("http://", adapter)
        self.http_session.mount("https://", adapter)
        self.http_session.headers.update({
            'User-Agent': 'KritikosETL/1.0 (Optimized 2025)',
            'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        if not self.gcs or not self.gcs.is_available():
            raise RuntimeError("GCS não disponível")
        
        logger.info("✅ Processador OTIMIZADO de PLs 2025 inicializado")
    
    def obter_pls_2025_faltantes(self, limite: int = 50) -> list:
        """Obtém PLs 2025 que realmente não têm texto."""
        logger.info(f"🔍 Buscando PLs 2025 faltantes (limite: {limite})")
        
        query = text("""
            SELECT id, api_camara_id, tipo, numero, ano, ementa
            FROM proposicoes 
            WHERE ano = 2025 AND tipo = 'PL'
            ORDER BY data_apresentacao DESC
            LIMIT :limite
        """)
        
        result = self.session.execute(query, {'limite': limite}).fetchall()
        
        props_faltantes = []
        props_com_texto = 0
        
        for row in result:
            prop_info = {
                'id': row[0],
                'api_camara_id': row[1],
                'tipo': row[2],
                'numero': row[3],
                'ano': row[4],
                'ementa': row[5] or ''
            }
            
            # Verificação REAL no GCS (download para confirmar)
            if not self.verificar_arquivo_existe_gcs_real(prop_info):
                props_faltantes.append(prop_info)
                logger.debug(f"❌ Sem texto real: {prop_info['api_camara_id']}")
            else:
                props_com_texto += 1
                logger.debug(f"✅ Com texto real: {prop_info['api_camara_id']}")
        
        logger.info(f"📊 Encontrados {len(props_faltantes)} PLs 2025 faltantes")
        logger.info(f"📊 PLs com texto real: {props_com_texto}")
        return props_faltantes
    
    def verificar_arquivo_existe_gcs_rapido(self, prop_info: dict) -> bool:
        """Verificação rápida se arquivo existe no GCS."""
        api_id = str(prop_info['api_camara_id'])
        tipo = prop_info['tipo']
        ano = str(prop_info['ano'])
        
        path = f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto-completo.txt"
        
        try:
            # Verificação rápida sem download completo
            blob = self.gcs.bucket.blob(path)
            return blob.exists()
        except:
            return False
    
    def verificar_arquivo_existe_gcs_real(self, prop_info: dict) -> bool:
        """Verificação REAL se arquivo existe e tem conteúdo no GCS."""
        api_id = str(prop_info['api_camara_id'])
        tipo = prop_info['tipo']
        ano = str(prop_info['ano'])
        
        path = f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto-completo.txt"
        
        try:
            # Download real para verificar conteúdo
            blob_data = self.gcs.download_text(path, compressed=False)
            return blob_data is not None and len(blob_data.strip()) > 100
        except:
            return False
    
    def obter_url_inteiro_teor_rapido(self, api_id: str) -> str:
        """Obtém URL do inteiro teor com timeout reduzido e tratamento robusto."""
        try:
            url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{api_id}"
            
            response = self.http_session.get(url, timeout=10)  # Timeout reduzido
            response.raise_for_status()
            
            # Verificar content-type
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                logger.warning(f"⚠️ API não retornou JSON para {api_id}: {content_type}")
                return None
            
            # Verificar se resposta está vazia
            if not response.text.strip():
                logger.warning(f"⚠️ API retornou resposta vazia para {api_id}")
                return None
            
            # Tentar fazer parse do JSON
            try:
                dados = response.json()
            except ValueError as json_error:
                logger.warning(f"⚠️ JSON inválido para {api_id}: {str(json_error)[:100]}")
                logger.debug(f"Resposta recebida: {response.text[:200]}...")
                return None
            
            url_inteiro_teor = dados.get('dados', {}).get('urlInteiroTeor')
            
            if url_inteiro_teor:
                logger.debug(f"✅ URL inteiro teor: {url_inteiro_teor}")
            else:
                logger.warning(f"⚠️ Sem URL inteiro teor para {api_id}")
                # Verificar se há outros campos úteis
                status = dados.get('dados', {}).get('statusProposicao', {})
                logger.debug(f"Status da proposição {api_id}: {status}")
            
            return url_inteiro_teor
            
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout na API para {api_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Erro de requisição para {api_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao obter URL inteiro teor {api_id}: {e}")
            return None
    
    def baixar_pdf_rapido(self, url_pdf: str, api_id: str) -> bytes:
        """Baixa PDF com timeout reduzido e streaming."""
        try:
            logger.info(f"📄 Baixando PDF: {url_pdf}")
            
            response = self.http_session.get(url_pdf, timeout=15, stream=True)
            response.raise_for_status()
            
            # Verificar content-type
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' not in content_type:
                logger.warning(f"⚠️ URL não retorna PDF: {content_type}")
                return None
            
            # Download em chunks para evitar travamento
            content = b''
            total_size = 0
            max_size = 10 * 1024 * 1024  # 10MB max
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk
                    total_size += len(chunk)
                    
                    # Limitar tamanho para evitar problemas
                    if total_size > max_size:
                        logger.warning(f"⚠️ PDF muito grande, truncando: {total_size} bytes")
                        break
            
            logger.debug(f"✅ PDF baixado: {len(content)} bytes")
            return content
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout no download do PDF {api_id}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao baixar PDF {api_id}: {e}")
            return None
    
    def extrair_texto_pdf_simples(self, pdf_bytes: bytes, api_id: str) -> str:
        """Extração simples de texto com fallback."""
        if not pdf_bytes:
            return None
        
        # Tentar pdfplumber primeiro
        texto = self._extrair_pdfplumber_simples(pdf_bytes, api_id)
        
        # Fallback para PyPDF2
        if not texto:
            texto = self._extrair_pypdf2_simples(pdf_bytes, api_id)
        
        if texto:
            texto = self._limpar_texto_simples(texto)
            logger.debug(f"✅ Texto extraído: {len(texto)} caracteres")
        
        return texto
    
    def _extrair_pdfplumber_simples(self, pdf_bytes: bytes, api_id: str) -> str:
        """Extração simples com pdfplumber."""
        try:
            import io
            import pdfplumber
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texto_paginas = []
                
                for i, page in enumerate(pdf.pages[:10]):  # Limitar a 10 páginas
                    try:
                        texto_pagina = page.extract_text()
                        if texto_pagina and texto_pagina.strip():
                            texto_paginas.append(texto_pagina.strip())
                    except:
                        continue
                
                return '\n\n'.join(texto_paginas)
                
        except Exception as e:
            logger.debug(f"Erro pdfplumber {api_id}: {e}")
            return None
    
    def _extrair_pypdf2_simples(self, pdf_bytes: bytes, api_id: str) -> str:
        """Extração simples com PyPDF2."""
        try:
            import io
            import PyPDF2
            
            with io.BytesIO(pdf_bytes) as pdf_stream:
                reader = PyPDF2.PdfReader(pdf_stream)
                texto_paginas = []
                
                for i, page in enumerate(reader.pages[:10]):  # Limitar a 10 páginas
                    try:
                        texto_pagina = page.extract_text()
                        if texto_pagina and texto_pagina.strip():
                            texto_paginas.append(texto_pagina.strip())
                    except:
                        continue
                
                return '\n\n'.join(texto_paginas)
                
        except Exception as e:
            logger.debug(f"Erro PyPDF2 {api_id}: {e}")
            return None
    
    def _limpar_texto_simples(self, texto: str) -> str:
        """Limpeza simples de texto."""
        if not texto:
            return ""
        
        # Remover caracteres problemáticos
        texto = texto.replace('\x00', '').replace('\x0b', '')
        
        # Normalizar espaços
        texto = ' '.join(texto.split())
        
        # Limitar tamanho
        if len(texto) > 20000:
            texto = texto[:20000] + "...[truncado]"
        
        return texto.strip()
    
    def processar_pl_rapido(self, prop_info: dict) -> bool:
        """Processa um PL de forma otimizada."""
        api_id = str(prop_info['api_camara_id'])
        
        try:
            logger.info(f"📄 Processando {prop_info['tipo']} {prop_info['numero']}/{prop_info['ano']} (ID: {api_id})")
            
            # Passo 1: Obter URL do inteiro teor
            url_inteiro_teor = self.obter_url_inteiro_teor_rapido(api_id)
            if not url_inteiro_teor:
                logger.warning(f"⚠️ Sem URL inteiro teor para {api_id}")
                return False
            
            # Passo 2: Baixar PDF
            pdf_bytes = self.baixar_pdf_rapido(url_inteiro_teor, api_id)
            if not pdf_bytes:
                logger.warning(f"⚠️ Não foi possível baixar PDF para {api_id}")
                return False
            
            # Passo 3: Extrair texto
            texto = self.extrair_texto_pdf_simples(pdf_bytes, api_id)
            if not texto:
                logger.warning(f"⚠️ Não foi possível extrair texto de {api_id}")
                return False
            
            # Passo 4: Upload para GCS
            tipo = prop_info['tipo']
            ano = prop_info['ano']
            filename = f"{tipo}-{api_id}-texto-completo.txt"
            blob_path = f"proposicoes/{ano}/{tipo}/texto-completo/{filename}"
            
            if self.gcs.upload_text(texto, blob_path, compress=True):
                # Atualizar banco
                gcs_url = f"https://storage.googleapis.com/{self.gcs.bucket_name}/{blob_path}"
                
                self.session.execute(text("""
                    UPDATE proposicoes 
                    SET gcs_url = :gcs_url
                    WHERE id = :prop_id
                """), {'gcs_url': gcs_url, 'prop_id': prop_info['id']})
                self.session.commit()
                
                logger.info(f"✅ PL processado: {blob_path} ({len(texto)} caracteres)")
                return True
            else:
                logger.error(f"❌ Falha no upload para {api_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar PL {api_id}: {e}")
            return False
    
    def processar_lote_otimizado(self, limite: int = 50, delay_segundos: float = 0.5) -> dict:
        """Processa lote de forma otimizada."""
        logger.info(f"🚀 Processando lote otimizado (limite: {limite})")
        
        props_faltantes = self.obter_pls_2025_faltantes(limite)
        
        if not props_faltantes:
            logger.info("✅ Todos os PLs 2025 já têm texto!")
            return {'total': 0, 'sucesso': 0, 'falha': 0, 'taxa_sucesso': 100.0}
        
        stats = {
            'total': len(props_faltantes),
            'sucesso': 0,
            'falha': 0,
            'erros': []
        }
        
        for i, prop_info in enumerate(props_faltantes, 1):
            logger.info(f"📄 Processando {i}/{stats['total']}: {prop_info['tipo']} {prop_info['numero']}/{prop_info['ano']}")
            
            if self.processar_pl_rapido(prop_info):
                stats['sucesso'] += 1
            else:
                stats['falha'] += 1
                stats['erros'].append(f"Falha: {prop_info['api_camara_id']}")
            
            # Rate limiting reduzido
            if delay_segundos > 0:
                time.sleep(delay_segundos)
        
        stats['taxa_sucesso'] = (stats['sucesso'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        logger.info(f"📊 Lote concluído: {stats['sucesso']}/{stats['total']} ({stats['taxa_sucesso']:.1f}%)")
        return stats


def main():
    """Função principal otimizada."""
    try:
        logger.info("🚀 INICIANDO PROCESSAMENTO OTIMIZADO DE PLs 2025")
        logger.info("=" * 70)
        
        processador = ProcessadorOtimizadoPLs2025()
        
        # Configurações otimizadas
        TAMANHO_LOTE = 100  # Lote maior para processamento completo
        DELAY_SEGUNDOS = 0.5  # Delay reduzido
        LOTES_MAXIMOS = 60  # Processar até completar todos
        
        total_processado = 0
        total_sucesso = 0
        total_falha = 0
        
        for lote_num in range(1, LOTES_MAXIMOS + 1):
            logger.info(f"\n🚀 PROCESSANDO LOTE OTIMIZADO {lote_num}/{LOTES_MAXIMOS}")
            logger.info("-" * 60)
            
            stats = processador.processar_lote_otimizado(
                limite=TAMANHO_LOTE, 
                delay_segundos=DELAY_SEGUNDOS
            )
            
            total_processado += stats['total']
            total_sucesso += stats['sucesso']
            total_falha += stats['falha']
            
            taxa_geral = (total_sucesso / total_processado * 100) if total_processado > 0 else 0
            logger.info(f"📊 Progresso do lote {lote_num}: {stats['sucesso']}/{stats['total']} ({stats['taxa_sucesso']:.1f}%)")
            logger.info(f"📈 Progresso geral: {total_sucesso}/{total_processado} ({taxa_geral:.1f}%)")
            
            if stats['total'] == 0:
                logger.info("✅ Todos os PLs 2025 foram processados!")
                break
            
            # Pausa reduzida
            if lote_num < LOTES_MAXIMOS:
                logger.info(f"⏸️ Pausa de 2 segundos...")
                time.sleep(2)
        
        # Relatório final
        logger.info("\n" + "=" * 70)
        logger.info("📋 RELATÓRIO FINAL DO PROCESSAMENTO OTIMIZADO")
        logger.info("=" * 70)
        
        taxa_final = (total_sucesso / total_processado * 100) if total_processado > 0 else 0
        
        print(f"📊 Total processado: {total_processado} PLs 2025")
        print(f"✅ Total sucesso: {total_sucesso}")
        print(f"❌ Total falhas: {total_falha}")
        print(f"📈 Taxa de sucesso geral: {taxa_final:.1f}%")
        
        logger.info("\n✅ PROCESSAMENTO OTIMIZADO CONCLUÍDO")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Processamento interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)


if __name__ == "__main__":
    main()
