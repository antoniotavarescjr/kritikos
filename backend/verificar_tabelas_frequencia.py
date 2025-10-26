#!/usr/bin/env python3
"""
Script para verificar e corrigir o estado das tabelas de frequência
"""

from src.models.database import engine
from sqlalchemy import text

def verificar_e_corrigir():
    with engine.connect() as conn:
        # Verificar quais tabelas existem
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE '%frequencia%'
        """))
        tables = [row[0] for row in result]
        print('Tabelas de frequência existentes:', tables)
        
        # Atualizar versão para a mais recente
        conn.execute(text("UPDATE alembic_version SET version_num = 'criar_frequencia'"))
        conn.commit()
        print('Version updated to criar_frequencia')

if __name__ == "__main__":
    verificar_e_corrigir()
