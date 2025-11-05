#!/usr/bin/env python3
"""
Script de teste para coleta de textos completos de proposições
"""

import sys
import os
from pathlib import Path

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.etl.coleta_proposicoes import ColetorProposicoes
from src.utils.common_utils import setup_logging
import logging

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("🧪 Testando coleta de textos completos")
    print("=" * 50)
    
    # Inicializar coletor
    coletor = ColetorProposicoes()
    
    # Dados de teste
    dados_teste = {
        'id': 2482075,
        'siglaTipo': 'PL',
        'numero': 5,
        'ano': 2025,
        'ementa': 'Proíbe a utilização de recursos públicos para shows e apresentações artísticas que promovam ou façam apologia ao crime organizado',
        'uri': 'https://dadosabertos.camara.leg.br/api/v2/proposicoes/2482075'
    }
    
    print(f"📋 Testando com: {dados_teste['siglaTipo']} {dados_teste['numero']}/{dados_teste['ano']} (ID: {dados_teste['id']})")
    
    # Testar salvamento com download de texto
    try:
        # Forçar nova proposição (não verificar existência)
        print("🔍 Forçando nova coleta (ignorando existência)...")
        
        # Chamar diretamente o método de texto para teste
        uri = dados_teste['uri']
        api_id = str(dados_teste['id'])
        
        print(f"📥 Testando download direto: {uri}")
        texto = coletor.texto_utils.obter_texto_completo(uri, api_id)
        
        if texto:
            print(f"✅ Texto obtido: {len(texto)} caracteres")
            print(f"📝 Primeiros 200 caracteres: {texto[:200]}...")
            
            # Testar salvamento no GCS
            if coletor.gcs_disponivel:
                print("💾 Testando salvamento no GCS...")
                gcs_url = coletor._salvar_texto_completo_gcs(dados_teste, texto)
                if gcs_url:
                    print(f"✅ Salvo no GCS: {gcs_url}")
                else:
                    print("❌ Falha ao salvar no GCS")
        else:
            print("❌ Não foi possível obter texto")
        
        resultado = coletor.salvar_proposicao(dados_teste, salvar_gcs=True)
        
        if resultado:
            print(f"✅ Proposição salva com sucesso! ID: {resultado}")
            
            # Verificar se texto foi baixado
            if coletor.gcs_disponivel:
                print("📁 GCS disponível - verificando texto salvo...")
                
                # Path esperado no GCS
                path_esperado = f"proposicoes/{dados_teste['ano']}/{dados_teste['siglaTipo']}/texto-completo/{dados_teste['siglaTipo']}-{dados_teste['id']}-texto-completo.txt"
                print(f"📍 Path esperado: {path_esperado}")
                
                # Tentar baixar para verificar
                try:
                    texto = coletor.gcs_manager.download_text(path_esperado, compressed=False)
                    if texto:
                        print(f"✅ Texto encontrado no GCS: {len(texto)} caracteres")
                        print(f"📝 Primeiros 200 caracteres: {texto[:200]}...")
                    else:
                        print("❌ Texto não encontrado no GCS")
                except Exception as e:
                    print(f"❌ Erro ao verificar texto no GCS: {e}")
            else:
                print("⚠️ GCS não disponível")
        else:
            print("❌ Falha ao salvar proposição")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
