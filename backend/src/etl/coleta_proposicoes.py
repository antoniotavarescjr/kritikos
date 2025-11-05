"""
Coletor de Proposições para Ranking de Deputados

Implementa abordagem híbrida: JSON para carga inicial + API para atualizações
Foco em proposições de alto impacto legislativo para hackathon.
"""

import logging
import requests
import json
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from models.db_utils import get_db_session
from models.proposicao_models import Proposicao, Autoria
from models.politico_models import Deputado
from utils.common_utils import setup_logging
from utils.cache_utils import CacheManager
from utils.gcs_utils import get_gcs_manager

logger = logging.getLogger(__name__)


class ColetorProposicoes:
    """
    Coletor de proposições dos deputados para sistema de ranking.
    
    Abordagem híbrida:
    1. Download JSON para carga inicial rápida
    2. API para atualizações específicas
    3. Foco em proposições de alto impacto
    """
    
    def __init__(self):
        self.cache = CacheManager('coletorproposicoes')
        self.base_url = "https://dadosabertos.camara.leg.br/api/v2"
        
        # Tipos de proposições relevantes para ranking (excluídos acessórios)
        self.tipos_relevantes = ['PEC', 'PLP', 'PL', 'MPV', 'PLV', 'SUG']
        
        # Sistema de pontuação por tipo
        self.pontuacao_tipos = {
            'PEC': 10,    # Proposta de Emenda à Constituição - Maior impacto
            'MPV': 8,     # Medida Provisória - Urgência e impacto
            'PLP': 7,     # Projeto de Lei Complementar - Alta relevância
            'PL': 5,      # Projeto de Lei - Relevância média-alta
            'PDC': 3,     # Projeto de Decreto Legislativo - Relevância média
            'PRC': 2      # Projeto de Resolução - Relevância variável
        }
        
        # Multiplicadores por status
        self.multiplicadores = {
            'aprovada': 1.5,      # Proposições aprovadas valem mais
            'em tramitação': 1.0,   # Em andamento normal
            'arquivada': 0.5,      # Arquivadas valem menos
            'rejeitada': 0.3,      # Rejeitadas valem pouco
        }
        
        self.session = get_db_session()
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager is not None and self.gcs_manager.is_available()
        
        if self.gcs_disponivel:
            logger.info("✅ GCS disponível para armazenamento")
        else:
            logger.warning("⚠️ GCS não disponível - usando apenas banco de dados local")
        
    def baixar_json_proposicoes(self, tipo: str, ano: int) -> Optional[List[Dict]]:
        """
        Baixa arquivo JSON de proposições por tipo e ano usando ARQUIVO OFICIAL COMPLETO.
        
        Args:
            tipo: Tipo da proposição (PEC, PL, etc.)
            ano: Ano das proposições
            
        Returns:
            Lista de proposições ou None em caso de erro
        """
        try:
            # Usar ARQUIVO OFICIAL COMPLETO da Câmara (não API limitada)
            url = f"https://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-{ano}.json"
            
            logger.info(f"📥 Baixando JSON COMPLETO de proposições de {ano}...")
            
            response = requests.get(url, timeout=60)  # Timeout maior para arquivo grande
            response.raise_for_status()
            
            dados = response.json()
            proposicoes = dados.get('dados', [])
            
            # Filtrar por tipo e ano
            props_filtradas = [
                p for p in proposicoes 
                if p.get('siglaTipo') == tipo and p.get('ano') == ano
            ]
            
            logger.info(f"✅ Download {tipo}: {len(props_filtradas)} proposições (de {len(proposicoes)} totais)")
            return props_filtradas
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar JSON de {tipo}s: {e}")
            return None
    
    def buscar_proposicoes_deputado_api(self, deputado_id: int) -> Optional[List[Dict]]:
        """
        Busca proposições de um deputado específico via API.
        
        Args:
            deputado_id: ID do deputado na API da Câmara
            
        Returns:
            Lista de proposições ou None em caso de erro
        """
        try:
            url = f"{self.base_url}/deputados/{deputado_id}/proposicoes"
            
            # Cache para evitar requisições repetidas
            cache_key = f"deputado_{deputado_id}_proposicoes"
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f"📦 Cache hit: proposições do deputado {deputado_id}")
                return cached_data
            
            logger.info(f"🔍 Buscando proposições do deputado {deputado_id}...")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            dados = response.json()
            proposicoes = dados.get('dados', [])
            
            # Filtrar apenas tipos relevantes
            props_filtradas = [
                p for p in proposicoes 
                if p.get('siglaTipo') in self.tipos_relevantes
            ]
            
            # Salvar no cache por 1 hora
            self.cache.set(cache_key, props_filtradas, ttl=3600)
            
            logger.info(f"✅ API deputado {deputado_id}: {len(props_filtradas)} proposições relevantes")
            return props_filtradas
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar proposições do deputado {deputado_id}: {e}")
            return None
    
    def calcular_pontos_proposicao(self, proposicao: Dict) -> float:
        """
        Calcula pontos de uma proposição baseado no tipo e status.
        
        Args:
            proposicao: Dicionário com dados da proposição
            
        Returns:
            Pontuação calculada
        """
        tipo = proposicao.get('siglaTipo', '')
        pontos_base = self.pontuacao_tipos.get(tipo, 1)
        
        # Verificar status para multiplicador
        status = proposicao.get('statusProposicao', {}).get('descricao', '').lower()
        multiplicador = 1.0
        
        if 'aprov' in status:
            multiplicador = self.multiplicadores['aprovada']
        elif 'tramit' in status:
            multiplicador = self.multiplicadores['em tramitação']
        elif 'arquiv' in status:
            multiplicador = self.multiplicadores['arquivada']
        elif 'rejeit' in status:
            multiplicador = self.multiplicadores['rejeitada']
        
        return pontos_base * multiplicador
    
    def salvar_proposicao(self, dados_proposicao: Dict, salvar_gcs: bool = True, autores_dict: Optional[Dict] = None) -> Optional[int]:
        """
        Salva uma proposição no banco de dados e opcionalmente no GCS.
        
        Args:
            dados_proposicao: Dicionário com dados da proposição
            salvar_gcs: Se deve salvar no GCS (padrão: True)
            autores_dict: Dicionário de autores pré-carregado (otimização)
            
        Returns:
            ID da proposição salva ou None em caso de erro
        """
        try:
            # Verificar se já existe
            api_id = dados_proposicao.get('id')
            existente = self.session.execute(
                text("SELECT id FROM proposicoes WHERE api_camara_id = :api_id"),
                {'api_id': api_id}
            ).scalar()
            
            if existente:
                return existente
            
            # Usar autores do dicionário pré-carregado (OTIMIZAÇÃO)
            autores = []
            if autores_dict and api_id in autores_dict:
                autores = autores_dict[api_id]
            else:
                # Fallback: buscar via API (apenas se necessário)
                autores = self._buscar_autores_proposicao(api_id)
            
            # Desabilitar download de documentos (muitos erros 403)
            documento_html = None
            url_inteiro_teor = dados_proposicao.get('urlInteiroTeor', '')
            # if url_inteiro_teor and salvar_gcs:
            #     documento_html = self._baixar_documento_proposicao(url_inteiro_teor)
            
            # Desabilitar GCS temporariamente para evitar rate limiting
            gcs_url = None
            # if salvar_gcs:
            #     gcs_url = self._salvar_proposicao_gcs(dados_proposicao, autores, documento_html)
            
            # Mapear campos com tratamento de encoding
            proposicao = Proposicao(
                api_camara_id=api_id,
                tipo=dados_proposicao.get('siglaTipo', ''),
                numero=dados_proposicao.get('numero', 0),
                ano=dados_proposicao.get('ano', 2025),
                ementa=self._clean_text(dados_proposicao.get('ementa', '')),
                explicacao=self._clean_text(dados_proposicao.get('descricao', '')),
                data_apresentacao=self._parse_data(dados_proposicao.get('dataApresentacao')) or datetime.now().date(),
                situacao=self._clean_text(dados_proposicao.get('statusProposicao', {}).get('descricao', '')),
                link_inteiro_teor=dados_proposicao.get('uri', ''),
                keywords=self._clean_text(dados_proposicao.get('keywords', '')),
                gcs_url=gcs_url or dados_proposicao.get('urlInteiroTeor', '')
            )
            
            self.session.add(proposicao)
            self.session.flush()  # Obter ID sem commit
            
            # Salvar autoria no banco (OTIMIZADO)
            self._salvar_autoria_otimizado(proposicao.id, autores)
            
            logger.info(f"💾 Salva proposição {proposicao.tipo} {proposicao.numero}/{proposicao.ano}")
            if gcs_url:
                logger.info(f"📁 GCS: {gcs_url}")
            
            return proposicao.id
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar proposição: {e}")
            self.session.rollback()
            return None
    
    def _buscar_autores_proposicao(self, proposicao_id: int) -> List[Dict]:
        """
        Busca autores de uma proposição específica via API.
        
        Args:
            proposicao_id: ID da proposição na API da Câmara
            
        Returns:
            Lista de autores ou lista vazia em caso de erro
        """
        try:
            url = f"{self.base_url}/proposicoes/{proposicao_id}/autores"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            dados = response.json()
            autores = dados.get('dados', [])
            
            logger.info(f"👥 Encontrados {len(autores)} autores para proposição {proposicao_id}")
            return autores
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar autores da proposição {proposicao_id}: {e}")
            return []
    
    def baixar_json_autores(self, ano: int) -> Optional[Dict[int, List[Dict]]]:
        """
        Baixa arquivo JSON COMPLETO de autores de proposições por ano.
        
        Args:
            ano: Ano das proposições
            
        Returns:
            Dicionário mapeando ID da proposição -> lista de autores
        """
        try:
            # Usar ARQUIVO OFICIAL COMPLETO da Câmara
            url = f"https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/json/proposicoesAutores-{ano}.json"
            
            logger.info(f"📥 Baixando JSON COMPLETO de autores de {ano}...")
            
            response = requests.get(url, timeout=60)  # Timeout maior para arquivo grande
            response.raise_for_status()
            
            dados = response.json()
            autores_data = dados.get('dados', [])
            
            # Criar dicionário: id_proposicao -> lista de autores
            autores_dict = {}
            for autor_info in autores_data:
                prop_id = autor_info.get('idProposicao')
                if prop_id not in autores_dict:
                    autores_dict[prop_id] = []
                autores_dict[prop_id].append(autor_info)
            
            logger.info(f"✅ Download autores: {len(autores_data)} registros para {len(autores_dict)} proposições")
            return autores_dict
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar JSON de autores: {e}")
            return None
    
    def _salvar_autoria_otimizado(self, proposicao_id: int, autores: List[Dict]):
        """
        Salva autoria da proposição usando lista de autores pré-carregada (OTIMIZADO).
        
        Args:
            proposicao_id: ID da proposição salva
            autores: Lista de autores da proposição (do arquivo JSON completo)
        """
        try:
            for autor in autores:
                # Usar ID direto do autor (mais confiável que URI)
                deputado_api_id = autor.get('idDeputadoAutor')
                if deputado_api_id:
                    
                    # Buscar deputado pelo ID da API
                    deputado = self.session.execute(
                        text("SELECT id FROM deputados WHERE api_camara_id = :api_id"),
                        {'api_id': int(deputado_api_id)}
                    ).scalar()
                    
                    if deputado:
                        # Criar e salvar autoria imediatamente
                        autoria = Autoria(
                            proposicao_id=proposicao_id,
                            deputado_id=deputado,
                            tipo_autoria=autor.get('tipoAutor', 'Autor'),
                            ordem=int(autor.get('ordemAssinatura', 1))
                        )
                        self.session.add(autoria)
                        self.session.flush()
                        logger.info(f"   👤 Autoria: {autor.get('nomeAutor')} ({autor.get('tipoAutor')})")
                    else:
                        # Criar deputado se não existir (para autores de legislaturas anteriores)
                        logger.info(f"   🆕 Criando deputado: {autor.get('nomeAutor')} (ID: {deputado_api_id})")
                        
                        novo_deputado = Deputado(
                            api_camara_id=int(deputado_api_id),
                            nome=autor.get('nomeAutor', ''),
                            uf_nascimento=None,  # Não disponível neste endpoint
                            situacao='Fora de Exercício',  # Provavelmente não está mais em exercício
                            data_nascimento=None,
                            escolaridade=None,
                            email=None
                        )
                        self.session.add(novo_deputado)
                        self.session.flush()  # Obter ID sem commit
                        
                        # Criar autoria com o novo deputado
                        autoria = Autoria(
                            proposicao_id=proposicao_id,
                            deputado_id=novo_deputado.id,
                            tipo_autoria=autor.get('tipoAutor', 'Autor'),
                            ordem=int(autor.get('ordemAssinatura', 1))
                        )
                        self.session.add(autoria)
                        self.session.flush()  # Garantir persistência
                        logger.info(f"   👤 Autoria criada: {autor.get('nomeAutor')} ({autor.get('tipoAutor')})")
                else:
                    # Outro tipo de autor (sem ID de deputado)
                    logger.info(f"   📝 Autoria: {autor.get('nomeAutor')} ({autor.get('tipoAutor')}) - Sem ID deputado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar autoria otimizada: {e}")
            raise  # Propagar erro para debug
    
    def _salvar_autoria(self, proposicao_id: int, dados_proposicao: Dict):
        """
        Salva autoria da proposição.
        
        Args:
            proposicao_id: ID da proposição salva
            dados_proposicao: Dicionário com dados da proposição
        """
        try:
            # Buscar autores separadamente via API
            api_prop_id = dados_proposicao.get('id')
            autores = self._buscar_autores_proposicao(api_prop_id)
            
            for autor in autores:
                # Extrair ID do deputado da URI
                uri = autor.get('uri', '')
                if '/deputados/' in uri:
                    deputado_api_id = uri.split('/deputados/')[1].split('/')[0]
                    
                    # Buscar deputado pelo ID da API
                    deputado = self.session.execute(
                        text("SELECT id FROM deputados WHERE api_camara_id = :api_id"),
                        {'api_id': int(deputado_api_id)}
                    ).scalar()
                    
                    if deputado:
                        autoria = Autoria(
                            proposicao_id=proposicao_id,
                            deputado_id=deputado,
                            tipo_autoria=autor.get('tipo', 'Autor'),
                            ordem=autor.get('ordemAssinatura', 1)
                        )
                        self.session.add(autoria)
                        logger.info(f"   👤 Autoria: {autor.get('nome')} ({autor.get('tipo')})")
                    else:
                        # Criar deputado se não existir (para autores de legislaturas anteriores)
                        logger.info(f"   🆕 Criando deputado: {autor.get('nome')} (ID: {deputado_api_id})")
                        
                        novo_deputado = Deputado(
                            api_camara_id=int(deputado_api_id),
                            nome=autor.get('nome', ''),
                            uf_nascimento=None,  # Não disponível neste endpoint
                            situacao='Fora de Exercício',  # Provavelmente não está mais em exercício
                            data_nascimento=None,
                            escolaridade=None,
                            email=None
                        )
                        self.session.add(novo_deputado)
                        self.session.flush()  # Obter ID sem commit
                        
                        # Criar autoria com o novo deputado
                        autoria = Autoria(
                            proposicao_id=proposicao_id,
                            deputado_id=novo_deputado.id,
                            tipo_autoria=autor.get('tipo', 'Autor'),
                            ordem=autor.get('ordemAssinatura', 1)
                        )
                        self.session.add(autoria)
                        logger.info(f"   👤 Autoria criada: {autor.get('nome')} ({autor.get('tipo')})")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar autoria: {e}")
    
    def _clean_text(self, text: str) -> str:
        """
        Limpa e normaliza texto para evitar problemas de encoding.
        
        Args:
            text: Texto original
            
        Returns:
            Texto limpo e normalizado
        """
        if not text:
            return ""
        
        try:
            # Remover caracteres problemáticos e normalizar
            cleaned = str(text).strip()
            # Substituir caracteres que causam problemas no PostgreSQL
            cleaned = cleaned.replace('\x00', '')  # Null character
            cleaned = cleaned.replace('\r\n', '\n')  # Normalizar line breaks
            cleaned = cleaned.replace('\r', '\n')
            
            # Limitar tamanho para evitar problemas
            if len(cleaned) > 10000:
                cleaned = cleaned[:10000] + "..."
            
            return cleaned
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar texto: {e}")
            return str(text)[:500] if text else ""
    
    def _parse_data(self, data_str: Optional[str]) -> Optional[date]:
        """
        Converte string de data para objeto date.
        
        Args:
            data_str: String de data no formato DD/MM/YYYY
            
        Returns:
            Objeto date ou None
        """
        if not data_str:
            return None
            
        try:
            # Formato da API: DD/MM/YYYY
            return datetime.strptime(data_str, '%d/%m/%Y').date()
        except:
            try:
                # Formato alternativo: YYYY-MM-DD
                return datetime.strptime(data_str, '%Y-%m-%d').date()
            except:
                return None
    
    def _baixar_documento_proposicao(self, url_inteiro_teor: str) -> Optional[str]:
        """
        Baixa o texto completo de uma proposição.
        
        Args:
            url_inteiro_teor: URL do texto completo da proposição
            
        Returns:
            HTML do documento ou None em caso de erro
        """
        if not url_inteiro_teor:
            return None
            
        try:
            logger.info(f"📄 Baixando documento: {url_inteiro_teor}")
            
            response = requests.get(url_inteiro_teor, timeout=30)
            response.raise_for_status()
            
            # Verificar se é HTML
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                logger.info(f"✅ Documento baixado como HTML ({len(response.text)} caracteres)")
                return response.text
            else:
                logger.warning(f"⚠️ Documento não é HTML: {content_type}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao baixar documento: {e}")
            return None
    
    def _obter_proxima_versao(self, ano: int, tipo: str, api_id: str) -> str:
        """
        Obtém a próxima versão para uma proposição no GCS.
        
        Args:
            ano: Ano da proposição
            tipo: Tipo da proposição
            api_id: ID da API
            
        Returns:
            Número da próxima versão (v1, v2, etc.)
        """
        if not self.gcs_disponivel:
            return "v1"
        
        try:
            # Listar versões existentes
            prefix = f"proposicoes/{ano}/{tipo}/{tipo}_{api_id}_"
            blobs = self.gcs_manager.list_blobs(prefix=prefix)
            
            # Encontrar versão mais alta
            max_version = 0
            for blob in blobs:
                if '_metadata.json' in blob.name:
                    # Extrair número da versão
                    parts = blob.name.split('_')
                    for part in parts:
                        if part.startswith('v') and part.endswith('metadata.json'):
                            version_num = int(part[1:-13])  # Remove 'v' e 'metadata.json'
                            max_version = max(max_version, version_num)
            
            return f"v{max_version + 1}"
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter próxima versão: {e}")
            return "v1"
    
    def _salvar_proposicao_gcs(self, dados_proposicao: Dict, autores: List[Dict], documento_html: Optional[str] = None) -> Optional[str]:
        """
        Salva proposição completa no GCS com versionamento.
        
        Args:
            dados_proposicao: Dados completos da proposição
            autores: Lista de autores da proposição
            documento_html: Texto completo do documento (opcional)
            
        Returns:
            URL do metadado no GCS ou None se erro
        """
        if not self.gcs_disponivel:
            logger.warning("⚠️ GCS não disponível - pulando salvamento no storage")
            return None
        
        try:
            api_id = dados_proposicao.get('id')
            tipo = dados_proposicao.get('siglaTipo', '')
            ano = dados_proposicao.get('ano', datetime.now().year)
            
            # Obter próxima versão
            versao = self._obter_proxima_versao(ano, tipo, str(api_id))
            
            # Preparar metadados completos
            metadados_completos = {
                'proposicao': dados_proposicao,
                'autores': autores,
                'data_coleta': datetime.now().isoformat(),
                'versao': versao,
                'documento_disponivel': documento_html is not None
            }
            
            # Salvar metadados
            filename_metadata = f"{tipo}_{api_id}_{versao}_metadata.json"
            blob_path_metadata = f"proposicoes/{ano}/{tipo}/metadata/{filename_metadata}"
            
            if not self.gcs_manager.upload_json(metadados_completos, blob_path_metadata):
                return None
            
            # Salvar documento se disponível
            if documento_html:
                filename_doc = f"{tipo}_{api_id}_{versao}.html"
                blob_path_doc = f"proposicoes/{ano}/{tipo}/documentos/{filename_doc}"
                
                if not self.gcs_manager.upload_text(documento_html, blob_path_doc, compress=False):
                    logger.warning(f"⚠️ Falha ao salvar documento para {api_id}")
            
            # Atualizar índice
            self._atualizar_indice_ano(ano)
            
            url_gcs = f"https://storage.googleapis.com/{self.gcs_manager.bucket_name}/{blob_path_metadata}"
            logger.info(f"✅ Salvo no GCS: {tipo} {api_id} ({versao})")
            
            return url_gcs
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar no GCS: {e}")
            return None
    
    def _atualizar_indice_ano(self, ano: int):
        """
        Atualiza o índice de proposições de um ano.
        
        Args:
            ano: Ano para atualizar o índice
        """
        if not self.gcs_disponivel:
            return
        
        try:
            # Buscar todas as proposições do ano no banco
            props_no_banco = self.session.execute(text("""
                SELECT api_camara_id, tipo, numero, ano, ementa, situacao, gcs_url
                FROM proposicoes 
                WHERE ano = :ano AND gcs_url IS NOT NULL
                ORDER BY tipo, numero
            """), {'ano': ano}).fetchall()
            
            # Criar índice
            indice = {
                'ano': ano,
                'data_atualizacao': datetime.now().isoformat(),
                'total_proposicoes': len(props_no_banco),
                'proposicoes': []
            }
            
            for prop in props_no_banco:
                indice['proposicoes'].append({
                    'api_camara_id': prop[0],
                    'tipo': prop[1],
                    'numero': prop[2],
                    'ano': prop[3],
                    'ementa': prop[4],
                    'situacao': prop[5],
                    'gcs_url': prop[6]
                })
            
            # Salvar índice no GCS
            blob_path = f"proposicoes/indexes/{ano}_proposicoes_index.json"
            self.gcs_manager.upload_json(indice, blob_path)
            
            logger.info(f"✅ Índice atualizado: {ano} ({len(props_no_banco)} proposições)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar índice: {e}")
    
    def limpar_bucket_proposicoes(self) -> bool:
        """
        Limpa todos os arquivos de proposições do bucket GCS.
        
        Returns:
            True se sucesso, False caso contrário
        """
        if not self.gcs_disponivel:
            logger.warning("⚠️ GCS não disponível - não é possível limpar")
            return False
        
        try:
            logger.info("🧹 Limpando bucket de proposições...")
            
            # Listar todos os arquivos de proposições
            blobs = self.gcs_manager.list_blobs(prefix='proposicoes/')
            
            deletados = 0
            for blob in blobs:
                if self.gcs_manager.delete_blob(blob.name):
                    deletados += 1
            
            logger.info(f"✅ Bucket limpo: {deletados} arquivos deletados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar bucket: {e}")
            return False
    
    def coletar_por_json(self, ano: int = 2024) -> int:
        """
        Coleta proposições usando download de arquivos JSON OFICIAIS COMPLETOS.
        
        Args:
            ano: Ano das proposições a coletar
            
        Returns:
            Quantidade de proposições coletadas
        """
        logger.info(f"🚀 Iniciando coleta por JSON COMPLETO - Ano {ano}")
        
        # Baixar arquivo COMPLETO de autores uma vez só
        logger.info("📥 Baixando arquivo COMPLETO de autores...")
        autores_dict = self.baixar_json_autores(ano)
        
        total_coletadas = 0
        
        for tipo in self.tipos_relevantes:
            logger.info(f"📥 Processando tipo: {tipo}")
            
            proposicoes = self.baixar_json_proposicoes(tipo, ano)
            if not proposicoes:
                continue
            
            for dados_prop in proposicoes:
                # Usar autores do dicionário pré-carregado (mais eficiente)
                api_id = dados_prop.get('id')
                autores = autores_dict.get(api_id, []) if autores_dict else []
                
                if self.salvar_proposicao(dados_prop, salvar_gcs=True, autores_dict=autores_dict):
                    total_coletadas += 1
        
        try:
            self.session.commit()
            logger.info(f"✅ Coleta JSON COMPLETO concluída: {total_coletadas} proposições")
        except Exception as e:
            logger.error(f"❌ Erro no commit: {e}")
            self.session.rollback()
        
        return total_coletadas
    
    def coletar_por_deputados(self, limite_deputados: int = 50) -> int:
        """
        Coleta proposições buscando por cada deputado via API.
        
        Args:
            limite_deputados: Limite de deputados para processar
            
        Returns:
            Quantidade de proposições coletadas
        """
        logger.info(f"🚀 Iniciando coleta por deputados - Limite: {limite_deputados}")
        
        # Buscar deputados ativos
        deputados = self.session.execute(
            text("SELECT api_camara_id, nome FROM deputados WHERE situacao = 'Exercício' LIMIT :limite"),
            {'limite': limite_deputados}
        ).fetchall()
        
        total_coletadas = 0
        
        for api_id, nome in deputados:
            logger.info(f"👥 Processando deputado: {nome}")
            
            proposicoes = self.buscar_proposicoes_deputado_api(api_id)
            if not proposicoes:
                continue
            
            for dados_prop in proposicoes:
                if self.salvar_proposicao(dados_prop):
                    total_coletadas += 1
        
        try:
            self.session.commit()
            logger.info(f"✅ Coleta por deputados concluída: {total_coletadas} proposições")
        except Exception as e:
            logger.error(f"❌ Erro no commit: {e}")
            self.session.rollback()
        
        return total_coletadas
    
    def coletar_hibrido(self, ano_json: int = 2024, limite_api: int = 20) -> Tuple[int, int]:
        """
        Coleta usando abordagem híbrida: JSON para carga inicial + API para atualizações.
        
        Args:
            ano_json: Ano para coleta por JSON
            limite_api: Limite de deputados para coleta por API
            
        Returns:
            Tupla (coletadas_json, coletadas_api)
        """
        logger.info("🚀 Iniciando coleta híbrida de proposições")
        
        # Fase 1: Coleta por JSON (rápida)
        logger.info("📥 FASE 1: Coleta por JSON (carga inicial)")
        coletadas_json = self.coletar_por_json(ano_json)
        
        # Fase 2: Coleta por API (atualizações)
        logger.info("🔍 FASE 2: Coleta por API (atualizações)")
        coletadas_api = self.coletar_por_deputados(limite_api)
        
        return coletadas_json, coletadas_api
    
    def __del__(self):
        """Cleanup ao destruir o objeto."""
        if hasattr(self, 'session'):
            self.session.close()


def main():
    """
    Função principal para teste do coletor.
    """
    setup_logging()
    logger.info("Iniciando coletor de proposições")
    
    try:
        coletor = ColetorProposicoes()
        
        # Teste com abordagem híbrida
        json_count, api_count = coletor.coletar_hibrido(
            ano_json=2024,  # Ano completo para JSON
            limite_api=20      # Apenas alguns deputados para teste
        )
        
        logger.info(f"🎉 Coleta concluída!")
        logger.info(f"📊 JSON: {json_count} proposições")
        logger.info(f"🔍 API: {api_count} proposições")
        logger.info(f"📋 Total: {json_count + api_count} proposições")
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)


if __name__ == "__main__":
    main()
