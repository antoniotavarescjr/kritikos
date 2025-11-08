#!/usr/bin/env python3
"""
Script para gerar migração do Alembic automaticamente
"""

import os
import sys
sys.path.append('src')

from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

def gerar_migracao():
    """Gera migração automática para o Alembic"""
    # Carregar variáveis de ambiente
    load_dotenv('.env')
    
    # Configurar Alembic
    alembic_cfg = Config('alembic.ini')
    
    # Garantir que o URL do banco esteja configurado
    if not alembic_cfg.get_main_option("sqlalchemy.url"):
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    # Executar migração existente
    try:
        # Executar migração
        command.upgrade(alembic_cfg, "head")
        print("✅ Migração executada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao executar migração: {e}")
        raise

if __name__ == "__main__":
    gerar_migracao()
