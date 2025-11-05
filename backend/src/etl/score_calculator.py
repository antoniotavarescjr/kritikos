#!/usr/bin/env python3
"""
Calculadora de scores dos deputados usando a metodologia Kritikos.
Implementa o cálculo do IDP (Índice de Desempenho Parlamentar).
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

# Adicionar models ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'models'))

from models.db_utils import get_db_session
from sqlalchemy import text
from models.analise_models import AnaliseProposicao, ScoreDeputado, LogProcessamento
from models.politico_models import Deputado
from models.proposicao_models import Proposicao, Autoria


class ScoreCalculator:
    """
    Calculadora de scores dos deputados usando a metodologia Kritikos.
    
    Fórmula do IDP:
    IDP = (Desempenho_Legislativo × 0.35) + 
           (Relevância_Social × 0.30) + 
           (Responsabilidade_Fiscal × 0.20) + 
           (Ética_Legalidade × 0.15)
    """
    
    def __init__(self):
        self.session = get_db_session()
    
    def calcular_desempenho_legislativo(self, deputado_id: int) -> float:
        """
        Calcula o score de Desempenho Legislativo (0-100).
        
        Critérios:
        - Quantidade de proposições apresentadas
        - Diversidade de tipos de proposições
        - Frequência de apresentação
        """
        try:
            # Buscar estatísticas do deputado
            stats = self.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT p.id) as total_props,
                    COUNT(DISTINCT p.tipo) as tipos_diferentes,
                    COUNT(DISTINCT DATE_TRUNC('month', p.data_apresentacao)) as meses_ativos,
                    MIN(p.data_apresentacao) as primeira_prop,
                    MAX(p.data_apresentacao) as ultima_prop
                FROM deputados d
                JOIN autorias a ON d.id = a.deputado_id
                JOIN proposicoes p ON a.proposicao_id = p.id
                WHERE d.id = :deputado_id
                AND p.ano = 2025
                AND a.deputado_id IS NOT NULL
            """), {"deputado_id": deputado_id}).fetchone()
            
            if not stats or stats[0] == 0:
                return 0.0
            
            total_props = stats[0]
            tipos_diferentes = stats[1]
            meses_ativos = stats[2]
            
            # Cálculo baseado na quantidade (máximo 40 pts)
            # Considerando 50+ proposições como excelente
            score_quantidade = min((total_props / 50) * 40, 40)
            
            # Cálculo baseado na diversidade (máximo 30 pts)
            # Considerando 5+ tipos diferentes como excelente
            score_diversidade = min((tipos_diferentes / 5) * 30, 30)
            
            # Cálculo baseado na constância (máximo 30 pts)
            # Considerando atividade em 6+ meses como excelente
            score_constancia = min((meses_ativos / 6) * 30, 30)
            
            desempenho = score_quantidade + score_diversidade + score_constancia
            
            return min(desempenho, 100.0)
            
        except Exception as e:
            print(f"Erro ao calcular desempenho legislativo: {e}")
            return 0.0
    
    def calcular_relevancia_social(self, deputado_id: int) -> float:
        """
        Calcula o score de Relevância Social (0-100).
        
        Critérios:
        - Média dos PARs das proposições não-triviais
        - Número de proposições relevantes
        - Impacto social das propostas
        """
        try:
            # Buscar análises PAR do deputado
            analises = self.session.execute(text("""
                SELECT 
                    ap.par_score,
                    ap.is_trivial,
                    COUNT(*) as count
                FROM analise_proposicoes ap
                JOIN proposicoes p ON ap.proposicao_id = p.id
                JOIN autorias a ON p.id = a.proposicao_id
                WHERE a.deputado_id = :deputado_id
                AND ap.par_score IS NOT NULL
                AND ap.is_trivial = FALSE
                GROUP BY ap.par_score, ap.is_trivial
            """), {"deputado_id": deputado_id}).fetchall()
            
            if not analises:
                return 0.0
            
            # Calcular média dos PARs
            total_parcial = 0
            total_props = 0
            
            for row in analises:
                par_score = row[0] or 0
                count = row[2]
                total_parcial += par_score * count
                total_props += count
            
            if total_props == 0:
                return 0.0
            
            media_par = total_parcial / total_props
            
            # Converter para escala 0-100 (PAR já é 0-100)
            relevancia = media_par
            
            return min(relevancia, 100.0)
            
        except Exception as e:
            print(f"Erro ao calcular relevância social: {e}")
            return 0.0
    
    def calcular_responsabilidade_fiscal(self, deputado_id: int) -> float:
        """
        Calcula o score de Responsabilidade Fiscal (0-100).
        
        Critérios:
        - Média de sustentabilidade fiscal das proposições
        - Penalidades por oneração
        - Propostas com fontes de custeio claras
        """
        try:
            # Buscar análises de sustentabilidade fiscal
            analises = self.session.execute(text("""
                SELECT 
                    ap.sustentabilidade_fiscal,
                    ap.penalidade_oneracao,
                    COUNT(*) as count
                FROM analise_proposicoes ap
                JOIN proposicoes p ON ap.proposicao_id = p.id
                JOIN autorias a ON p.id = a.proposicao_id
                WHERE a.deputado_id = :deputado_id
                AND ap.sustentabilidade_fiscal IS NOT NULL
                AND ap.is_trivial = FALSE
                GROUP BY ap.sustentabilidade_fiscal, ap.penalidade_oneracao
            """), {"deputado_id": deputado_id}).fetchall()
            
            if not analises:
                return 50.0  # Neutro se não há análises
            
            # Calcular média ajustada
            total_ajustado = 0
            total_props = 0
            
            for row in analises:
                sust_fiscal = row[0] or 0
                penalidade = row[1] or 0
                count = row[2]
                
                # Aplicar penalidade
                score_ajustado = max(sust_fiscal - penalidade, 0)
                total_ajustado += score_ajustado * count
                total_props += count
            
            if total_props == 0:
                return 50.0
            
            media_ajustada = total_ajustado / total_props
            
            return min(media_ajustada, 100.0)
            
        except Exception as e:
            print(f"Erro ao calcular responsabilidade fiscal: {e}")
            return 50.0
    
    def calcular_etica_legalidade(self, deputado_id: int) -> float:
        """
        Calcula o score de Ética e Legalidade (0-100).
        
        Critérios:
        - Conformidade das proposições
        - Ausência de irregularidades
        - Qualidade técnica das propostas
        """
        try:
            # Buscar indicadores de qualidade
            stats = self.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT p.id) as total_props,
                    COUNT(DISTINCT CASE WHEN ap.par_score >= 70 THEN p.id END) as props_boas,
                    COUNT(DISTINCT CASE WHEN ap.is_trivial = TRUE THEN p.id END) as props_triviais
                FROM deputados d
                JOIN autorias a ON d.id = a.deputado_id
                JOIN proposicoes p ON a.proposicao_id = p.id
                LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
                WHERE d.id = :deputado_id
                AND p.ano = 2025
                AND a.deputado_id IS NOT NULL
            """), {"deputado_id": deputado_id}).fetchone()
            
            if not stats or stats[0] == 0:
                return 50.0
            
            total_props = stats[0]
            props_boas = stats[1] or 0
            props_triviais = stats[2] or 0
            
            # Cálculo baseado na qualidade (máximo 60 pts)
            score_qualidade = (props_boas / total_props) * 60 if total_props > 0 else 0
            
            # Cálculo baseado na seriedade (máximo 40 pts)
            # Penalizar muitas propostas triviais
            taxa_triviais = props_triviais / total_props if total_props > 0 else 0
            score_seriedade = max(40 - (taxa_triviais * 40), 0)
            
            etica = score_qualidade + score_seriedade
            
            return min(etica, 100.0)
            
        except Exception as e:
            print(f"Erro ao calcular ética e legalidade: {e}")
            return 50.0
    
    def calcular_idp_final(self, deputado_id: int) -> Dict[str, Any]:
        """
        Calcula o IDP final do deputado.
        
        Returns:
            Dicionário com todos os scores e o IDP final
        """
        try:
            # Calcular scores individuais
            desempenho = self.calcular_desempenho_legislativo(deputado_id)
            relevancia = self.calcular_relevancia_social(deputado_id)
            responsabilidade = self.calcular_responsabilidade_fiscal(deputado_id)
            etica = self.calcular_etica_legalidade(deputado_id)
            
            # Aplicar pesos da metodologia Kritikos
            idp_final = (
                desempenho * 0.35 +
                relevancia * 0.30 +
                responsabilidade * 0.20 +
                etica * 0.15
            )
            
            # Buscar estatísticas adicionais
            stats = self.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT p.id) as total_props,
                    COUNT(DISTINCT ap.id) as props_analisadas,
                    COUNT(DISTINCT CASE WHEN ap.is_trivial = TRUE THEN ap.id END) as props_triviais,
                    COUNT(DISTINCT CASE WHEN ap.is_trivial = FALSE THEN ap.id END) as props_relevantes
                FROM deputados d
                JOIN autorias a ON d.id = a.deputado_id
                JOIN proposicoes p ON a.proposicao_id = p.id
                LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
                WHERE d.id = :deputado_id
                AND p.ano = 2025
                AND a.deputado_id IS NOT NULL
            """), {"deputado_id": deputado_id}).fetchone()
            
            return {
                'deputado_id': deputado_id,
                'desempenho_legislativo': round(desempenho, 2),
                'relevancia_social': round(relevancia, 2),
                'responsabilidade_fiscal': round(responsabilidade, 2),
                'etica_legalidade': round(etica, 2),
                'idp_final': round(idp_final, 2),
                'total_proposicoes': stats[0] if stats else 0,
                'props_analisadas': stats[1] if stats else 0,
                'props_triviais': stats[2] if stats else 0,
                'props_relevantes': stats[3] if stats else 0
            }
            
        except Exception as e:
            print(f"Erro ao calcular IDP final: {e}")
            return {
                'deputado_id': deputado_id,
                'desempenho_legislativo': 0.0,
                'relevancia_social': 0.0,
                'responsabilidade_fiscal': 0.0,
                'etica_legalidade': 0.0,
                'idp_final': 0.0,
                'total_proposicoes': 0,
                'props_analisadas': 0,
                'props_triviais': 0,
                'props_relevantes': 0
            }
    
    def salvar_score_deputado(self, deputado_id: int) -> bool:
        """
        Salva o score do deputado no banco de dados.
        
        Args:
            deputado_id: ID do deputado
            
        Returns:
            True se salvo com sucesso, False caso contrário
        """
        try:
            # Calcular scores
            scores = self.calcular_idp_final(deputado_id)
            
            # Verificar se já existe score
            score_existente = self.session.query(ScoreDeputado).filter_by(
                deputado_id=deputado_id
            ).first()
            
            if score_existente:
                # Atualizar score existente
                score_existente.desempenho_legislativo = scores['desempenho_legislativo']
                score_existente.relevancia_social = scores['relevancia_social']
                score_existente.responsabilidade_fiscal = scores['responsabilidade_fiscal']
                score_existente.etica_legalidade = scores['etica_legalidade']
                score_existente.score_final = scores['idp_final']
                score_existente.total_proposicoes = scores['total_proposicoes']
                score_existente.props_analisadas = scores['props_analisadas']
                score_existente.props_triviais = scores['props_triviais']
                score_existente.props_relevantes = scores['props_relevantes']
                score_existente.data_calculo = datetime.utcnow()
            else:
                # Criar novo score
                novo_score = ScoreDeputado(
                    deputado_id=deputado_id,
                    desempenho_legislativo=scores['desempenho_legislativo'],
                    relevancia_social=scores['relevancia_social'],
                    responsabilidade_fiscal=scores['responsabilidade_fiscal'],
                    etica_legalidade=scores['etica_legalidade'],
                    score_final=scores['idp_final'],
                    total_proposicoes=scores['total_proposicoes'],
                    props_analisadas=scores['props_analisadas'],
                    props_triviais=scores['props_triviais'],
                    props_relevantes=scores['props_relevantes'],
                    data_calculo=datetime.utcnow()
                )
                self.session.add(novo_score)
            
            self.session.commit()
            
            # Registrar log
            log = LogProcessamento(
                tipo_processo='score',
                deputado_id=deputado_id,
                status='sucesso',
                dados_saida={'idp_final': scores['idp_final']}
            )
            self.session.add(log)
            self.session.commit()
            
            return True
            
        except Exception as e:
            print(f"Erro ao salvar score do deputado {deputado_id}: {e}")
            self.session.rollback()
            
            # Registrar erro no log
            try:
                log = LogProcessamento(
                    tipo_processo='score',
                    deputado_id=deputado_id,
                    status='erro',
                    mensagem=str(e)
                )
                self.session.add(log)
                self.session.commit()
            except:
                pass
            
            return False
    
    def calcular_todos_deputados(self) -> Dict[str, Any]:
        """
        Calcula scores para todos os deputados com proposições.
        
        Returns:
            Estatísticas do processamento
        """
        try:
            # Buscar todos os deputados com proposições em 2025
            deputados = self.session.execute(text("""
                SELECT DISTINCT d.id
                FROM deputados d
                JOIN autorias a ON d.id = a.deputado_id
                JOIN proposicoes p ON a.proposicao_id = p.id
                WHERE p.ano = 2025
                AND a.deputado_id IS NOT NULL
                ORDER BY d.id
            """)).fetchall()
            
            total_deputados = len(deputados)
            sucessos = 0
            erros = 0
            
            print(f"Calculando scores para {total_deputados} deputados...")
            
            for i, (deputado_id,) in enumerate(deputados, 1):
                print(f"Processando deputado {i}/{total_deputados} (ID: {deputado_id})")
                
                if self.salvar_score_deputado(deputado_id):
                    sucessos += 1
                else:
                    erros += 1
            
            return {
                'total_deputados': total_deputados,
                'sucessos': sucessos,
                'erros': erros,
                'taxa_sucesso': (sucessos / total_deputados * 100) if total_deputados > 0 else 0
            }
            
        except Exception as e:
            print(f"Erro ao calcular todos os deputados: {e}")
            return {
                'total_deputados': 0,
                'sucessos': 0,
                'erros': 0,
                'taxa_sucesso': 0
            }
        finally:
            self.session.close()
    
    def get_ranking_geral(self, limite: int = 100) -> List[Dict[str, Any]]:
        """
        Retorna o ranking geral de deputados.
        
        Args:
            limite: Número máximo de deputados no ranking
            
        Returns:
            Lista com ranking
        """
        try:
            ranking = self.session.execute(text("""
                SELECT 
                    d.id,
                    d.nome,
                    d.email,
                    d.foto_url,
                    sd.score_final,
                    sd.desempenho_legislativo,
                    sd.relevancia_social,
                    sd.responsabilidade_fiscal,
                    sd.etica_legalidade,
                    sd.total_proposicoes,
                    sd.props_relevantes,
                    sd.data_calculo
                FROM scores_deputados sd
                JOIN deputados d ON sd.deputado_id = d.id
                ORDER BY sd.score_final DESC
                LIMIT :limite
            """), {"limite": limite}).fetchall()
            
            resultado = []
            for i, row in enumerate(ranking, 1):
                resultado.append({
                    'posicao': i,
                    'id': row[0],
                    'nome': row[1],
                    'email': row[2],
                    'foto_url': row[3],
                    'score_final': float(row[4]),
                    'desempenho_legislativo': float(row[5]),
                    'relevancia_social': float(row[6]),
                    'responsabilidade_fiscal': float(row[7]),
                    'etica_legalidade': float(row[8]),
                    'total_proposicoes': row[9],
                    'props_relevantes': row[10],
                    'data_calculo': row[11].isoformat() if row[11] else None
                })
            
            return resultado
            
        except Exception as e:
            print(f"Erro ao obter ranking geral: {e}")
            return []
        finally:
            self.session.close()


def calcular_scores_todos():
    """
    Função principal para calcular scores de todos os deputados.
    """
    calculator = ScoreCalculator()
    resultado = calculator.calcular_todos_deputados()
    
    print(f"\n🎉 CÁLCULO DE SCORES CONCLUÍDO")
    print(f"Total deputados: {resultado['total_deputados']}")
    print(f"Sucessos: {resultado['sucessos']}")
    print(f"Erros: {resultado['erros']}")
    print(f"Taxa de sucesso: {resultado['taxa_sucesso']:.2f}%")
    
    return resultado


if __name__ == "__main__":
    calcular_scores_todos()
