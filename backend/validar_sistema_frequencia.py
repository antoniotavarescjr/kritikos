#!/usr/bin/env python3
"""
Script simples para validar o sistema de frequência
Validação estrutural e de centralização
"""

import sys
import os

def validar_imports():
    """Valida se os models podem ser importados"""
    try:
        from src.models.frequencia_models import (
            FrequenciaDeputado, 
            DetalheFrequencia, 
            RankingFrequencia,
            ResumoFrequenciaMensal
        )
        print("✅ Models de frequência importados com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar models: {e}")
        return False

def validar_arquivos():
    """Valida se os arquivos existem"""
    arquivos_esperados = [
        'src/models/frequencia_models.py',
        'src/etl/coleta_frequencia.py',
        'alembic/versions/criar_tabelas_frequencia_deputados.py'
    ]
    
    print("🔍 VALIDAÇÃO DE ARQUIVOS")
    print("=" * 40)
    
    todos_existem = True
    for arquivo in arquivos_esperados:
        if os.path.exists(arquivo):
            print(f"✅ {arquivo}: EXISTE")
        else:
            print(f"❌ {arquivo}: NÃO EXISTE")
            todos_existem = False
    
    return todos_existem

def validar_integracao():
    """Valida se o coletor pode ser importado"""
    try:
        from src.etl.coleta_frequencia import ColetorFrequencia
        print("✅ ColetorFrequencia importado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar ColetorFrequencia: {e}")
        return False

def main():
    """Função principal de validação"""
    print("🚀 VALIDAÇÃO DO SISTEMA DE FREQUÊNCIA")
    print("=" * 60)
    
    # Validação 1: Imports
    print("\n📋 1. VALIDAÇÃO DE IMPORTS")
    imports_ok = validar_imports()
    
    # Validação 2: Arquivos
    print("\n📁 2. VALIDAÇÃO DE ARQUIVOS")
    arquivos_ok = validar_arquivos()
    
    # Validação 3: Integração
    print("\n🔗 3. VALIDAÇÃO DE INTEGRAÇÃO")
    integracao_ok = validar_integracao()
    
    # Resumo
    print("\n📊 RESUMO DA VALIDAÇÃO")
    print("=" * 40)
    print(f"✅ Models: {'OK' if imports_ok else 'FALHOU'}")
    print(f"✅ Arquivos: {'OK' if arquivos_ok else 'FALHOU'}")
    print(f"✅ Integração: {'OK' if integracao_ok else 'FALHOU'}")
    
    if imports_ok and arquivos_ok and integracao_ok:
        print("\n🎉 SISTEMA DE FREQUÊNCIA VALIDADO COM SUCESSO!")
        return 0
    else:
        print("\n❌ SISTEMA DE FREQUÊNCIA COM PROBLEMAS!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
