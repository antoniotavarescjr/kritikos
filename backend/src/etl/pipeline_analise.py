#!/usr/bin/env python3
"""
Pipeline completo de análise de proposições com agentes Kritikos.
Integra resumo, filtro de trivialidade, análise PAR e cálculo de scores.
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Adicionar paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'agents', 'tools'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'models'))

# Importar ferramentas dos agentes
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'agents', 'tools'))
from document_summarizer_tool import summarize_proposal_text, analyze_proposal_par
from trivial_filter_tool import is_summary_trivial, get_trivial_statistics

# Importar ferramentas de banco
from database_tools import (
    get_proposicao_completa,
    get_texto_completo_proposicao,
    buscar_proposicoes_por_criterio,
    get_proposicoes_para_analise
)

# Importar calculadora de scores
from score_calculator import ScoreCalculator

# Importar modelos
from models.db_utils import get_db_session
from models.analise_models import AnaliseProposicao, LogProcessamento


class PipelineAnalise:
    """
    Pipeline completo para análise de proposições com agentes Kritikos.
    
    Fluxo:
    1. Buscar proposições não analisadas
    2. Gerar resumo com SummarizerAgent
    3. Aplicar filtro de trivialidade
    4. Se não trivial, analisar PAR
    5. Calcular scores dos deputados
    """
    
    def __init__(self):
        self.session = get_db_session()
        self.score_calculator = ScoreCalculator()
    
    def analisar_proposicao(self, proposicao_id: int) -> Dict[str, Any]:
        """
        Analisa uma proposição completa usando o fluxo de agentes.
        
        Args:
            proposicao_id: ID da proposição
            
        Returns:
            Dicionário com resultado da análise
        """
        resultado = {
            'proposicao_id': proposicao_id,
            'sucesso': False,
            'etapas': {},
            'erros': []
        }
        
        try:
            print(f"\n🔍 Analisando proposição {proposicao_id}")
            
            # ETAPA 1: Obter dados completos
            print("1. 📄 Obtendo dados completos...")
            prop = get_proposicao_completa(proposicao_id)
            if not prop:
                raise Exception(f"Proposição {proposicao_id} não encontrada")
            
            resultado['etapas']['dados_completos'] = {
                'sucesso': True,
                'tipo': prop['tipo'],
                'numero': prop['numero'],
                'ano': prop['ano'],
                'ementa': prop['ementa'][:100] + '...' if len(prop['ementa']) > 100 else prop['ementa']
            }
            
            # ETAPA 2: Gerar texto completo
            print("2. 📖 Gerando texto completo...")
            texto_completo = get_texto_completo_proposicao(proposicao_id)
            if not texto_completo:
                raise Exception("Falha ao gerar texto completo")
            
            resultado['etapas']['texto_completo'] = {
                'sucesso': True,
                'tamanho': len(texto_completo)
            }
            
            # ETAPA 3: Verificar se já foi resumido
            analise_existente = self.session.query(AnaliseProposicao).filter_by(
                proposicao_id=proposicao_id
            ).first()
            
            if analise_existente and analise_existente.resumo_texto:
                print("3. 📝 Resumo já existe, pulando geração...")
                resumo = analise_existente.resumo_texto
                resultado['etapas']['resumo'] = {
                    'sucesso': True,
                    'reutilizado': True,
                    'tamanho': len(resumo)
                }
            else:
                print("3. 📝 Gerando resumo...")
                resumo = summarize_proposal_text(texto_completo, proposicao_id)
                if not resumo:
                    raise Exception("Falha ao gerar resumo")
                
                resultado['etapas']['resumo'] = {
                    'sucesso': True,
                    'reutilizado': False,
                    'tamanho': len(resumo)
                }
            
            # ETAPA 4: Aplicar filtro de trivialidade
            if analise_existente and analise_existente.is_trivial is not None:
                print("4. 🔍 Filtro já aplicado, pulando...")
                is_trivial = analise_existente.is_trivial
                resultado['etapas']['filtro_trivial'] = {
                    'sucesso': True,
                    'reutilizado': True,
                    'resultado': is_trivial
                }
            else:
                print("4. 🔍 Aplicando filtro de trivialidade...")
                is_trivial = is_summary_trivial(resumo, proposicao_id)
                resultado['etapas']['filtro_trivial'] = {
                    'sucesso': True,
                    'reutilizado': False,
                    'resultado': is_trivial
                }
            
            # ETAPA 5: Análise PAR (se não trivial)
            if is_trivial:
                print("5. ⏭️ Proposição trivial - pulando análise PAR")
                resultado['etapas']['analise_par'] = {
                    'sucesso': True,
                    'pulado': True,
                    'motivo': 'Proposição trivial'
                }
            else:
                if analise_existente and analise_existente.par_score is not None:
                    print("5. 📊 Análise PAR já existe, pulando...")
                    resultado['etapas']['analise_par'] = {
                        'sucesso': True,
                        'reutilizado': True,
                        'par_score': analise_existente.par_score
                    }
                else:
                    print("5. 📊 Analisando PAR...")
                    analise_par = analyze_proposal_par(resumo, proposicao_id)
                    if not analise_par:
                        raise Exception("Falha na análise PAR")
                    
                    # Parse do JSON
                    try:
                        par_data = json.loads(analise_par)
                        resultado['etapas']['analise_par'] = {
                            'sucesso': True,
                            'reutilizado': False,
                            'par_score': par_data.get('par_final'),
                            'escopo_impacto': par_data.get('escopo_impacto'),
                            'alinhamento_ods': par_data.get('alinhamento_ods'),
                            'inovacao_eficiencia': par_data.get('inovacao_eficiencia'),
                            'sustentabilidade_fiscal': par_data.get('sustentabilidade_fiscal'),
                            'penalidade_oneracao': par_data.get('penalidade_oneracao')
                        }
                    except json.JSONDecodeError as e:
                        raise Exception(f"Erro ao parsear JSON da análise PAR: {e}")
            
            resultado['sucesso'] = True
            print(f"✅ Análise concluída com sucesso!")
            
        except Exception as e:
            erro_msg = str(e)
            resultado['erros'].append(erro_msg)
            print(f"❌ Erro na análise: {erro_msg}")
            
            # Registrar erro no log
            try:
                log = LogProcessamento(
                    tipo_processo='pipeline',
                    proposicao_id=proposicao_id,
                    status='erro',
                    mensagem=erro_msg
                )
                self.session.add(log)
                self.session.commit()
            except:
                pass
        
        return resultado
    
    def analisar_lote_proposicoes(self, limite: int = 50) -> Dict[str, Any]:
        """
        Analisa um lote de proposições não analisadas.
        
        Args:
            limite: Número máximo de proposições a analisar
            
        Returns:
            Estatísticas do processamento
        """
        try:
            # Buscar proposições não analisadas
            props_nao_analisadas = self.session.execute(text("""
                SELECT DISTINCT p.id
                FROM proposicoes p
                LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
                WHERE p.ano = 2025
                AND (ap.id IS NULL OR ap.resumo_texto IS NULL)
                ORDER BY p.data_apresentacao DESC
                LIMIT :limite
            """), {"limite": limite}).fetchall()
            
            total_props = len(props_nao_analisadas)
            if total_props == 0:
                print("🎉 Todas as proposições já foram analisadas!")
                return {
                    'total_proposicoes': 0,
                    'sucessos': 0,
                    'erros': 0,
                    'taxa_sucesso': 100.0
                }
            
            print(f"📋 Analisando {total_props} proposições...")
            
            sucessos = 0
            erros = 0
            
            for i, (prop_id,) in enumerate(props_nao_analisadas, 1):
                print(f"\n{'='*60}")
                print(f"Processando {i}/{total_props} - Proposição {prop_id}")
                print(f"{'='*60}")
                
                resultado = self.analisar_proposicao(prop_id)
                
                if resultado['sucesso']:
                    sucessos += 1
                else:
                    erros += 1
                    print(f"❌ Erros: {resultado['erros']}")
            
            return {
                'total_proposicoes': total_props,
                'sucessos': sucessos,
                'erros': erros,
                'taxa_sucesso': (sucessos / total_props * 100) if total_props > 0 else 0
            }
            
        except Exception as e:
            print(f"Erro ao analisar lote: {e}")
            return {
                'total_proposicoes': 0,
                'sucessos': 0,
                'erros': 1,
                'taxa_sucesso': 0
            }
    
    def calcular_scores_deputados(self) -> Dict[str, Any]:
        """
        Calcula scores de todos os deputados.
        
        Returns:
            Estatísticas do cálculo
        """
        print("\n🎯 CALCULANDO SCORES DOS DEPUTADOS")
        print("="*60)
        
        return self.score_calculator.calcular_todos_deputados()
    
    def executar_pipeline_completo(self, limite_props: int = 50) -> Dict[str, Any]:
        """
        Executa o pipeline completo: análise de proposições + cálculo de scores.
        
        Args:
            limite_props: Limite de proposições para analisar
            
        Returns:
            Estatísticas gerais do processamento
        """
        print("🚀 INICIANDO PIPELINE COMPLETO DE ANÁLISE")
        print("="*80)
        print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"Limite de proposições: {limite_props}")
        print("="*80)
        
        resultado_final = {
            'inicio': datetime.now(),
            'etapas': {},
            'sucesso_geral': False
        }
        
        try:
            # ETAPA 1: Análise de proposições
            print("\n📋 ETAPA 1: ANÁLISE DE PROPOSIÇÕES")
            print("="*50)
            
            resultado_analise = self.analisar_lote_proposicoes(limite_props)
            resultado_final['etapas']['analise_proposicoes'] = resultado_analise
            
            # ETAPA 2: Cálculo de scores
            print("\n🎯 ETAPA 2: CÁLCULO DE SCORES")
            print("="*50)
            
            resultado_scores = self.calcular_scores_deputados()
            resultado_final['etapas']['calculo_scores'] = resultado_scores
            
            # ETAPA 3: Estatísticas finais
            print("\n📊 ETAPA 3: ESTATÍSTICAS FINAIS")
            print("="*50)
            
            stats_trivial = get_trivial_statistics()
            resultado_final['etapas']['estatisticas'] = stats_trivial
            
            resultado_final['sucesso_geral'] = True
            resultado_final['fim'] = datetime.now()
            resultado_final['duracao_segundos'] = (resultado_final['fim'] - resultado_final['inicio']).total_seconds()
            
            # Exibir resumo final
            print(f"\n🎉 PIPELINE CONCLUÍDO COM SUCESSO!")
            print(f"⏱️ Duração total: {resultado_final['duracao_segundos']:.2f} segundos")
            print(f"📋 Proposições analisadas: {resultado_analise['sucessos']}/{resultado_analise['total_proposicoes']}")
            print(f"🎯 Scores calculados: {resultado_scores['sucessos']}/{resultado_scores['total_deputados']}")
            print(f"📊 Taxa de sucesso geral: {((resultado_analise['sucessos'] + resultado_scores['sucessos']) / (resultado_analise['total_proposicoes'] + resultado_scores['total_deputados']) * 100):.2f}%")
            
            return resultado_final
            
        except Exception as e:
            print(f"❌ Erro no pipeline completo: {e}")
            resultado_final['erro_geral'] = str(e)
            resultado_final['fim'] = datetime.now()
            return resultado_final
        finally:
            self.session.close()
    
    def get_relatorio_execucao(self) -> Dict[str, Any]:
        """
        Gera relatório detalhado da execução do pipeline.
        
        Returns:
            Relatório completo com estatísticas
        """
        try:
            # Estatísticas gerais
            stats_gerais = self.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT p.id) as total_props_2025,
                    COUNT(DISTINCT ap.id) as props_analisadas,
                    COUNT(DISTINCT CASE WHEN ap.resumo_texto IS NOT NULL THEN ap.id END) as com_resumo,
                    COUNT(DISTINCT CASE WHEN ap.is_trivial IS NOT NULL THEN ap.id END) as com_filtro,
                    COUNT(DISTINCT CASE WHEN ap.par_score IS NOT NULL THEN ap.id END) as com_par
                FROM proposicoes p
                LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
                WHERE p.ano = 2025
            """)).fetchone()
            
            # Estatísticas de trivialidade
            stats_trivial = get_trivial_statistics()
            
            # Estatísticas de scores
            stats_scores = self.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT sd.id) as deputados_com_score,
                    AVG(sd.score_final) as media_score,
                    MAX(sd.score_final) as max_score,
                    MIN(sd.score_final) as min_score
                FROM scores_deputados sd
            """)).fetchone()
            
            # Logs recentes
            logs_recentes = self.session.execute(text("""
                SELECT 
                    tipo_processo,
                    status,
                    COUNT(*) as quantidade,
                    MAX(data_inicio) as ultimo_registro
                FROM logs_processamento
                WHERE data_inicio >= NOW() - INTERVAL '24 hours'
                GROUP BY tipo_processo, status
                ORDER BY tipo_processo, status
            """)).fetchall()
            
            return {
                'data_geracao': datetime.now().isoformat(),
                'proposicoes': {
                    'total_2025': stats_gerais[0] if stats_gerais else 0,
                    'analisadas': stats_gerais[1] if stats_gerais else 0,
                    'com_resumo': stats_gerais[2] if stats_gerais else 0,
                    'com_filtro': stats_gerais[3] if stats_gerais else 0,
                    'com_par': stats_gerais[4] if stats_gerais else 0,
                    'taxa_analise': (stats_gerais[1] / stats_gerais[0] * 100) if stats_gerais and stats_gerais[0] > 0 else 0
                },
                'trivialidade': stats_trivial,
                'scores': {
                    'deputados_com_score': stats_scores[0] if stats_scores else 0,
                    'media_score': float(stats_scores[1]) if stats_scores and stats_scores[1] else 0,
                    'max_score': float(stats_scores[2]) if stats_scores and stats_scores[2] else 0,
                    'min_score': float(stats_scores[3]) if stats_scores and stats_scores[3] else 0
                },
                'logs_recentes': [
                    {
                        'tipo': log[0],
                        'status': log[1],
                        'quantidade': log[2],
                        'ultimo_registro': log[3].isoformat() if log[3] else None
                    }
                    for log in logs_recentes
                ]
            }
            
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            return {'erro': str(e)}
        finally:
            self.session.close()


def executar_pipeline_analise(limite_props: int = 50):
    """
    Função principal para executar o pipeline completo.
    
    Args:
        limite_props: Número de proposições para analisar
    """
    pipeline = PipelineAnalise()
    resultado = pipeline.executar_pipeline_completo(limite_props)
    
    # Gerar relatório final
    relatorio = pipeline.get_relatorio_execucao()
    
    print(f"\n📋 RELATÓRIO FINAL")
    print("="*50)
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    
    return resultado, relatorio


if __name__ == "__main__":
    # Executar pipeline com limite padrão de 50 proposições
    executar_pipeline_analise(50)
