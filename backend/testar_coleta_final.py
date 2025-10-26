#!/usr/bin/env python3
"""
Script para testar coleta completa do pipeline Kritikos
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from etl.config import get_coleta_config, get_data_inicio_coleta, get_data_fim_coleta
from etl.coleta_referencia import ColetorDadosCamara
from etl.coleta_emendas_transparencia import ColetorEmendasTransparencia
from etl.coleta_votacoes_fallback import ColetorVotacoesFallback
from etl.validacao_pipeline import ValidadorPipeline
from etl.relatorio_coletas import GeradorRelatorio
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Executa coleta completa do pipeline"""
    logger.info("🚀 INICIANDO COLETA COMPLETA DO PIPELINE KRITIKOS")
    logger.info("=" * 60)
    
    try:
        # Obter datas configuradas
        data_inicio = get_data_inicio_coleta()
        data_fim = get_data_fim_coleta()
        logger.info(f"📅 Período: {data_inicio} até {data_fim}")
        
        # 1. Coleta de dados de referência
        logger.info("📋 ETAPA 1: Coletando dados de referência...")
        coletor_ref = ColetorDadosCamara()
        resultado_ref = coletor_ref.coletar_todos()
        logger.info(f"✅ Referência: {resultado_ref}")
        
        # 2. Coleta de emendas
        logger.info("💰 ETAPA 2: Coletando emendas...")
        coletor_emendas = ColetorEmendasTransparencia()
        resultado_emendas = coletor_emendas.coletar_emendas_periodo(data_inicio, data_fim)
        logger.info(f"✅ Emendas: {resultado_emendas}")
        
        # 3. Coleta de votações com fallback
        logger.info("🗳️ ETAPA 3: Coletando votações...")
        coletor_votacoes = ColetorVotacoesFallback()
        resultado_votacoes = coletor_votacoes.coletar_votacoes_periodo(data_inicio, data_fim)
        logger.info(f"✅ Votações: {resultado_votacoes}")
        
        # 4. Validação final
        logger.info("🔍 ETAPA 4: Validando dados coletados...")
        validador = ValidadorPipeline()
        resultado_validacao = validador.executar_validacao_completa()
        
        # 5. Relatório final
        logger.info("📊 ETAPA 5: Gerando relatório final...")
        gerador = GeradorRelatorio()
        relatorio = gerador.gerar_relatorio_completo(resultado_validacao)
        
        logger.info("=" * 60)
        logger.info("🎉 COLETA COMPLETA FINALIZADA COM SUCESSO!")
        logger.info(f"📁 Relatório: {relatorio['arquivos']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na coleta completa: {str(e)}")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
