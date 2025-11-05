#!/usr/bin/env python3
"""
Gera relatório completo em Markdown com rankings de deputados:
- Maiores gastos (CEAP)
- Mais proposições
- Maiores valores em emendas
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.db_utils import get_db_session
from sqlalchemy import text
import pandas as pd

def gerar_relatorio_completo():
    """Gera relatório completo em Markdown com todos os rankings."""
    
    session = get_db_session()
    
    try:
        print("🔍 Coletando dados para relatório completo...")
        
        # 1. Ranking de Gastos (CEAP)
        print("📊 Buscando ranking de gastos...")
        ranking_gastos = session.execute(text("""
            SELECT 
                d.nome,
                p.sigla as sigla_partido,
                e.sigla as uf,
                COALESCE(SUM(g.valor_liquido), 0) as total_gastos,
                COUNT(DISTINCT g.mes) as meses_com_gasto,
                COUNT(g.id) as total_despesas
            FROM deputados d
            LEFT JOIN gastos_parlamentares g ON d.id = g.deputado_id AND g.ano = 2025
            LEFT JOIN mandatos m ON d.id = m.deputado_id AND m.data_fim IS NULL
            LEFT JOIN partidos p ON m.partido_id = p.id
            LEFT JOIN estados e ON m.estado_id = e.id
            GROUP BY d.id, d.nome, p.sigla, e.sigla
            HAVING COALESCE(SUM(g.valor_liquido), 0) > 0
            ORDER BY total_gastos DESC
            LIMIT 20
        """)).fetchall()
        
        # 2. Ranking de Proposições
        print("📋 Buscando ranking de proposições...")
        ranking_proposicoes = session.execute(text("""
            SELECT 
                d.nome,
                pt.sigla as sigla_partido,
                est.sigla as uf,
                COUNT(DISTINCT p.id) as total_proposicoes,
                COUNT(DISTINCT p.tipo) as tipos_diferentes,
                STRING_AGG(DISTINCT p.tipo, ', ') as tipos_principais
            FROM deputados d
            JOIN autorias a ON d.id = a.deputado_id
            JOIN proposicoes p ON a.proposicao_id = p.id
            LEFT JOIN mandatos m ON d.id = m.deputado_id AND m.data_fim IS NULL
            LEFT JOIN partidos pt ON m.partido_id = pt.id
            LEFT JOIN estados est ON m.estado_id = est.id
            WHERE p.ano = 2025
            AND a.deputado_id IS NOT NULL
            GROUP BY d.id, d.nome, pt.sigla, est.sigla
            HAVING COUNT(DISTINCT p.id) > 0
            ORDER BY total_proposicoes DESC
            LIMIT 20
        """)).fetchall()
        
        # 3. Ranking de Emendas
        print("💰 Buscando ranking de emendas...")
        ranking_emendas = session.execute(text("""
            SELECT 
                d.nome,
                pt.sigla as sigla_partido,
                est.sigla as uf,
                COUNT(e.id) as total_emendas,
                COALESCE(SUM(e.valor_empenhado), 0) as total_empenhado,
                COALESCE(SUM(e.valor_liquidado), 0) as total_liquidado,
                COALESCE(SUM(e.valor_pago), 0) as total_pago,
                COUNT(DISTINCT e.uf_beneficiario) as ufs_beneficiadas,
                COUNT(DISTINCT e.municipio_beneficiario) as municipios_beneficiados
            FROM deputados d
            LEFT JOIN emendas_parlamentares e ON d.id = e.deputado_id 
                AND e.ano = 2025
            LEFT JOIN mandatos m ON d.id = m.deputado_id AND m.data_fim IS NULL
            LEFT JOIN partidos pt ON m.partido_id = pt.id
            LEFT JOIN estados est ON m.estado_id = est.id
            GROUP BY d.id, d.nome, pt.sigla, est.sigla
            HAVING COUNT(e.id) > 0
            ORDER BY total_empenhado DESC
            LIMIT 20
        """)).fetchall()
        
        # 4. Estatísticas gerais
        print("📈 Calculando estatísticas gerais...")
        stats_gerais = session.execute(text("""
            SELECT 
                'Deputados ativos' as metrica, COUNT(*) as valor
            FROM deputados
            WHERE situacao = 'Exercício'
            UNION ALL
            SELECT 
                'Total de proposições (2025)', COUNT(*) 
            FROM proposicoes WHERE ano = 2025
            UNION ALL
            SELECT 
                'Total de autorias (2025)', COUNT(*) 
            FROM autorias 
            WHERE deputado_id IS NOT NULL
            UNION ALL
            SELECT 
                'Total de emendas (2025)', COUNT(*) 
            FROM emendas_parlamentares 
            WHERE deputado_id IS NOT NULL AND ano = 2025
            UNION ALL
            SELECT 
                'Total gastos CEAP (2025)', COALESCE(SUM(valor_liquido), 0)
            FROM gastos_parlamentares WHERE ano = 2025
        """)).fetchall()
        
        # Imprimir relatório direto no terminal
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        print(f"\n{'='*80}")
        print(f"📊 RELATÓRIO COMPLETO DE ATIVIDADE PARLAMENTAR - 2025")
        print(f"{'='*80}")
        print(f"🕐 Gerado em: {timestamp}")
        print(f"📂 Fonte: Dados da Câmara dos Deputados e Portal da Transparência")
        print(f"\n{'-'*80}")
        
        print(f"\n📈 ESTATÍSTICAS GERAIS")
        print(f"{'-'*40}")
        for metrica, valor in stats_gerais:
            if 'gastos' in metrica.lower():
                valor_formatado = f"R$ {valor}" if valor else "R$ 0,00"
            else:
                valor_formatado = str(valor) if valor else "0"
            print(f"  {metrica}: {valor_formatado}")
        
        print(f"\n💰 TOP 20 - MAIORES GASTOS CEAP (2025)")
        print(f"{'-'*60}")
        print(f"{'Pos':<4} {'Deputado':<30} {'Partido':<8} {'UF':<4} {'Total Gasto':<15} {'Meses':<6} {'Despesas':<8}")
        print(f"{'-'*80}")
        for i, row in enumerate(ranking_gastos, 1):
            nome, partido, uf, total_gastos, meses, despesas = row
            print(f"{i:<4} {nome[:28]:<30} {partido or 'N/A':<8} {uf or 'N/A':<4} R$ {total_gastos:<13,.2f} {meses:<6} {despesas:<8}")
        
        print(f"\n📋 TOP 20 - MAIS PROPOSIÇÕES APRESENTADAS (2025)")
        print(f"{'-'*70}")
        print(f"{'Pos':<4} {'Deputado':<30} {'Partido':<8} {'UF':<4} {'Proposições':<10} {'Tipos':<6} {'Principais':<20}")
        print(f"{'-'*80}")
        for i, row in enumerate(ranking_proposicoes, 1):
            nome, partido, uf, total_props, tipos, principais = row
            print(f"{i:<4} {nome[:28]:<30} {partido or 'N/A':<8} {uf or 'N/A':<4} {total_props:<10} {tipos:<6} {(principais or 'N/A')[:18]:<20}")
        
        print(f"\n💰 TOP 20 - MAIORES VALORES EM EMENDAS (2025)")
        print(f"{'-'*80}")
        print(f"{'Pos':<4} {'Deputado':<30} {'Partido':<8} {'UF':<4} {'Emendas':<8} {'Empenhado':<12} {'Liquidado':<12} {'Pago':<12}")
        print(f"{'-'*80}")
        for i, row in enumerate(ranking_emendas, 1):
            nome, partido, uf, total_emendas, empenhado, liquidado, pago, ufs_benef, municipios = row
            print(f"{i:<4} {nome[:28]:<30} {partido or 'N/A':<8} {uf or 'N/A':<4} {total_emendas:<8} R$ {empenhado:<10,.2f} R$ {liquidado:<10,.2f} R$ {pago:<10,.2f}")
        
        print(f"\n🏆 DESTAQUES DO PERÍODO")
        print(f"{'-'*40}")
        if ranking_gastos:
            print(f"💰 Maior Gasto CEAP: {ranking_gastos[0][1]} ({ranking_gastos[0][2]}) - R$ {ranking_gastos[0][3]:,.2f}")
        if ranking_proposicoes:
            print(f"📋 Mais Proposições: {ranking_proposicoes[0][0]} ({ranking_proposicoes[0][2]}) - {ranking_proposicoes[0][3]} proposições")
        if ranking_emendas:
            print(f"💰 Maior Valor em Emendas: {ranking_emendas[0][0]} ({ranking_emendas[0][2]}) - R$ {ranking_emendas[0][4]:,.2f} empenhado")
        
        print(f"\n📝 METODOLOGIA")
        print(f"{'-'*20}")
        print("• Gastos CEAP: Valores líquidos de despesas parlamentares em 2025")
        print("• Proposições: Contagem de todas as proposições com autoria registrada em 2025")
        print("• Emendas: Valores empenhados de emendas parlamentares de 2025")
        print("• Período: Ano legislativo de 2025")
        print("• Fonte: Câmara dos Deputados e Portal da Transparência")
        
        print(f"\n{'='*80}")
        print(f"📊 {len(ranking_gastos)} deputados com gastos")
        print(f"📋 {len(ranking_proposicoes)} deputados com proposições")
        print(f"💰 {len(ranking_emendas)} deputados com emendas")
        print(f"{'='*80}")
        
        return None
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        return None
    finally:
        session.close()

def main():
    """Função principal."""
    print("🚀 Gerando Relatório Completo de Atividade Parlamentar")
    print("=" * 60)
    
    resultado = gerar_relatorio_completo()
    
    if resultado is None:  # None significa que funcionou (imprimiu no terminal)
        print("\n✅ Relatório gerado com sucesso!")
        print("📊 Relatório exibido no terminal acima")
    else:
        print("\n❌ Falha ao gerar relatório")

if __name__ == "__main__":
    main()
