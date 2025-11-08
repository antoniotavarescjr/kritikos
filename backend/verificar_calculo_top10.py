#!/usr/bin/env python3
"""
Script para verificar detalhadamente o cálculo do TOP 10 deputados
usando a metodologia Kritikos adaptada.
"""

import sys
import os
from datetime import datetime

# Adicionar models ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.etl.score_calculator_adaptado import ScoreCalculatorAdaptado
from src.models.db_utils import get_db_session
from sqlalchemy import text

def verificar_calculo_top10():
    """Verifica detalhadamente o cálculo do TOP 10"""
    
    print("🔍 VERIFICAÇÃO DETALHADA - CÁLCULO TOP 10 KRITIKOS ADAPTADA")
    print("=" * 80)
    
    calculator = ScoreCalculatorAdaptado()
    session = get_db_session()
    
    try:
        # Buscar TOP 10 do ranking adaptado
        ranking = session.execute(text("""
            SELECT 
                d.id,
                d.nome,
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
            LIMIT 10
        """)).fetchall()
        
        print(f"📊 TOP 10 DEPUTADOS - RANKING ADAPTADO")
        print("=" * 80)
        
        for i, row in enumerate(ranking, 1):
            deputado_id = row[0]
            nome = row[1]
            score_final = float(row[2]) if row[2] else 0
            desempenho = float(row[3]) if row[3] else 0
            relevancia = float(row[4]) if row[4] else 0
            responsabilidade = float(row[5]) if row[5] else 0
            etica = row[6]
            total_props = row[7] or 0
            props_relevantes = row[8] or 0
            data_calculo = row[9]
            
            print(f"\n🏆 #{i} - {nome} (ID: {deputado_id})")
            print(f"   📊 IDP Final: {score_final:.2f}")
            print(f"   🏛️  Desempenho Legislativo: {desempenho:.2f} (peso 41%)")
            print(f"   🌍  Relevância Social: {relevancia:.2f} (peso 35%)")
            print(f"   💰  Responsabilidade Fiscal: {responsabilidade:.2f} (peso 24%)")
            print(f"   ⚖️  Ética e Legalidade: {etica} (NÃO CONSIDERADO)")
            print(f"   📋  Total Proposições: {total_props} | Relevantes: {props_relevantes}")
            
            # Verificar cálculo manual
            calculo_manual = (desempenho * 0.41) + (relevancia * 0.35) + (responsabilidade * 0.24)
            diferenca = abs(score_final - calculo_manual)
            
            print(f"   🔍 Verificação: ({desempenho:.2f} × 0.41) + ({relevancia:.2f} × 0.35) + ({responsabilidade:.2f} × 0.24)")
            print(f"   🔍 Cálculo: {desempenho * 0.41:.2f} + {relevancia * 0.35:.2f} + {responsabilidade * 0.24:.2f} = {calculo_manual:.2f}")
            print(f"   ✅ Diferença: {diferenca:.4f} {'✓' if diferenca < 0.01 else '✗ ERRO'}")
            
            # Buscar detalhes adicionais para verificação
            detalhes = calculator.calcular_idp_final(deputado_id)
            
            print(f"\n   📋 DETALHES COMPLETOS:")
            print(f"   🏛️  Desempenho (calculado): {detalhes['desempenho_legislativo']:.2f}")
            print(f"   🌍  Relevância (calculado): {detalhes['relevancia_social']:.2f}")
            print(f"   💰  Responsabilidade (calculado): {detalhes['responsabilidade_fiscal']:.2f}")
            print(f"   📊 IDP (calculado): {detalhes['idp_final']:.2f}")
            print(f"   💸 Emendas: {detalhes['total_emendas']} (R$ {detalhes['valor_total_emendas']:,.2f})")
            
            # Verificar consistência
            diff_desempenho = abs(desempenho - detalhes['desempenho_legislativo'])
            diff_relevancia = abs(relevancia - detalhes['relevancia_social'])
            diff_responsabilidade = abs(responsabilidade - detalhes['responsabilidade_fiscal'])
            diff_idp = abs(score_final - detalhes['idp_final'])
            
            print(f"\n   🔍 CONSISTÊNCIA DOS DADOS:")
            print(f"   🏛️  Desempenho: {diff_desempenho:.4f} {'✓' if diff_desempenho < 0.01 else '✗'}")
            print(f"   🌍  Relevância: {diff_relevancia:.4f} {'✓' if diff_relevancia < 0.01 else '✗'}")
            print(f"   💰  Responsabilidade: {diff_responsabilidade:.4f} {'✓' if diff_responsabilidade < 0.01 else '✗'}")
            print(f"   📊 IDP: {diff_idp:.4f} {'✓' if diff_idp < 0.01 else '✗'}")
            
            print("-" * 60)
        
        # Análise estatística do TOP 10
        print(f"\n📈 ANÁLISE ESTATÍSTICA DO TOP 10")
        print("=" * 80)
        
        scores = [float(row[2]) for row in ranking if row[2]]
        desempenhos = [float(row[3]) for row in ranking if row[3]]
        relevancias = [float(row[4]) for row in ranking if row[4]]
        responsabilidades = [float(row[5]) for row in ranking if row[5]]
        
        print(f"📊 MÉDIAS DO TOP 10:")
        print(f"   🏆 IDP Final: {sum(scores)/len(scores):.2f}")
        print(f"   🏛️  Desempenho: {sum(desempenhos)/len(desempenhos):.2f}")
        print(f"   🌍  Relevância: {sum(relevancias)/len(relevancias):.2f}")
        print(f"   💰  Responsabilidade: {sum(responsabilidades)/len(responsabilidades):.2f}")
        
        print(f"\n📊 VALORES MÍNIMOS E MÁXIMOS:")
        print(f"   🏆 IDP: min {min(scores):.2f} | max {max(scores):.2f}")
        print(f"   🏛️  Desempenho: min {min(desempenhos):.2f} | max {max(desempenhos):.2f}")
        print(f"   🌍  Relevância: min {min(relevancias):.2f} | max {max(relevancias):.2f}")
        print(f"   💰  Responsabilidade: min {min(responsabilidades):.2f} | max {max(responsabilidades):.2f}")
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    verificar_calculo_top10()
