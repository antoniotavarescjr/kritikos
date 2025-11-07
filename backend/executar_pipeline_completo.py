#!/usr/bin/env python3
"""
Script principal para executar pipeline completo do zero
"""

import sys
import os
import time
from datetime import datetime
import logging

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def executar_limpeza():
    """Executa limpeza completa."""
    print("🗑️ ETAPA PREPARATIVA: Limpando tudo...")
    
    try:
        # Importar e executar limpeza
        from limpar_tudo import LimpezaCompleta
        limpeza = LimpezaCompleta()
        resultado = limpeza.executar_limpeza_completa()
        
        if 'erro' in resultado:
            logger.error(f"❌ Limpeza falhou: {resultado['erro']}")
            return False
        else:
            logger.info("✅ Limpeza concluída com sucesso!")
            time.sleep(2)  # Pausa para estabilizar
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro na limpeza: {e}")
        return False

def executar_pipeline_v2():
    """Executa pipeline otimizado V2."""
    print("🚀 ETAPA PRINCIPAL: Executando Pipeline Otimizado V2...")
    
    try:
        # Importar pipeline V2
        from pipeline_otimizado_v2 import PipelineOtimizadoV2
        pipeline = PipelineOtimizadoV2()
        resultado = pipeline.executar_pipeline_completo()
        
        if 'erro' in resultado:
            logger.error(f"❌ Pipeline falhou: {resultado['erro']}")
            return False
        else:
            logger.info("✅ Pipeline concluído com sucesso!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro no pipeline: {e}")
        return False

def exibir_resumo_execucao(inicio, sucesso_limpeza, sucesso_pipeline):
    """Exibe resumo final da execução completa."""
    fim = time.time()
    duracao_total = fim - inicio
    
    print("\n" + "="*80)
    print("🎉 EXECUÇÃO COMPLETA - RESUMO FINAL")
    print("="*80)
    
    print(f"\n⏱️ Duração total: {duracao_total:.1f}s ({duracao_total/60:.1f}min)")
    
    print(f"\n📊 Resultados:")
    print(f"   Limpeza: {'✅ Sucesso' if sucesso_limpeza else '❌ Falha'}")
    print(f"   Pipeline: {'✅ Sucesso' if sucesso_pipeline else '❌ Falha'}")
    
    if sucesso_limpeza and sucesso_pipeline:
        print(f"\n🎯 SISTEMA PRONTO!")
        print(f"   ✅ Banco de dados limpo e atualizado")
        print(f"   ✅ GCS limpo e com novos dados")
        print(f"   ✅ 5000+ proposições processadas")
        print(f"   ✅ Pipeline otimizado funcionando")
    else:
        print(f"\n⚠️ EXECUÇÃO COM PROBLEMAS")
        if not sucesso_limpeza:
            print(f"   ❌ Limpeza falhou - verificar permissões")
        if not sucesso_pipeline:
            print(f"   ❌ Pipeline falhou - verificar logs")
    
    print("="*80)

def main():
    """Função principal."""
    print("=" * 80)
    print("     🚀 EXECUÇÃO COMPLETA DO SISTEMA")
    print("=" * 80)
    print("📋 Plano:")
    print("   1. Limpar banco de dados + GCS + cache")
    print("   2. Executar pipeline otimizado V2")
    print("   3. Processar 5000+ proposições de 2025")
    print("=" * 80)
    
    inicio_total = time.time()
    
    # Etapa 1: Limpeza completa
    sucesso_limpeza = executar_limpeza()
    
    if sucesso_limpeza:
        # Etapa 2: Pipeline otimizado
        sucesso_pipeline = executar_pipeline_v2()
    else:
        sucesso_pipeline = False
    
    # Resumo final
    exibir_resumo_execucao(inicio_total, sucesso_limpeza, sucesso_pipeline)
    
    # Retorno para script
    return 0 if sucesso_limpeza and sucesso_pipeline else 1

if __name__ == "__main__":
    exit(main())
