#!/usr/bin/env python3
"""
Script para testar o coletor de votações fallback corrigido
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from etl.coleta_votacoes_fallback_corrigido import ColetorVotacoesFallback
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Executa coleta de votações via fallback corrigido"""
    logger.info("🚀 TESTANDO COLETOR DE VOTAÇÕES CORRIGIDO")
    logger.info("=" * 60)
    
    try:
        # Inicializar coletor
        coletor = ColetorVotacoesFallback()
        
        # Testar apenas 2024 com limite pequeno
        ano = 2024
        limite = 100
        
        logger.info(f"📅 Testando coleta de {ano} com limite {limite}")
        logger.info("")
        
        # Executar coleta
        resultado = coletor.coletar_votacoes_periodo(ano, limite)
        logger.info(f"✅ Resultado: {resultado}")
        
        total_registros = sum(v for k, v in resultado.items() if k != 'erros')
        logger.info(f"🎉 TOTAL DE REGISTROS: {total_registros}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na coleta de votações: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
