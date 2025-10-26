#!/usr/bin/env python3
"""
Análise Comparativa entre Coletor Atual e Código Validado
Identifica diferenças críticas que causam a falha na coleta
"""

import sys
import os
from pathlib import Path

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

def analisar_diferencas_criticas():
    """
    Compara o coletor atual com o código validado para identificar problemas
    """
    print("🔍 ANÁLISE COMPARATIVA - COLETOR ATUAL vs CÓDIGO VALIDADO")
    print("=" * 70)
    
    print("\n📋 DIFERENÇAS CRÍTICAS IDENTIFICADAS:")
    print("-" * 50)
    
    print("\n1. 🎯 ESTRATÉGIA DE COLETA:")
    print("   ❌ COLETOR ATUAL:")
    print("      - Busca por ano com limite fixo (500 emendas)")
    print("      - Usa paginação genérica sem filtro de deputado")
    print("      - Limitado a 100 itens por página")
    print("      - Para quando atinge limite ou 100 páginas")
    print("")
    print("   ✅ CÓDIGO VALIDADO:")
    print("      - Busca por deputado específico + ano")
    print("      - Coleta TODAS as emendas do deputado")
    print("      - Paginação até não ter mais resultados")
    print("      - Sem limite artificial")
    
    print("\n2. 🔑 PARÂMETROS DA API:")
    print("   ❌ COLETOR ATUAL:")
    print("      - params = {'ano': ano, 'pagina': pagina, 'itens': 100}")
    print("      - Sem filtro de autor/nome")
    print("      - Retorna emendas de TODOS os deputados misturadas")
    print("")
    print("   ✅ CÓDIGO VALIDADO:")
    print("      - params = {'ano': ano, 'nomeAutor': nome_deputado, 'pagina': pagina}")
    print("      - Filtro específico por deputado")
    print("      - Retorna apenas emendas daquele deputado")
    
    print("\n3. 💰 TRATAMENTO DE VALORES:")
    print("   ❌ COLETOR ATUAL:")
    print("      - Usa limpar_valor_monetario() que pode falhar")
    print("      - Converte string → float com replace simples")
    print("      - Pode perder valores se formato for diferente")
    print("")
    print("   ✅ CÓDIGO VALIDADO:")
    print("      - Conversão robusta: float(str(valor).replace('.', '').replace(',', '.') or 0)")
    print("      - Trata casos nulos e vazios")
    print("      - Garante conversão bem-sucedida")
    
    print("\n4. 🏷️ MAPEAMENTO DE DEPUTADOS:")
    print("   ❌ COLETOR ATUAL:")
    print("      - buscar_deputado_por_nome() com match aproximado")
    print("      - Pode não encontrar correspondência exata")
    print("      - Muitos deputados ficam com deputado_id = NULL")
    print("")
    print("   ✅ CÓDIGO VALIDADO:")
    print("      - Usa nome exato da API")
    print("      - Teste com nomes conhecidos (NIKOLAS FERREIRA, etc.)")
    print("      - Garante correspondência correta")
    
    print("\n5. 📊 ESTRATÉGIA DE PAGINAÇÃO:")
    print("   ❌ COLETOR ATUAL:")
    print("      - Para quando len(emendas_pagina) < itens")
    print("      - Limite de 100 páginas como segurança")
    print("      - Pode parar antes de pegar todos os dados")
    print("")
    print("   ✅ CÓDIGO VALIDADO:")
    print("      - Para quando retorna [] (lista vazia)")
    print("      - Continua até não ter mais resultados")
    print("      - Garante coleta completa")

