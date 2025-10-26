#!/usr/bin/env python3
"""
Pipeline Específica para Hackathon Kritikos 2025
Foco em dados de deputados, votações e proposições a partir de 07/2025

ETL-HACKATHON: Pipeline otimizada para hackathon
- Limpeza completa de dados existentes
- Coleta focada em deputados (100% completo)
- Coleta de votações (novidade)
- Coleta de proposições via JSON (nova abordagem)
"""

import sys
from pathlib import Path
import time
from datetime import datetime
from typing import Dict, Any

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar coletores
from etl.coleta_referencia import ColetorDadosCamara
from etl.coleta_votacoes import ColetorVotacoes
from etl.coleta_proposicoes_json import ColetorProposicoesJSON
from etl.coleta_proposicoes import ColetorProposicoes

# Importar utilitários
from models.db_utils import get_db_session
from etl.config import get_config

class PipelineHackathon:
    """
    Pipeline otimizada para o hackaton Kritikos 2025
    Foco em dados de deputados e votações recentes
    """
    
    def __init__(self):
        """Inicializa a pipeline do hackathon"""
        self.resultados = {}
        self.inicio_execucao = datetime.now()
        self.hackathon_config = get_config('hackathon')
        
        print("🚀 PIPELINE HACKATHON KRITIKOS 2025")
        print("=" * 60)
        print(f"📅 Início: {self.inicio_execucao.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🎯 Foco: Dados de {self.hackathon_config['data_inicio_hackathon']} em diante")
        print(f"📋 Prioridades: Deputados + Votações + Proposições")
        
        # Inicializar coletores
        self._inicializar_coletores()
        
        # Verificar configurações
        self._verificar_configuracoes()
    
    def _inicializar_coletores(self):
        """Inicializa os coletores com fallback automático"""
        print("\n🔧 Inicializando coletores...")
        
        # Inicializar coletor de votações
        try:
            self.coletor_votacoes = ColetorVotacoes()
            print("   ✅ Coletor de Votações inicializado")
        except Exception as e:
            print(f"   ❌ Erro ao inicializar ColetorVotacoes: {e}")
            self.coletor_votacoes = None
        
        # Inicializar coletor de proposições JSON
        try:
            self.coletor_proposicoes_json = ColetorProposicoesJSON()
            print("   ✅ Coletor de Proposições JSON inicializado")
        except Exception as e:
            print(f"   ❌ Erro ao inicializar ColetorProposicoesJSON: {e}")
            self.coletor_proposicoes_json = None
        
        # Inicializar coletor de proposições antigo (fallback)
        try:
            self.coletor_proposicoes_antigo = ColetorProposicoes()
            print("   ✅ Coletor de Proposições (antigo) inicializado")
        except Exception as e:
            print(f"   ❌ Erro ao inicializar ColetorProposicoes: {e}")
            self.coletor_proposicoes_antigo = None
    
    def _verificar_configuracoes(self):
        """Verifica se as configurações estão corretas para o hackathon"""
        print(f"\n⚙️  CONFIGURAÇÕES DO HACKATHON")
        print("=" * 40)
        
        # Deputados
        dep_config = self.hackathon_config['deputados']
        print(f"👥 Deputados: {dep_config['limite_total']} limite | "
              f"{'✅' if dep_config['apenas_em_exercicio'] else '❌'} apenas em exercício")
        
        # Votações
        vot_config = self.hackathon_config['votacoes']
        print(f"🗳️  Votações: {'✅ HABILITADO' if vot_config['habilitado'] else '❌ DESABILITADO'} | "
              f"{vot_config['limite_total']} limite")
        
        # Proposições
        prop_config = self.hackathon_config['proposicoes']
        print(f"📄 Proposições: {'❌ DESABILITADO' if not prop_config['habilitado'] else '✅ HABILITADO'}")
        
        # Emendas
        emend_config = self.hackathon_config['emendas']
        print(f"📝 Emendas: {'❌ DESABILITADO' if not emend_config['habilitado'] else '✅ HABILITADO'}")
        
        print(f"\n📅 Período de coleta: {self.hackathon_config['data_inicio_hackathon']} a {datetime.now().strftime('%Y-%m-%d')}")
    
    def executar_etapa(self, nome_etapa: str, funcao_etapa, *args, **kwargs) -> Dict[str, Any]:
        """
        Executa uma etapa da pipeline com tratamento de erros e timing
        
        Args:
            nome_etapa: Nome da etapa para logging
            funcao_etapa: Função a ser executada
            *args, **kwargs: Argumentos da função
            
        Returns:
            Dict: Resultados da etapa
        """
        print(f"\n{'='*20} {nome_etapa} {'='*20}")
        inicio_etapa = datetime.now()
        
        try:
            print(f"⏱️ Iniciando {nome_etapa} em {inicio_etapa.strftime('%H:%M:%S')}")
            
            # Executar etapa
            resultado = funcao_etapa(*args, **kwargs)
            
            fim_etapa = datetime.now()
            duracao = (fim_etapa - inicio_etapa).total_seconds()
            
            print(f"✅ {nome_etapa} concluída em {duracao:.1f}s")
            
            # Salvar resultado
            self.resultados[nome_etapa.lower().replace(' ', '_')] = {
                'status': 'sucesso',
                'duracao_segundos': duracao,
                'resultado': resultado,
                'inicio': inicio_etapa,
                'fim': fim_etapa
            }
            
            return resultado
            
        except Exception as e:
            fim_etapa = datetime.now()
            duracao = (fim_etapa - inicio_etapa).total_seconds()
            
            print(f"❌ ERRO em {nome_etapa}: {e}")
            print(f"⏱️ Tempo decorrido: {duracao:.1f}s")
            
            # Salvar erro
            self.resultados[nome_etapa.lower().replace(' ', '_')] = {
                'status': 'erro',
                'duracao_segundos': duracao,
                'erro': str(e),
                'inicio': inicio_etapa,
                'fim': fim_etapa
            }
            
            return {'status': 'erro', 'erro': str(e)}
    
    def executar_coleta_deputados(self, db_session) -> Dict[str, int]:
        """Executa coleta completa de dados de deputados"""
        coletor = ColetorDadosCamara()
        
        resultados = {}
        
        # Coletar partidos
        print("\n🏛️ Coletando partidos...")
        partidos = coletor.buscar_e_salvar_partidos(db_session)
        resultados['partidos'] = partidos
        
        # Coletar deputados
        print("\n👥 Coletando deputados...")
        deputados = coletor.buscar_e_salvar_deputados(db_session)
        resultados['deputados'] = deputados
        
        # Coletar gastos (apenas período do hackathon)
        print("\n💰 Coletando gastos parlamentares...")
        meses_para_coletar = self.hackathon_config['gastos']['meses_para_coletar']
        gastos = coletor.buscar_e_salvar_gastos(db_session, meses_historico=len(meses_para_coletar))
        resultados['gastos'] = gastos
        
        return resultados
    
    def executar_coleta_votacoes(self, db_session) -> Dict[str, int]:
        """Executa coleta de votações"""
        if not self.coletor_votacoes:
            print("❌ Coletor de votações não inicializado")
            return {'status': 'erro', 'erro': 'Coletor não inicializado'}
        
        # Coletar votações do período do hackathon
        resultados = self.coletor_votacoes.buscar_votacoes_periodo(db_session)
        
        # Gerar resumo
        try:
            self.coletor_votacoes.gerar_resumo_votacoes(db_session)
        except Exception as e:
            print(f"⚠️ Erro ao gerar resumo de votações: {e}")
        
        return resultados
    
    def executar_coleta_proposicoes_json(self, db_session) -> Dict[str, int]:
        """
        Executa coleta de proposições usando abordagem JSON com fallback automático
        """
        print("🔧 Coleta de Proposições - Abordagem JSON com Fallback Otimizado")
        
        # Verificar se proposições estão habilitadas
        prop_config = self.hackathon_config.get('proposicoes', {})
        if not prop_config.get('habilitado', False):
            print("⏭️ Proposições desabilitadas nas configurações")
            return {'status': 'desabilitado', 'motivo': 'Proposições desabilitadas'}
        
        # Usar Coletor JSON com fallback automático integrado
        if self.coletor_proposicoes_json:
            try:
                print("   📡 Usando Coletor JSON com fallback automático...")
                
                # Validação de custo e volume
                if not self.coletor_proposicoes_json._validar_custo_volume(db_session):
                    print("   ⚠️ Volume ou custo muito alto, considerando limpeza")
                
                # Validação de disponibilidade do JSON
                if not self.coletor_proposicoes_json._validar_json_disponivel():
                    print("   ⚠️ JSON não está disponível, usando fallback para API tradicional")
                    # Fallback direto para API tradicional
                    from etl.coleta_proposicoes import ColetorProposicoes
                    coletor_antigo = ColetorProposicoes()
                    anos = prop_config.get('anos_para_coletar', [2025])
                    resultados = coletor_antigo.coletar_proposicoes_periodo(anos, db_session)
                    
                    if resultados:
                        print("   ✅ Coletor antigo (fallback) funcionou!")
                        return resultados
                    else:
                        print("   ❌ Coletor antigo não retornou dados")
                        return {'status': 'erro', 'erro': 'Coletor antigo falhou'}
                
                # Executar coleta com fallback automático
                resultados = self.coletor_proposicoes_json.coletar_proposicoes_com_fallback(db_session)
                
                if resultados and resultados.get('proposicoes_salvas', 0) > 0:
                    print("   ✅ Coletor JSON com fallback funcionou!")
                    
                    # Gerar resumo se disponível
                    try:
                        self.coletor_proposicoes_json.gerar_resumo_coleta(db_session)
                    except Exception as e:
                        print(f"   ⚠️ Erro ao gerar resumo JSON: {e}")
                    
                    return resultados
                else:
                    print("   ⚠️ Coletor JSON não retornou dados, mas fallback foi executado")
                    if 'proposicoes_encontradas' in resultados:
                        print(f"   📊 Encontradas: {resultados.get('proposicoes_encontradas', 0)} proposições")
                    if 'proposicoes_filtradas' in resultados:
                        print(f"   🔍 Filtradas: {resultados.get('proposicoes_filtradas', 0)} proposições")
                    
                    if resultados:
                        return resultados
                    else:
                        return {'status': 'erro', 'erro': 'Nenhuma proposição encontrada'}
                        
            except Exception as e:
                print(f"   ❌ Erro no Coletor JSON com fallback: {e}")
                print("   🔄 Tentando fallback manual para API tradicional")
        
        # Fallback manual para coletor antigo
        if self.coletor_proposicoes_antigo:
            try:
                print("   🔄 Usando coletor antigo (fallback manual)...")
                
                # Obter anos para coleta
                anos = prop_config.get('anos_para_coletar', [2025])
                
                resultados = self.coletor_proposicoes_antigo.coletar_proposicoes_periodo(anos, db_session)
                
                if resultados:
                    print("   ✅ Coletor antigo (fallback manual) funcionou!")
                    
                    # Gerar resumo se disponível
                    try:
                        self.coletor_proposicoes_antigo.gerar_resumo_coleta(2025, db_session)
                    except Exception as e:
                        print(f"   ⚠️ Erro ao gerar resumo antigo: {e}")
                    
                    return resultados
                else:
                    print("   ❌ Coletor antigo não retornou dados")
                    
            except Exception as e:
                print(f"   ❌ Erro no coletor antigo: {e}")
        
        # Se chegou aqui, todos os métodos falharam
        print("   ❌ Todos os métodos de coleta de proposições falharam")
        return {'status': 'erro', 'erro': 'Todos os métodos de coleta falharam'}
    
    def _validar_json_disponivel(self) -> bool:
        """
        Valida se o JSON de proposições está disponível
        
        Returns:
            bool: True se disponível
        """
        try:
            import requests
            
            json_url = self.hackathon_config.get('proposicoes', {}).get('json_url')
            if not json_url:
                return False
            
            print(f"   🔍 Validando disponibilidade do JSON: {json_url}")
            
            # Fazer HEAD request para verificar disponibilidade
            response = requests.head(json_url, timeout=10)
            
            if response.status_code == 200:
                content_length = response.headers.get('content-length', '0')
                print(f"   ✅ JSON disponível ({content_length} bytes)")
                return True
            else:
                print(f"   ❌ JSON não disponível (HTTP {response.status_code})")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro na validação do JSON: {e}")
            return False
    
    def gerar_resumo_final(self):
        """Gera resumo final da execução"""
        fim_execucao = datetime.now()
        duracao_total = (fim_execucao - self.inicio_execucao).total_seconds()
        
        print(f"\n{'='*60}")
        print("📋 RESUMO FINAL - PIPELINE HACKATHON")
        print(f"{'='*60}")
        print(f"📅 Início: {self.inicio_execucao.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📅 Fim: {fim_execucao.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"⏱️ Duração total: {duracao_total:.1f}s ({duracao_total/60:.1f}min)")
        
        print(f"\n📊 Resultados por etapa:")
        total_registros = 0
        
        for etapa, dados in self.resultados.items():
            status = dados['status']
            duracao = dados['duracao_segundos']
            
            if status == 'sucesso':
                resultado = dados.get('resultado', {})
                if isinstance(resultado, dict):
                    # Contar registros
                    registros = sum(v for v in resultado.values() if isinstance(v, (int, float)))
                    total_registros += registros
                    
                    # Mostrar detalhes
                    print(f"   ✅ {etapa.replace('_', ' ').title()}: {registros} registros ({duracao:.1f}s)")
                    
                    # Detalhar tipos se for dicionário
                    for tipo, quantidade in resultado.items():
                        if isinstance(quantidade, (int, float)) and quantidade > 0:
                            print(f"      • {tipo}: {int(quantidade)}")
                else:
                    print(f"   ✅ {etapa.replace('_', ' ').title()}: Concluída ({duracao:.1f}s)")
            else:
                erro = dados.get('erro', 'Erro desconhecido')
                print(f"   ❌ {etapa.replace('_', ' ').title()}: {erro} ({duracao:.1f}s)")
        
        print(f"\n🎯 TOTAL GERAL: {total_registros} registros processados")
        
        # Status final
        etapas_sucesso = sum(1 for d in self.resultados.values() if d['status'] == 'sucesso')
        total_etapas = len(self.resultados)
        
        if etapas_sucesso == total_etapas:
            print(f"\n🎉 PIPELINE HACKATHON CONCLUÍDA COM SUCESSO! ({etapas_sucesso}/{total_etapas} etapas)")
        else:
            print(f"\n⚠️ PIPELINE CONCLUÍDA COM ALERTAS ({etapas_sucesso}/{total_etapas} etapas)")
        
        # Recomendações para o hackathon
        print(f"\n💡 RECOMENDAÇÕES PARA O HACKATHON:")
        print(f"   📊 Foco em análise de dados de deputados, votações e proposições")
        print(f"   🗳️  Use os dados de votações para analisar posicionamentos")
        print(f"   💰 Analise padrões de gastos parlamentares")
        print(f"   📄 Analise textos completos das proposições (NLP)")
        print(f"   🏛️  Compare dados entre partidos e estados")
        print(f"   🔗 Cruze proposições com autores e votações")
        
        return {
            'status': 'sucesso' if etapas_sucesso == total_etapas else 'parcial',
            'duracao_total': duracao_total,
            'total_registros': total_registros,
            'etapas_sucesso': etapas_sucesso,
            'total_etapas': total_etapas,
            'resultados_detalhados': self.resultados
        }
    
    def executar_pipeline_hackathon(self) -> Dict[str, Any]:
        """Executa todas as etapas da pipeline do hackathon"""
        
        # Obter sessão do banco
        from models.database import get_db
        db_session = next(get_db())
        
        try:
            # Etapa 1: Coleta de Deputados (prioridade máxima)
            self.executar_etapa(
                "Coleta de Deputados",
                self.executar_coleta_deputados,
                db_session
            )
            
            # Etapa 2: Coleta de Votações (novidade)
            self.executar_etapa(
                "Coleta de Votações",
                self.coletor_votacoes.buscar_votacoes_periodo,
                db_session
            )
            
            # Etapa 3: Coleta de Proposições via JSON (nova abordagem)
            self.executar_etapa(
                "Coleta de Proposições (JSON)",
                self.executar_coleta_proposicoes_json,
                db_session
            )
            
            # Gerar resumo final
            return self.gerar_resumo_final()
            
        except Exception as e:
            print(f"\n❌ ERRO CRÍTICO NA PIPELINE: {e}")
            return {
                'status': 'erro_critico',
                'erro': str(e),
                'duracao_total': (datetime.now() - self.inicio_execucao).total_seconds(),
                'resultados_parciais': self.resultados
            }
            
        finally:
            db_session.close()

def main():
    """Função principal para execução"""
    print("🚀 PIPELINE HACKATHON KRITIKOS 2025")
    print("ETL-HACKATHON: Foco em Deputados + Votações + Proposições")
    print("=" * 60)
    
    # Criar e executar pipeline
    pipeline = PipelineHackathon()
    resultado = pipeline.executar_pipeline_hackathon()
    
    # Mostrar resultado final
    if resultado['status'] == 'sucesso':
        print(f"\n✅ Pipeline do hackathon executada com sucesso!")
        print(f"📊 {resultado['total_registros']} registros processados")
        print(f"⏱️ Duração: {resultado['duracao_total']/60:.1f} minutos")
        print(f"\n🎯 Pronto para o hackathon! Use os dados para suas análises.")
    else:
        print(f"\n⚠️ Pipeline executada com problemas")
        print(f"❌ Status: {resultado['status']}")
    
    return resultado

if __name__ == "__main__":
    main()
