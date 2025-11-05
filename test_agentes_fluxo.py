#!/usr/bin/env python3
"""
Teste do fluxo completo dos agentes Kritikos com dados reais.
Valida integração com banco de dados e funcionamento das ferramentas.
"""

import sys
import os
import json
from datetime import datetime

# Adicionar paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents', 'tools'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Importar ferramentas
from database_tools import (
    get_proposicao_completa,
    get_texto_completo_proposicao,
    get_dados_deputado,
    buscar_proposicoes_por_criterio,
    get_ranking_atualizado,
    get_estatisticas_gerais,
    get_proposicoes_para_analise
)

# Importar agentes
from agents.tools.document_summarizer_tool import (
    summarize_proposal_text,
    analyze_proposal_par
)
from agents.tools.trivial_filter_tool import is_summary_trivial


def test_ferramentas_banco():
    """Testa ferramentas de banco de dados."""
    print("🔧 TESTANDO FERRAMENTAS DE BANCO DE DADOS")
    print("=" * 60)
    
    # Testar estatísticas gerais
    print("\n1. 📊 Estatísticas Gerais:")
    stats = get_estatisticas_gerais()
    if stats:
        print(f"   ✅ Deputados: {stats['totais'].get('deputados', 0)}")
        print(f"   ✅ Proposições 2025: {stats['totais'].get('proposicoes_2025', 0)}")
        print(f"   ✅ Autorias 2025: {stats['totais'].get('autorias_2025', 0)}")
        print(f"   ✅ Cobertura: {stats['cobertura_autorias']['percentual']}%")
    else:
        print("   ❌ Falha ao obter estatísticas")
    
    # Testar ranking
    print("\n2. 🏆 Ranking (Top 5):")
    ranking = get_ranking_atualizado(limite=5)
    if ranking:
        for i, dep in enumerate(ranking, 1):
            print(f"   {i}. {dep['nome']} - {dep['total_proposicoes']} props")
    else:
        print("   ❌ Falha ao obter ranking")
    
    # Testar busca de proposições
    print("\n3. 📋 Busca de Proposições (Top 3):")
    props = buscar_proposicoes_por_criterio(limite=3)
    if props:
        for i, prop in enumerate(props, 1):
            print(f"   {i}. {prop['tipo']} {prop['numero']}/{prop['ano']} - {prop['ementa'][:50]}...")
    else:
        print("   ❌ Falha ao buscar proposições")
    
    return len(ranking) > 0 and len(props) > 0


def test_fluxo_agente_completo(proposicao_id: int):
    """Testa fluxo completo do agente para uma proposição."""
    print(f"\n🤖 TESTANDO FLUXO COMPLETO DO AGENTE")
    print("=" * 60)
    print(f"Proposição ID: {proposicao_id}")
    
    # Etapa 1: Obter dados completos
    print("\n1. 📄 Obtendo dados completos...")
    prop = get_proposicao_completa(proposicao_id)
    if not prop:
        print("   ❌ Proposição não encontrada")
        return False
    
    print(f"   ✅ {prop['tipo']} {prop['numero']}/{prop['ano']}")
    print(f"   📝 Ementa: {prop['ementa'][:100]}...")
    print(f"   👥 Autores: {len(prop['autores'])}")
    
    # Etapa 2: Obter texto completo
    print("\n2. 📖 Gerando texto completo...")
    texto_completo = get_texto_completo_proposicao(proposicao_id)
    if not texto_completo:
        print("   ❌ Falha ao gerar texto completo")
        return False
    
    print(f"   ✅ Texto gerado ({len(texto_completo)} caracteres)")
    
    # Etapa 3: Sumarização
    print("\n3. 📝 Sumarizando proposta...")
    try:
        resumo = summarize_proposal_text(texto_completo)
        if not resumo:
            print("   ❌ Falha na sumarização")
            return False
        
        print(f"   ✅ Resumo gerado ({len(resumo)} caracteres)")
        print(f"   📄 Resumo: {resumo[:150]}...")
    except Exception as e:
        print(f"   ❌ Erro na sumarização: {e}")
        return False
    
    # Etapa 4: Filtro de trivialidade
    print("\n4. 🔍 Verificando relevância...")
    try:
        is_trivial = is_summary_trivial(resumo)
        print(f"   ✅ Resultado: {'Trivial' if is_trivial else 'Relevante'}")
        
        if is_trivial:
            print("   ⏭️ Proposição trivial - análise não necessária")
            return True
    except Exception as e:
        print(f"   ❌ Erro no filtro: {e}")
        return False
    
    # Etapa 5: Análise PAR
    print("\n5. 📊 Analisando PAR...")
    try:
        analise_str = analyze_proposal_par(resumo)
        if not analise_str:
            print("   ❌ Falha na análise PAR")
            return False
        
        # Tentar parse do JSON
        try:
            analise = json.loads(analise_str)
            print(f"   ✅ PAR Final: {analise.get('par_final', 'N/A')}")
            print(f"   📈 Escopo: {analise.get('escopo_impacto', 'N/A')}/30")
            print(f"   🎯 ODS: {analise.get('alinhamento_ods', 'N/A')}/30")
            print(f"   💡 Inovação: {analise.get('inovacao_eficiencia', 'N/A')}/20")
            print(f"   💰 Sustentabilidade: {analise.get('sustentabilidade_fiscal', 'N/A')}/20")
            print(f"   ⚠️ Penalidade: {analise.get('penalidade_oneracao', 'N/A')}")
            print(f"   📋 ODS Identificados: {analise.get('ods_identificados', [])}")
            print(f"   📝 Análise: {analise.get('resumo_analise', 'N/A')[:100]}...")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"   ❌ Erro ao parsear JSON da análise: {e}")
            print(f"   📄 Resposta bruta: {analise_str[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro na análise PAR: {e}")
        return False


