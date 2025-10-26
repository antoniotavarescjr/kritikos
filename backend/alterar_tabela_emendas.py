#!/usr/bin/env python3
"""
Script para alterar a tabela emendas_parlamentares e permitir deputado_id nulo
"""

import sys
from pathlib import Path

# Adicionar src ao path
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))

from models.database import get_db
from sqlalchemy import text

def alterar_tabela_emendas():
    """Altera a tabela para permitir deputado_id nulo"""
    print("🔧 ALTERANDO TABELA EMENDAS_PARLAMENTARES")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Executar SQL para alterar a coluna
        sql = """
        ALTER TABLE emendas_parlamentares 
        ALTER COLUMN deputado_id DROP NOT NULL;
        """
        
        print("📝 Executando SQL...")
        print(sql)
        
        db.execute(text(sql))
        db.commit()
        
        print("✅ Tabela alterada com sucesso!")
        print("   📄 deputado_id agora pode ser nulo")
        
        # Verificar a alteração
        print("\n🔍 VERIFICANDO ALTERAÇÃO...")
        result = db.execute(text("""
            SELECT column_name, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'emendas_parlamentares' 
            AND column_name = 'deputado_id';
        """))
        
        row = result.fetchone()
        if row:
            print(f"   📋 Coluna: {row[0]}")
            print(f"   ✅ Nullable: {row[1]}")
        
    except Exception as e:
        print(f"❌ Erro ao alterar tabela: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    alterar_tabela_emendas()
