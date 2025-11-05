"""
Pipeline de coleta de dados da Câmara dos Deputados.

Este módulo implementa uma pipeline ETL completa para coletar, processar
e armazenar dados da API pública da Câmara dos Deputados.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from etl.coleta_emendas_transparencia import ColetorEmendasTransparencia
from etl.coleta_proposicoes import ColetorProposicoes
from etl.config import get_coleta_config, get_data_inicio_coleta, coleta_habilitada, get_tipos_coleta_habilitados
from utils.common_utils import setup_logging, clear_screen, exibir_menu

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
        from etl.coleta_referencia import ColetorDadosCamara
        from etl.coleta_proposicoes import ColetorProposicoes
        
        self.referencia_etl = ColetorDadosCamara()
        self.proposicoes_etl = ColetorProposicoes()
        # Frequência removida conforme solicitado

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
        # Importar database manager para passar sessão do banco
        from models.db_utils import get_db_session
        
        db_session = get_db_session()
        try:
            resumo_execucao["etapas"]["referencia"] = self._executar_etapa(
                "Coleta de Referência",
                lambda: self.referencia_etl.executar_coleta_completa(db_session)
            )
        finally:
            db_session.close()

        # Etapa 2: Coleta de Emendas
        print(f"\n{'='*60}")
        print(f"📝 ETAPA 2/4: Coletando Emendas Parlamentares")
        print(f"{'='*60}")
        
        # Importar database manager para passar sessão do banco
        from models.db_utils import get_db_session
        
        db_session = get_db_session()
        try:
            resumo_execucao["etapas"]["emendas"] = self._executar_etapa(
                "Coleta de Emendas",
                lambda: self.emendas_etl.coletar_emendas_periodo(ano, db=db_session)
            )
        finally:
            db_session.close()

        # Votações e Proposições removidos - Evolução Futura
        print(f"\n{'='*60}")
        print(f"🗳️ ETAPA 3/3: Votações e Proposições (REMOVIDOS)")
        print(f"{'='*60}")
        print("   ❌ Votações e Proposições foram removidos - evolução futura")

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
        print(f"✅ Proposições habilitadas com integração GCS")

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
            # Importar database manager para passar sessão do banco
            from models.db_utils import get_db_session
            
            db_session = get_db_session()
            try:
                resumo_execucao["etapas"]["referencia"] = self._executar_etapa(
                    "Coleta de Referência",
                    lambda: self.referencia_etl.executar_coleta_completa(db_session)
                )
            finally:
                db_session.close()

        # Gastos já são coletados na referência - removido para evitar duplicação
        if coleta_habilitada('gastos'):
            print(f"\n{'='*60}")
            print(f"💰 GASTOS PARLAMENTARES (Já incluídos na Referência)")
            print(f"{'='*60}")
            print("   ✅ Gastos já foram coletados junto com os dados de referência")

        if coleta_habilitada('emendas'):
            print(f"\n{'='*60}")
            print(f"📝 COLETANDO EMENDAS")
            print(f"{'='*60}")
            resumo_execucao["etapas"]["emendas"] = self._executar_etapa(
                "Coleta de Emendas",
                self.emendas_etl.coletar_emendas_periodo,
                ano=2024  # Usar 2024 pois API não tem dados de 2025
            )

        # Coleta de Proposições com GCS
        if coleta_habilitada('proposicoes'):
            print(f"\n{'='*60}")
            print(f"📋 COLETANDO PROPOSIÇÕES (2025 + GCS)")
            print(f"{'='*60}")
            
            # Obter configurações das proposições
            config_props = get_coleta_config('proposicoes')
            ano_coleta = config_props.get('ano_coleta', 2025)
            limite_deputados = config_props.get('limite_deputados_api', 50)
            
            resumo_execucao["etapas"]["proposicoes"] = self._executar_etapa(
                "Coleta de Proposições",
                lambda: self.proposicoes_etl.coletar_por_json(ano_coleta)
            )

        # Votações e Frequência removidos - Evolução Futura
        if coleta_habilitada('votacoes') or coleta_habilitada('frequencia'):
            print(f"\n{'='*60}")
            print(f"🗳️ VOTAÇÕES E FREQUÊNCIA (REMOVIDOS)")
            print(f"{'='*60}")
            print("   ❌ Votações e Frequência foram removidos - evolução futura")

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
            # Executa a pipeline ETL para o ano atual (antiga opção 10)
            ano_atual = datetime.now().year
            pipeline = ColetaPipeline()
            pipeline.executar_pipeline_etl(ano_atual)
        else:
            print("\n⚠️ Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()
