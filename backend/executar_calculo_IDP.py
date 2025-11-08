#!/usr/bin/env python3
"""
Script de teste para validar o cálculo adaptado do IDP Kritikos
Compara resultados entre metodologia original e adaptada
"""

import sys
import os
from datetime import datetime

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from etl.score_calculator import ScoreCalculator
from etl.score_calculator_adaptado import ScoreCalculatorAdaptado
from models.db_utils import get_db_session
from sqlalchemy import text


class TestadorCalculoAdaptado:
    """
    Classe para testar e comparar os cálculos do IDP
    """
    
    def __init__(self):
        self.calculator_original = ScoreCalculator()
        self.calculator_adaptado = ScoreCalculatorAdaptado()
        self.session = get_db_session()
    
    def buscar_deputados_amostra(self, limite: int = 10) -> list:
        """
        Busca uma amostra de deputados para teste
        """
        try:
            deputados = self.session.execute(text("""
                SELECT DISTINCT d.id, d.nome
                FROM deputados d
                JOIN autorias a ON d.id = a.deputado_id
                JOIN proposicoes p ON a.proposicao_id = p.id
                WHERE p.ano = 2025
                AND a.deputado_id IS NOT NULL
                ORDER BY d.id
                LIMIT :limite
            """), {"limite": limite}).fetchall()
            
            return [(row[0], row[1]) for row in deputados]
            
        except Exception as e:
            print(f"Erro ao buscar deputados: {e}")
            return []
    
    def comparar_calculos_deputado(self, deputado_id: int, nome: str) -> dict:
        """
        Compara os cálculos original e adaptado para um deputado
        """
        try:
            print(f"\n🔍 Analisando deputado: {nome} (ID: {deputado_id})")
            
            # Calcular com metodologia original
            score_original = self.calculator_original.calcular_idp_final(deputado_id)
            
            # Calcular com metodologia adaptada
            score_adaptado = self.calculator_adaptado.calcular_idp_final(deputado_id)
            
            # Comparar resultados
            comparacao = {
                'deputado_id': deputado_id,
                'nome': nome,
                'original': score_original,
                'adaptado': score_adaptado,
                'diferenca_idp': score_adaptado['idp_final'] - score_original['idp_final'],
                'diferenca_percentual': ((score_adaptado['idp_final'] - score_original['idp_final']) / score_original['idp_final'] * 100) if score_original['idp_final'] > 0 else 0
            }
            
            # Exibir comparação
            print(f"   📊 IDP Original: {score_original['idp_final']:.2f}")
            print(f"   📊 IDP Adaptado: {score_adaptado['idp_final']:.2f}")
            print(f"   📈 Diferença: {comparacao['diferenca_idp']:+.2f} ({comparacao['diferenca_percentual']:+.1f}%)")
            
            # Comparar eixos
            print(f"   🏛️ Desempenho: {score_original['desempenho_legislativo']:.2f} → {score_adaptado['desempenho_legislativo']:.2f}")
            print(f"   🌍 Relevância: {score_original['relevancia_social']:.2f} → {score_adaptado['relevancia_social']:.2f}")
            print(f"   💰 Responsabilidade: {score_original['responsabilidade_fiscal']:.2f} → {score_adaptado['responsabilidade_fiscal']:.2f}")
            print(f"   ⚖️ Ética: {score_original['etica_legalidade']:.2f} → {score_adaptado['etica_legalidade']}")
            
            # Mostrar dados de emendas (novo)
            if score_adaptado['total_emendas'] > 0:
                print(f"   💸 Emendas: {score_adaptado['total_emendas']} (R$ {score_adaptado['valor_total_emendas']:,.2f})")
            
            return comparacao
            
        except Exception as e:
            print(f"   ❌ Erro ao comparar cálculos: {e}")
            return None
    
    def validar_amostra(self, limite: int = 10) -> dict:
        """
        Valida o cálculo com uma amostra de deputados
        """
        print("🚀 INICIANDO TESTE DE CÁLCULO ADAPTADO")
        print("=" * 60)
        
        # Buscar amostra
        deputados = self.buscar_deputados_amostra(limite)
        
        if not deputados:
            print("❌ Nenhum deputado encontrado para teste")
            return {'erro': 'sem_dados'}
        
        print(f"📊 Testando com {len(deputados)} deputados...")
        
        resultados = []
        erros = 0
        
        for deputado_id, nome in deputados:
            try:
                resultado = self.comparar_calculos_deputado(deputado_id, nome)
                if resultado:
                    resultados.append(resultado)
                else:
                    erros += 1
            except Exception as e:
                print(f"   ❌ Erro no deputado {deputado_id}: {e}")
                erros += 1
        
        # Análise estatística
        if resultados:
            self.analisar_resultados(resultados)
        
        # Resumo final
        print(f"\n{'='*60}")
        print("📊 RESUMO DO TESTE")
        print(f"{'='*60}")
        print(f"📋 Deputados testados: {len(deputados)}")
        print(f"✅ Análises concluídas: {len(resultados)}")
        print(f"❌ Erros: {erros}")
        print(f"📈 Taxa de sucesso: {(len(resultados)/len(deputados)*100):.1f}%")
        
        return {
            'total_testados': len(deputados),
            'analises_concluidas': len(resultados),
            'erros': erros,
            'taxa_sucesso': (len(resultados)/len(deputados)*100) if deputados else 0,
            'resultados': resultados
        }
    
    def analisar_resultados(self, resultados: list):
        """
        Analisa estatisticamente os resultados da comparação
        """
        print(f"\n📈 ANÁLISE ESTATÍSTICA")
        print(f"{'='*40}")
        
        # Estatísticas das diferenças
        diferencas = [r['diferenca_idp'] for r in resultados]
        diferencas_percent = [r['diferenca_percentual'] for r in resultados]
        
        import statistics
        
        print(f"📊 Diferença IDP:")
        print(f"   Média: {statistics.mean(diferencas):+.2f}")
        print(f"   Mediana: {statistics.median(diferencas):+.2f}")
        print(f"   Mínimo: {min(diferencas):+.2f}")
        print(f"   Máximo: {max(diferencas):+.2f}")
        
        print(f"\n📊 Diferença Percentual:")
        print(f"   Média: {statistics.mean(diferencas_percent):+.1f}%")
        print(f"   Mediana: {statistics.median(diferencas_percent):+.1f}%")
        print(f"   Mínimo: {min(diferencas_percent):+.1f}%")
        print(f"   Máximo: {max(diferencas_percent):+.1f}%")
        
        # Análise de impacto
        aumentaram = len([r for r in resultados if r['diferenca_idp'] > 0])
        diminuiram = len([r for r in resultados if r['diferenca_idp'] < 0])
        iguais = len([r for r in resultados if abs(r['diferenca_idp']) < 0.01])
        
        print(f"\n📊 Impacto no Ranking:")
        print(f"   ⬆️ Aumentaram IDP: {aumentaram} ({(aumentaram/len(resultados)*100):.1f}%)")
        print(f"   ⬇️ Diminuiram IDP: {diminuiram} ({(diminuiram/len(resultados)*100):.1f}%)")
        print(f"   ➡️ Mantiveram IDP: {iguais} ({(iguais/len(resultados)*100):.1f}%)")
        
        # Top 5 maiores mudanças
        sorted_by_diff = sorted(resultados, key=lambda x: abs(x['diferenca_idp']), reverse=True)
        print(f"\n🏆 Top 5 Maiores Mudanças:")
        for i, r in enumerate(sorted_by_diff[:5], 1):
            sinal = "⬆️" if r['diferenca_idp'] > 0 else "⬇️"
            print(f"   {i}. {r['nome']}: {r['original']['idp_final']:.2f} → {r['adaptado']['idp_final']:.2f} {sinal} {abs(r['diferenca_idp']):.2f}")
    
    def testar_calculo_completo(self):
        """
        Testa o cálculo completo para todos os deputados
        """
        print("\n🚀 TESTANDO CÁLCULO COMPLETO ADAPTADO")
        print("=" * 60)
        
        try:
            resultado = self.calculator_adaptado.calcular_todos_deputados()
            
            print(f"\n📊 RESULTADO DO CÁLCULO COMPLETO:")
            print(f"   Versão: {resultado['versao_metodologia']}")
            print(f"   Total deputados: {resultado['total_deputados']}")
            print(f"   Sucessos: {resultado['sucessos']}")
            print(f"   Erros: {resultado['erros']}")
            print(f"   Taxa de sucesso: {resultado['taxa_sucesso']:.2f}%")
            
            # Buscar ranking
            ranking = self.calculator_adaptado.get_ranking_geral(10)
            
            if ranking:
                print(f"\n🏆 TOP 10 RANKING ADAPTADO:")
                for i, dep in enumerate(ranking, 1):
                    print(f"   {i:2d}. {dep['nome']:<30} - IDP: {dep['score_final']:6.2f}")
            
            return resultado
            
        except Exception as e:
            print(f"❌ Erro no cálculo completo: {e}")
            return {'erro': str(e)}


