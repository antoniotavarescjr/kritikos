#!/usr/bin/env python3
"""
ETL Utils - Utilitários Centralizados para Coletores
Elimina redundâncias e padroniza operações comuns entre todos os coletores ETL

Autor: Kritikos Team
Data: Outubro/2025
"""

import requests
import time
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod
import hashlib
import json

# Importar utilitários existentes
try:
    from ..utils.cache_utils import CacheManager, get_cache_manager
except ImportError:
    # Fallback para execução direta
    from utils.cache_utils import CacheManager, get_cache_manager

try:
    from ..utils.gcs_utils import get_gcs_manager
except ImportError:
    # Fallback para execução direta
    from utils.gcs_utils import get_gcs_manager

try:
    from .config import get_config
except ImportError:
    # Fallback para execução direta
    from etl.config import get_config


class ETLBase(ABC):
    """
    Classe base abstrata para todos os coletores ETL
    Fornece funcionalidades comuns e padronizadas
    """
    
    def __init__(self, config_name: str = None):
        """
        Inicializa o coletor base
        
        Args:
            config_name: Nome da configuração específica no config.py
        """
        self.config_name = config_name
        self.api_config = get_config('api')
        self.session = self._setup_session()
        self.cache = self._setup_cache()
        self.gcs_manager = get_gcs_manager()
        
        # Carregar configurações específicas se fornecido
        self.specific_config = {}
        if config_name:
            hackathon_config = get_config('hackathon')
            self.specific_config = hackathon_config.get(config_name, {})
        
        print(f"✅ {self.__class__.__name__} inicializado")
        if config_name:
            print(f"   📋 Config: {config_name}")
    
    def _setup_session(self) -> requests.Session:
        """
        Configura sessão HTTP padrão com headers e timeout
        
        Returns:
            requests.Session: Sessão configurada
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.api_config['user_agent'],
            'Accept': 'application/json'
        })
        return session
    
    def _setup_cache(self) -> Optional[CacheManager]:
        """
        Setup do cache manager
        
        Returns:
            CacheManager: Instância do cache ou None
        """
        try:
            cache_dir = f"cache/{self.__class__.__name__.lower()}"
            return get_cache_manager(cache_dir=cache_dir, ttl_hours=6)
        except Exception as e:
            print(f"⚠️ Cache não disponível: {e}")
            return None
    
    def make_request(self, url: str, params: Optional[Dict] = None, use_cache: bool = True, timeout: int = None) -> Optional[Dict]:
        """
        Método unificado para requisições HTTP com cache e rate limiting
        
        Args:
            url: URL da API
            params: Parâmetros da requisição
            use_cache: Se deve usar cache
            timeout: Timeout personalizado
            
        Returns:
            Dict: Resposta da API ou None se erro
        """
        # Verificar cache primeiro
        if use_cache and self.cache:
            cache_key = f"{url}_{str(sorted(params.items()) if params else '')}"
            cached_data = self.cache.get(cache_key)
            if cached_data:
                print(f"      📦 Cache hit: {url}")
                return cached_data
        
        try:
            # Rate limiting
            time.sleep(self.api_config['rate_limit_delay'])
            
            # Fazer requisição
            response = self.session.get(
                url, 
                params=params, 
                timeout=timeout or self.api_config['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Salvar no cache
            if use_cache and self.cache and data:
                from datetime import timedelta
                self.cache.set(cache_key, data, ttl=timedelta(hours=2))
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição {url}: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro ao processar resposta: {e}")
            return None
    
    def paginated_request(self, endpoint: str, params: Optional[Dict] = None, max_pages: int = None, max_items: int = None) -> List[Dict]:
        """
        Requisição com paginação automática
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            max_pages: Número máximo de páginas
            max_items: Número máximo de itens
            
        Returns:
            List[Dict]: Lista de todos os itens retornados
        """
        all_items = []
        page = 1
        pages_processed = 0
        
        while True:
            # Adicionar página aos parâmetros
            pag_params = params.copy() if params else {}
            pag_params['pagina'] = page
            pag_params['itens'] = pag_params.get('itens', 100)
            
            print(f"      📄 Página {page}...")
            data = self.make_request(endpoint, pag_params, use_cache=False)
            
            if not data:
                break
            
            items = data.get('dados', [])
            if not items:
                print(f"      📄 Página {page} vazia")
                break
            
            all_items.extend(items)
            pages_processed += 1
            
            print(f"      📊 Página {page}: +{len(items)} itens (total: {len(all_items)})")
            
            # Verificar limites
            if max_pages and pages_processed >= max_pages:
                print(f"      ⏹️ Limite de páginas ({max_pages}) atingido")
                break
            
            if max_items and len(all_items) >= max_items:
                print(f"      ⏹️ Limite de itens ({max_items}) atingido")
                break
            
            # Verificar próxima página
            links = {link['rel']: link['href'] for link in data.get('links', [])}
            if not links.get('next'):
                break
            
            page += 1
        
        return all_items


class DateParser:
    """Utilitário centralizado para parsing de datas"""
    
    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string de data para objeto datetime
        
        Args:
            date_str: String de data
            
        Returns:
            datetime: Data convertida ou None
        """
        if not date_str:
            return None
        
        try:
            # Remover timezone info se presente
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None
    
    @staticmethod
    def parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string de datetime para objeto datetime
        
        Args:
            datetime_str: String de datetime
            
        Returns:
            datetime: Objeto datetime ou None
        """
        if not datetime_str:
            return None
        
        try:
            # Formato da API: "2025-07-15T14:30:00"
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except:
            return None


class ProgressLogger:
    """Logger centralizado para progresso ETL"""
    
    def __init__(self, total_items: int, description: str = "Processando", show_percentage: bool = True):
        """
        Inicializa o logger de progresso
        
        Args:
            total_items: Total de itens a processar
            description: Descrição da operação
            show_percentage: Se deve mostrar percentual
        """
        self.total = total_items
        self.current = 0
        self.description = description
        self.show_percentage = show_percentage
        self.start_time = datetime.now()
        
        print(f"🔄 {self.description}: 0/{self.total}")
    
    def update(self, increment: int = 1, item_description: str = ""):
        """
        Atualiza progresso com logging
        
        Args:
            increment: Incremento no contador
            item_description: Descrição do item atual
        """
        self.current += increment
        
        if self.show_percentage:
            percentage = (self.current / self.total) * 100
            print(f"🔄 {self.description}: {self.current}/{self.total} ({percentage:.1f}%)")
        else:
            print(f"🔄 {self.description}: {self.current}/{self.total}")
        
        if item_description:
            print(f"   📄 {item_description}")
    
    def finish(self, message: str = "Concluído"):
        """
        Finaliza com resumo
        
        Args:
            message: Mensagem de conclusão
        """
        duration = datetime.now() - self.start_time
        print(f"✅ {message}: {self.current}/{self.total} itens")
        print(f"⏱️ Duração: {duration.total_seconds():.1f}s")


class DatabaseManager:
    """Gerenciador de operações em lote no banco"""
    
    def __init__(self, db: Session, batch_size: int = 1000):
        """
        Inicializa o gerenciador de banco
        
        Args:
            db: Sessão do banco
            batch_size: Tamanho do lote para commits
        """
        self.db = db
        self.batch_size = batch_size
    
    def check_duplicate(self, model_class, unique_field: str, value: Any) -> bool:
        """
        Verifica se registro já existe
        
        Args:
            model_class: Classe do modelo
            unique_field: Campo único
            value: Valor a verificar
            
        Returns:
            bool: True se existe, False caso contrário
        """
        try:
            filter_kwargs = {unique_field: value}
            existing = self.db.query(model_class).filter_by(**filter_kwargs).first()
            return existing is not None
        except Exception as e:
            print(f"❌ Erro ao verificar duplicata: {e}")
            return False
    
    def bulk_save(self, objects: List[Any]) -> int:
        """
        Salva objetos em lote com commit automático
        
        Args:
            objects: Lista de objetos para salvar
            
        Returns:
            int: Número de objetos salvos
        """
        if not objects:
            return 0
        
        saved_count = 0
        
        try:
            for obj in objects:
                self.db.add(obj)
                saved_count += 1
                
                # Commit em lote
                if saved_count % self.batch_size == 0:
                    self.db.commit()
                    print(f"      💾 Commit em lote: {saved_count} objetos")
            
            # Commit final
            self.db.commit()
            print(f"      ✅ Commit final: {saved_count} objetos salvos")
            
        except Exception as e:
            print(f"❌ Erro ao salvar em lote: {e}")
            self.db.rollback()
            return 0
        
        return saved_count
    
    def safe_commit(self) -> bool:
        """
        Commit seguro com tratamento de erro
        
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            self.db.commit()
            return True
        except Exception as e:
            print(f"❌ Erro no commit: {e}")
            self.db.rollback()
            return False


