"""
Configurações da Kritikos API
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # Configurações do servidor
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Configurações do banco de dados
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/kritikos"
    )
    
    # Configurações de CORS
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000",  # React dev
        "http://localhost:8080",  # Vue dev
        "https://kritikos.com.br",  # Produção
        "http://localhost:8000",  # API docs
    ]
    
    # URLs de documentação
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    # Configurações de logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Configurações de cache (opcional)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutos
    
    # Configurações de rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
    # Configurações de paginação
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    # Configurações de busca
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "50"))
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"  # Allow extra fields from environment variables
    }


# Instância global de configurações
settings = Settings()
