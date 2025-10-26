#!/usr/bin/env python3
"""
Script para limpar completamente o Google Cloud Storage do Kritikos.
Remove todos os arquivos do bucket permitindo uma repopulação limpa.
"""

import sys
from pathlib import Path
import os
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

# Adicionar o diretório src ao sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.append(str(SRC_DIR))

from utils.gcs_utils import get_gcs_manager

def confirmar_limpeza_gcs():
    """Solicita confirmação do usuário antes de limpar o GCS."""
    print("⚠️  ATENÇÃO: Este script irá APAGAR TODOS os arquivos do Google Cloud Storage!")
    print("🗑️  Esta operação é IRREVERSÍVEL!")
    print("\nArquivos que serão removidos:")
    print("   • Todos os dados de proposições")
    print("   • Todos os dados de emendas")
    print("   • Todos os textos completos")
    print("   • Todos os metadados")
    print("\nDigite 'LIMPAR GCS' em maiúsculas para confirmar:")
    
    confirmacao = input("> ").strip()
    
    if confirmacao == "LIMPAR GCS":
        return True
    else:
        print("❌ Operação cancelada pelo usuário.")
        return False

def listar_arquivos_antes(gcs_manager):
    """Lista arquivos antes da limpeza."""
    print("\n📊 ARQUIVOS ANTES DA LIMPEZA GCS")
    print("=" * 50)
    
    try:
        # Listar todos os blobs
        blobs = gcs_manager.list_blobs()
        
        if not blobs:
            print("✅ Bucket já está vazio!")
            return 0
        
        total_arquivos = len(blobs)
        total_size = 0
        
        # Agrupar por tipo
        tipos = {}
        
        for blob in blobs:
            total_size += blob.size or 0
            
            # Extrair tipo do caminho
            path_parts = blob.name.split('/')
            tipo_principal = path_parts[0] if path_parts else 'outros'
            
            if tipo_principal not in tipos:
                tipos[tipo_principal] = {'count': 0, 'size': 0}
            
            tipos[tipo_principal]['count'] += 1
            tipos[tipo_principal]['size'] += blob.size or 0
        
        print(f"📁 Total de arquivos: {total_arquivos:,}")
        print(f"💾 Tamanho total: {total_size / (1024*1024):.1f} MB")
        
        print(f"\n📂 Arquivos por tipo:")
        for tipo, info in tipos.items():
            print(f"   📁 {tipo}: {info['count']:,} arquivos ({info['size'] / (1024*1024):.1f} MB)")
        
        return total_arquivos
        
    except Exception as e:
        print(f"❌ Erro ao listar arquivos: {e}")
        return 0

def limpar_bucket_gcs(gcs_manager):
    """Limpa todos os arquivos do bucket GCS."""
    print("\n🗑️  LIMPANDO BUCKET GCS...")
    print("=" * 50)
    
    try:
        # Listar todos os blobs
        blobs = gcs_manager.list_blobs()
        
        if not blobs:
            print("✅ Bucket já está vazio!")
            return True, 0
        
        total_arquivos = len(blobs)
        arquivos_removidos = 0
        erros = 0
        
        print(f"📁 Encontrados {total_arquivos:,} arquivos para remover...")
        
        # Remover em lotes para melhor performance
        lote_size = 100
        lote_atual = 0
        
        for i, blob in enumerate(blobs):
            try:
                if gcs_manager.delete_blob(blob.name):
                    arquivos_removidos += 1
                else:
                    erros += 1
                
                # Progresso
                if (i + 1) % lote_size == 0:
                    lote_atual += 1
                    progresso = ((i + 1) / total_arquivos) * 100
                    print(f"   📦 Lote {lote_atual}: {arquivos_removidos}/{i+1} arquivos removidos ({progresso:.1f}%)")
                
            except Exception as e:
                erros += 1
                print(f"   ❌ Erro ao remover {blob.name}: {e}")
        
        print(f"\n✅ Limpeza concluída!")
        print(f"   📁 Arquivos removidos: {arquivos_removidos:,}")
        print(f"   ❌ Erros: {erros}")
        
        return erros == 0, arquivos_removidos
        
    except Exception as e:
        print(f"❌ Erro durante limpeza do GCS: {e}")
        return False, 0

