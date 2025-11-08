#!/usr/bin/env python3
"""
Script para testar importação da API
"""

try:
    from api.main import app
    print("✅ API importada com sucesso!")
    print(f"✅ Título: {app.title}")
    print(f"✅ Versão: {app.version}")
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
except Exception as e:
    print(f"❌ Erro geral: {e}")