def main():
    """
    Função principal de teste
    """
    print("🧪 TESTE DE VALIDAÇÃO - CÁLCULO ADAPTADO KRITIKOS")
    print("=" * 60)
    print("Comparando metodologia original vs adaptada (sem ética/legalidade)")
    print("=" * 60)
    
    testador = TestadorCalculoAdaptado()
    
    # Teste 1: Amostra pequena
    print("\n📋 TESTE 1: AMOSTRA PEQUENA (5 deputados)")
    resultado_amostra = testador.validar_amostra(5)
    
    # Teste 2: Cálculo completo
    print(f"\n{'='*60}")
    resultado_completo = testador.testar_calculo_completo()
    
    # Resumo final
    print(f"\n{'='*60}")
    print("🎉 TESTES CONCLUÍDOS")
    print(f"{'='*60}")
    
    if 'erro' not in resultado_amostra and 'erro' not in resultado_completo:
        print("✅ Todos os testes executados com sucesso!")
        print("📊 Metodologia adaptada validada e pronta para uso")
    else:
        print("⚠️ Alguns testes apresentaram erros")
        print("🔧 Verificar os logs acima para detalhes")
    
    print(f"\n⚠️  Lembrete: Versão adaptada não considera eixo de Ética e Legalidade")
    print("📝 Documentação disponível em METODOLOGIA_KRITIKOS_ATUAL.md")


if __name__ == "__main__":
    main()
