#!/usr/bin/env python3
"""
Coletor de Proposições Parlamentares - ABORDAGEM JSON
Download do JSON completo da Câmara dos Deputados e processamento estruturado
Foco em proposições de alto impacto com documentos completos
"""

import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Iterator
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações
sys.path.append(str(Path(__file__).parent))
from config import get_config

# Importar utilitários
from utils.gcs_utils import get_gcs_manager
from utils.cache_utils import get_cache_manager

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.proposicao_models import Proposicao, Autoria

# Importar ETL utils
from etl_utils import ETLBase, DateParser, ProgressLogger, DatabaseManager

class ColetorProposicoesJSON(ETLBase):
    """
    Coletor de proposições usando JSON completo da Câmara dos Deputados
    Abordagem: Download único + Processamento em lote + Download de documentos
    """
    
    def __init__(self):
        """Inicializa o coletor usando ETLBase"""
        super().__init__('proposicoes_json')
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager.is_available()
        
        # Inicializar Cache Manager
        self.cache_manager = get_cache_manager(cache_dir="cache/proposicoes_json", ttl_hours=6)
        
        # Carregar configurações específicas
        self.config = get_config('hackathon', 'proposicoes')
        self.proposicoes_config = self.config
        
        print(f"✅ Coletor de Proposições JSON inicializado")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")
        print(f"   🗄️ Cache ativo: {self.cache_manager.cache_dir}")
        print(f"   📋 JSON URL: {self.proposicoes_config.get('json_url')}")
        print(f"   🎯 Tipos prioritários: {', '.join(self.proposicoes_config.get('tipos_prioritarios', []))}")
        print(f"   📅 Meses foco: {self.proposicoes_config.get('meses_foco', [])}")
        
        # Controle de downloads paralelos
        self.download_semaphore = threading.Semaphore(
            self.proposicoes_config.get('max_downloads_paralelos', 10)
        )
    
    def _fazer_requisicao_json(self, url: str, timeout: int = None) -> Optional[Dict]:
        """
        Faz requisição para download do JSON com cache
        
        Args:
            url: URL do JSON
            timeout: Timeout personalizado
            
        Returns:
            Dict: Dados do JSON ou None
        """
        if timeout is None:
            timeout = self.proposicoes_config.get('json_download_timeout', 300)
        
        # Verificar cache primeiro
        cached_response = self.cache_manager.get_cached_api_response(url, {})
        if cached_response:
            print(f"      📦 Cache hit JSON: {url}")
            return cached_response
        
        try:
            print(f"      📥 Baixando JSON: {url}")
            print(f"      ⏱️ Timeout: {timeout}s")
            
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Verificar se é JSON válido
            try:
                data = response.json()
                
                # Salvar no cache
                self.cache_manager.cache_api_response(url, {}, data, ttl_hours=6)
                
                print(f"      ✅ JSON baixado com sucesso ({len(response.content)} bytes)")
                return data
                
            except json.JSONDecodeError as e:
                print(f"      ❌ Erro ao decodificar JSON: {e}")
                print(f"      📄 Conteúdo (primeiros 200 chars): {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"      ❌ Erro na requisição JSON: {e}")
            return None
    
    def _baixar_json_com_retry(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Baixa JSON com retry e backoff exponencial
        
        Args:
            url: URL do JSON
            max_retries: Número máximo de tentativas
            
        Returns:
            Dict: Dados do JSON ou None
        """
        import time
        import random
        
        for tentativa in range(max_retries):
            try:
                # Tentar download normal
                return self._baixar_json_streaming(url)
                
            except Exception as e:
                if tentativa == max_retries - 1:
                    print(f"      ❌ Falha após {max_retries} tentativas: {e}")
                    raise e
                
                # Backoff exponencial com jitter
                delay = (2 ** tentativa) + random.uniform(0, 1)
                print(f"      ⚠️ Tentativa {tentativa + 1} falhou, retry em {delay:.1f}s: {e}")
                time.sleep(delay)
        
        return None
    
    def _baixar_json_streaming(self, url: str) -> Optional[Dict]:
        """
        Baixa o JSON completo usando streaming para não sobrecarregar memória
        
        Args:
            url: URL do JSON
            
        Returns:
            Dict: Dados do JSON ou None
        """
        try:
            print(f"📥 Iniciando download streaming do JSON...")
            print(f"   📡 URL: {url}")
            
            response = self.session.get(url, stream=True, timeout=self.proposicoes_config.get('json_download_timeout', 300))
            response.raise_for_status()
            
            # Ler o conteúdo em chunks
            content = b''
            total_size = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                total_size += len(chunk)
                
                # Mostrar progresso
                if total_size % (1024 * 1024) == 0:  # A cada MB
                    print(f"      📊 Baixado: {total_size // (1024 * 1024)} MB")
            
            print(f"      ✅ Download concluído: {total_size} bytes")
            
            # Fazer parse do JSON
            try:
                data = json.loads(content.decode('utf-8'))
                print(f"      ✅ JSON parseado com sucesso")
                return data
            except json.JSONDecodeError as e:
                print(f"      ❌ Erro ao decodificar JSON: {e}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro no download streaming: {e}")
            return None
    
    def _usar_cache_persistente(self, url: str) -> Optional[Dict]:
        """
        Usa cache persistente para evitar downloads duplicados
        
        Args:
            url: URL do JSON
            
        Returns:
            Dict: Dados do JSON ou None
        """
        try:
            import hashlib
            
            # Criar hash da URL para nome de arquivo
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_file = self.cache_manager.cache_dir / f"json_{url_hash}.json"
            
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Verificar se o cache é recente (menos de 6 horas)
                    cache_time = datetime.fromisoformat(data.get('metadata', {}).get('cache_time', ''))
                    if (datetime.now() - cache_time).total_seconds() < 21600:  # 6 horas
                        print(f"      📦 Cache persistente hit: {url}")
                        return data
                    else:
                        print(f"      📦 Cache persistente expirado: {url}")
                        
                except Exception as e:
                    print(f"      ⚠️ Erro ao ler cache persistente: {e}")
            
            return None
            
        except Exception as e:
            print(f"      ⚠️ Erro ao usar cache persistente: {e}")
            return None
    
    def _salvar_cache_persistente(self, url: str, data: Dict) -> bool:
        """
        Salva dados no cache persistente
        
        Args:
            url: URL do JSON
            data: Dados do JSON
            
        Returns:
            bool: True se sucesso
        """
        try:
            import hashlib
            
            # Criar hash da URL para nome de arquivo
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_file = self.cache_manager.cache_dir / f"json_{url_hash}.json"
            
            # Adicionar metadados de cache
            data['metadata'] = data.get('metadata', {})
            data['metadata']['cache_time'] = datetime.now().isoformat()
            data['metadata']['url'] = url
            data['metadata']['source'] = 'coletor_json'
            
            # Salvar no cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"      💾 Cache persistente salvo: {url}")
            return True
            
        except Exception as e:
            print(f"      ⚠️ Erro ao salvar cache persistente: {e}")
            return False
    
    def _filtrar_proposicoes(self, proposicoes: List[Dict]) -> List[Dict]:
        """
        Filtra proposições baseado nos critérios do hackathon
        Versão otimizada para usar apenas tipos prioritários disponíveis no storage
        
        Args:
            proposicoes: Lista de proposições do JSON
            
        Returns:
            List[Dict]: Lista filtrada de proposições
        """
        print(f"🔍 Filtrando {len(proposicoes)} proposições...")
        
        # Obter configurações de filtro
        meses_foco = self.proposicoes_config.get('meses_foco', [])
        # Usar apenas tipos prioritários que temos no storage após limpeza
        tipos_prioritarios = ['PL', 'PLP', 'MPV', 'PLV', 'PRC']  # Removidos: PEC, PDC (não encontrados)
        
        print(f"      📋 Tipos prioritários: {', '.join(tipos_prioritarios)}")
        print(f"      📅 Meses foco: {meses_foco}")
        
        filtradas = []
        estatisticas = {
            'total_original': len(proposicoes),
            'por_tipo': {},
            'por_mes': {},
            'aprovadas': 0,
            'tipos_removidos': set()
        }
        
        for prop in proposicoes:
            try:
                # Extrair dados básicos
                tipo = prop.get('siglaTipo', '')
                data_apresentacao = prop.get('dataApresentacao', '')
                
                # Contar estatísticas
                estatisticas['por_tipo'][tipo] = estatisticas['por_tipo'].get(tipo, 0) + 1
                
                if data_apresentacao:
                    mes = int(data_apresentacao[5:7])  # Formato YYYY-MM-DD
                    estatisticas['por_mes'][mes] = estatisticas['por_mes'].get(mes, 0) + 1
                
                # Verificar se está no período foco
                if not self._esta_no_periodo_foco(data_apresentacao, meses_foco):
                    continue
                
                # Verificar se é tipo prioritário (CRÍTICO)
                if tipo not in tipos_prioritarios:
                    estatisticas['tipos_removidos'].add(tipo)
                    continue
                
                # Verificar status
                status = prop.get('statusProposicao', {}).get('descricao', '')
                if status and 'aprovada' in status.lower():
                    estatisticas['aprovadas'] += 1
                
                filtradas.append(prop)
                
            except Exception as e:
                print(f"      ⚠️ Erro ao filtrar proposição: {e}")
                continue
        
        print(f"      📊 Estatísticas da filtragem:")
        print(f"         📋 Tipos encontrados: {dict(sorted(estatisticas['por_tipo'].items()))}")
        print(f"         📅 Meses encontrados: {dict(sorted(estatisticas['por_mes'].items()))}")
        print(f"         ✅ Aprovadas: {estatisticas['aprovadas']}")
        
        if estatisticas['tipos_removidos']:
            print(f"         🗑️  Tipos removidos: {list(sorted(estatisticas['tipos_removidos']))}")
        
        print(f"      📄 Proposições filtradas: {len(filtradas)} (de {estatisticas['total_original']})")
        print(f"      📊 Taxa de retenção: {(len(filtradas)/estatisticas['total_original']*100):.1f}%")
        
        return filtradas
    
    def _esta_no_periodo_foco(self, data_str: str, meses_foco: List[int]) -> bool:
        """
        Verifica se a data está no período foco
        
        Args:
            data_str: Data no formato YYYY-MM-DD
            meses_foco: Lista de meses foco
            
        Returns:
            bool: True se está no período foco
        """
        if not data_str or not meses_foco:
            return False
        
        try:
            mes = int(data_str[5:7])  # Formato YYYY-MM-DD
            return mes in meses_foco
        except (ValueError, IndexError):
            return False
    
    def _ordenar_proposicoes(self, proposicoes: List[Dict]) -> List[Dict]:
        """
        Ordena proposições por prioridade e data
        
        Args:
            proposicoes: Lista de proposições
            
        Returns:
            List[Dict]: Lista ordenada
        """
        prioridade_tipos = self.proposicoes_config.get('prioridade_tipos', {})
        
        def chave_ordenacao(prop):
            tipo = prop.get('siglaTipo', '')
            prioridade = prioridade_tipos.get(tipo, 999)
            data = prop.get('dataApresentacao', '')
            
            # Ordenar por prioridade (menor = mais importante) e data (mais recente primeiro)
            return (prioridade, data, prop.get('id', ''))
        
        ordenadas = sorted(proposicoes, key=chave_ordenacao)
        print(f"      📊 Proposições ordenadas por prioridade e data")
        
        return ordenadas
    
    def _baixar_documento(self, url_documento: str, prop_data: Dict) -> Optional[str]:
        """
        Baixa documento de uma proposição
        
        Args:
            url_documento: URL do documento
            prop_data: Dados da proposição
            
        Returns:
            str: Conteúdo do documento ou None
        """
        if not url_documento:
            return None
        
        try:
            tipo = prop_data.get('siglaTipo', '')
            
            # Verificar se é tipo prioritário para download
            # Usar apenas tipos que temos no storage após limpeza
            tipos_foco = ['PL', 'PLP', 'MPV']  # Apenas estes têm documentos no storage
            if tipo not in tipos_foco:
                return None
            
            print(f"      📄 Baixando documento: {tipo} {prop_data.get('numero', '?')}/{prop_data.get('ano', '?')}")
            
            with self.download_semaphore:
                # Usar headers de navegador para contornar bloqueios
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/pdf',
                    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                timeout = self.proposicoes_config.get('document_download_timeout', 30)
                response = self.session.get(url_documento, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                # Verificar se é PDF pelo content-type
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/pdf' in content_type:
                    # Tratar como PDF binário
                    content_bytes = response.content
                    
                    # Verificar se é PDF válido
                    if content_bytes.startswith(b'%PDF'):
                        print(f"         ✅ PDF baixado ({len(content_bytes)} bytes)")
                        return content_bytes.decode('latin-1')
                    else:
                        print(f"         ❌ Conteúdo não é PDF válido")
                        return None
                else:
                    # Tratar como HTML/texto
                    content = response.text
                    
                    # Indicadores de que temos o conteúdo correto
                    indicadores = ['proposição', 'proposicao', 'art.', 'caput', 'parágrafo']
                    
                    if any(indicador in content.lower() for indicador in indicadores):
                        print(f"         ✅ HTML baixado ({len(content)} caracteres)")
                        return content
                    else:
                        print(f"         ❌ Conteúdo não parece ser o texto da proposição")
                        return None
                        
        except Exception as e:
            print(f"      ❌ Erro ao baixar documento: {e}")
            return None
    
    def _upload_para_gcs(self, prop_data: Dict, documento: str = None) -> Optional[str]:
        """
        Faz upload dos dados para o Google Cloud Storage
        
        Args:
            prop_data: Dados da proposição
            documento: Conteúdo do documento (opcional)
            
        Returns:
            str: URL do objeto no GCS ou None
        """
        if not self.gcs_disponivel:
            print(f"      ⚠️ GCS não disponível, pulando upload")
            return None
        
        try:
            # Preparar dados completos
            dados_completos = {
                'proposicao': prop_data,
                'documento': documento,
                'metadados': {
                    'data_coleta': datetime.now().isoformat(),
                    'fonte': 'JSON Câmara dos Deputados',
                    'versao': '1.0',
                    'hackathon': '2025'
                }
            }
            
            # Extrair informações para nome do arquivo
            tipo = prop_data.get('siglaTipo', 'UNKNOWN')
            numero = prop_data.get('numero', 0)
            ano = prop_data.get('ano', 2025)
            api_id = str(prop_data.get('id', 'unknown'))
            
            # Upload de metadados
            gcs_url = self.gcs_manager.upload_proposicao(
                dados_completos, ano, tipo, api_id, documento
            )
            
            if gcs_url:
                print(f"      📁 Upload GCS realizado: {gcs_url}")
                return gcs_url
            else:
                print(f"      ❌ Erro no upload GCS")
                return None
                
        except Exception as e:
            print(f"      ❌ Erro no upload GCS: {e}")
            return None
    
    def _mapear_deputado(self, autor_data: Dict, db: Session) -> Optional[int]:
        """
        Mapeia autor para ID do deputado no banco
        
        Args:
            autor_data: Dados do autor da API
            db: Sessão do banco
            
        Returns:
            int: ID do deputado ou None
        """
        if not autor_data:
            return None
        
        # Se for deputado, buscar por ID da API
        if autor_data.get('tipo') == 'Deputado':
            api_id = autor_data.get('codTipo', 0)
            if api_id:
                deputado = db.query(Deputado).filter(
                    Deputado.api_camara_id == api_id
                ).first()
                if deputado:
                    return deputado.id
        
        # Tentar buscar por nome
        nome = autor_data.get('nome')
        if nome:
            deputado = db.query(Deputado).filter(
                Deputado.nome.ilike(f"%{nome}%")
            ).first()
            if deputado:
                return deputado.id
        
        return None
    
    def _salvar_proposicao(self, prop_data: Dict, db: Session) -> Optional[Proposicao]:
        """
        Salva proposição no banco com dados completos no GCS
        
        Args:
            prop_data: Dados da proposição
            db: Sessão do banco
            
        Returns:
            Proposicao: Proposição salva ou None
        """
        try:
            # Verificar se já existe
            existente = db.query(Proposicao).filter(
                Proposicao.api_camara_id == prop_data.get('id')
            ).first()
            
            if existente:
                print(f"      ⏭️ Proposição já existe: {prop_data.get('siglaTipo', 'UNKNOWN')} {prop_data.get('numero', '?')}/{prop_data.get('ano', '?')}")
                return existente
            
            # Baixar documento se disponível
            documento = None
            url_documento = prop_data.get('urlInteiroTeor')
            if url_documento and self.proposicoes_config.get('baixar_documentos', True):
                documento = self._baixar_documento(url_documento, prop_data)
            
            # Upload para GCS se disponível
            gcs_url = self._upload_para_gcs(prop_data, documento)
            
            # Criar proposição no banco
            proposicao = Proposicao(
                api_camara_id=prop_data.get('id'),
                tipo=prop_data.get('siglaTipo', 'UNKNOWN'),
                numero=int(prop_data.get('numero', 0)),
                ano=int(prop_data.get('ano', 2025)),
                ementa=prop_data.get('ementa', ''),
                explicacao=prop_data.get('explicacaoEmenta'),
                data_apresentacao=DateParser.parse_date(prop_data.get('dataApresentacao')),
                situacao=prop_data.get('statusProposicao', {}).get('descricao'),
                link_inteiro_teor=prop_data.get('urlInteiroTeor'),
                keywords=prop_data.get('keywords', []),
                gcs_url=gcs_url
            )
            
            db.add(proposicao)
            db.flush()  # Para obter o ID
            
            # Buscar e salvar autores
            autores = prop_data.get('autores', [])
            if autores:
                for autor_data in autores:
                    deputado_id = self._mapear_deputado(autor_data, db)
                    if deputado_id:
                        autoria = Autoria(
                            proposicao_id=proposicao.id,
                            deputado_id=deputado_id,
                            tipo_autoria=autor_data.get('tipo', 'Autor'),
                            ordem=autor_data.get('ordemAssinatura', 1)
                        )
                        db.add(autoria)
            
            db.commit()
            
            print(f"      ✅ Proposição salva: {proposicao.tipo} {proposicao.numero}/{proposicao.ano}")
            if documento:
                print(f"         📄 Documento baixado ({len(documento)} chars)")
            if gcs_url:
                print(f"         📁 Upload GCS realizado")
            
            return proposicao
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar proposição: {e}")
            db.rollback()
            return None
    
    def coletar_proposicoes_json(self, db: Session) -> Dict[str, int]:
        """
        Coleta proposições usando abordagem JSON
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            Dict: Resultados da coleta
        """
        print(f"\n📄 COLETANDO PROPOSIÇÕES - ABORDAGEM JSON")
        print("=" * 50)
        print(f"🔧 Usando JSON completo da Câmara dos Deputados")
        print(f"📡 URL: {self.proposicoes_config.get('json_url')}")
        
        resultados = {
            'proposicoes_encontradas': 0,
            'proposicoes_filtradas': 0,
            'proposicoes_salvas': 0,
            'documentos_baixados': 0,
            'uploads_gcs': 0,
            'autores_mapeados': 0,
            'erros': 0,
            'tipos_coletados': set(),
            'meses_coletados': set()
        }
        
        # Etapa 1: Download do JSON completo com cache e retry
        json_url = self.proposicoes_config.get('json_url')
        if not json_url:
            print(f"❌ URL do JSON não configurada")
            return resultados
        
        print(f"\n📥 ETAPA 1: Download do JSON completo")
        
        # Tentar cache persistente primeiro
        if self.proposicoes_config.get('usar_cache_persistente', True):
            print(f"      📦 Verificando cache persistente...")
            dados_json = self._usar_cache_persistente(json_url)
        
        # Se não tiver cache, baixar com retry
        if not dados_json:
            print(f"      📥 Baixando JSON com retry e backoff...")
            max_retries = self.proposicoes_config.get('max_retries', 3)
            dados_json = self._baixar_json_com_retry(json_url, max_retries)
        
        # Salvar no cache persistente se disponível
        if dados_json and self.proposicoes_config.get('usar_cache_persistente', True):
            print(f"      💾 Salvando em cache persistente...")
            self._salvar_cache_persistente(json_url, dados_json)
        
        if not dados_json:
            print(f"❌ Falha no download do JSON")
            return resultados
        
        # Extrair lista de proposições
        proposicoes_brutas = dados_json.get('dados', [])
        resultados['proposicoes_encontradas'] = len(proposicoes_brutas)
        
        print(f"      📊 Total de proposições no JSON: {resultados['proposicoes_encontradas']}")
        
        # Etapa 2: Filtragem
        print(f"\n🔍 ETAPA 2: Filtragem por período e tipo")
        proposicoes_filtradas = self._filtrar_proposicoes(proposicoes_brutas)
        resultados['proposicoes_filtradas'] = len(proposicoes_filtradas)
        
        # Etapa 3: Ordenação
        print(f"\n📊 ETAPA 3: Ordenação por prioridade")
        proposicoes_ordenadas = self._ordenar_proposicoes(proposicoes_filtradas)
        
        # Etapa 4: Limitar se necessário
        limite_total = self.proposicoes_config.get('limite_total', 15000)
        if len(proposicoes_ordenadas) > limite_total:
            proposicoes_ordenadas = proposicoes_ordenadas[:limite_total]
            print(f"      🎯 Limitado a {limite_total} proposições")
        
        # Etapa 5: Processamento e salvamento
        print(f"\n💾 ETAPA 4: Processamento e salvamento")
        print(f"      📄 Processando {len(proposicoes_ordenadas)} proposições...")
        
        for i, prop_data in enumerate(proposicoes_ordenadas, 1):
            try:
                # Coletar estatísticas
                tipo = prop_data.get('siglaTipo', 'UNKNOWN')
                data_apresentacao = prop_data.get('dataApresentacao', '')
                
                if tipo != 'UNKNOWN':
                    resultados['tipos_coletados'].add(tipo)
                
                if data_apresentacao:
                    mes = int(data_apresentacao[5:7])
                    resultados['meses_coletados'].add(mes)
                
                print(f"      📄 Processando {i}/{len(proposicoes_ordenadas)}: {tipo} {prop_data.get('numero', '?')}/{prop_data.get('ano', '?')}")
                
                # Salvar proposição
                proposicao = self._salvar_proposicao(prop_data, db)
                if proposicao:
                    resultados['proposicoes_salvas'] += 1
                    
                    # Contar autores
                    if hasattr(proposicao, 'autores'):
                        resultados['autores_mapeados'] += len(proposicao.autores)
                    
                    # Contar documentos e uploads
                    if hasattr(proposicao, 'gcs_url') and proposicao.gcs_url:
                        resultados['uploads_gcs'] += 1
                    
                    # Verificar se tem documento (baseado no tamanho do GCS URL)
                    if hasattr(proposicao, 'gcs_url') and proposicao.gcs_url and 'documents' in proposicao.gcs_url:
                        resultados['documentos_baixados'] += 1
                
                # Progresso
                if i % 50 == 0 or i == len(proposicoes_ordenadas):
                    progresso = (i / len(proposicoes_ordenadas)) * 100
                    print(f"      📊 Progresso: {progresso:.1f}% - {resultados['proposicoes_salvas']} salvas")
                
            except Exception as e:
                print(f"      ❌ Erro ao processar proposição {i}: {e}")
                resultados['erros'] += 1
                continue
        
        # Converter sets para listas para JSON serialização
        resultados['tipos_coletados'] = list(resultados['tipos_coletados'])
        resultados['meses_coletados'] = sorted(list(resultados['meses_coletados']))
        
        return resultados
    
    def gerar_resumo_coleta(self, db: Session) -> bool:
        """
        Gera resumo estatístico da coleta
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            bool: True se sucesso
        """
        try:
            print(f"\n📊 GERANDO RESUMO DA COLETA - PROPOSIÇÕES JSON")
            print("=" * 40)
            
            # Contar proposições por tipo
            from sqlalchemy import func
            
            resumo = db.query(
                Proposicao.tipo,
                func.count(Proposicao.id).label('quantidade'),
                func.count(Proposicao.gcs_url).label('com_gcs')
            ).filter(
                Proposicao.ano == 2025
            ).group_by(Proposicao.tipo).all()
            
            print(f"📋 Resumo por tipo:")
            for tipo, quantidade, com_gcs in sorted(resumo, key=lambda x: x[1], reverse=True):
                print(f"   • {tipo}: {quantidade} proposições ({com_gcs} no GCS)")
            
            # Total geral
            total = db.query(func.count(Proposicao.id)).filter(Proposicao.ano == 2025).scalar()
            total_gcs = db.query(func.count(Proposicao.id)).filter(
                and_(Proposicao.ano == 2025, Proposicao.gcs_url.isnot(None))
            ).scalar()
            
            print(f"\n📈 Totais:")
            print(f"   • Total de proposições: {total}")
            print(f"   • No GCS: {total_gcs}")
            print(f"   • Taxa de armazenamento: {(total_gcs/total*100):.1f}%" if total > 0 else "   • Taxa de armazenamento: 0%")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao gerar resumo: {e}")
            return False
    
    def _extrair_tipo_documento(self, blob_name: str) -> str:
        """
        Extrai o tipo do documento do caminho do blob
        Método para teste de extração de tipos
        
        Args:
            blob_name: Nome do blob no formato "proposicoes/2025/PL/PL_12345_2025.json"
            
        Returns:
            str: Tipo do documento (PL, PEC, REQ, etc.)
        """
        try:
            # Estrutura real: proposicoes/2025/TIPO/...
            partes = blob_name.split('/')
            
            if len(partes) >= 3 and partes[0] == 'proposicoes':
                return partes[2]  # Pega "PL" de "proposicoes/2025/PL/..."
            else:
                return 'OUTRO'
                
        except Exception:
            return 'OUTRO'
    
    def coletar_proposicoes_com_fallback(self, db: Session) -> Dict[str, int]:
        """
        Coleta proposições com fallback automático
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            Dict: Resultados da coleta
        """
        try:
            # Tentar coletor JSON corrigido
            print("📄 Tentando coletor JSON corrigido...")
            resultados = self.coletar_proposicoes_json(db)
            
            if resultados and resultados.get('proposicoes_salvas', 0) > 0:
                print("✅ Coletor JSON funcionou!")
                return resultados
            else:
                print("⚠️ Coletor JSON falhou, usando fallback...")
                # Fallback para coletor antigo
                from etl.coleta_proposicoes import ColetorProposicoes
                coletor_antigo = ColetorProposicoes()
                return coletor_antigo.coletar_proposicoes_periodo([2025], db)
                
        except Exception as e:
            print(f"❌ Erro na coleta com fallback: {e}")
            return {'status': 'erro', 'erro': str(e)}
    
    def _validar_custo_volume(self, db: Session) -> bool:
        """
        Valida custo e volume antes de processar
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            bool: True se seguro para processar
        """
        try:
            from sqlalchemy import func
            
            # Verificar volume no banco
            total_proposicoes = db.query(func.count(Proposicao.id)).filter(
                Proposicao.ano == 2025
            ).scalar()
            
            # Verificar uso do GCS
            blobs = self.gcs_manager.list_blobs()
            
            print(f"      📊 Volume atual: {total_proposicoes} proposições")
            print(f"      📁 Storage atual: {len(blobs)} arquivos")
            
            # Limites seguros
            if total_proposicoes > 10000:
                print(f"      ⚠️ Volume alto ({total_proposicoes}), considerando limpeza")
                return False
            
            if len(blobs) > 2000:
                print(f"      ⚠️ Storage alto ({len(blobs)}), considerando limpeza")
                return False
            
            return True
            
        except Exception as e:
            print(f"      ⚠️ Erro ao validar custo/volume: {e}")
            return True
    
    def _validar_json_disponivel(self) -> bool:
        """
        Valida se o JSON de proposições está disponível
        
        Returns:
            bool: True se disponível
        """
        try:
            import requests
            
            json_url = self.proposicoes_config.get('json_url')
            if not json_url:
                return False
            
            response = requests.head(json_url, timeout=10)
            return response.status_code == 200
            
        except Exception:
            return False

def main():
    """
    Função principal para execução standalone
    """
    print("📄 COLETOR DE PROPOSIÇÕES - ABORDAGEM JSON")
    print("=" * 50)
    print("🔧 Nova abordagem: Download do JSON completo da Câmara")
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = get_db_session()
    
    try:
        coletor = ColetorProposicoesJSON()
        
        print(f"🎯 Configurações:")
        print(f"   📡 JSON URL: {coletor.proposicoes_config.get('json_url')}")
        print(f"   📅 Meses foco: {coletor.proposicoes_config.get('meses_foco', [])}")
        print(f"   📋 Tipos prioritários: {', '.join(coletor.proposicoes_config.get('tipos_prioritarios', []))}")
        
        # Coletar proposições
        resultados = coletor.coletar_proposicoes_json(db_session)
        
        print(f"\n📋 RESUMO FINAL DA COLETA")
        print("=" * 40)
        print(f"📄 Encontradas: {resultados['proposicoes_encontradas']}")
        print(f"🔍 Filtradas: {resultados['proposicoes_filtradas']}")
        print(f"✅ Salvas: {resultados['proposicoes_salvas']}")
        print(f"📄 Documentos: {resultados['documentos_baixados']}")
        print(f"📁 Uploads GCS: {resultados['uploads_gcs']}")
        print(f"👥 Autores: {resultados['autores_mapeados']}")
        print(f"❌ Erros: {resultados['erros']}")
        print(f"📋 Tipos: {resultados['tipos_coletados']}")
        print(f"📅 Meses: {resultados['meses_coletados']}")
        
        # Gerar resumo
        coletor.gerar_resumo_coleta(db_session)
        
        print(f"\n✅ Coleta de proposições JSON concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
