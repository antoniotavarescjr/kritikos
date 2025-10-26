#!/usr/bin/env python3
"""
Script Completo de Investigação do GCS
Analisa todos os arquivos para descobrir estrutura real e tipos de documentos
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

# Adicionar diretório src ao sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.append(str(SRC_DIR))

from utils.gcs_utils import get_gcs_manager

def investigar_completo():
    """
    Investigação completa para descobrir todos os tipos de documentos
    """
    print("🔍 INVESTIGAÇÃO COMPLETA DO GCS")
    print("=" * 50)
    
    # Inicializar GCS Manager
    gcs_manager = get_gcs_manager()
    
    if not gcs_manager or not gcs_manager.is_available():
        print("❌ GCS não está disponível!")
        return
    
    print(f"✅ GCS Manager inicializado - Bucket: {gcs_manager.bucket_name}")
    
    try:
        # Listar todos os blobs
        blobs = gcs_manager.list_blobs()
        
        if not blobs:
            print("✅ Bucket está vazio!")
            return
        
        print(f"📁 Total de arquivos: {len(blobs)}")
        
        # Analisar todos os arquivos
        estruturas = {}
        tipos_diretorio = {}
        tipos_arquivo = {}
        extensoes = {}
        tamanhos = {}
        
        print(f"\n📊 ANALISANDO TODOS OS {len(blobs)} ARQUIVOS...")
        
        for blob in blobs:
            partes = blob.name.split('/')
            
            # Analisar estrutura
            estrutura = f"profundidade_{len(partes)}"
            estruturas[estrutura] = estruturas.get(estrutura, 0) + 1
            
            # Analisar tipo de diretório (parte 3)
            if len(partes) >= 3:
                tipo_dir = partes[2]  # proposicoes/2025/TIPO/...
                tipos_diretorio[tipo_dir] = tipos_diretorio.get(tipo_dir, 0) + 1
            
            # Analisar extensão
            if '.' in partes[-1]:
                extensao = partes[-1].split('.')[-1].lower()
                extensoes[extensao] = extensoes.get(extensao, 0) + 1
            
            # Analisar tamanho
            tamanho = getattr(blob, 'size', 0)
            tamanhos['total'] = tamanhos.get('total', 0) + tamanho
            
            if len(partes) >= 3:
                tipo_dir = partes[2]
                tamanhos[tipo_dir] = tamanhos.get(tipo_dir, 0) + tamanho
        
        print(f"\n📂 ESTRUTURAS ENCONTRADAS:")
        for estrutura, quantidade in sorted(estruturas.items()):
            print(f"   📁 {estrutura}: {quantidade:,} arquivos")
        
        print(f"\n📋 TIPOS POR DIRETÓRIO (parte 3 do caminho):")
        for tipo_dir, quantidade in sorted(tipos_diretorio.items()):
            tamanho_mb = tamanhos.get(tipo_dir, 0) / (1024 * 1024)
            print(f"   📋 {tipo_dir}: {quantidade:,} arquivos ({tamanho_mb:.1f} MB)")
        
        print(f"\n📄 EXTENSÕES ENCONTRADAS:")
        for extensao, quantidade in sorted(extensoes.items()):
            print(f"   📄 {extensao}: {quantidade:,} arquivos")
        
        # Salvar resultado completo
        with open('investigacao_completa_resultado.txt', 'w', encoding='utf-8') as f:
            f.write("INVESTIGAÇÃO COMPLETA DO GCS\n")
            f.write(f"Total de arquivos: {len(blobs)}\n\n")
            
            f.write("ESTRUTURAS:\n")
            for estrutura, quantidade in sorted(estruturas.items()):
                f.write(f"{estrutura}: {quantidade}\n")
            f.write("\n")
            
            f.write("TIPOS POR DIRETÓRIO:\n")
            for tipo_dir, quantidade in sorted(tipos_diretorio.items()):
                tamanho_mb = tamanhos.get(tipo_dir, 0) / (1024 * 1024)
                f.write(f"{tipo_dir}: {quantidade} arquivos ({tamanho_mb:.1f} MB)\n")
            f.write("\n")
            
            f.write("EXTENSÕES:\n")
            for extensao, quantidade in sorted(extensoes.items()):
                f.write(f"{extensao}: {quantidade}\n")
            f.write("\n")
            
            f.write("TAMANHO TOTAL:\n")
            f.write(f"{tamanhos['total'] / (1024*1024):.1f} MB\n")
        
        print(f"\n✅ Resultado salvo em: investigacao_completa_resultado.txt")
        
        # Análise específica para tipos prioritários
        print(f"\n🎯 ANÁLISE DE TIPOS PRIORITÁRIOS:")
        tipos_prioritarios = ['PL', 'PEC', 'PLP', 'MPV', 'PDC', 'PLV', 'PRC']
        tipos_irrelevantes = ['REQ', 'SUG', 'RIC', 'IND', 'PRL', 'MSC', 'PCR']
        
        print(f"   📋 Tipos prioritários encontrados:")
        for tipo in tipos_prioritarios:
            quantidade = tipos_diretorio.get(tipo, 0)
            if quantidade > 0:
                tamanho_mb = tamanhos.get(tipo, 0) / (1024 * 1024)
                print(f"      ✅ {tipo}: {quantidade:,} arquivos ({tamanho_mb:.1f} MB)")
            else:
                print(f"      ⏭️  {tipo}: 0 arquivos")
        
        print(f"   🗑️  Tipos irrelevantes encontrados:")
        for tipo in tipos_irrelevantes:
            quantidade = tipos_diretorio.get(tipo, 0)
            if quantidade > 0:
                tamanho_mb = tamanhos.get(tipo, 0) / (1024 * 1024)
                print(f"      ❌ {tipo}: {quantidade:,} arquivos ({tamanho_mb:.1f} MB)")
            else:
                print(f"      ⏭️  {tipo}: 0 arquivos")
        
        # Calcular economia potencial
        total_irrelevantes = sum(tipos_diretorio.get(tipo, 0) for tipo in tipos_irrelevantes)
        economia_mb = sum(tamanhos.get(tipo, 0) for tipo in tipos_irrelevantes) / (1024 * 1024)
        
        print(f"\n💰 ECONOMIA POTENCIAL:")
        print(f"   📁 Arquivos irrelevantes: {total_irrelevantes:,}")
        print(f"   💾 Economia de storage: {economia_mb:.1f} MB")
        print(f"   💰 Custo economizado: ~${economia_mb * 0.023:.2f} USD/mês")
        
    except Exception as e:
        print(f"❌ Erro durante investigação: {e}")

if __name__ == "__main__":
    investigar_completo()