def verificar_limpeza(gcs_manager):
    """Verifica se o bucket foi limpo corretamente."""
    print("\n🔍 VERIFICANDO LIMPEZA...")
    print("=" * 30)
    
    try:
        blobs = gcs_manager.list_blobs()
        
        if not blobs:
            print("✅ Bucket limpo com sucesso!")
            return True
        else:
            print(f"⚠️  Ainda existem {len(blobs)} arquivos no bucket:")
            for blob in blobs[:10]:  # Mostrar apenas os primeiros 10
                print(f"   • {blob.name}")
            if len(blobs) > 10:
                print(f"   ... e mais {len(blobs) - 10} arquivos")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar limpeza: {e}")
        return False

def limpar_cache_local():
    """Limpa cache local."""
    print("\n🧹 LIMPANDO CACHE LOCAL...")
    print("=" * 30)
    
    cache_dirs = [
        Path(__file__).parent.parent / 'cache',
        Path(__file__).parent.parent.parent / 'cache',
        Path(__file__).parent.parent / 'test_cache'
    ]
    
    total_removido = 0
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                # Remover todos os arquivos do cache
                import shutil
                tamanho_original = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(exist_ok=True)
                
                arquivos_removidos = len(list(cache_dir.rglob('*')))
                total_removido += arquivos_removidos
                
                print(f"   ✅ Cache {cache_dir.name}: {tamanho_original / (1024*1024):.1f} MB limpos")
                
            except Exception as e:
                print(f"   ⚠️  Erro ao limpar cache {cache_dir}: {e}")
        else:
            print(f"   ⏭️  Cache {cache_dir.name}: não existe")
    
    if total_removido > 0:
        print(f"✅ Cache local limpo!")
    else:
        print("✅ Nenhum cache local para limpar")

def main():
    """Função principal do script."""
    print("🧹 LIMPEZA COMPLETA DO GOOGLE CLOUD STORAGE KRITIKOS")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Inicializar GCS Manager
    gcs_manager = get_gcs_manager()
    
    if not gcs_manager or not gcs_manager.is_available():
        print("❌ GCS não está disponível!")
        print("Verifique suas credenciais e configuração.")
        return
    
    print(f"✅ GCS Manager inicializado - Bucket: {gcs_manager.bucket_name}")
    
    try:
        # Mostrar estado atual
        total_antes = listar_arquivos_antes(gcs_manager)
        
        if total_antes == 0:
            print("\n✅ O bucket já está vazio!")
            limpar_cache_local()
            return
        
        # Solicitar confirmação
        if not confirmar_limpeza_gcs():
            return
        
        # Executar limpeza
        print("\n🚀 Iniciando limpeza do GCS...")
        
        sucesso, arquivos_removidos = limpar_bucket_gcs(gcs_manager)
        
        if sucesso:
            # Verificar resultado
            if verificar_limpeza(gcs_manager):
                print(f"\n📋 RESUMO DA OPERAÇÃO GCS")
                print("=" * 30)
                print(f"📁 Arquivos antes: {total_antes:,}")
                print(f"📁 Arquivos depois: 0")
                print(f"🗑️  Arquivos removidos: {arquivos_removidos:,}")
                print("\n✅ Google Cloud Storage limpo com sucesso!")
                
                # Limpar cache local também
                limpar_cache_local()
                
                print("\n🎯 Ambiente limpo e pronto para nova coleta!")
            else:
                print("\n⚠️  Limpeza incompleta - verifique manualmente")
        else:
            print("\n❌ Falha durante limpeza do GCS")
            
    except Exception as e:
        print(f"\n❌ Erro durante limpeza: {e}")
        
    finally:
        print("\n🔚 Operação finalizada.")

if __name__ == "__main__":
    main()