def identificar_problema_principal():
    """
    Identifica o problema principal que causa a falha
    """
    print("\n🚨 PROBLEMA PRINCIPAL IDENTIFICADO:")
    print("=" * 50)
    
    print("\n❌ O COLETOR ATUAL NÃO ESTÁ FALHANDO - ESTÁ FUNCIONANDO DIFERENTE!")
    print("")
    print("🔍 ANÁLISE DO PROBLEMA:")
    print("   1. Coletor atual busca emendas de TODOS os deputados juntos")
    print("   2. Código validado busca emendas de UM deputado por vez")
    print("   3. Teste anterior comparou 'maçãs com laranjas'")
    print("")
    print("📊 EVIDÊNCIA:")
    print("   - Coletor atual: 500 emendas de vários deputados")
    print("   - Código validado: 9-19 emendas de um deputado específico")
    print("   - Banco pode ter dados, mas não dos deputados testados")
    
    print("\n🎯 VERDADEIRO PROBLEMA:")
    print("   1. Coletor atual não está salvando corretamente os dados")
    print("   2. Ou está salvando mas com deputado_id = NULL")
    print("   3. Ou está salvando mas com valores zerados")
    print("   4. Ou está salvando mas com IDs diferentes")

def criar_plano_correcao():
    """
    Cria plano de correção baseado na análise
    """
    print("\n🔧 PLANO DE CORREÇÃO - ABORDAGEM HÍBRIDA")
    print("=" * 50)
    
    print("\n📋 ESTRATÉGIA RECOMENDADA:")
    print("   1. ✅ Manter arquitetura do coletor atual")
    print("   2. ✅ Adicionar método de coleta por deputado")
    print("   3. ✅ Corrigir tratamento de valores")
    print("   4. ✅ Melhorar mapeamento de deputados")
    print("   5. ✅ Implementar coleta completa")
    
    print("\n🎯 MUDANÇAS ESPECÍFICAS:")
    print("   1. Adicionar método coletar_por_deputado()")
    print("   2. Melhorar limpar_valor_monetario()")
    print("   3. Adicionar estratégia de fallback para nomes")
    print("   4. Implementar validação de salvamento")
    print("   5. Adicionar logging detalhado")
    
    print("\n📊 ESTRATÉGIA DE COLETA:")
    print("   Opção A: Coleta por deputado (mais precisa)")
    print("   - Iterar sobre todos os deputados")
    print("   - Coletar emendas de cada um")
    print("   - Garante cobertura completa")
    print("")
    print("   Opção B: Coleta por ano (mais rápida)")
    print("   - Manter lógica atual")
    print("   - Melhorar mapeamento de deputados")
    print("   - Corrigir tratamento de valores")

def testar_hipotese():
    """
    Testa hipótese sobre o que está acontecendo
    """
    print("\n🧪 TESTE DE HIPÓTESE - O QUE ESTÁ ACONTECENDO?")
    print("=" * 50)
    
    print("\n🔍 HIPÓTESE 1: DADOS ESTÃO SENDO SALVOS MAS COM PROBLEMAS")
    print("   - Deputado_id = NULL")
    print("   - Valor_emenda = 0")
    print("   - API_camara_id diferente")
    
    print("\n🔍 HIPÓTESE 2: COLETA ATUAL NÃO ESTÁ RODANDO")
    print("   - Ninguém executou o coletor recentemente")
    print("   - Banco está vazio de emendas")
    print("   - Só tem dados da API Câmara")
    
    print("\n🔍 HIPÓTESE 3: CONFLITO DE FONTES")
    print("   - Coletor atual vs API Câmara")
    print("   - Dados se sobrescrevendo")
    print("   - IDs conflitantes")
    
    print("\n🎯 TESTE NECESSÁRIO:")
    print("   1. Verificar se há emendas no banco")
    print("   2. Verificar se há emendas com deputado_id NULL")
    print("   3. Verificar se há emendas com valor = 0")
    print("   4. Verificar qual fonte gerou os dados existentes")

def main():
    """
    Função principal
    """
    print("🔍 ANÁLISE COMPARATIVA DE COLETORES")
    print("=" * 70)
    print("🎯 Objetivo: Identificar diferenças críticas entre coletor atual e código validado")
    print("🔧 Método: Análise detalhada das abordagens")
    print("=" * 70)
    
    try:
        analisar_diferencas_criticas()
        identificar_problema_principal()
        criar_plano_correcao()
        testar_hipotese()
        
        print(f"\n🎉 ANÁLISE CONCLUÍDA!")
        print(f"📋 Próximo passo: Verificar dados atuais no banco")
        print(f"🔧 Depois: Implementar correções específicas")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE ANÁLISE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
