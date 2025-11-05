"""
Script de Validação de Dados do Banco Kritikos

Este script realiza validações completas nos dados coletados
sem modificar o banco, apenas verificando consistência e integridade.
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
from sqlalchemy import text
from models.db_utils import get_db_session
from utils.common_utils import setup_logging, clear_screen

logger = logging.getLogger(__name__)


class ValidadorBancoDados:
    """
    Classe responsável por validar a integridade dos dados no banco.
    """
    
    def __init__(self):
        self.resultados = {
            'deputados': {},
            'partidos': {},
            'gastos': {},
            'emendas': {},
            'relacionamentos': {},
            'avisos': [],
            'erros': []
        }
        self.data_inicio_hackathon = '2025-06-01'
        
    def validar_deputados(self, session) -> Dict[str, Any]:
        """
        Valida dados dos deputados.
        """
        logger.info("🔍 Validando dados de deputados...")
        
        try:
            # Contagem total de deputados
            total_query = text("SELECT COUNT(*) FROM deputados")
            total_deputados = session.execute(total_query).scalar()
            
            # Deputados em exercício
            em_exercicio_query = text("SELECT COUNT(*) FROM deputados WHERE situacao = 'Exercício'")
            em_exercicio = session.execute(em_exercicio_query).scalar()
            
            # Deputados com mandato recente (pós 06/2025)
            dados_recentes_query = text("""
                SELECT COUNT(DISTINCT d.id) FROM deputados d
                INNER JOIN mandatos m ON d.id = m.deputado_id
                WHERE m.data_inicio >= :data_inicio
            """)
            dados_recentes = session.execute(
                dados_recentes_query, 
                {'data_inicio': self.data_inicio_hackathon}
            ).scalar()
            
            # Deputados sem partido (através de mandatos)
            sem_partido_query = text("""
                SELECT COUNT(DISTINCT d.id) FROM deputados d
                LEFT JOIN mandatos m ON d.id = m.deputado_id
                LEFT JOIN partidos p ON m.partido_id = p.id
                WHERE p.id IS NULL
            """)
            sem_partido = session.execute(sem_partido_query).scalar()
            
            self.resultados['deputados'] = {
                'total': total_deputados,
                'em_exercicio': em_exercicio,
                'dados_recentes': dados_recentes,
                'sem_partido': sem_partido,
                'status': 'OK' if sem_partido == 0 else 'AVISO'
            }
            
            if sem_partido > 0:
                self.resultados['avisos'].append(
                    f"⚠️ {sem_partido} deputados sem partido associado"
                )
            
            logger.info(f"✅ Deputados validados: {total_deputados} total, {em_exercicio} em exercício")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar deputados: {e}")
            self.resultados['erros'].append(f"Erro na validação de deputados: {e}")
            
    def validar_partidos(self, session) -> Dict[str, Any]:
        """
        Valida dados dos partidos.
        """
        logger.info("🔍 Validando dados de partidos...")
        
        try:
            # Contagem total de partidos
            total_query = text("SELECT COUNT(*) FROM partidos")
            total_partidos = session.execute(total_query).scalar()
            
            # Partidos ativos
            ativos_query = text("SELECT COUNT(*) FROM partidos WHERE status = 'Ativo'")
            partidos_ativos = session.execute(ativos_query).scalar()
            
            # Partidos com deputados (através de mandatos)
            com_deputados_query = text("""
                SELECT COUNT(DISTINCT p.id) FROM partidos p
                INNER JOIN mandatos m ON p.id = m.partido_id
            """)
            com_deputados = session.execute(com_deputados_query).scalar()
            
            self.resultados['partidos'] = {
                'total': total_partidos,
                'ativos': partidos_ativos,
                'com_deputados': com_deputados,
                'status': 'OK' if total_partidos >= 20 else 'AVISO'
            }
            
            if total_partidos < 20:
                self.resultados['avisos'].append(
                    f"⚠️ Apenas {total_partidos} partidos encontrados (esperado: ~20)"
                )
            
            logger.info(f"✅ Partidos validados: {total_partidos} total, {partidos_ativos} ativos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar partidos: {e}")
            self.resultados['erros'].append(f"Erro na validação de partidos: {e}")
            
    def validar_gastos(self, session) -> Dict[str, Any]:
        """
        Valida dados dos gastos parlamentares.
        """
        logger.info("🔍 Validando dados de gastos...")
        
        try:
            # Gastos totais
            total_query = text("SELECT COUNT(*) FROM gastos_parlamentares")
            total_gastos = session.execute(total_query).scalar()
            
            # Gastos de 2025 (período hackathon)
            gastos_2025_query = text("""
                SELECT COUNT(*) FROM gastos_parlamentares 
                WHERE ano = 2025 AND mes >= 6
            """)
            gastos_2025 = session.execute(gastos_2025_query).scalar()
            
            # Gastos por mês em 2025
            gastos_por_mes_query = text("""
                SELECT mes, COUNT(*) as quantidade 
                FROM gastos_parlamentares 
                WHERE ano = 2025 AND mes >= 6
                GROUP BY mes 
                ORDER BY mes
            """)
            gastos_por_mes = session.execute(gastos_por_mes_query).fetchall()
            
            # Deputados com gastos recentes
            deputados_com_gastos_query = text("""
                SELECT COUNT(DISTINCT deputado_id) FROM gastos_parlamentares 
                WHERE ano = 2025 AND mes >= 6
            """)
            deputados_com_gastos = session.execute(deputados_com_gastos_query).scalar()
            
            # Deputados sem gastos recentes
            deputados_sem_gastos_query = text("""
                SELECT COUNT(*) FROM deputados d
                WHERE d.id NOT IN (
                    SELECT DISTINCT deputado_id FROM gastos_parlamentares 
                    WHERE ano = 2025 AND mes >= 6
                )
                AND d.situacao = 'Exercício'
            """)
            deputados_sem_gastos = session.execute(deputados_sem_gastos_query).scalar()
            
            self.resultados['gastos'] = {
                'total': total_gastos,
                'gastos_2025': gastos_2025,
                'deputados_com_gastos': deputados_com_gastos,
                'deputados_sem_gastos': deputados_sem_gastos,
                'gastos_por_mes': dict(gastos_por_mes),
                'status': 'OK' if gastos_2025 > 0 else 'AVISO'
            }
            
            if deputados_sem_gastos > 0:
                self.resultados['avisos'].append(
                    f"⚠️ {deputados_sem_gastos} deputados sem gastos recentes (06/2025+)"
                )
            
            logger.info(f"✅ Gastos validados: {gastos_2025} registros em 2025+")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar gastos: {e}")
            self.resultados['erros'].append(f"Erro na validação de gastos: {e}")
            
    def validar_emendas(self, session) -> Dict[str, Any]:
        """
        Valida dados das emendas.
        """
        logger.info("🔍 Validando dados de emendas...")
        
        try:
            # Total de emendas
            total_query = text("SELECT COUNT(*) FROM emendas_parlamentares")
            total_emendas = session.execute(total_query).scalar()
            
            # Emendas de 2025
            emendas_2025_query = text("SELECT COUNT(*) FROM emendas_parlamentares WHERE ano = 2025")
            emendas_2025 = session.execute(emendas_2025_query).scalar()
            
            # Emendas por ano
            emendas_por_ano_query = text("""
                SELECT ano, COUNT(*) as quantidade 
                FROM emendas_parlamentares 
                GROUP BY ano 
                ORDER BY ano DESC
                LIMIT 5
            """)
            emendas_por_ano = session.execute(emendas_por_ano_query).fetchall()
            
            self.resultados['emendas'] = {
                'total': total_emendas,
                'emendas_2025': emendas_2025,
                'emendas_por_ano': dict(emendas_por_ano),
                'status': 'OK'
            }
            
            # É normal não ter emendas para 2025 (ano em curso)
            logger.info(f"✅ Emendas validadas: {total_emendas} total, {emendas_2025} em 2025")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar emendas: {e}")
            self.resultados['erros'].append(f"Erro na validação de emendas: {e}")
            
    def validar_relacionamentos(self, session) -> Dict[str, Any]:
        """
        Valida integridade de relacionamentos.
        """
        logger.info("🔍 Validando relacionamentos...")
        
        try:
            # Gastos com deputados inválidos
            gastos_deputado_invalido_query = text("""
                SELECT COUNT(*) FROM gastos_parlamentares g
                LEFT JOIN deputados d ON g.deputado_id = d.id
                WHERE d.id IS NULL
            """)
            gastos_orfaos = session.execute(gastos_deputado_invalido_query).scalar()
            
            # Emendas com deputados inválidos
            emendas_deputado_invalido_query = text("""
                SELECT COUNT(*) FROM emendas_parlamentares e
                LEFT JOIN deputados d ON e.deputado_id = d.id
                WHERE d.id IS NULL AND e.deputado_id IS NOT NULL
            """)
            emendas_orfas = session.execute(emendas_deputado_invalido_query).scalar()
            
            self.resultados['relacionamentos'] = {
                'gastos_orfaos': gastos_orfaos,
                'emendas_orfas': emendas_orfas,
                'status': 'OK' if gastos_orfaos == 0 and emendas_orfas == 0 else 'ERRO'
            }
            
            if gastos_orfaos > 0:
                self.resultados['erros'].append(
                    f"❌ {gastos_orfaos} gastos sem deputado válido"
                )
                
            if emendas_orfas > 0:
                self.resultados['erros'].append(
                    f"❌ {emendas_orfas} emendas sem deputado válido"
                )
            
            logger.info("✅ Relacionamentos validados")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar relacionamentos: {e}")
            self.resultados['erros'].append(f"Erro na validação de relacionamentos: {e}")
            
    def executar_validacao_completa(self) -> Dict[str, Any]:
        """
        Executa todas as validações e retorna resultado consolidado.
        """
        logger.info("🚀 Iniciando validação completa do banco de dados")
        clear_screen()
        
        print("=" * 60)
        print("     🔍 VALIDAÇÃO DE DADOS - KRIKTIKOS")
        print("=" * 60)
        
        session = get_db_session()
        try:
            # Executar todas as validações
            self.validar_deputados(session)
            self.validar_partidos(session)
            self.validar_gastos(session)
            self.validar_emendas(session)
            self.validar_relacionamentos(session)
            
            # Determinar status geral
            status_geral = 'OK'
            if self.resultados['erros']:
                status_geral = 'ERRO'
            elif self.resultados['avisos']:
                status_geral = 'AVISO'
                
            self.resultados['status_geral'] = status_geral
            self.resultados['data_validacao'] = datetime.now().isoformat()
            
            self.exibir_relatorio()
            
        finally:
            session.close()
            
        return self.resultados
        
    def exibir_relatorio(self):
        """
        Exibe relatório formatado dos resultados.
        """
        print("\n" + "=" * 60)
        print("📋 RELATÓRIO DE VALIDAÇÃO")
        print("=" * 60)
        
        # Deputados
        dep = self.resultados['deputados']
        print(f"\n👥 DEPUTADOS:")
        print(f"   Total: {dep.get('total', 0)}")
        print(f"   Em exercício: {dep.get('em_exercicio', 0)}")
        print(f"   Dados recentes (06/2025+): {dep.get('dados_recentes', 0)}")
        print(f"   Sem partido: {dep.get('sem_partido', 0)}")
        print(f"   Status: {dep.get('status', 'DESCONHECIDO')}")
        
        # Partidos
        par = self.resultados['partidos']
        print(f"\n🏛️ PARTIDOS:")
        print(f"   Total: {par.get('total', 0)}")
        print(f"   Ativos: {par.get('ativos', 0)}")
        print(f"   Com deputados: {par.get('com_deputados', 0)}")
        print(f"   Status: {par.get('status', 'DESCONHECIDO')}")
        
        # Gastos
        gas = self.resultados['gastos']
        print(f"\n💰 GASTOS:")
        print(f"   Total: {gas.get('total', 0)}")
        print(f"   2025 (06/2025+): {gas.get('gastos_2025', 0)}")
        print(f"   Deputados com gastos: {gas.get('deputados_com_gastos', 0)}")
        print(f"   Deputados sem gastos: {gas.get('deputados_sem_gastos', 0)}")
        print(f"   Status: {gas.get('status', 'DESCONHECIDO')}")
        
        if gas.get('gastos_por_mes'):
            print("   Gastos por mês (2025):")
            for mes, qtd in sorted(gas['gastos_por_mes'].items()):
                print(f"     Mês {mes}: {qtd} registros")
        
        # Emendas
        eme = self.resultados['emendas']
        print(f"\n📝 EMENDAS:")
        print(f"   Total: {eme.get('total', 0)}")
        print(f"   2025: {eme.get('emendas_2025', 0)}")
        print(f"   Status: {eme.get('status', 'DESCONHECIDO')}")
        
        if eme.get('emendas_por_ano'):
            print("   Emendas por ano (últimos 5):")
            for ano, qtd in eme['emendas_por_ano'].items():
                print(f"     {ano}: {qtd} registros")
        
        # Relacionamentos
        rel = self.resultados['relacionamentos']
        print(f"\n🔗 RELACIONAMENTOS:")
        print(f"   Gastos órfãos: {rel.get('gastos_orfaos', 0)}")
        print(f"   Emendas órfãs: {rel.get('emendas_orfas', 0)}")
        print(f"   Status: {rel.get('status', 'DESCONHECIDO')}")
        
        # Avisos
        if self.resultados['avisos']:
            print(f"\n⚠️ AVISOS ({len(self.resultados['avisos'])}):")
            for aviso in self.resultados['avisos']:
                print(f"   {aviso}")
        
        # Erros
        if self.resultados['erros']:
            print(f"\n❌ ERROS ({len(self.resultados['erros'])}):")
            for erro in self.resultados['erros']:
                print(f"   {erro}")
        
        # Status geral
        status = self.resultados['status_geral']
        status_emoji = "✅" if status == "OK" else "⚠️" if status == "AVISO" else "❌"
        
        print(f"\n" + "=" * 60)
        print(f"🎯 STATUS GERAL: {status_emoji} {status}")
        print(f"📅 Data da validação: {self.resultados['data_validacao']}")
        
        # Recomendação
        if status == "OK":
            print("\n🎉 BANCO DE DADOS ESTÁ PRONTO PARA O HACKATHON!")
            print("   ✅ Todos os dados consistentes")
            print("   ✅ Integridade verificada")
            print("   ✅ Relacionamentos válidos")
        elif status == "AVISO":
            print("\n⚠️ BANCO DE DADOS FUNCIONAL COM ALGUNS AVISOS")
            print("   🔍 Verifique os avisos acima")
            print("   ✅ Pode ser usado no hackathon")
        else:
            print("\n❌ BANCO DE DADOS COM PROBLEMAS")
            print("   🔧 Corrija os erros antes do hackathon")
            print("   ❌ Não recomendado para uso")
        
        print("=" * 60)


def main():
    """
    Função principal para execução da validação.
    """
    setup_logging()
    logger.info("Iniciando validação do banco de dados Kritikos")
    
    try:
        validador = ValidadorBancoDados()
        resultado = validador.executar_validacao_completa()
        
        # Retornar código de saída baseado no status
        if resultado['status_geral'] == 'OK':
            return 0
        elif resultado['status_geral'] == 'AVISO':
            return 1
        else:
            return 2
            
    except Exception as e:
        logger.error(f"❌ Erro fatal na validação: {e}", exc_info=True)
        return 3


if __name__ == "__main__":
    exit(main())
