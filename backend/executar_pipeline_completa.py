#!/usr/bin/env python3
"""
Pipeline Completa de Coleta de Dados da Câmara dos Deputados
Executa todas as etapas do ETL de forma organizada e monitorada

ETL-01: Coleta de Dados da API da Câmara
- Coleta de dados de referência (deputados, partidos)
- Coleta de proposições de alto impacto
- Coleta de dados de frequência
- Coleta de emendas
- Armazenamento no Google Cloud Storage
"""

import sys
from pathlib import Path
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar coletores
from etl.coleta_referencia import ColetorDadosCamara
from etl.coleta_proposicoes import ColetorProposicoes
from etl.coleta_emendas import ColetorEmendas

# Importar utilitários
from models.db_utils import get_db_session
from etl.config import get_config

class PipelineCompleta:
    """
    Classe principal para executar toda a pipeline de coleta
    """
    
    def __init__(self):
        """Inicializa a pipeline"""
        self.resultados = {}
        self.inicio_execucao = datetime.now()
        print("🚀 INICIANDO PIPELINE COMPLETA DE COLETA")
        print("=" * 60)
        print(f"📅 Início: {self.inicio_execucao.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔧 Ambiente: {get_config('hackathon', 'ano_limite')}")
    
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
    
    def executar_coleta_referencia(self, db_session) -> Dict[str, int]:
        """Executa coleta de dados de referência"""
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
        
        # Coletar gastos
        print("\n💰 Coletando gastos parlamentares...")
        meses_historico = get_config('hackathon', 'gastos')['meses_historico']
        gastos = coletor.buscar_e_salvar_gastos(db_session, meses_historico=meses_historico)
        resultados['gastos'] = gastos
        
        return resultados
    
    def executar_coleta_proposicoes(self, db_session) -> Dict[str, int]:
        """Executa coleta de proposições de alto impacto"""
        coletor = ColetorProposicoes()
        
        # Usar 2024 que tem mais dados disponíveis
        ano_coleta = 2024
        
        # Coletar proposições do ano
        resultados = coletor.coletar_proposicoes_periodo(ano_coleta, db_session)
        
        # Gerar resumo
        coletor.gerar_resumo_coleta(ano_coleta, db_session)
        
        return resultados
    
    
    def executar_coleta_emendas(self, db_session) -> Dict[str, int]:
        """Executa coleta de emendas"""
        coletor = ColetorEmendas()
        
        # Usar 2024 que tem dados disponíveis
        ano_coleta = 2024
        resultados = coletor.coletar_emendas_ano(ano_coleta, db_session)
        
        return resultados
    
    def gerar_resumo_final(self):
        """Gera resumo final da execução"""
        fim_execucao = datetime.now()
        duracao_total = (fim_execucao - self.inicio_execucao).total_seconds()
        
        print(f"\n{'='*60}")
        print("📋 RESUMO FINAL DA EXECUÇÃO")
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
            print(f"\n🎉 PIPELINE CONCLUÍDA COM SUCESSO! ({etapas_sucesso}/{total_etapas} etapas)")
        else:
            print(f"\n⚠️ PIPELINE CONCLUÍDA COM ALERTAS ({etapas_sucesso}/{total_etapas} etapas)")
        
        return {
            'status': 'sucesso' if etapas_sucesso == total_etapas else 'parcial',
            'duracao_total': duracao_total,
            'total_registros': total_registros,
            'etapas_sucesso': etapas_sucesso,
            'total_etapas': total_etapas,
            'resultados_detalhados': self.resultados
        }
    
    def executar_pipeline_completa(self) -> Dict[str, Any]:
        """Executa todas as etapas da pipeline"""
        
        # Obter sessão do banco
        from models.database import get_db
        db_session = next(get_db())
        
        try:
            # Etapa 1: Coleta de Referência
            self.executar_etapa(
                "Coleta de Referência",
                self.executar_coleta_referencia,
                db_session
            )
            
            # Etapa 2: Coleta de Proposições
            self.executar_etapa(
                "Coleta de Proposições",
                self.executar_coleta_proposicoes,
                db_session
            )
            
            # Etapa 3: Coleta de Emendas
            self.executar_etapa(
                "Coleta de Emendas",
                self.executar_coleta_emendas,
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
    print("🚀 PIPELINE COMPLETA DE COLETA DE DADOS")
    print("ETL-01: Coleta de Dados da API da Câmara")
    print("=" * 60)
    
    # Criar e executar pipeline
    pipeline = PipelineCompleta()
    resultado = pipeline.executar_pipeline_completa()
    
    # Mostrar resultado final
    if resultado['status'] == 'sucesso':
        print(f"\n✅ Pipeline executada com sucesso!")
        print(f"📊 {resultado['total_registros']} registros processados")
        print(f"⏱️ Duração: {resultado['duracao_total']/60:.1f} minutos")
    else:
        print(f"\n⚠️ Pipeline executada com problemas")
        print(f"❌ Status: {resultado['status']}")
    
    return resultado

if __name__ == "__main__":
    main()
