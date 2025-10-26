#!/usr/bin/env python3
"""
Script para executar migrações do Alembic
"""

import os
import sys
from pathlib import Path

# Adicionar diretório src ao path
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))

# Mudar para o diretório backend para garantir que alembic.ini seja encontrado
os.chdir(Path(__file__).resolve().parent)

from alembic.config import Config
from alembic import command

def main():
    """Executa as migrações do Alembic"""
    print("🔧 EXECUTANDO MIGRAÇÕES DO BANCO")
    print("=" * 50)
    
    try:
        # Configurar Alembic
        alembic_cfg = Config('alembic.ini')
        print(f"📁 Arquivo de configuração: alembic.ini")
        print(f"📂 Diretório de scripts: {alembic_cfg.get_main_option('script_location')}")
        
        # Executar migração para todas as heads
        print("🚀 Executando migração para 'heads'...")
        command.upgrade(alembic_cfg, 'heads')
        print("✅ Migração executada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao executar migração: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
