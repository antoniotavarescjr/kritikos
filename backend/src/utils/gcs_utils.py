"""
Google Cloud Storage Utilities
Módulo para gerenciamento de arquivos no GCS com cache local e compressão
"""

import os
import json
import gzip
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Union, BinaryIO
from datetime import datetime, timedelta
import logging

from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError, NotFound

logger = logging.getLogger(__name__)

class GCSManager:
    """
    Gerenciador de arquivos no Google Cloud Storage
    """
    
    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Inicializa o gerenciador GCS
        
        Args:
            bucket_name: Nome do bucket GCS
            project_id: ID do projeto Google Cloud
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.client = None
        self.bucket = None
        
        # Tentar inicializar cliente
        self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """
        Inicializa o cliente GCS
        
        Returns:
            bool: True se inicializado com sucesso, False caso contrário
        """
        try:
            # Tentar usar credenciais padrão
            self.client = storage.Client(project=self.project_id)
            
            # Testar acesso ao bucket
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Verificar se bucket existe
            if not self.bucket.exists():
                logger.error(f"Bucket {self.bucket_name} não existe ou não tem acesso")
                return False
            
            logger.info(f"✅ GCS Manager inicializado - Bucket: {self.bucket_name}")
            return True
            
        except DefaultCredentialsError as e:
            logger.error(f"❌ Erro de credenciais GCS: {e}")
            logger.error("Verifique se GOOGLE_APPLICATION_CREDENTIALS está configurado")
            return False
        except GoogleAPIError as e:
            logger.error(f"❌ Erro na API GCS: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar GCS: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Verifica se o GCS está disponível
        
        Returns:
            bool: True se disponível, False caso contrário
        """
        return self.client is not None and self.bucket is not None
    
    def _generate_blob_path(self, file_type: str, year: int, sub_type: str = "", filename: str = "") -> str:
        """
        Gera o caminho do blob no GCS
        
        Args:
            file_type: Tipo de arquivo (proposicoes, emendas, etc.)
            year: Ano dos dados
            sub_type: Subtipo (PEC, PL, etc.)
            filename: Nome do arquivo
            
        Returns:
            str: Caminho completo no bucket
        """
        path_parts = [file_type, str(year)]
        
        if sub_type:
            path_parts.append(sub_type)
        
        if filename:
            path_parts.append(filename)
        
        return "/".join(path_parts)
    
    def _compress_data(self, data: Union[str, bytes, Dict]) -> bytes:
        """
        Comprime dados usando gzip
        
        Args:
            data: Dados para comprimir
            
        Returns:
            bytes: Dados comprimidos
        """
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False, indent=2)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return gzip.compress(data)
    
    def _decompress_data(self, compressed_data: bytes) -> str:
        """
        Descomprime dados gzip
        
        Args:
            compressed_data: Dados comprimidos
            
        Returns:
            str: Dados descomprimidos
        """
        return gzip.decompress(compressed_data).decode('utf-8')
    
    def upload_json(self, data: Union[Dict, list], blob_path: str, compress: bool = True) -> bool:
        """
        Faz upload de dados JSON para o GCS
        
        Args:
            data: Dados para upload
            blob_path: Caminho do blob no bucket
            compress: Se deve comprimir os dados
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        if not self.is_available():
            logger.error("❌ GCS não disponível para upload")
            return False
        
        try:
            blob = self.bucket.blob(blob_path)
            
            # Preparar dados
            if compress:
                content = self._compress_data(data)
                blob.content_encoding = 'gzip'
                blob.content_type = 'application/json'
            else:
                content = json.dumps(data, ensure_ascii=False, indent=2)
                blob.content_type = 'application/json'
            
            # Upload
            blob.upload_from_string(content, content_type=blob.content_type)
            
            logger.info(f"✅ Upload JSON realizado: {blob_path} ({len(content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no upload JSON para {blob_path}: {e}")
            return False
    
    def upload_text(self, text: str, blob_path: str, compress: bool = True) -> bool:
        """
        Faz upload de texto para o GCS
        
        Args:
            text: Texto para upload
            blob_path: Caminho do blob no bucket
            compress: Se deve comprimir o texto
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        if not self.is_available():
            logger.error("❌ GCS não disponível para upload")
            return False
        
        try:
            blob = self.bucket.blob(blob_path)
            
            # Preparar dados
            if compress:
                content = self._compress_data(text)
                blob.content_encoding = 'gzip'
                blob.content_type = 'text/plain'
            else:
                content = text
                blob.content_type = 'text/plain'
            
            # Upload
            blob.upload_from_string(content, content_type=blob.content_type)
            
            logger.info(f"✅ Upload texto realizado: {blob_path} ({len(content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no upload texto para {blob_path}: {e}")
            return False
    
    def upload_text_with_content_type(self, text: str, blob_path: str, content_type: str, compress: bool = False) -> bool:
        """
        Faz upload de texto para o GCS com content-type específico
        
        Args:
            text: Texto para upload
            blob_path: Caminho do blob no bucket
            content_type: Content-type do arquivo
            compress: Se deve comprimir o texto
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        if not self.is_available():
            logger.error("❌ GCS não disponível para upload")
            return False
        
        try:
            blob = self.bucket.blob(blob_path)
            
            # Preparar dados
            if compress:
                content = self._compress_data(text)
                blob.content_encoding = 'gzip'
            else:
                # Para PDFs, garantir que seja bytes
                if content_type == 'application/pdf' and isinstance(text, str):
                    content = text.encode('latin-1')  # PDFs usam latin-1
                else:
                    content = text
            
            blob.content_type = content_type
            
            # Upload
            blob.upload_from_string(content, content_type=blob.content_type)
            
            logger.info(f"✅ Upload realizado: {blob_path} ({len(content)} bytes, {content_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no upload para {blob_path}: {e}")
            return False
    
    def download_binary(self, blob_path: str) -> Optional[bytes]:
        """
        Baixa dados binários do GCS
        
        Args:
            blob_path: Caminho do blob no bucket
            
        Returns:
            bytes: Dados baixados ou None se erro
        """
        if not self.is_available():
            logger.error("❌ GCS não disponível para download")
            return None
        
        try:
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning(f"⚠️ Blob não encontrado: {blob_path}")
                return None
            
            # Download como bytes
            content = blob.download_as_bytes()
            
            logger.info(f"✅ Download binário realizado: {blob_path} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"❌ Erro no download binário de {blob_path}: {e}")
            return None
    
    def download_json(self, blob_path: str, compressed: bool = True) -> Optional[Dict]:
        """
        Baixa dados JSON do GCS
        
        Args:
            blob_path: Caminho do blob no bucket
            compressed: Se os dados estão comprimidos
            
        Returns:
            Dict: Dados baixados ou None se erro
        """
        if not self.is_available():
            logger.error("❌ GCS não disponível para download")
            return None
        
        try:
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning(f"⚠️ Blob não encontrado: {blob_path}")
                return None
            
            # Download
            content = blob.download_as_string()
            
            # Tentar descomprimir se necessário, mas com fallback
            if compressed:
                try:
                    content = self._decompress_data(content)
                except:
                    # Se falhar descompressão, tentar direto como string
                    content = content.decode('utf-8')
            
            # Parse JSON
            data = json.loads(content)
            
            logger.info(f"✅ Download JSON realizado: {blob_path}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Erro no download JSON de {blob_path}: {e}")
            return None
    
    def download_text(self, blob_path: str, compressed: bool = True) -> Optional[str]:
        """
        Baixa texto do GCS
        
        Args:
            blob_path: Caminho do blob no bucket
            compressed: Se os dados estão comprimidos
            
        Returns:
            str: Texto baixado ou None se erro
        """
        if not self.is_available():
            logger.error("❌ GCS não disponível para download")
            return None
        
        try:
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning(f"⚠️ Blob não encontrado: {blob_path}")
                return None
            
            # Download
            content = blob.download_as_string()
            
            # Descomprimir se necessário
            if compressed:
                content = self._decompress_data(content)
            
            logger.info(f"✅ Download texto realizado: {blob_path}")
            return content
            
        except Exception as e:
            logger.error(f"❌ Erro no download texto de {blob_path}: {e}")
            return None
    
    def upload_proposicao(self, proposicao_data: Dict, ano: int, tipo: str, api_id: str, texto_completo: Optional[str] = None) -> Optional[str]:
        """
        Faz upload de dados completos de uma proposição
        
        Args:
            proposicao_data: Dados completos da proposição
            ano: Ano da proposição
            tipo: Tipo (PEC, PL, etc.)
            api_id: ID da API
            texto_completo: Texto completo da proposição (opcional)
            
        Returns:
            str: URL do arquivo no GCS ou None se erro
        """
        # Upload dos metadados (JSON)
        filename_json = f"{tipo}-{api_id}.json"
        blob_path_json = self._generate_blob_path("proposicoes", ano, tipo, "texto-completo/" + filename_json)
        
        if not self.upload_json(proposicao_data, blob_path_json):
            return None
        
        # Upload do texto completo se disponível
        if texto_completo:
            # Detectar formato do arquivo
            if texto_completo.startswith('%PDF'):
                filename_texto = f"{tipo}-{api_id}-texto.pdf"
                content_type = 'application/pdf'
            else:
                filename_texto = f"{tipo}-{api_id}-texto.html"
                content_type = 'text/html'
            
            blob_path_texto = self._generate_blob_path("proposicoes", ano, tipo, "documento/" + filename_texto)
            
            if not self.upload_text_with_content_type(texto_completo, blob_path_texto, content_type):
                logger.warning(f"⚠️ Falha no upload do texto completo para {api_id}")
        
        return f"https://storage.googleapis.com/{self.bucket_name}/{blob_path_json}"
    
    def upload_emenda(self, emenda_data: Dict, ano: int, api_id: str) -> Optional[str]:
        """
        Faz upload de dados completos de uma emenda
        
        Args:
            emenda_data: Dados completos da emenda
            ano: Ano da emenda
            api_id: ID da API
            
        Returns:
            str: URL do arquivo no GCS ou None se erro
        """
        filename = f"emenda-{api_id}.json"
        blob_path = self._generate_blob_path("emendas", ano, "texto-completo", filename)
        
        if self.upload_json(emenda_data, blob_path):
            return f"https://storage.googleapis.com/{self.bucket_name}/{blob_path}"
        
        return None
    
    def list_blobs(self, prefix: str = "", max_results: Optional[int] = None) -> list:
        """
        Lista blobs no bucket com prefixo específico
        
        Args:
            prefix: Prefixo para filtrar blobs
            max_results: Número máximo de resultados (para compatibilidade)
            
        Returns:
            list: Lista de blobs
        """
        if not self.is_available():
            return []
        
        try:
            blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
            blob_list = list(blobs)
            
            # Aplicar limite se especificado
            if max_results and len(blob_list) > max_results:
                blob_list = blob_list[:max_results]
            
            return blob_list
        except Exception as e:
            logger.error(f"❌ Erro ao listar blobs com prefixo {prefix}: {e}")
            return []
    
    def delete_blob(self, blob_path: str) -> bool:
        """
        Deleta um blob do bucket
        
        Args:
            blob_path: Caminho do blob para deletar
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        if not self.is_available():
            return False
        
        try:
            blob = self.bucket.blob(blob_path)
            blob.delete()
            logger.info(f"✅ Blob deletado: {blob_path}")
            return True
        except NotFound:
            logger.warning(f"⚠️ Blob não encontrado para deletar: {blob_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao deletar blob {blob_path}: {e}")
            return False
    
    def get_blob_metadata(self, blob_path: str) -> Optional[Dict]:
        """
        Obtém metadados de um blob
        
        Args:
            blob_path: Caminho do blob
            
        Returns:
            Dict: Metadados ou None se erro
        """
        if not self.is_available():
            return None
        
        try:
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                return None
            
            blob.reload()
            
            return {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'content_encoding': blob.content_encoding,
                'created': blob.time_created,
                'updated': blob.updated,
                'md5_hash': blob.md5_hash,
                'crc32c': blob.crc32c
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadados de {blob_path}: {e}")
            return None

# Função utilitária para criar instância GCS
def get_gcs_manager() -> GCSManager:
    """
    Cria instância do GCS Manager usando variáveis de ambiente
    
    Returns:
        GCSManager: Instância configurada ou None se não configurado
    """
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    project_id = os.getenv('GCS_PROJECT_ID')
    
    if not bucket_name:
        logger.error("❌ GCS_BUCKET_NAME não configurado")
        return None
    
    return GCSManager(bucket_name, project_id)
