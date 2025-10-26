"""
Cache Utilities
Módulo para gerenciamento de cache local com TTL e limpeza automática
"""

import os
import json
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Gerenciador de cache local com suporte a TTL e múltiplos formatos
    """
    
    def __init__(self, cache_dir: str = "cache", default_ttl_hours: int = 24):
        """
        Inicializa o gerenciador de cache
        
        Args:
            cache_dir: Diretório do cache
            default_ttl_hours: TTL padrão em horas
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = timedelta(hours=default_ttl_hours)
        
        # Criar diretórios de cache
        self.cache_dir.mkdir(exist_ok=True)
        (self.cache_dir / "json").mkdir(exist_ok=True)
        (self.cache_dir / "pickle").mkdir(exist_ok=True)
        (self.cache_dir / "metadata").mkdir(exist_ok=True)
        
        logger.info(f"✅ Cache Manager inicializado - Diretório: {self.cache_dir}")
    
    def _generate_cache_key(self, key_data: Union[str, Dict, Any]) -> str:
        """
        Gera uma chave de cache única
        
        Args:
            key_data: Dados para gerar a chave
            
        Returns:
            str: Chave de cache hash
        """
        if isinstance(key_data, str):
            content = key_data
        elif isinstance(key_data, dict):
            content = json.dumps(key_data, sort_keys=True)
        else:
            content = str(key_data)
        
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, cache_key: str, format_type: str = "json") -> Path:
        """
        Obtém o caminho do arquivo de cache
        
        Args:
            cache_key: Chave do cache
            format_type: Tipo de formato (json, pickle)
            
        Returns:
            Path: Caminho do arquivo
        """
        return self.cache_dir / format_type / f"{cache_key}.{format_type}"
    
    def _get_metadata_path(self, cache_key: str) -> Path:
        """
        Obtém o caminho do arquivo de metadados
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            Path: Caminho do arquivo de metadados
        """
        return self.cache_dir / "metadata" / f"{cache_key}.meta"
    
    def _save_metadata(self, cache_key: str, ttl: Optional[timedelta] = None):
        """
        Salva metadados do cache
        
        Args:
            cache_key: Chave do cache
            ttl: Time to live
        """
        metadata = {
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + (ttl or self.default_ttl)).isoformat(),
            'ttl_hours': (ttl or self.default_ttl).total_seconds() / 3600
        }
        
        meta_path = self._get_metadata_path(cache_key)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
    
    def _is_expired(self, cache_key: str) -> bool:
        """
        Verifica se o cache está expirado
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            bool: True se expirado, False caso contrário
        """
        meta_path = self._get_metadata_path(cache_key)
        
        if not meta_path.exists():
            return True
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            return datetime.now() > expires_at
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ler metadados do cache {cache_key}: {e}")
            return True
    
    def set(self, key_data: Union[str, Dict, Any], value: Any, 
            ttl: Optional[timedelta] = None, format_type: str = "json") -> bool:
        """
        Salva dados no cache
        
        Args:
            key_data: Chave dos dados
            value: Valor para cache
            ttl: Time to live personalizado
            format_type: Formato de salvamento (json, pickle)
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            cache_key = self._generate_cache_key(key_data)
            cache_path = self._get_cache_path(cache_key, format_type)
            
            # Salvar dados
            if format_type == "json":
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(value, f, ensure_ascii=False, indent=2)
            elif format_type == "pickle":
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
            else:
                logger.error(f"❌ Formato de cache não suportado: {format_type}")
                return False
            
            # Salvar metadados
            self._save_metadata(cache_key, ttl)
            
            logger.debug(f"✅ Dados cacheados: {cache_key} ({format_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar no cache: {e}")
            return False
    
    def get(self, key_data: Union[str, Dict, Any], 
            format_type: str = "json", default: Any = None) -> Any:
        """
        Recupera dados do cache
        
        Args:
            key_data: Chave dos dados
            format_type: Formato dos dados (json, pickle)
            default: Valor padrão se não encontrado
            
        Returns:
            Any: Dados cacheados ou valor padrão
        """
        try:
            cache_key = self._generate_cache_key(key_data)
            cache_path = self._get_cache_path(cache_key, format_type)
            
            # Verificar se arquivo existe
            if not cache_path.exists():
                return default
            
            # Verificar se está expirado
            if self._is_expired(cache_key):
                self.delete(key_data, format_type)
                return default
            
            # Carregar dados
            if format_type == "json":
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif format_type == "pickle":
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            else:
                logger.error(f"❌ Formato de cache não suportado: {format_type}")
                return default
                
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar do cache: {e}")
            return default
    
    def delete(self, key_data: Union[str, Dict, Any], format_type: str = "json") -> bool:
        """
        Deleta dados do cache
        
        Args:
            key_data: Chave dos dados
            format_type: Formato dos dados
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            cache_key = self._generate_cache_key(key_data)
            cache_path = self._get_cache_path(cache_key, format_type)
            meta_path = self._get_metadata_path(cache_key)
            
            # Deletar arquivos
            if cache_path.exists():
                cache_path.unlink()
            
            if meta_path.exists():
                meta_path.unlink()
            
            logger.debug(f"🗑️ Cache deletado: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao deletar do cache: {e}")
            return False
    
    def clear_expired(self) -> int:
        """
        Limpa todos os caches expirados
        
        Returns:
            int: Quantidade de arquivos deletados
        """
        deleted_count = 0
        
        try:
            # Limpar caches JSON
            for cache_file in (self.cache_dir / "json").glob("*.json"):
                cache_key = cache_file.stem
                if self._is_expired(cache_key):
                    self.delete(cache_key, "json")
                    deleted_count += 1
            
            # Limpar caches Pickle
            for cache_file in (self.cache_dir / "pickle").glob("*.pickle"):
                cache_key = cache_file.stem
                if self._is_expired(cache_key):
                    self.delete(cache_key, "pickle")
                    deleted_count += 1
            
            logger.info(f"🧹 Cache limpo: {deleted_count} arquivos expirados removidos")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache expirado: {e}")
            return 0
    
    def clear_all(self) -> int:
        """
        Limpa todos os caches
        
        Returns:
            int: Quantidade de arquivos deletados
        """
        deleted_count = 0
        
        try:
            # Contar arquivos antes de deletar
            json_files = list((self.cache_dir / "json").glob("*.json"))
            pickle_files = list((self.cache_dir / "pickle").glob("*.pickle"))
            meta_files = list((self.cache_dir / "metadata").glob("*.meta"))
            
            # Deletar todos os arquivos
            for file_list in [json_files, pickle_files, meta_files]:
                for file_path in file_list:
                    file_path.unlink()
                    deleted_count += 1
            
            logger.info(f"🧹 Todos os caches limpos: {deleted_count} arquivos removidos")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar todos os caches: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do cache
        
        Returns:
            Dict: Estatísticas do cache
        """
        try:
            json_files = list((self.cache_dir / "json").glob("*.json"))
            pickle_files = list((self.cache_dir / "pickle").glob("*.pickle"))
            meta_files = list((self.cache_dir / "metadata").glob("*.meta"))
            
            # Calcular tamanhos
            total_size = 0
            for file_list in [json_files, pickle_files, meta_files]:
                for file_path in file_list:
                    total_size += file_path.stat().st_size
            
            # Contar expirados
            expired_count = 0
            for meta_file in meta_files:
                cache_key = meta_file.stem
                if self._is_expired(cache_key):
                    expired_count += 1
            
            return {
                'total_files': len(json_files) + len(pickle_files) + len(meta_files),
                'json_files': len(json_files),
                'pickle_files': len(pickle_files),
                'metadata_files': len(meta_files),
                'expired_files': expired_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': str(self.cache_dir)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas do cache: {e}")
            return {}
    
    def cache_api_response(self, api_url: str, params: Dict, response_data: Any, 
                          ttl_hours: int = 1) -> bool:
        """
        Cache específico para respostas de API
        
        Args:
            api_url: URL da API
            params: Parâmetros da requisição
            response_data: Dados de resposta
            ttl_hours: TTL em horas
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        cache_key = {
            'url': api_url,
            'params': params
        }
        
        return self.set(cache_key, response_data, 
                       ttl=timedelta(hours=ttl_hours), 
                       format_type="json")
    
    def get_cached_api_response(self, api_url: str, params: Dict) -> Any:
        """
        Recupera resposta de API cacheada
        
        Args:
            api_url: URL da API
            params: Parâmetros da requisição
            
        Returns:
            Any: Dados cacheados ou None
        """
        cache_key = {
            'url': api_url,
            'params': params
        }
        
        return self.get(cache_key, format_type="json", default=None)

# Função utilitária para criar instância do cache
def get_cache_manager(cache_dir: str = "cache", ttl_hours: int = 24) -> CacheManager:
    """
    Cria instância do Cache Manager
    
    Args:
        cache_dir: Diretório do cache
        ttl_hours: TTL padrão em horas
        
    Returns:
        CacheManager: Instância configurada
    """
    return CacheManager(cache_dir, ttl_hours)
