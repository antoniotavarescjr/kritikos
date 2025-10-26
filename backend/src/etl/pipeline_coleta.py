"""
Pipeline de coleta de dados da Câmara dos Deputados.

Este módulo implementa uma pipeline ETL completa para coletar, processar
e armazenar dados da API pública da Câmara dos Deputados.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from .coleta_emendas_transparencia import ColetorEmendasTransparencia
from .config import get_coleta_config, get_data_inicio_coleta, coleta_habilitada, get_tipos_coleta_habilitados, deve_usar_fallback_votacoes
from ..utils.common_utils import setup_logging, clear_screen, exibir_menu

logger = logging.getLogger(__name__)


class ColetaPipeline:
    """
    Pipeline principal para orquestrar a coleta de dados.
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Inicializa a pipeline de coleta.

        Args:
            config: Configurações da ETL. Se None, usa o padrão.
        """
        self.config = config
        self.emendas_etl = ColetorEmendasTransparencia()
        
        # Importar e inicializar coletores disponíveis
        from .coleta_votacoes import ColetorVotacoes
        from .coleta_votacoes_fallback import ColetorVotacoesFallback
        from .coleta_frequencia import ColetorFrequencia
        from .coleta_referencia import ColetorDadosCamara
        
        self.votacoes_etl = ColetorVotacoes()
        self.votacoes_fallback = ColetorVotacoesFallback()
        self.frequencia_etl = ColetorFrequencia()
        self.referencia_etl = ColetorDadosCamara()

    def _executar_etapa(
        self,
        nome_etapa: str,
        funcao_etl,
        ano: Optional[int] = None,
        ids_deputados: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Executa uma etapa da ETL com tratamento de erro e logging.

        Args:
            nome_etapa: Nome descritivo da etapa.
            funcao_etl: Função ETL a ser executada.
            ano: Ano alvo para a coleta.
            ids_deputados: Lista de IDs dos deputados.
            **kwargs: Argumentos adicionais para a função ETL.

        Returns:
            Dicionário com o resultado da etapa.
        """
        logger.info(f"🚀 Iniciando etapa: {nome_etapa}")
        inicio = time.time()

        try:
            if ano and ids_deputados:
                resultado = funcao_etl(ano, ids_deputados, **kwargs)
            elif ano:
                resultado = funcao_etl(ano, **kwargs)
            elif ids_deputados:
                resultado = funcao_etl(ids_deputados, **kwargs)
            else:
                resultado = funcao_etl(**kwargs)

            fim = time.time()
            duracao = fim - inicio

            logger.info(f"✅ Etapa '{nome_etapa}' concluída com sucesso em {duracao:.1f}s.")
            return {
                "status": "sucesso",
                "duracao": duracao,
                "dados": resultado,
            }

        except Exception as e:
            logger.error(f"❌ Erro na etapa '{nome_etapa}': {str(e)}", exc_info=True)
            return {
                "status": "erro",
                "duracao": time.time() - inicio,
                "erro": str(e),
            }

    def _obter_ano_alvo(self) -> int:
        """
        Solicita ao usuário o ano alvo para a coleta.

        Returns:
            Ano informado pelo usuário.
        """
        while True:
            try:
                ano_str = input("📅 Informe o ano para a coleta (ex: 2024): ").strip()
                ano = int(ano_str)
                if 2000 <= ano <= datetime.now().year + 1:
                    return ano
                else:
                    print("⚠️ Ano inválido. Digite um ano entre 2000 e o próximo ano.")
            except ValueError:
                print("⚠️ Entrada inválida. Digite um número inteiro para o ano.")

    def _obter_ids_deputados(self) -> List[str]:
        """
        Busca no banco os IDs dos deputados ativos para o usuário escolher.

        Returns:
            Lista de IDs dos deputados selecionados.
        """
        try:
            deputados = self.db_ops.listar_deputados_ativos()
            if not deputados:
                logger.warning("Nenhum deputado ativo encontrado no banco.")
                return []

            print("\n📋 Deputados Ativos Encontrados:")
            for i, dep in enumerate(deputados, 1):
                print(f"  {i}. {dep['nome']} ({dep['partido']}) - ID: {dep['id']}")

            print("\nOpções:")
            print("  a. Coletar de TODOS os deputados")
            print("  b. Selecionar deputados específicos (informe os números separados por vírgula)")
            print("  c. Cancelar")

            escolha = input("\nEscolha uma opção: ").strip().lower()

            if escolha == 'a':
                return [dep['id'] for dep in deputados]
            elif escolha == 'b':
                numeros_str = input("Informe os números dos deputados (ex: 1,3,5): ").strip()
                indices = [int(n.strip()) - 1 for n in numeros_str.split(',') if n.strip().isdigit()]
                ids_selecionados = []
                for idx in indices:
                    if 0 <= idx < len(deputados):
                        ids_selecionados.append(deputados[idx]['id'])
                    else:
                        print(f"⚠️ Número {idx + 1} é inválido e será ignorado.")
                return ids_selecionados
            elif escolha == 'c':
                return []
            else:
                print("⚠️ Opção inválida.")
                return []

        except Exception as e:
            logger.error(f"Erro ao obter IDs dos deputados: {e}", exc_info=True)
            return []

    def executar_coleta_completa(self) -> Dict[str, Any]:
        """
        Executa a pipeline completa de coleta de dados para um ano específico.

        Returns:
            Dicionário com o resumo de toda a execução.
        """
        logger.info("🚀 Iniciando Pipeline de Coleta Completa")
        clear_screen()
        print("=" * 60)
        print("     🚀 PIPELINE DE COLETA COMPLETA DE DADOS")
        print("=" * 60)

        ano_alvo = self._obter_ano_alvo()
        print(f"\n📅 Ano alvo para a coleta: {ano_alvo}")

        ids_deputados = self._obter_ids_deputados()
        if not ids_deputados:
            print("⚠️ Nenhum deputado selecionado. Encerrando pipeline.")
            return {"status": "cancelado", "motivo": "nenhum deputado selecionado"}

        print(f"\n👥 Deputados selecionados: {len(ids_deputados)}")

        resumo_execucao = {
            "ano_alvo": ano_alvo,
            "deputados_selecionados": len(ids_deputados),
            "etapas": {},
            "inicio": datetime.now().isoformat(),
        }

        # Etapa 1: Coleta de Dados de Referência
        print("\n" + "=" * 60)
        print("📋 ETAPA 1/5: Coletando Dados de Referência (Partidos, Deputados)")
        print("=" * 60)
        resumo_execucao["etapas"]["referencia"] = self._executar_etapa(
            "Coleta de Referência",
            self.referencia_etl.coletar_e_salvar
        )

        # Etapa 2: Coleta de Gastos Parlamentares
        print("\n" + "=" * 60)
        print("💰 ETAPA 2/5: Coletando Gastos Parlamentares (CEAP)")
        print("=" * 60)
        resumo_execucao["etapas"]["gastos"] = self._executar_etapa(
            "Coleta de Gastos",
            self.gastos_etl.coletar_e_salvar,
            ano=ano_alvo,
            ids_deputados=ids_deputados
        )

        # Etapa 3: Coleta de Emendas
        print("\n" + "=" * 60)
        print("📝 ETAPA 3/5: Coletando Emendas Parlamentares")
        print("=" * 60)
        resumo_execucao["etapas"]["emendas"] = self._executar_etapa(
            "Coleta de Emendas",
            self.emendas_etl.coletar_emendas_periodo,
            ano=ano_alvo
        )

        # Etapa 4: Coleta de Votações (com fallback)
        print("\n" + "=" * 60)
        print("🗳️ ETAPA 4/5: Coletando Votações (API + Fallback)")
        print("=" * 60)
        
        # Tentar API primeiro, depois fallback
        resultado_votacoes = self._executar_etapa(
            "Coleta de Votações (API)",
            self.votacoes_etl.buscar_votacoes_periodo,
            ano=ano_alvo
        )
        
        # Se API falhar, usar fallback
        if resultado_votacoes["status"] == "erro" or deve_usar_fallback_votacoes():
            print("   🔄 API falhou ou fallback habilitado, usando arquivos JSON...")
            resumo_execucao["etapas"]["votacoes_fallback"] = self._executar_etapa(
                "Coleta de Votações (Fallback JSON)",
                self.votacoes_fallback.coletar_votacoes_periodo,
                ano=ano_alvo
            )
        else:
            resumo_execucao["etapas"]["votacoes"] = resultado_votacoes

        # Etapa 5: Coleta de Proposições (se habilitada)
        if coleta_habilitada('proposicoes'):
            print("\n" + "=" * 60)
            print("📜 ETAPA 5/5: Coletando Proposições Legislativas")
            print("=" * 60)
            resumo_execucao["etapas"]["proposicoes"] = self._executar_etapa(
                "Coleta de Proposições",
                self.proposicoes_etl.coletar_e_salvar,
                ano=ano_alvo
            )

        resumo_execucao["fim"] = datetime.now().isoformat()
        self._exibir_resumo_final(resumo_execucao)

        return resumo_execucao

    def executar_pipeline_etl(self, ano: int) -> Dict[str, Any]:
        """
        Executa a pipeline ETL completa para um ano específico, sem interação do usuário.

        Args:
            ano: O ano para o qual os dados serão coletados.

        Returns:
            Dicionário com o resumo de toda a execução.
        """
        logger.info(f"🚀 Iniciando Pipeline ETL para o ano {ano}")
        clear_screen()
        print(f"{'='*60}")
        print(f"     🚀 PIPELINE ETL - ANO {ano}")
        print(f"{'='*60}")

        resumo_execucao = {
            "ano_alvo": ano,
            "etapas": {},
            "inicio": datetime.now().isoformat(),
        }

        # Etapa 1: Coleta de Dados de Referência
        print(f"\n{'='*60}")
        print(f"📋 ETAPA 1/4: Coletando Dados de Referência (Partidos, Deputados)")
        print(f"{'='*60}")
        resumo_execucao["etapas"]["referencia"] = self._executar_etapa(
            "Coleta de Referência",
            self.referencia_etl.coletar_e_salvar
        )

        # Etapa 2: Coleta de Gastos
        print(f"\n{'='*60}")
        print(f"💰 ETAPA 2/4: Coletando Gastos Parlamentares (CEAP)")
        print(f"{'='*60}")
        resumo_execucao["etapas"]["gastos"] = self._executar_etapa(
            "Coleta de Gastos",
            self.gastos_etl.coletar_e_salvar,
            ano=ano
        )

        # Etapa 3: Coleta de Votações (com fallback)
        print(f"\n{'='*60}")
        print(f"🗳️ ETAPA 3/4: Coletando Votações (API + Fallback)")
        print(f"{'='*60}")
        
        # Tentar API primeiro, depois fallback
        resultado_votacoes = self._executar_etapa(
            "Coleta de Votações (API)",
            self.votacoes_etl.buscar_votacoes_periodo,
            ano=ano
        )
        
        # Se API falhar, usar fallback
        if resultado_votacoes["status"] == "erro" or deve_usar_fallback_votacoes():
            print("   🔄 API falhou ou fallback habilitado, usando arquivos JSON...")
            resumo_execucao["etapas"]["votacoes_fallback"] = self._executar_etapa(
                "Coleta de Votações (Fallback JSON)",
                self.votacoes_fallback.coletar_votacoes_periodo,
                ano=ano
            )
        else:
            resumo_execucao["etapas"]["votacoes"] = resultado_votacoes

        # Etapa 4: Coleta de Proposições (se habilitada)
        if coleta_habilitada('proposicoes'):
            print(f"\n{'='*60}")
            print(f"📜 ETAPA 4/4: Coletando Proposições Legislativas")
            print(f"{'='*60}")
            resumo_execucao["etapas"]["proposicoes"] = self._executar_etapa(
                "Coleta de Proposições",
                self.proposicoes_etl.coletar_e_salvar,
                ano=ano
            )

        resumo_execucao["fim"] = datetime.now().isoformat()
        self._exibir_resumo_final(resumo_execucao)

        return resumo_execucao

    def executar_pipeline_configurado(self) -> Dict[str, Any]:
        """
        Executa pipeline usando configurações centralizadas de coleta.
        Respeita o período 06/2025+ e exclui proposições.
        """
        logger.info("🚀 Iniciando Pipeline Configurado (06/2025+)")
        clear_screen()
        print("=" * 60)
        print("     🚀 PIPELINE CONFIGURADO - 06/2025+")
        print("=" * 60)

        # Obter configurações centralizadas
        data_inicio = get_data_inicio_coleta()
        tipos_habilitados = get_tipos_coleta_habilitados()
        
        print(f"📅 Período de coleta: {data_inicio} até hoje")
        print(f"🔧 Tipos habilitados: {', '.join(tipos_habilitados)}")
        print(f"❌ Proposições desabilitadas conforme configuração")

        resumo_execucao = {
            "data_inicio": data_inicio,
            "tipos_habilitados": tipos_habilitados,
            "etapas": {},
            "inicio": datetime.now().isoformat(),
        }

        # Executar apenas coletores habilitados (exceto proposições)
        if coleta_habilitada('referencia'):
            print(f"\n{'='*60}")
            print(f"📋 COLETANDO DADOS DE REFERÊNCIA")
            print(f"{'='*60}")
            resumo_execucao["etapas"]["referencia"] = self._executar_etapa(
                "Coleta de Referência",
                self.referencia_etl.coletar_e_salvar
            )

        if coleta_habilitada('gastos'):
            print(f"\n{'='*60}")
            print(f"💰 COLETANDO GASTOS PARLAMENTARES")
            print(f"{'='*60}")
            resumo_execucao["etapas"]["gastos"] = self._executar_etapa(
                "Coleta de Gastos",
                self.gastos_etl.coletar_e_salvar,
                ano=2025  # Ano atual conforme configuração
            )

        if coleta_habilitada('emendas'):
            print(f"\n{'='*60}")
            print(f"📝 COLETANDO EMENDAS")
            print(f"{'='*60}")
            resumo_execucao["etapas"]["emendas"] = self._executar_etapa(
                "Coleta de Emendas",
                self.emendas_etl.coletar_emendas_periodo,
                ano=2024  # Usar 2024 pois API não tem dados de 2025
            )

        if coleta_habilitada('votacoes'):
            print(f"\n{'='*60}")
            print(f"🗳️ COLETANDO VOTAÇÕES (API + FALLBACK)")
            print(f"{'='*60}")
            
            # Tentar API primeiro, depois fallback
            resultado_votacoes = self._executar_etapa(
                "Coleta de Votações (API)",
                self.votacoes_etl.buscar_votacoes_periodo,
                ano=2025
            )
            
            # Se API falhar, usar fallback
            if resultado_votacoes["status"] == "erro" or deve_usar_fallback_votacoes():
                print("   🔄 API falhou ou fallback habilitado, usando arquivos JSON...")
                resumo_execucao["etapas"]["votacoes_fallback"] = self._executar_etapa(
                    "Coleta de Votações (Fallback JSON)",
                    self.votacoes_fallback.coletar_votacoes_periodo,
                    ano=2024  # Usar 2024 pois tem dados completos
                )
            else:
                resumo_execucao["etapas"]["votacoes"] = resultado_votacoes

        if coleta_habilitada('frequencia'):
            print(f"\n{'='*60}")
            print(f"📊 COLETANDO FREQUÊNCIA DE DEPUTADOS")
            print(f"{'='*60}")
            resumo_execucao["etapas"]["frequencia"] = self._executar_etapa(
                "Coleta de Frequência",
                self.frequencia_etl.coletar_e_salvar,
                ano=2024  # Usar 2024 pois tem dados completos
            )

        resumo_execucao["fim"] = datetime.now().isoformat()
        self._exibir_resumo_final_configurado(resumo_execucao)

        return resumo_execucao

    def _exibir_resumo_final_configurado(self, resumo: Dict[str, Any]):
        """Exibe resumo do pipeline configurado."""
        print("\n" + "=" * 60)
        print("📋 RESUMO FINAL DA EXECUÇÃO CONFIGURADA")
        print("=" * 60)

        inicio = datetime.fromisoformat(resumo["inicio"])
        fim = datetime.fromisoformat(resumo["fim"])
        duracao_total = (fim - inicio).total_seconds()

        print(f"📅 Período: {resumo['data_inicio']} até hoje")
        print(f"📅 Início: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📅 Fim: {fim.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"⏱️ Duração total: {duracao_total:.1f}s ({duracao_total / 60:.1f}min)\n")

        total_geral = 0
        for nome_etapa, dados_etapa in resumo["etapas"].items():
            status = dados_etapa.get("status", "desconhecido")
            duracao = dados_etapa.get("duracao", 0)
            registros = 0

            if status == "sucesso":
                dados = dados_etapa.get("dados", {})
                if isinstance(dados, list):
                    registros = len(dados)
                elif isinstance(dados, dict):
                    registros = sum(len(v) if isinstance(v, list) else 1 for v in dados.values())
                
                total_geral += registros
                print(f"   ✅ {nome_etapa.title()}: {registros} registros ({duracao:.1f}s)")
            else:
                erro = dados_etapa.get("erro", "Erro desconhecido")
                print(f"   ❌ {nome_etapa.title()}: FALHOU ({duracao:.1f}s) - {erro}")

        print(f"\n🎯 TOTAL GERAL: {total_geral} registros processados")
        print(f"🔧 Tipos habilitados: {', '.join(resumo['tipos_habilitados'])}")
        print("\n🎉 PIPELINE CONFIGURADO CONCLUÍDO COM SUCESSO!")

    def _exibir_resumo_final(self, resumo: Dict[str, Any]):
        """Exibe um resumo detalhado da execução da pipeline."""
        print("\n" + "=" * 60)
        print("📋 RESUMO FINAL DA EXECUÇÃO")
        print("=" * 60)

        inicio = datetime.fromisoformat(resumo["inicio"])
        fim = datetime.fromisoformat(resumo["fim"])
        duracao_total = (fim - inicio).total_seconds()

        print(f"📅 Início: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📅 Fim: {fim.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"⏱️ Duração total: {duracao_total:.1f}s ({duracao_total / 60:.1f}min)\n")

        total_geral = 0
        for nome_etapa, dados_etapa in resumo["etapas"].items():
            status = dados_etapa.get("status", "desconhecido")
            duracao = dados_etapa.get("duracao", 0)
            registros = 0

            if status == "sucesso":
                dados = dados_etapa.get("dados", {})
                if isinstance(dados, list):
                    registros = len(dados)
                elif isinstance(dados, dict):
                    # Caso especial para referência que pode ter múltiplos tipos
                    registros = sum(len(v) if isinstance(v, list) else 1 for v in dados.values())
                
                total_geral += registros
                print(f"   ✅ {nome_etapa.title()}: {registros} registros ({duracao:.1f}s)")
            else:
                erro = dados_etapa.get("erro", "Erro desconhecido")
                print(f"   ❌ {nome_etapa.title()}: FALHOU ({duracao:.1f}s) - {erro}")

        print(f"\n🎯 TOTAL GERAL: {total_geral} registros processados")
        print("\n🎉 PIPELINE CONCLUÍDA COM SUCESSO!")


def main():
    """
    Função principal para execução da pipeline via linha de comando.
    """
    setup_logging()
    logger.info("Iniciando a aplicação de coleta de dados da Câmara dos Deputados.")

    while True:
        opcao = exibir_menu()

        if opcao == 0:
            print("\n👋 Saindo do sistema...")
            break
        elif opcao == 1:
            pipeline = ColetaPipeline()
            pipeline._executar_etapa("Coleta de Referência", pipeline.referencia_etl.coletar_e_salvar)
        elif opcao == 2:
            pipeline = ColetaPipeline()
            ano = pipeline._obter_ano_alvo()
            ids = pipeline._obter_ids_deputados()
            if ids:
                pipeline._executar_etapa("Coleta de Gastos", pipeline.gastos_etl.coletar_e_salvar, ano=ano, ids_deputados=ids)
        elif opcao == 3:
            pipeline = ColetaPipeline()
            ano = pipeline._obter_ano_alvo()
            ids = pipeline._obter_ids_deputados()
            if ids:
                pipeline._executar_etapa("Coleta de Remuneração", pipeline.remuneracao_etl.coletar_e_salvar, ano=ano, ids_deputados=ids)
        elif opcao == 4:
            pipeline = ColetaPipeline()
            ano = pipeline._obter_ano_alvo()
            pipeline._executar_etapa("Coleta de Emendas", pipeline.emendas_etl.coletar_e_salvar, ano=ano)
        elif opcao == 5:
            print("🔍 Funcionalidade de análise cruzada ainda não implementada.")
        elif opcao == 6:
            print("✅ Funcionalidade de validação de qualidade ainda não implementada.")
        elif opcao == 7:
            print("📊 Funcionalidade de verificação de dados ainda não implementada.")
        elif opcao == 8:
            print("🧹 Funcionalidade de limpeza de banco de dados ainda não implementada.")
        elif opcao == 9:
            pipeline = ColetaPipeline()
            pipeline.executar_coleta_completa()
        elif opcao == 10:
            # Executa a pipeline ETL para o ano atual
            ano_atual = datetime.now().year
            pipeline = ColetaPipeline()
            pipeline.executar_pipeline_etl(ano_atual)
        else:
            print("\n⚠️ Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()
