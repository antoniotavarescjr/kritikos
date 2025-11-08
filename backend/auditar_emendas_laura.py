#!/usr/bin/env python3
"""
Script de auditoria detalhada das emendas da Laura Carneiro (ID: 287)
Para investigar a discrepância nos valores reportados.
"""

import sys
import os
from decimal import Decimal

# Adicionar models ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.db_utils import get_db_session
from sqlalchemy import text

def auditar_emendas_laura_carneiro():
    """Audita detalhadamente as emendas da Laura Carneiro"""
    
    print("🔍 AUDITORIA DETALHADA - EMENDAS LAURA CARNEIRO (ID: 287)")
    print("=" * 80)
    
    session = get_db_session()
    
    try:
        # 1. Verificação básica - contagem e soma
        print("\n📊 VERIFICAÇÃO BÁSICA")
        print("-" * 40)
        
        basic_stats = session.execute(text("""
            SELECT 
                COUNT(*) as total_emendas,
                COUNT(DISTINCT id) as emendas_unicas,
                COALESCE(SUM(valor_emenda), 0) as soma_valor_emenda,
                COALESCE(SUM(valor_empenhado), 0) as soma_valor_empenhado,
                COALESCE(SUM(valor_liquidado), 0) as soma_valor_liquidado,
                COALESCE(SUM(valor_pago), 0) as soma_valor_pago,
                MIN(valor_emenda) as menor_valor_emenda,
                MAX(valor_emenda) as maior_valor_emenda,
                AVG(valor_emenda) as media_valor_emenda
            FROM emendas_parlamentares 
            WHERE deputado_id = 287 AND ano = 2025
        """)).fetchone()
        
        print(f"📋 Total de emendas: {basic_stats[0]}")
        print(f"🔢 Emendas únicas: {basic_stats[1]}")
        print(f"💰 Soma valor_emenda: R$ {float(basic_stats[2]):,.2f}")
        print(f"💸 Soma valor_empenhado: R$ {float(basic_stats[3]):,.2f}")
        print(f"💳 Soma valor_liquidado: R$ {float(basic_stats[4]):,.2f}")
        print(f"💵 Soma valor_pago: R$ {float(basic_stats[5]):,.2f}")
        print(f"📉 Menor valor: R$ {float(basic_stats[6]):,.2f}")
        print(f"📈 Maior valor: R$ {float(basic_stats[7]):,.2f}")
        print(f"📊 Média por emenda: R$ {float(basic_stats[8]):,.2f}")
        
        # 2. Detalhe individual de cada emenda
        print("\n📋 DETALHE INDIVIDUAL DAS EMENDAS")
        print("-" * 40)
        
        emendas_detalhe = session.execute(text("""
            SELECT 
                id,
                tipo_emenda,
                numero,
                valor_emenda,
                valor_empenhado,
                valor_liquidado,
                valor_pago,
                local,
                beneficiario_principal,
                uf_beneficiario,
                municipio_beneficiario,
                data_apresentacao,
                situacao
            FROM emendas_parlamentares 
            WHERE deputado_id = 287 AND ano = 2025
            ORDER BY valor_emenda DESC
        """)).fetchall()
        
        soma_manual = 0
        for i, emenda in enumerate(emendas_detalhe, 1):
            valor_emenda = float(emenda[2]) if emenda[2] else 0
            valor_empenhado = float(emenda[3]) if emenda[3] else 0
            valor_liquidado = float(emenda[4]) if emenda[4] else 0
            valor_pago = float(emenda[5]) if emenda[5] else 0
            
            soma_manual += valor_emenda
            
            print(f"\n🏷️  Emenda #{i}:")
            print(f"   ID: {emenda[0]}")
            print(f"   Tipo: {emenda[1]}")
            print(f"   Número: {emenda[2]}")
            print(f"   💰 Valor Emenda: R$ {valor_emenda:,.2f}")
            print(f"   💸 Valor Empenhado: R$ {valor_empenhado:,.2f}")
            print(f"   💳 Valor Liquidado: R$ {valor_liquidado:,.2f}")
            print(f"   💵 Valor Pago: R$ {valor_pago:,.2f}")
            print(f"   📍 Local: {emenda[6]}")
            print(f"   🏛️  Beneficiário: {emenda[7]}")
            print(f"   🌍 UF: {emenda[8]}")
            print(f"   🏘️  Município: {emenda[9]}")
            print(f"   📅 Data Apresentação: {emenda[10]}")
            print(f"   📊 Situação: {emenda[11]}")
            
            # Verificar consistência dos valores
            if valor_emenda > 0:
                taxa_empenho = (valor_empenhado / valor_emenda * 100) if valor_emenda > 0 else 0
                taxa_liquidacao = (valor_liquidado / valor_emenda * 100) if valor_emenda > 0 else 0
                taxa_pagamento = (valor_pago / valor_emenda * 100) if valor_emenda > 0 else 0
                
                print(f"   📈 Taxa Empenho: {taxa_empenho:.1f}%")
                print(f"   📊 Taxa Liquidação: {taxa_liquidacao:.1f}%")
                print(f"   💵 Taxa Pagamento: {taxa_pagamento:.1f}%")
        
        print(f"\n🔢 SOMA MANUAL VERIFICADA: R$ {soma_manual:,.2f}")
        
        # 3. Verificar possíveis duplicações
        print("\n🔍 VERIFICAÇÃO DE DUPLICAÇÕES")
        print("-" * 40)
        
        duplicacoes = session.execute(text("""
            SELECT 
                id,
                tipo_emenda,
                numero,
                valor_emenda,
                COUNT(*) as duplicatas
            FROM emendas_parlamentares 
            WHERE deputado_id = 287 AND ano = 2025
            GROUP BY id, tipo_emenda, numero, valor_emenda
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if duplicacoes:
            print("⚠️  POSSÍVEIS DUPLICAÇÕES ENCONTRADAS:")
            for dup in duplicacoes:
                print(f"   ID: {dup[0]} | Tipo: {dup[1]} | Número: {dup[2]} | Valor: R$ {float(dup[3]):,.2f} | Duplicatas: {dup[4]}")
        else:
            print("✅ Nenhuma duplicação encontrada")
        
        # 4. Verificar valores suspeitos (muito altos)
        print("\n🚨 ANÁLISE DE VALORES SUSPEITOS")
        print("-" * 40)
        
        valores_altos = session.execute(text("""
            SELECT 
                id,
                tipo_emenda,
                numero,
                valor_emenda,
                beneficiario_principal
            FROM emendas_parlamentares 
            WHERE deputado_id = 287 AND ano = 2025
            AND valor_emenda > 10000000  -- Acima de R$ 10 milhões
            ORDER BY valor_emenda DESC
        """)).fetchall()
        
        if valores_altos:
            print("⚠️  EMENDAS COM VALORES ACIMA DE R$ 10 MILHÕES:")
            for val in valores_altos:
                print(f"   ID: {val[0]} | Tipo: {val[1]} | Número: {val[2]} | Valor: R$ {float(val[3]):,.2f} | Beneficiário: {val[4]}")
        else:
            print("✅ Nenhuma emenda com valor suspeitamente alto")
        
        # 5. Comparar com o que o script de cálculo reportou
        print("\n🔍 COMPARAÇÃO COM SCRIPT DE CÁLCULO")
        print("-" * 40)
        
        # Simular a consulta do score calculator
        stats_calculator = session.execute(text("""
            SELECT 
                COUNT(DISTINCT e.id) as total_emendas,
                COALESCE(SUM(e.valor_emenda), 0) as valor_total_emendas
            FROM emendas_parlamentares e
            WHERE e.deputado_id = 287
            AND e.ano = 2025
        """)).fetchone()
        
        valor_calculator = float(stats_calculator[1]) if stats_calculator[1] else 0
        
        print(f"📊 Valor reportado pelo calculator: R$ {valor_calculator:,.2f}")
        print(f"🔢 Soma manual verificada: R$ {soma_manual:,.2f}")
        print(f"📉 Diferença: R$ {abs(valor_calculator - soma_manual):,.2f}")
        
        if abs(valor_calculator - soma_manual) > 0.01:
            print("❌ ERRO: Há discrepância nos valores!")
            print("🔍 Possíveis causas:")
            print("   - Erro na query do calculator")
            print("   - Dados duplicados na consulta")
            print("   - Problema de formatação")
        else:
            print("✅ Valores consistentes entre calculator e soma manual")
        
        # 6. Análise final
        print("\n📈 ANÁLISE FINAL E RECOMENDAÇÕES")
        print("-" * 40)
        
        media_por_emenda = soma_manual / basic_stats[0] if basic_stats[0] > 0 else 0
        
        print(f"📊 Análise estatística:")
        print(f"   Total de emendas: {basic_stats[0]}")
        print(f"   Valor total: R$ {soma_manual:,.2f}")
        print(f"   Média por emenda: R$ {media_por_emenda:,.2f}")
        
        if soma_manual > 100000000:  # Acima de R$ 100 milhões
            print("⚠️  ALERTA: Valor total muito elevado!")
            print("   - Possível erro de escala (milhar vs milhão)")
            print("   - Verificar se valores estão em centavos")
        
        if media_por_emenda > 5000000:  # Acima de R$ 5M por emenda
            print("⚠️  ALERTA: Média por emenda muito alta!")
            print("   - Valores individuais suspeitos")
            print("   - Possível erro de digitação")
        
        print("\n🎯 RECOMENDAÇÕES:")
        print("1. Verificar fonte original dos dados das emendas")
        print("2. Confirmar escala dos valores (centavos vs reais)")
        print("3. Investigar possíveis duplicações no banco")
        print("4. Validar contra dados oficiais da Câmara")
        
    except Exception as e:
        print(f"❌ Erro na auditoria: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    auditar_emendas_laura_carneiro()
