#!/usr/bin/env python3
"""
Script para executar coleta de votações via fallback
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from etl.coleta_votacoes_fallback import ColetorVotacoesFallback
from etl.config import get_votacoes_fallback_config
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Executa coleta de votações via fallback"""
    logger.info("🚀 EXECUTANDO COLETA DE VOTAÇÕES VIA FALLBACK")
    logger.info("=" * 60)
    
    try:
        # Inicializar coletor
        coletor = ColetorVotacoesFallback()
        anos = get_votacoes_fallback_config('anos_para_coletar')
        limite = get_votacoes_fallback_config('limite_registros')
        
        logger.info(f"📅 Anos para coletar: {anos}")
        logger.info(f"🎯 Limite de registros: {limite}")
        logger.info("")
        
        # Executar coleta para cada ano
        total_geral = 0
        for ano in anos:
            logger.info(f"📅 Coletando votações de {ano}...")
            resultado = coletor.coletar_votacoes_periodo(ano, limite)
            logger.info(f"✅ {ano}: {resultado}")
            total_geral += resultado.get('votacoes_principais', 0)
        
        logger.info("")
        logger.info(f"🎉 TOTAL GERAL DE VOTAÇÕES COLETADAS: {total_geral}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na coleta de votações: {str(e)}")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
