"""
Coleta de dados de frequência de deputados da Câmara dos Deputados.

Este módulo implementa a pipeline ETL para coletar, processar e armazenar
dados de frequência e presença dos deputados nas sessões plenárias e em comissões.
"""

import logging
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..models.database import get_db
from ..models.frequencia_models import (
    FrequenciaDeputado, DetalheFrequencia, RankingFrequencia, ResumoFrequenciaMensal
)
from ..models.politico_models import Deputado, Mandato
from .config import get_config
from .etl_utils import ETLBase

logger = logging.getLogger(__name__)


class ColetorFrequencia(ETLBase):
    """
    Classe principal para coleta de dados de frequência dos deputados.
    Herda de ETLBase para usar funcionalidades comuns
    """

    def __init__(self):
        """Inicializa o coletor de frequência usando ETLBase"""
        super().__init__('frequencia')
        print("📊 Coletor de Frequência inicializado")

    def coletar_frequencia_periodo(
        self, 
        ano: int, 
        mes: int, 
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Coleta dados de frequência para um período específico.

        Args:
            ano: Ano de referência
            mes: Mês de referência (1-12)
            session: Sessão do banco de dados. Se None, cria uma nova.

        Returns:
            Dicionário com resultados da coleta.
        """
        inicio = time.time()
        
        if session is None:
            session = next(get_db())
            should_close_session = True
        else:
            should_close_session = False

        try:
            self.logger.info(f"Coletando frequência para {ano}/{mes}")
            
            # Verificar se já foi coletado
            if self._verificar_dados_existentes(ano, mes, session):
                self.logger.info(f"Dados de frequência para {ano}/{mes} já existem")
                return {
                    'status': 'ja_coletado',
                    'ano': ano,
                    'mes': mes,
                    'mensagem': 'Dados já existem no banco'
                }

            # Obter deputados ativos no período
            deputados = self._obter_deputados_ativos(ano, mes, session)
            if not deputados:
                self.logger.warning(f"Nenhum deputado ativo encontrado para {ano}/{mes}")
                return {
                    'status': 'sem_deputados',
                    'ano': ano,
                    'mes': mes,
                    'mensagem': 'Nenhum deputado ativo encontrado'
                }

            # Coletar dados de frequência para cada deputado
            resultados = []
            for deputado in deputados:
                try:
                    resultado = self._coletar_frequencia_deputado(
                        deputado, ano, mes, session
                    )
                    if resultado:
                        resultados.append(resultado)
                except Exception as e:
                    self.logger.error(
                        f"Erro ao coletar frequência do deputado {deputado.id}: {e}"
                    )
                    continue

            # Gerar rankings
            if resultados:
                self._gerar_rankings_mensais(ano, mes, session)
                self._gerar_resumo_mensal(ano, mes, session)

            # Commit das alterações
            session.commit()

            fim = time.time()
            duracao = fim - inicio

            self.logger.info(
                f"Coleta de frequência concluída: {len(resultados)} deputados, "
                f"{duracao:.1f}s"
            )

            return {
                'status': 'sucesso',
                'ano': ano,
                'mes': mes,
                'deputados_processados': len(resultados),
                'duracao': duracao,
                'frequencias_salvas': len(resultados),
                'detalhes_salvos': sum(r.get('detalhes', 0) for r in resultados)
            }

        except Exception as e:
            session.rollback()
            self.logger.error(f"Erro na coleta de frequência para {ano}/{mes}: {e}")
            return {
                'status': 'erro',
                'ano': ano,
                'mes': mes,
                'erro': str(e)
            }
        finally:
            if should_close_session:
                session.close()

    def _verificar_dados_existentes(self, ano: int, mes: int, session: Session) -> bool:
        """Verifica se já existem dados de frequência para o período."""
        count = session.query(FrequenciaDeputado).filter(
            and_(
                FrequenciaDeputado.ano == ano,
                FrequenciaDeputado.mes == mes
            )
        ).count()
        return count > 0

    def _obter_deputados_ativos(self, ano: int, mes: int, session: Session) -> List[Deputado]:
        """Obtém lista de deputados ativos no período."""
        data_referencia = date(ano, mes, 1)
        
        # Buscar deputados com mandatos ativos no período
        deputados = session.query(Deputado).join(Mandato).filter(
            and_(
                Mandato.data_inicio <= data_referencia,
                or_(
                    Mandato.data_fim.is_(None),
                    Mandato.data_fim >= data_referencia
                ),
                Deputado.situacao == 'Exercício'
            )
        ).distinct().all()
        
        return deputados

    def _coletar_frequencia_deputado(
        self, 
        deputado: Deputado, 
        ano: int, 
        mes: int, 
        session: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Coleta dados de frequência de um deputado específico.

        Args:
            deputado: Objeto Deputado
            ano: Ano de referência
            mes: Mês de referência
            session: Sessão do banco de dados

        Returns:
            Dicionário com resultados ou None em caso de erro.
        """
        try:
            # Obter dados da API da Câmara
            url = f"{self.api_config['base_url']}/deputados/{deputado.api_camara_id}/frequencia"
            params = {
                'ano': ano,
                'mes': mes
            }
            dados_frequencia = self.make_request(url, params)
            
            if not dados_frequencia:
                self.logger.warning(
                    f"Sem dados de frequência para deputado {deputado.id} ({ano}/{mes})"
                )
                return None

            # Processar dados principais
            frequencia = FrequenciaDeputado(
                deputado_id=deputado.id,
                ano=ano,
                mes=mes,
                dias_trabalhados=dados_frequencia.get('diasTrabalhados', 0),
                dias_recesso=dados_frequencia.get('diasRecesso', 0),
                faltas_justificadas=dados_frequencia.get('faltasJustificadas', 0),
                faltas_nao_justificadas=dados_frequencia.get('faltasNaoJustificadas', 0),
                licencas=dados_frequencia.get('licencas', 0),
                sessoes_plenario=dados_frequencia.get('sessoesPlenario', 0),
                sessoes_comissoes=dados_frequencia.get('sessoesComissoes', 0),
                percentual_presenca=self._calcular_percentual_presenca(dados_frequencia),
                percentual_comparecimento=self._calcular_percentual_comparecimento(dados_frequencia),
                fonte_dados='API_Camara'
            )
            
            session.add(frequencia)
            session.flush()  # Para obter o ID
            
            # Processar detalhes diários
            detalhes_salvos = 0
            detalhes_api = dados_frequencia.get('detalhes', [])
            
            for detalhe_api in detalhes_api:
                detalhe = DetalheFrequencia(
                    frequencia_id=frequencia.id,
                    deputado_id=deputado.id,
                    data_evento=datetime.strptime(
                        detalhe_api['data'], '%Y-%m-%d'
                    ).date(),
                    tipo_evento=detalhe_api.get('tipoEvento', 'Sessão'),
                    descricao_evento=detalhe_api.get('descricao'),
                    presente=detalhe_api.get('presente', False),
                    justificado=detalhe_api.get('justificado', False),
                    licenca=detalhe_api.get('licenca', False),
                    tipo_presenca=detalhe_api.get('tipoPresenca'),
                    horario_inicio=self._parse_timestamp(detalhe_api.get('horarioInicio')),
                    horario_fim=self._parse_timestamp(detalhe_api.get('horarioFim')),
                    duracao_minutos=detalhe_api.get('duracaoMinutos')
                )
                
                session.add(detalhe)
                detalhes_salvos += 1
            
            return {
                'deputado_id': deputado.id,
                'frequencia_id': frequencia.id,
                'detalhes': detalhes_salvos
            }

        except Exception as e:
            self.logger.error(
                f"Erro ao processar frequência do deputado {deputado.id}: {e}"
            )
            return None

    def _calcular_percentual_presenca(self, dados_frequencia: Dict[str, Any]) -> float:
        """Calcula percentual de presença baseado nos dados."""
        dias_trabalhados = dados_frequencia.get('diasTrabalhados', 0)
        faltas_justificadas = dados_frequencia.get('faltasJustificadas', 0)
        faltas_nao_justificadas = dados_frequencia.get('faltasNaoJustificadas', 0)
        
        total_dias = dias_trabalhados + faltas_nao_justificadas
        if total_dias == 0:
            return 0.0
        
        return round((dias_trabalhados / total_dias) * 100, 2)

    def _calcular_percentual_comparecimento(self, dados_frequencia: Dict[str, Any]) -> float:
        """Calcula percentual de comparecimento (incluindo justificadas)."""
        dias_trabalhados = dados_frequencia.get('diasTrabalhados', 0)
        faltas_justificadas = dados_frequencia.get('faltasJustificadas', 0)
        faltas_nao_justificadas = dados_frequencia.get('faltasNaoJustificadas', 0)
        
        total_dias = dias_trabalhados + faltas_justificadas + faltas_nao_justificadas
        if total_dias == 0:
            return 0.0
        
        dias_comparecimento = dias_trabalhados + faltas_justificadas
        return round((dias_comparecimento / total_dias) * 100, 2)

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Converte string de timestamp para datetime."""
        if not timestamp_str:
            return None
        
        try:
            # Tentar diferentes formatos
            formatos = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f'
            ]
            
            for formato in formatos:
                try:
                    return datetime.strptime(timestamp_str, formato)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None

    def _gerar_rankings_mensais(self, ano: int, mes: int, session: Session) -> None:
        """
        Gera rankings mensais de frequência dos deputados.

        Args:
            ano: Ano de referência
            mes: Mês de referência
            session: Sessão do banco de dados
        """
        try:
            self.logger.info(f"Gerando rankings para {ano}/{mes}")
            
            # Obter todas as frequências do período
            frequencias = session.query(FrequenciaDeputado).filter(
                and_(
                    FrequenciaDeputado.ano == ano,
                    FrequenciaDeputado.mes == mes
                )
            ).all()
            
            if not frequencias:
                return
            
            # Ordenar por percentual de presença (decrescente)
            frequencias_ordenadas = sorted(
                frequencias, 
                key=lambda f: float(f.percentual_presenca or 0), 
                reverse=True
            )
            
            # Calcular totais para rankings
            total_deputados = len(frequencias_ordenadas)
            
            # Agrupar por partido e estado
            partidos = {}
            estados = {}
            
            for i, freq in enumerate(frequencias_ordenadas, 1):
                # Posição geral
                posicao_geral = i
                
                # Obter informações do deputado
                deputado = session.query(Deputado).filter(
                    Deputado.id == freq.deputado_id
                ).first()
                
                if not deputado:
                    continue
                
                # Agrupar por partido
                partido_sigla = self._obter_partido_atual(deputado, session)
                if partido_sigla not in partidos:
                    partidos[partido_sigla] = []
                partidos[partido_sigla].append((freq.percentual_presenca or 0, freq))
                
                # Agrupar por estado
                estado_sigla = self._obter_estado_atual(deputado, session)
                if estado_sigla not in estados:
                    estados[estado_sigla] = []
                estados[estado_sigla].append((freq.percentual_presenca or 0, freq))
            
            # Calcular posições por partido
            posicoes_partido = {}
            for partido_sigla, lista_partido in partidos.items():
                lista_partido.sort(key=lambda x: x[0], reverse=True)
                for i, (_, freq) in enumerate(lista_partido, 1):
                    posicoes_partido[freq.id] = i
            
            # Calcular posições por estado
            posicoes_estado = {}
            for estado_sigla, lista_estado in estados.items():
                lista_estado.sort(key=lambda x: x[0], reverse=True)
                for i, (_, freq) in enumerate(lista_estado, 1):
                    posicoes_estado[freq.id] = i
            
            # Criar registros de ranking
            for i, freq in enumerate(frequencias_ordenadas, 1):
                ranking = RankingFrequencia(
                    frequencia_id=freq.id,
                    deputado_id=freq.deputado_id,
                    ano=ano,
                    mes=mes,
                    posicao_geral=i,
                    posicao_partido=posicoes_partido.get(freq.id),
                    posicao_estado=posicoes_estado.get(freq.id),
                    total_deputados=total_deputados,
                    total_deputados_partido=len(partidos.get(
                        self._obter_partido_atual(
                            session.query(Deputado).filter(
                                Deputado.id == freq.deputado_id
                            ).first(), session
                        ), []
                    )),
                    total_deputados_estado=len(estados.get(
                        self._obter_estado_atual(
                            session.query(Deputado).filter(
                                Deputado.id == freq.deputado_id
                            ).first(), session
                        ), []
                    )),
                    percentil_geral=round((i / total_deputados) * 100, 2),
                    versao_metodologia='v1.0'
                )
                
                session.add(ranking)
            
            self.logger.info(f"Rankings gerados: {total_deputados} deputados")

        except Exception as e:
            self.logger.error(f"Erro ao gerar rankings: {e}")
            raise

    def _obter_partido_atual(self, deputado: Deputado, session: Session) -> str:
        """Obtém sigla do partido atual do deputado."""
        mandato = session.query(Mandato).filter(
            and_(
                Mandato.deputado_id == deputado.id,
                Mandato.data_fim.is_(None)
            )
        ).first()
        
        if mandato and mandato.partido:
            return mandato.partido.sigla
        
        return 'Sem Partido'

    def _obter_estado_atual(self, deputado: Deputado, session: Session) -> str:
        """Obtém sigla do estado atual do deputado."""
        mandato = session.query(Mandato).filter(
            and_(
                Mandato.deputado_id == deputado.id,
                Mandato.data_fim.is_(None)
            )
        ).first()
        
        if mandato and mandato.estado:
            return mandato.estado.sigla
        
        return 'Sem Estado'

    def _gerar_resumo_mensal(self, ano: int, mes: int, session: Session) -> None:
        """
        Gera resumo estatístico mensal de frequência.

        Args:
            ano: Ano de referência
            mes: Mês de referência
            session: Sessão do banco de dados
        """
        try:
            self.logger.info(f"Gerando resumo para {ano}/{mes}")
            
            # Obter estatísticas agregadas
            stats = session.query(
                func.count(FrequenciaDeputado.id).label('total_deputados'),
                func.sum(FrequenciaDeputado.sessoes_plenario).label('total_sessoes'),
                func.sum(FrequenciaDeputado.dias_trabalhados).label('total_dias'),
                func.sum(FrequenciaDeputado.faltas_justificadas).label('total_faltas_just'),
                func.sum(FrequenciaDeputado.faltas_nao_justificadas).label('total_faltas_nao_just'),
                func.avg(FrequenciaDeputado.percentual_presenca).label('media_presenca')
            ).filter(
                and_(
                    FrequenciaDeputado.ano == ano,
                    FrequenciaDeputado.mes == mes
                )
            ).first()
            
            if not stats or stats.total_deputados == 0:
                return
            
            # Contar deputados acima e abaixo da meta (95%)
            acima_meta = session.query(FrequenciaDeputado).filter(
                and_(
                    FrequenciaDeputado.ano == ano,
                    FrequenciaDeputado.mes == mes,
                    FrequenciaDeputado.percentual_presenca >= 95.0
                )
            ).count()
            
            abaixo_meta = stats.total_deputados - acima_meta
            
            # Criar resumo
            resumo = ResumoFrequenciaMensal(
                ano=ano,
                mes=mes,
                total_deputados_ativos=stats.total_deputados,
                total_sessoes_realizadas=stats.total_sessoes or 0,
                total_presencas=stats.total_dias or 0,
                total_ausencias=(stats.total_faltas_just or 0) + (stats.total_faltas_nao_just or 0),
                media_presenca_percentual=round(float(stats.media_presenca or 0), 2),
                media_dias_trabalhados=round(
                    (stats.total_dias or 0) / stats.total_deputados, 2
                ),
                media_faltas_justificadas=round(
                    (stats.total_faltas_just or 0) / stats.total_deputados, 2
                ),
                media_faltas_nao_justificadas=round(
                    (stats.total_faltas_nao_just or 0) / stats.total_deputados, 2
                ),
                deputados_acima_meta_presenca=acima_meta,
                deputados_abaixo_meta_presenca=abaixo_meta,
                fonte_dados='Sistema_Kritikos'
            )
            
            session.add(resumo)
            self.logger.info(f"Resumo gerado para {ano}/{mes}")

        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo: {e}")
            raise

    def coletar_e_salvar(self, ano: int, ids_deputados: List[str]) -> List[Dict[str, Any]]:
        """
        Método principal para coleta e salvamento de dados de frequência.

        Args:
            ano: Ano para coleta
            ids_deputados: Lista de IDs dos deputados

        Returns:
            Lista de resultados da coleta.
        """
        resultados = []
        
        with next(get_db()) as session:
            # Coletar para todos os meses do ano (ou mês atual)
            meses = list(range(1, 13))  # Todos os meses
            
            for mes in meses:
                try:
                    resultado = self.coletar_frequencia_periodo(ano, mes, session)
                    if resultado['status'] == 'sucesso':
                        resultados.append(resultado)
                    elif resultado['status'] != 'ja_coletado':
                        self.logger.warning(
                            f"Falha na coleta {ano}/{mes}: {resultado.get('erro')}"
                        )
                except Exception as e:
                    self.logger.error(f"Erro na coleta {ano}/{mes}: {e}")
                    continue
        
        return resultados


def main():
    """Função principal para execução direta do coletor."""
    setup_logging()
    logger.info("Iniciando coleta de dados de frequência")
    
    coletor = ColetorFrequencia()
    
    # Exemplo: coletar dados do ano atual
    ano_atual = datetime.now().year
    resultados = coletor.coletar_e_salvar(ano_atual, [])
    
    logger.info(f"Coleta concluída: {len(resultados)} períodos processados")


if __name__ == "__main__":
    main()
