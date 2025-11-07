#!/usr/bin/env python3
"""
Pipeline FINAL INTEGRADO com o coletor de textos restantes V2.
- Usa método eficiente de offset + verificação
- Suporta todos os tipos de proposições
- Integrado com pipeline completo
"""

import sys
import os
import time
from datetime import datetime
import logging

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.db_utils import get_db_session
from sqlalchemy import text
from etl.pipeline_coleta import ColetaPipeline
from etl.coleta_proposicoes import ColetorProposicoes
from etl.coletor_emendas import ColetorEmendasGenerico
from etl.coleta_referencia import ColetorDadosCamara
from etl.pdf_coleta_module import PDFColetaManager
from utils.gcs_utils import GCSManager

# Importar o coletor V2
from coletar_textos_restantes_v2 import ColetorTextosRestantesV2

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineFinalIntegrado:
    """Pipeline final integrado com coletor V2."""
    
    def __init__(self):
        self.pipeline = ColetaPipeline()
        self.coletor = ColetorProposicoes()
        self.coletor_emendas = ColetorEmendasGenerico()
        self.coletor_referencia = ColetorDadosCamara()
        self.coletor_textos = ColetorTextosRestantesV2()
        
    def executar_pipeline_completo(self):
        """Executa pipeline completo integrado."""
        logger.info("🚀 Iniciando Pipeline FINAL INTEGRADO")
        print("=" * 80)
        print("     🚀 PIPELINE FINAL INTEGRADO - VERSÃO OTIMIZADA")
        print("=" * 80)
        
        inicio_total = time.time()
        resultados = {}
        
        try:
            # Etapa 1: Coleta de Dados de Referência
            print(f"\n{'='*60}")
            print(f"🏛️ ETAPA 1/4: Coleta de Dados de Referência")
            print(f"   • Partidos")
            print(f"   • Deputados")
            print(f"   • Gastos Parlamentares")
            print(f"{'='*60}")
            
            try:
                referencia_result = self.coletor_referencia.executar_coleta_completa(get_db_session())
                resultados['referencia'] = referencia_result
                logger.info(f"✅ Dados de referência coletados:")
                logger.info(f"   Partidos: {referencia_result.get('partidos', 0)}")
                logger.info(f"   Deputados: {referencia_result.get('deputados', 0)}")
                logger.info(f"   Gastos: {referencia_result.get('gastos', 0)}")
            except Exception as e:
                logger.error(f"❌ Erro na coleta de referência: {e}")
                resultados['referencia'] = {'erro': str(e)}
            
            # Etapa 2: Coleta de Proposições
            print(f"\n{'='*60}")
            print(f"📋 ETAPA 2/4: Coleta de Proposições")
            print(f"{'='*60}")
            
            try:
                self.coletor.coletar_proposicoes_2025()
                logger.info("✅ Proposições 2025 coletadas/atualizadas")
                resultados['proposicoes'] = True
            except Exception as e:
                logger.error(f"❌ Erro na coleta de proposições: {e}")
                resultados['proposicoes'] = False
            
            # Etapa 3: Coleta de Textos (MÉTODO V2 OTIMIZADO)
            print(f"\n{'='*60}")
            print(f"📚 ETAPA 3/4: Coleta de Textos (MÉTODO V2 OTIMIZADO)")
            print(f"   • Offset dinâmico para pular já processados")
            print(f"   • Verificação individual real")
            print(f"   • Suporta todos os tipos (PL, PEC, PLP, MPV, PLV, SUG)")
            print(f"   • Performance otimizada")
            print(f"{'='*60}")
            
            try:
                textos_result = self.coletor_textos.executar_coleta_completa(limite_por_lote=100)
                resultados['textos'] = textos_result
                
                if textos_result:
                    logger.info("✅ Coleta de textos concluída com sucesso!")
                    logger.info("🎉 Todos os textos foram coletados!")
                else:
                    logger.warning("⚠️ Coleta de textos concluída, mas ainda há textos faltando")
                    
            except Exception as e:
                logger.error(f"❌ Erro na coleta de textos: {e}")
                resultados['textos'] = False
            
            # Etapa 4: Coleta de Emendas
            print(f"\n{'='*60}")
            print(f"💰 ETAPA 4/4: Coleta de Emendas Parlamentares")
            print(f"{'='*60}")
            
            try:
                session = get_db_session()
                resultado = self.coletor_emendas.coletar_emendas(session)
                session.close()
                
                if resultado and resultado.get('emendas_salvas', 0) > 0:
                    logger.info(f"✅ Emendas coletadas: {resultado['emendas_salvas']}")
                    logger.info(f"📊 Taxa de matching: {resultado.get('taxa_matching', 0):.1f}%")
                    resultados['emendas'] = True
                else:
                    logger.warning("⚠️ Nenhuma emenda salva")
                    resultados['emendas'] = False
                    
            except Exception as e:
                logger.error(f"❌ Erro na coleta de emendas: {e}")
                resultados['emendas'] = False
            
            # Resumo final
            print(f"\n{'='*60}")
            print(f"✅ PIPELINE FINAL INTEGRADO CONCLUÍDO")
            print(f"{'='*60}")
            
            # Exibir resumo final
            fim_total = time.time()
            duracao_total = fim_total - inicio_total
            
            print(f"\n⏱️ Duração total: {duracao_total:.1f}s ({duracao_total/60:.1f}min)")
            
            # Estatísticas finais
            print(f"\n📊 RESUMO FINAL COMPLETO:")
            
            # Dados de referência
            if 'referencia' in resultados and 'erro' not in resultados['referencia']:
                ref = resultados['referencia']
                print(f"   🏛️ Partidos: {ref.get('partidos', 0):,}")
                print(f"   👥 Deputados: {ref.get('deputados', 0):,}")
                print(f"   💰 Gastos: {ref.get('gastos', 0):,}")
            
            # Proposições
            print(f"   📋 Proposições: {'✅' if resultados.get('proposicoes') else '❌'}")
            
            # Textos
            print(f"   📚 Textos: {'✅ COMPLETO' if resultados.get('textos') else '❌ INCOMPLETO'}")
            
            # Emendas
            print(f"   💸 Emendas: {'✅' if resultados.get('emendas') else '❌'}")
            
            print(f"\n🎯 Sistema FINAL INTEGRADO pronto para produção!")
            print("="*80)
            
            return resultados
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no pipeline: {e}", exc_info=True)
            return {'erro': str(e)}


def main():
    """Função principal."""
    pipeline = PipelineFinalIntegrado()
    pipeline.executar_pipeline_completo()


if __name__ == "__main__":
    main()
