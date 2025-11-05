#!/usr/bin/env python3
"""
Script para testar o fluxo completo: Coleta + Análise
"""

import sys
import os
from pathlib import Path

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))

from src.etl.coleta_proposicoes import ColetorProposicoes
from pipeline_analise_agents import PipelineAnaliseAgents
from src.utils.common_utils import setup_logging
import logging

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("🧪 Testando Fluxo Completo: Coleta + Análise")
    print("=" * 60)
    
    # 1. Testar coleta de uma proposição
    print("\n📥 ETAPA 1: Coleta de Textos")
    print("-" * 40)
    
    coletor = ColetorProposicoes()
    
    dados_teste = {
        'id': 2482075,
        'siglaTipo': 'PL',
        'numero': 5,
        'ano': 2025,
        'ementa': 'Proíbe a utilização de recursos públicos para shows e apresentações artísticas que promovam ou façam apologia ao crime organizado',
        'uri': 'https://dadosabertos.camara.leg.br/api/v2/proposicoes/2482075'
    }
    
    # Salvar proposição (já fizemos no teste anterior)
    resultado_coleta = coletor.salvar_proposicao(dados_teste, salvar_gcs=True)
    
    if resultado_coleta:
        print(f"✅ Coleta realizada: ID {resultado_coleta}")
    else:
        print("❌ Falha na coleta")
        return
    
    # 2. Testar análise da proposição coletada
    print("\n🔍 ETAPA 2: Análise com Agents")
    print("-" * 40)
    
    pipeline = PipelineAnaliseAgents()
    
    # Criar tupla da proposição de teste manualmente
    # Ordem correta da query: (id, api_camara_id, tipo, numero, ano, ementa, gcs_url, link_inteiro_teor, ...)
    proposicao_teste = (
        resultado_coleta,  # id (banco)
        dados_teste['id'],  # api_camara_id
        dados_teste['siglaTipo'],  # tipo
        dados_teste['numero'],  # numero
        dados_teste['ano'],  # ano
        dados_teste['ementa'],  # ementa
        f"https://storage.googleapis.com/kritikos-emendas-prod/proposicoes/{dados_teste['ano']}/{dados_teste['siglaTipo']}/texto-completo/{dados_teste['siglaTipo']}-{dados_teste['id']}-texto-completo.txt",  # gcs_url
        dados_teste['uri']  # link_inteiro_teor
    )
    
    print(f"🎯 Testando com proposição: {proposicao_teste[2]} {proposicao_teste[3]}/{proposicao_teste[4]} (ID: {proposicao_teste[0]})")
    
    # Testar obtenção de texto
    texto = pipeline.obter_texto_proposicao(proposicao_teste)
    
    if texto and len(texto) > 200:
        print(f"✅ Texto obtido: {len(texto)} caracteres")
        print(f"📝 Primeiros 200 caracteres: {texto[:200]}...")
        
        # Testar análise completa
        resultado_analise = pipeline.analisar_proposicao(proposicao_teste)
        
        if resultado_analise:
            print(f"✅ Análise realizada com sucesso!")
            print(f"📊 Resumo: {resultado_analise.get('is_trivial', 'Unknown')}")
            print(f"📈 PAR Score: {resultado_analise.get('par_score', 'N/A')}")
            
            # Salvar análise
            if pipeline.salvar_analise_proposicao(proposicao_teste[0], resultado_analise):
                print("✅ Análise salva no banco")
            else:
                print("❌ Falha ao salvar análise")
        else:
            print("❌ Falha na análise")
    else:
        print("❌ Texto não obtido ou muito curto")
    
    print("\n🎯 Fluxo completo testado!")

if __name__ == "__main__":
    main()