class DataValidator:
    """Validador de dados centralizado"""
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> tuple[bool, List[str]]:
        """
        Valida campos obrigatórios
        
        Args:
            data: Dados a validar
            required_fields: Lista de campos obrigatórios
            
        Returns:
            tuple: (valido, campos_faltando)
        """
        if not data:
            return False, required_fields.copy()
        
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def sanitize_string(value: Any) -> Optional[str]:
        """
        Sanitização de strings
        
        Args:
            value: Valor a sanitizar
            
        Returns:
            str: String sanitizada ou None
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            return value.strip()
        
        return str(value).strip()
    
    @staticmethod
    def extract_monetary_value(text: str) -> Optional[float]:
        """
        Extrai valor monetário de texto
        
        Args:
            text: Texto contendo valor monetário
            
        Returns:
            float: Valor extraído ou None
        """
        if not text:
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
            match = re.search(padrao, text.lower())
            if match:
                valor_str = match.group(1).replace('.', '').replace(',', '')
                try:
                    return float(valor_str)
                except ValueError:
                    continue
        
        return None


class GCSUploader:
    """Uploader centralizado para GCS"""
    
    def __init__(self):
        """Inicializa o uploader GCS"""
        self.gcs_manager = get_gcs_manager()
        self.available = self.gcs_manager.is_available() if self.gcs_manager else False
        
        if self.available:
            print("✅ GCS Uploader inicializado")
        else:
            print("⚠️ GCS não disponível")
    
    def upload_data(self, data: Dict, bucket_path: str, metadata: Dict = None) -> Optional[str]:
        """
        Upload genérico para GCS
        
        Args:
            data: Dados para upload
            bucket_path: Caminho no bucket
            metadata: Metadados adicionais
            
        Returns:
            str: URL do objeto no GCS ou None
        """
        if not self.available:
            return None
        
        try:
            # Adicionar metadados se fornecidos
            if metadata:
                data['_metadata'] = metadata
            
            # Fazer upload usando o método apropriado baseado no tipo
            if 'proposicao' in bucket_path.lower():
                return self._upload_proposicao(data, bucket_path)
            elif 'emenda' in bucket_path.lower():
                return self._upload_emenda(data, bucket_path)
            else:
                return self._upload_generic(data, bucket_path)
                
        except Exception as e:
            print(f"❌ Erro no upload GCS: {e}")
            return None
    
    def _upload_proposicao(self, data: Dict, bucket_path: str) -> Optional[str]:
        """Upload específico para proposições"""
        try:
            ano = data.get('ano', datetime.now().year)
            tipo = data.get('tipo', 'UNKNOWN')
            api_id = str(data.get('api_camara_id', 'unknown'))
            
            return self.gcs_manager.upload_proposicao(
                data, ano, tipo, api_id, data.get('texto_completo')
            )
        except Exception as e:
            print(f"❌ Erro no upload de proposição: {e}")
            return None
    
    def _upload_emenda(self, data: Dict, bucket_path: str) -> Optional[str]:
        """Upload específico para emendas"""
        try:
            ano = data.get('ano', datetime.now().year)
            api_id = str(data.get('api_camara_id', 'unknown'))
            
            return self.gcs_manager.upload_emenda(data, ano, api_id)
        except Exception as e:
            print(f"❌ Erro no upload de emenda: {e}")
            return None
    
    def _upload_generic(self, data: Dict, bucket_path: str) -> Optional[str]:
        """Upload genérico"""
        try:
            # Implementar upload genérico se necessário
            return self.gcs_manager.upload_json(data, bucket_path)
        except Exception as e:
            print(f"❌ Erro no upload genérico: {e}")
            return None


class HashGenerator:
    """Gerador de hashes para deduplicação"""
    
    @staticmethod
    def generate_data_hash(data: Dict) -> str:
        """
        Gera hash MD5 dos dados para deduplicação
        
        Args:
            data: Dados para gerar hash
            
        Returns:
            str: Hash MD5
        """
        try:
            # Ordenar dados para consistência
            ordered_data = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(ordered_data.encode()).hexdigest()
        except Exception as e:
            print(f"❌ Erro ao gerar hash: {e}")
            return hashlib.md5(str(data).encode()).hexdigest()


class APIRateLimiter:
    """Gerenciador de rate limiting para APIs"""
    
    def __init__(self, delay: float = 1.0):
        """
        Inicializa o rate limiter
        
        Args:
            delay: Delay entre requisições em segundos
        """
        self.delay = delay
        self.last_request = None
    
    def wait_if_needed(self):
        """Aguarda se necessário para respeitar rate limit"""
        if self.last_request:
            elapsed = time.time() - self.last_request
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                time.sleep(sleep_time)
        
        self.last_request = time.time()


# Funções utilitárias globais para compatibilidade
def create_etl_logger(total_items: int, description: str = "Processando") -> ProgressLogger:
    """
    Factory function para criar logger de progresso
    
    Args:
        total_items: Total de itens
        description: Descrição da operação
        
    Returns:
        ProgressLogger: Instância do logger
    """
    return ProgressLogger(total_items, description)


def create_db_manager(db: Session, batch_size: int = 1000) -> DatabaseManager:
    """
    Factory function para criar gerenciador de banco
    
    Args:
        db: Sessão do banco
        batch_size: Tamanho do lote
        
    Returns:
        DatabaseManager: Instância do gerenciador
    """
    return DatabaseManager(db, batch_size)


def create_gcs_uploader() -> GCSUploader:
    """
    Factory function para criar uploader GCS
    
    Returns:
        GCSUploader: Instância do uploader
    """
    return GCSUploader()


# Classe de exceção personalizada para ETL
class ETLException(Exception):
    """Exceção base para operações ETL"""
    pass


class APIException(ETLException):
    """Exceção para erros de API"""
    pass


class DatabaseException(ETLException):
    """Exceção para erros de banco"""
    pass


class ValidationException(ETLException):
    """Exceção para erros de validação"""
    pass
