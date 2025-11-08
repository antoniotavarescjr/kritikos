#!/usr/bin/env python3
"""
Script para diagnosticar problemas da API antes do Docker
"""

import sys
import os

print("🔍 Diagnóstico da API Kritikos")
print("=" * 50)

# Adicionar path atual
sys.path.insert(0, '.')

try:
    print("1. Testando importação de dependências básicas...")
    import fastapi
    import uvicorn
    import sqlalchemy
    import psycopg2
    print("✅ Dependências básicas OK")
except ImportError as e:
    print(f"❌ Erro de dependência: {e}")
    sys.exit(1)

try:
    print("\n2. Testando configuração...")
    from api.config import settings
    print(f"✅ Configurações carregadas")
    print(f"   - DATABASE_URL: {settings.DATABASE_URL[:20]}...")
    print(f"   - HOST: {settings.HOST}")
    print(f"   - PORT: {settings.PORT}")
except Exception as e:
    print(f"❌ Erro na configuração: {e}")
    sys.exit(1)

try:
    print("\n3. Testando conexão com banco...")
    from src.models.database import engine, SessionLocal
    from sqlalchemy import text
    
    # Testar conexão
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexão com banco OK")
    
    # Testar models
    from src.models.politico_models import Deputado
    from src.models.analise_models import ScoreDeputado
    
    # Contar deputados
    session = SessionLocal()
    try:
        count = session.query(Deputado).count()
        print(f"✅ Models OK - {count} deputados no banco")
        
        # Testar se há dados de análise
        analise_count = session.query(ScoreDeputado).count()
        print(f"✅ Análises OK - {analise_count} análises no banco")
        
    finally:
        session.close()
        
except Exception as e:
    print(f"❌ Erro no banco/models: {e}")
    sys.exit(1)

try:
    print("\n4. Testando importação da API...")
    from api.main import app
    print("✅ API importada com sucesso")
    print(f"   - Título: {app.title}")
    print(f"   - Versão: {app.version}")
except Exception as e:
    print(f"❌ Erro na API: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n5. Testando services...")
    from services.deputado_service import get_deputado_service
    service = get_deputado_service()
    result = service.listar_deputados(page=1, per_page=5)
    print("✅ Service OK")
    print(f"   - Total deputados: {result['meta']['total']}")
    if result['data']:
        print(f"   - Primeiro deputado: {result['data'][0]['nome']}")
except Exception as e:
    print(f"❌ Erro no service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 Todos os testes passaram! A API deve funcionar.")