def test_deputado_detalhes(deputado_id: int):
    """Testa obtenção de detalhes de um deputado."""
    print(f"\n👥 TESTANDO DADOS DE DEPUTADO")
    print("=" * 60)
    print(f"Deputado ID: {deputado_id}")
    
    dep = get_dados_deputado(deputado_id)
    if not dep:
        print("   ❌ Deputado não encontrado")
        return False
    
    print(f"   ✅ Nome: {dep['nome']}")
    print(f"   ✅ Email: {dep['email']}")
    print(f"   ✅ Foto: {dep['foto_url']}")
    print(f"   ✅ Situação: {dep['situacao']}")
    print(f"   ✅ Total Props: {dep['estatisticas']['total_proposicoes']}")
    print(f"   ✅ Props 2025: {dep['estatisticas']['props_2025']}")
    print(f"   ✅ Ranking: #{dep['ranking_posicao']}")
    print(f"   ✅ Tipos: {dep['estatisticas']['tipos_proposicoes']}")
    
    return True


def main():
    """Função principal de teste."""
    print("🚀 TESTE COMPLETO DO FLUXO DE AGENTES KRITIKOS")
    print("=" * 80)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    sucesso_total = True
    
    # Teste 1: Ferramentas de banco
    if not test_ferramentas_banco():
        sucesso_total = False
    
    # Teste 2: Obter proposições para análise
    print("\n" + "="*60)
    print("📋 OBTENDO PROPOSIÇÕES PARA ANÁLISE")
    print("="*60)
    
    props_ids = get_proposicoes_para_analise(limite=3)
    if not props_ids:
        print("❌ Nenhuma proposição encontrada para teste")
        sucesso_total = False
    else:
        print(f"✅ Encontradas {len(props_ids)} proposições para teste")
        
        # Testar fluxo completo para cada proposição
        for prop_id in props_ids:
            if not test_fluxo_agente_completo(prop_id):
                sucesso_total = False
    
    # Teste 3: Dados de deputado
    print("\n" + "="*60)
    print("👥 TESTANDO DADOS DE DEPUTADO")
    print("="*60)
    
    # Pegar primeiro deputado do ranking
    ranking = get_ranking_atualizado(limite=1)
    if ranking:
        dep_id = ranking[0]['id_deputado']
        if not test_deputado_detalhes(dep_id):
            sucesso_total = False
    else:
        print("❌ Nenhum deputado encontrado para teste")
        sucesso_total = False
    
    # Resultado final
    print("\n" + "="*80)
    print("🎉 RESULTADO FINAL DOS TESTES")
    print("="*80)
    
    if sucesso_total:
        print("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("🎯 Sistema pronto para integração com FastAPI")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("🔧 Verifique os erros acima antes de prosseguir")
    
    print(f"\n⏱️ Teste concluído em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    return sucesso_total


if __name__ == "__main__":
    main()
