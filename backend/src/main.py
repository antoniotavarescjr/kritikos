import os
import sys
import logging
import argparse
from datetime import datetime

# Adiciona o diretório raiz ao Python path para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.common_utils import setup_logging, clear_screen, exibir_menu
from src.etl.pipeline_coleta import ColetaPipeline
from src.etl.config import get_etl_config

# Configuração de logging
logger = logging.getLogger(__name__)


def executar_coleta_referencia():
    """Executa a coleta de dados de referência (deputados e partidos)."""
    logger.info("Iniciando coleta de dados de referência...")
    try:
        pipeline = ColetaPipeline()
        resultado = pipeline.referencia_etl.coletar_e_salvar()
        if resultado:
            print(f"✅ Coleta de referência concluída. {len(resultado.get('partidos', []))} partidos e {len(resultado.get('deputados', []))} deputados coletados.")
        else:
            print("⚠️ Nenhum dado de referência foi coletado.")
    except Exception as e:
        logger.error(f"Erro na coleta de referência: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_coleta_gastos():
    """Executa a coleta de gastos parlamentares."""
    logger.info("Iniciando coleta de gastos parlamentares...")
    try:
        pipeline = ColetaPipeline()
        ano = pipeline._obter_ano_alvo()
        ids_deputados = pipeline._obter_ids_deputados()
        if ids_deputados:
            print(f"Coletando gastos para {len(ids_deputados)} deputados no ano {ano}...")
            resultado = pipeline.gastos_etl.coletar_e_salvar(ano, ids_deputados)
            print(f"✅ Coleta de gastos concluída. {len(resultado)} registros de gastos processados.")
        else:
            print("⚠️ Nenhum deputado selecionado. Operação cancelada.")
    except Exception as e:
        logger.error(f"Erro na coleta de gastos: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_coleta_remuneracao():
    """Executa a coleta de remunerações e benefícios."""
    logger.info("Iniciando coleta de remunerações...")
    try:
        pipeline = ColetaPipeline()
        ano = pipeline._obter_ano_alvo()
        ids_deputados = pipeline._obter_ids_deputados()
        if ids_deputados:
            print(f"Coletando remunerações para {len(ids_deputados)} deputados no ano {ano}...")
            resultado = pipeline.remuneracao_etl.coletar_e_salvar(ano, ids_deputados)
            print(f"✅ Coleta de remunerações concluída. {len(resultado)} registros processados.")
        else:
            print("⚠️ Nenhum deputado selecionado. Operação cancelada.")
    except Exception as e:
        logger.error(f"Erro na coleta de remuneração: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_coleta_emendas():
    """Executa a coleta de emendas parlamentares."""
    logger.info("Iniciando coleta de emendas parlamentares...")
    try:
        pipeline = ColetaPipeline()
        ano = pipeline._obter_ano_alvo()
        print(f"Coletando emendas para o ano {ano}...")
        resultado = pipeline.emendas_etl.coletar_e_salvar(ano)
        print(f"✅ Coleta de emendas concluída. {len(resultado)} registros de emendas processados.")
    except Exception as e:
        logger.error(f"Erro na coleta de emendas: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_coleta_frequencia():
    """Executa a coleta de dados de frequência."""
    logger.info("Iniciando coleta de dados de frequência...")
    try:
        pipeline = ColetaPipeline()
        ano = pipeline._obter_ano_alvo()
        ids_deputados = pipeline._obter_ids_deputados()
        if ids_deputados:
            print(f"Coletando frequência para {len(ids_deputados)} deputados no ano {ano}...")
            resultado = pipeline.frequencia_etl.coletar_e_salvar(ano, ids_deputados)
            print(f"✅ Coleta de frequência concluída. {len(resultado)} registros processados.")
        else:
            print("⚠️ Nenhum deputado selecionado. Operação cancelada.")
    except Exception as e:
        logger.error(f"Erro na coleta de frequência: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_coleta_proposicoes():
    """Executa a coleta de proposições legislativas."""
    logger.info("Iniciando coleta de proposições legislativas...")
    try:
        pipeline = ColetaPipeline()
        ano = pipeline._obter_ano_alvo()
        print(f"Coletando proposições para o ano {ano}...")
        resultado = pipeline.proposicoes_etl.coletar_e_salvar(ano)
        print(f"✅ Coleta de proposições concluída. {len(resultado)} proposições processadas.")
    except Exception as e:
        logger.error(f"Erro na coleta de proposições: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_pipeline_completa():
    """Executa a pipeline completa de coleta de dados."""
    logger.info("Iniciando pipeline completa de coleta...")
    try:
        pipeline = ColetaPipeline()
        pipeline.executar_coleta_completa()
    except Exception as e:
        logger.error(f"Erro na pipeline completa: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro: {e}")


def executar_pipeline_etl(ano: int):
    """
    Executa a pipeline ETL completa para um ano específico.
    Esta é a função principal para a automação.
    """
    logger.info(f"Iniciando Pipeline ETL para o ano {ano}")
    try:
        pipeline = ColetaPipeline()
        resultado = pipeline.executar_pipeline_etl(ano)
        
        # Análise do resultado para depuração
        print("\n" + "="*20 + " ANÁLISE DO RESULTADO " + "="*20)
        if resultado and resultado.get("status") == "sucesso":
            print("Pipeline executada com sucesso!")
            for etapa, dados in resultado.get("etapas", {}).items():
                status = dados.get("status")
                if status == "sucesso":
                    dados_saida = dados.get("dados", {})
                    if isinstance(dados_saida, dict):
                        print(f"\nEtapa: {etapa}")
                        for chave, valor in dados_saida.items():
                            if isinstance(valor, list):
                                print(f"  - {chave}: {len(valor)} registros")
                            else:
                                print(f"  - {chave}: {valor}")
                    elif isinstance(dados_saida, list):
                        print(f"\nEtapa: {etapa} - {len(dados_saida)} registros")
                else:
                    print(f"\nEtapa: {etapa} - FALHOU")
                    print(f"  - Erro: {dados.get('erro')}")

        else:
            print("A pipeline falhou ou não retornou um resultado válido.")
            if resultado:
                print(f"Status: {resultado.get('status')}")
                print(f"Erro: {resultado.get('erro')}")

        return resultado
    except Exception as e:
        logger.error(f"Erro na pipeline ETL: {e}", exc_info=True)
        print(f"❌ Ocorreu um erro crítico: {e}")
        return None


def main():
    """Função principal para execução via linha de comando."""
    parser = argparse.ArgumentParser(description="Sistema de Coleta de Dados da Câmara dos Deputados")
    parser.add_argument(
        "--etl",
        type=int,
        help="Executa a pipeline ETL completa para o ano especificado (ex: --etl 2025)"
    )
    args = parser.parse_args()

    setup_logging()
    
    clear_screen()
    print("=" * 60)
    print("    🇧🇷 SISTEMA DE COLETA DE DADOS - CÂMARA DOS DEPUTADOS")
    print("=" * 60)

    if args.etl:
        # Executa a pipeline ETL para o ano especificado
        print(f"🚀 Executando pipeline ETL automatizada para o ano {args.etl}...")
        executar_pipeline_etl(args.etl)
        print("\n🎉 Pipeline ETL concluída!")
        return

    # Se não for modo ETL, exibe o menu interativo
    while True:
        opcao = exibir_menu()

        if opcao == 0:
            print("\n👋 Saindo do sistema...")
            break
        elif opcao == 1:
            executar_coleta_referencia()
        elif opcao == 2:
            executar_coleta_gastos()
        elif opcao == 3:
            executar_coleta_remuneracao()
        elif opcao == 4:
            executar_coleta_emendas()
        elif opcao == 5:
            print("🔍 Funcionalidade de análise cruzada ainda não implementada.")
        elif opcao == 6:
            print("✅ Funcionalidade de validação de qualidade ainda não implementada.")
        elif opcao == 7:
            print("📊 Funcionalidade de verificação de dados ainda não implementada.")
        elif opcao == 8:
            print("🧹 Funcionalidade de limpeza de banco de dados ainda não implementada.")
        elif opcao == 9:
            executar_pipeline_completa()
        elif opcao == 10:
            # Executa a pipeline ETL para o ano atual
            ano_atual = datetime.now().year
            print(f"🚀 Executando pipeline ETL para o ano atual ({ano_atual})...")
            executar_pipeline_etl(ano_atual)
            print("\n🎉 Pipeline ETL concluída!")
        else:
            print("\n⚠️ Opção inválida. Tente novamente.")
        
        input("\nPressione Enter para continuar...")
        clear_screen()


if __name__ == "__main__":
    main()

