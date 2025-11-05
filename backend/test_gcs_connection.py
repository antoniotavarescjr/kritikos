#!/usr/bin/env python3
"""
Script de teste para conexão com Google Cloud Storage
Verifica se o backend consegue acessar o Storage corretamente
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Carregar variáveis de ambiente do .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.gcs_utils import get_gcs_manager

def test_gcs_connection():
    """Testa conexão com GCS e exibe informações detalhadas."""
    
    print("🧪 Teste de Conexão com Google Cloud Storage")
    print("=" * 60)
    
    # Verificar variáveis de ambiente
    print("📋 Variáveis de Ambiente:")
    print(f"   GCS_BUCKET_NAME: {os.getenv('GCS_BUCKET_NAME')}")
    print(f"   GCS_PROJECT_ID: {os.getenv('GCS_PROJECT_ID')}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    print()
    
    # Tentar inicializar GCS Manager
    print("🔧 Inicializando GCS Manager...")
    gcs = get_gcs_manager()
    
    if gcs is None:
        print("❌ Falha ao criar GCS Manager")
        print("Verifique as variáveis de ambiente acima")
        return False
    
    # Verificar disponibilidade
    print("📡 Verificando disponibilidade do GCS...")
    if not gcs.is_available():
        print("❌ GCS não está disponível")
        return False
    
    print("✅ GCS está disponível!")
    print(f"   Bucket: {gcs.bucket_name}")
    print(f"   Project: {gcs.project_id}")
    print()
    
    # Listar alguns arquivos para teste
    print("📁 Listando arquivos no bucket (primeiros 10)...")
    try:
        blobs = gcs.list_blobs(max_results=10)
        
        if not blobs:
            print("   ⚠️ Nenhum arquivo encontrado no bucket")
        else:
            print(f"   📊 Total de arquivos listados: {len(blobs)}")
            for i, blob in enumerate(blobs[:5], 1):
                print(f"   {i}. {blob.name} ({blob.size} bytes)")
                
    except Exception as e:
        print(f"   ❌ Erro ao listar arquivos: {e}")
        return False
    
    print()
    
    # Testar upload de um arquivo simples
    print("📤 Testando upload de arquivo...")
    test_data = {
        "teste": "conexão GCS",
        "timestamp": datetime.now().isoformat(),
        "projeto": "kritikos"
    }
    
    test_path = f"test/conexao_teste_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        if gcs.upload_json(test_data, test_path, compress=False):
            print(f"   ✅ Upload realizado: {test_path}")
            
            # Testar download do mesmo arquivo
            print("📥 Testando download do arquivo...")
            downloaded_data = gcs.download_json(test_path, compressed=False)
            
            if downloaded_data:
                print(f"   ✅ Download realizado com sucesso")
                print(f"   📋 Dados: {downloaded_data}")
                
                # Limpar arquivo de teste
                gcs.delete_blob(test_path)
                print(f"   🧹 Arquivo de teste removido")
            else:
                print(f"   ❌ Falha no download")
                return False
        else:
            print(f"   ❌ Falha no upload")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro no teste de upload/download: {e}")
        return False
    
    print()
    print("🎉 Todos os testes de conexão GCS passaram!")
    return True

def main():
    """Função principal."""
    success = test_gcs_connection()
    
    if success:
        print("\n✅ Conexão GCS está funcionando perfeitamente!")
        print("O backend pode usar o Storage normalmente.")
    else:
        print("\n❌ Problemas na conexão GCS!")
        print("Verifique:")
        print("1. Variáveis de ambiente no .env")
        print("2. Permissões da service account")
        print("3. Existência do bucket")

if __name__ == "__main__":
    main()
