#!/usr/bin/env python3
"""
Script simplificado para testar coleta do pipeline Kritikos
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from etl.executar_validacao_pipeline import main as validar_pipeline
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Executa teste simplificado do pipeline"""
    logger.info("🚀 INICIANDO TESTE SIMPLIFICADO DO PIPELINE KRITIKOS")
    logger.info("=" * 60)
    
    try:
        # Executar validação completa que já funciona
        logger.info("🔍 EXECUTANDO VALIDAÇÃO COMPLETA DO PIPELINE...")
        resultado = validar_pipeline()
        
        if resultado:
            logger.info("=" * 60)
            logger.info("🎉 TESTE FINALIZADO COM SUCESSO!")
            logger.info("✅ Pipeline validado e funcionando")
            return True
        else:
            logger.error("❌ Falha na validação do pipeline")
            return False
        
    except Exception as e:
        logger.error(f"❌ Erro no teste: {str(e)}")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
