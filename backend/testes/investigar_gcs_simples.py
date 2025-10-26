#!/usr/bin/env python3
"""
Script Simplificado de Investigação do GCS
Versão leve para descobrir estrutura real dos arquivos
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

def investigar_simples():
    """
    Investigação simplificada para descobrir estrutura real
    """
    print("🔍 INVESTIGAÇÃO SIMPLIFICADA DO GCS")
    print("=" * 40)
    
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
        print(f"\n📊 PRIMEIROS 10 ARQUIVOS:")
        
        for i, blob in enumerate(blobs[:10]):
            print(f"   {i+1:2d}. {blob.name}")
            
            # Analisar estrutura simples
            partes = blob.name.split('/')
            print(f"      📂 Partes ({len(partes)}): {partes}")
            
            # Tentar extrair tipo
            if len(partes) >= 1:
                ultima_parte = partes[-1]
                if '_' in ultima_parte:
                    tipo = ultima_parte.split('_')[0]
                    print(f"      📋 Tipo possível: {tipo}")
                else:
                    print(f"      📋 Sem underscore no nome")
            
            print()
        
        # Analisar padrões gerais
        print(f"\n📊 ANÁLISE DE PADRÕES:")
        
        estruturas = {}
        tipos_possiveis = {}
        
        for blob in blobs[:50]:  # Primeiros 50
            partes = blob.name.split('/')
            
            # Contar estruturas
            estrutura = f"profundidade_{len(partes)}"
            estruturas[estrutura] = estruturas.get(estrutura, 0) + 1
            
            # Tentar extrair tipo
            if len(partes) >= 1:
                nome_arquivo = partes[-1]
                if '_' in nome_arquivo:
                    tipo = nome_arquivo.split('_')[0]
                    if tipo and len(tipo) >= 2 and len(tipo) <= 10:
                        tipos_possiveis[tipo] = tipos_possiveis.get(tipo, 0) + 1
        
        print(f"   📂 Estruturas encontradas:")
        for estrutura, quantidade in sorted(estruturas.items()):
            print(f"      📁 {estrutura}: {quantidade} arquivos")
        
        print(f"   📋 Tipos possíveis:")
        for tipo, quantidade in sorted(tipos_possiveis.items()):
            print(f"      📋 {tipo}: {quantidade} arquivos")
        
        # Salvar resultado em arquivo
        with open('investigacao_simples_resultado.txt', 'w', encoding='utf-8') as f:
            f.write("INVESTIGAÇÃO SIMPLIFICADA DO GCS\n")
            f.write(f"Total de arquivos: {len(blobs)}\n\n")
            f.write("PRIMEIROS 10 ARQUIVOS:\n")
            for i, blob in enumerate(blobs[:10]):
                f.write(f"{i+1}. {blob.name}\n")
            f.write("\nESTRUTURAS:\n")
            for estrutura, quantidade in sorted(estruturas.items()):
                f.write(f"{estrutura}: {quantidade}\n")
            f.write("\nTIPOS POSSÍVEIS:\n")
            for tipo, quantidade in sorted(tipos_possiveis.items()):
                f.write(f"{tipo}: {quantidade}\n")
        
        print(f"\n✅ Resultado salvo em: investigacao_simples_resultado.txt")
        
    except Exception as e:
        print(f"❌ Erro durante investigação: {e}")

if __name__ == "__main__":
    investigar_simples()
