#!/usr/bin/env python3
"""
Script de teste simplificado do pipeline otimizado
Testa as funcionalidades básicas sem executar o pipeline completo
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Carregar variáveis de ambiente do .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.db_utils import get_db_session
from sqlalchemy import text
from utils.gcs_utils import get_gcs_manager
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Testa conexão com o banco de dados."""
    print("🗄️ Testando conexão com banco de dados...")
    
    try:
        session = get_db_session()
        
        # Teste simples
        result = session.execute(text("SELECT 1 as test")).fetchone()
        
        if result and result[0] == 1:
            print("✅ Conexão com banco OK")
            session.close()
            return True
        else:
            print("❌ Falha no teste de conexão")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão com banco: {e}")
        return False

def test_gcs_connection():
    """Testa conexão com GCS."""
    print("📡 Testando conexão com GCS...")
    
    try:
        gcs = get_gcs_manager()
        
        if gcs and gcs.is_available():
            print("✅ Conexão GCS OK")
            return True
        else:
            print("❌ Falha na conexão GCS")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão GCS: {e}")
        return False

def test_basic_queries():
    """Testa queries básicas no banco."""
    print("📊 Testando queries básicas...")
    
    try:
        session = get_db_session()
        
        # Contar tabelas principais
        tables = session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('deputados', 'proposicoes', 'emendas_parlamentares', 'autorias')
            ORDER BY table_name
        """)).fetchall()
        
        print(f"   Tabelas encontradas: {[t[0] for t in tables]}")
        
        # Contar registros
        stats = {}
        for table in ['deputados', 'proposicoes', 'emendas_parlamentares', 'autorias']:
            try:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
                stats[table] = count
            except:
                stats[table] = 0
        
        print(f"   Registros: {stats}")
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro nas queries: {e}")
        return False

def test_gcs_file_operations():
    """Testa operações de arquivo no GCS."""
    print("📁 Testando operações de arquivo no GCS...")
    
    try:
        gcs = get_gcs_manager()
        
        # Listar arquivos de emendas
        blobs = gcs.list_blobs(prefix="emendas/2025/", max_results=5)
        
        if blobs:
            print(f"   📋 Arquivos de emendas encontrados: {len(blobs)}")
            for blob in blobs[:3]:
                print(f"      - {blob.name} ({blob.size} bytes)")
        else:
            print("   ⚠️ Nenhum arquivo de emendas encontrado")
        
        # Tentar baixar um arquivo pequeno
        if blobs:
            first_blob = blobs[0]
            if first_blob.size < 5000:  # Apenas arquivos pequenos
                print(f"   📥 Tentando baixar: {first_blob.name}")
                data = gcs.download_json(first_blob.name)
                
                if data:
                    print(f"   ✅ Download OK: {len(str(data))} caracteres")
                else:
                    print(f"   ❌ Falha no download")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nas operações GCS: {e}")
        return False

def test_pipeline_components():
    """Testa componentes individuais do pipeline."""
    print("🔧 Testando componentes do pipeline...")
    
    try:
        # Testar import dos coletores
        from etl.pipeline_coleta import ColetaPipeline
        from etl.coleta_proposicoes import ColetorProposicoes
        from etl.coletor_emendas import ColetorEmendasGenerico
        
        print("   ✅ Importações dos coletores OK")
        
        # Criar instâncias (sem executar)
        pipeline = ColetaPipeline()
        coletor = ColetorProposicoes()
        coletor_emendas = ColetorEmendasGenerico()
        
        print("   ✅ Instâncias criadas com sucesso")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro nos componentes: {e}")
        return False

def run_simplified_tests():
    """Executa todos os testes simplificados."""
    print("🧪 PIPELINE OTIMIZADO - TESTE SIMPLIFICADO")
    print("=" * 60)
    
    tests = [
        ("Banco de Dados", test_database_connection),
        ("Google Cloud Storage", test_gcs_connection),
        ("Queries Básicas", test_basic_queries),
        ("Operações GCS", test_gcs_file_operations),
        ("Componentes Pipeline", test_pipeline_components)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testando: {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Erro inesperado no teste {test_name}: {e}")
            results[test_name] = False
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:20} : {status}")
        if result:
            success_count += 1
    
    print(f"\n🎯 Resultado: {success_count}/{len(tests)} testes passaram")
    
    if success_count == len(tests):
        print("🎉 Todos os testes passaram! Pipeline pronto para execução.")
    else:
        print("⚠️ Alguns testes falharam. Verifique os erros acima.")
    
    return results

def main():
    """Função principal."""
    return run_simplified_tests()

if __name__ == "__main__":
    main()
