#!/usr/bin/env python3
"""
Script de teste para validar o fluxo de agentes do Kritikos com texto dummy.
Este script testa cada agente individualmente e depois o fluxo completo.
"""

import os
import sys
import json
from typing import Dict, Any, Optional

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
sys.path.append(os.path.dirname(__file__))

# Importar ferramentas dos agentes
from tools.document_summarizer_tool import summarize_proposal_text, analyze_proposal_par
from tools.trivial_filter_tool import is_summary_trivial

# Configurar variáveis de ambiente para o Vertex AI
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "kritikos-474618")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


def get_dummy_proposal_text() -> str:
    """
    Retorna um texto dummy de uma proposição legislativa para testes.
    Esta proposição foi desenhada para ser relevante e ter bom potencial de análise PAR.
    """
    return """
    PROPOSTA DE EMENDA À CONSTITUIÇÃO Nº 45/2024
    
    Altera o Art. 6º da Constituição Federal para incluir a conectividade à internet 
    como direito social fundamental e estabelece o Programa Nacional de Inclusão Digital.
    
    As Mesas da Câmara dos Deputados e do Senado Federal, nos termos do § 3º do art. 60 
    da Constituição Federal, promulgam a seguinte Emenda ao texto constitucional:
    
    Art. 1º O Art. 6º da Constituição Federal passa a vigorar com a seguinte redação:
    
    "Art. 6º São direitos sociais a educação, a saúde, a alimentação, o trabalho, 
    a moradia, o transporte, o lazer, a segurança, a previdência social, a proteção 
    à maternidade e à infância, a assistência aos desamparados, NA FORMA DESTA 
    CONSTITUIÇÃO, e o acesso universal à internet de qualidade e à conectividade digital."
    
    Art. 2º Fica criado o Programa Nacional de Inclusão Digital (PNID) com os seguintes objetivos:
    
    I - garantir acesso gratuito à internet em banda larga para todas as escolas públicas 
    do país até 2026;
    
    II - fornecer kits digitais (computador + internet) para famílias de baixa renda 
    inscritas no Cadastro Único;
    
    III - criar pontos de conectividade gratuita em todas as praças públicas dos 
    municípios com mais de 20 mil habitantes;
    
    IV - capacitar 10 milhões de brasileiros em alfabetização digital até 2028.
    
    Art. 3º O programa será financiado com recursos provenientes de:
    
    I - 0,5% da receita líquida das empresas de telecomunicações;
    
    II - fundos soberanos e parcerias público-privadas;
    
    III - realocação de subsídios setoriais ineficientes.
    
    Art. 4º A implementação do PNID será coordenada pelo Ministério das Comunicações 
    em conjunto com o Ministério da Educação e o Ministério da Cidadania.
    
    Art. 5º Esta Emenda Constitucional entra em vigor na data de sua publicação.
    
    JUSTIFICATIVA
    
    A exclusão digital atinge aproximadamente 45 milhões de brasileiros, criando 
    uma nova forma de desigualdade social. O acesso à internet deixou de ser um 
    luxo para se tornar ferramenta essencial para educação, trabalho, cidadania 
    e participação democrática. Países como Estônia, Coreia do Sul e Finlândia 
    já garantem conectividade como direito fundamental, com resultados expressivos 
    em desenvolvimento humano e econômico.
    
    O impacto fiscal da proposta é moderado e sustentável, com fontes de custeio 
    claramente definidas que não oneram o contribuinte. Estima-se que o programa 
    gere um retorno social de R$ 12 para cada R$ 1 investido, através do aumento 
    da produtividade e da inclusão econômica.
    
    A proposta está alinhada aos Objetivos de Desenvolvimento Sustentável da ONU, 
    especialmente ODS 4 (Educação de Qualidade), ODS 8 (Trabalho Decente e 
    Crescimento Econômico), ODS 9 (Indústria, Inovação e Infraestrutura) e 
    ODS 10 (Redução das Desigualdades).
    """


def get_trivial_proposal_text() -> str:
    """
    Retorna um texto dummy de uma proposição trivial para testar o filtro.
    """
    return """
    PROJETO DE LEI Nº 1.234/2024
    
    Dá o nome de "Deputado João Silva" à ponte localizada na BR-101, 
    km 150, no município de Pequeno Vale, estado de Minas Gerais.
    
    O Congresso Nacional decreta:
    
    Art. 1º A ponte localizada na BR-101, km 150, no município de Pequeno Vale, 
    estado de Minas Gerais, passa a denominar-se "Ponte Deputado João Silva".
    
    Art. 2º Esta Lei entra em vigor na data de sua publicação.
    
    JUSTIFICATIVA
    
    O Deputado João Silva foi um ilustre parlamentar que dedicou 20 anos 
    de sua vida à representação do povo de Pequeno Vale e região. 
    Sua contribuição para o desenvolvimento local foi inestimável, 
    sendo justa e necessária a homenagem póstuma.
    """


def test_summarizer_agent(text: str) -> Dict[str, Any]:
    """
    Testa o Summarizer Agent com o texto fornecido.
    """
    print("🔍 Testando Summarizer Agent...")
    print("-" * 50)
    
    try:
        summary = summarize_proposal_text(text, proposicao_id=999)  # ID dummy
        
        print(f"✅ Resumo gerado com sucesso!")
        print(f"📝 Tamanho do resumo: {len(summary)} caracteres")
        print(f"📄 Primeiros 200 caracteres: {summary[:200]}...")
        
        return {
            'success': True,
            'summary': summary,
            'length': len(summary)
        }
        
    except Exception as e:
        print(f"❌ Erro no Summarizer Agent: {e}")
        return {
            'success': False,
            'error': str(e),
            'summary': None
        }


def test_trivial_filter_agent(summary: str) -> Dict[str, Any]:
    """
    Testa o Trivial Filter Agent com o resumo fornecido.
    """
    print("\n🔍 Testando Trivial Filter Agent...")
    print("-" * 50)
    
    try:
        is_trivial = is_summary_trivial(summary, proposicao_id=999)  # ID dummy
        
        result_text = "TRIVIAL" if is_trivial else "RELEVANTE"
        print(f"✅ Análise de trivialidade concluída!")
        print(f"📊 Resultado: {result_text}")
        
        return {
            'success': True,
            'is_trivial': is_trivial,
            'result_text': result_text
        }
        
    except Exception as e:
        print(f"❌ Erro no Trivial Filter Agent: {e}")
        return {
            'success': False,
            'error': str(e),
            'is_trivial': None
        }


def test_par_analyzer_agent(summary: str) -> Dict[str, Any]:
    """
    Testa o PAR Analyzer Agent com o resumo fornecido.
    """
    print("\n🔍 Testando PAR Analyzer Agent...")
    print("-" * 50)
    
    try:
        analysis_json = analyze_proposal_par(summary, proposicao_id=999)  # ID dummy
        
        # Tentar fazer parse do JSON para validar estrutura
        try:
            analysis_data = json.loads(analysis_json)
            par_final = analysis_data.get('par_final', 'N/A')
            
            print(f"✅ Análise PAR gerada com sucesso!")
            print(f"📊 PAR Final: {par_final}")
            print(f"📋 Estrutura JSON válida: {list(analysis_data.keys())}")
            
            return {
                'success': True,
                'analysis_json': analysis_json,
                'analysis_data': analysis_data,
                'par_final': par_final
            }
            
        except json.JSONDecodeError as je:
            print(f"⚠️ Resposta gerada mas JSON inválido: {je}")
            print(f"📄 Resposta bruta: {analysis_json[:300]}...")
            
            return {
                'success': False,
                'error': f'JSON inválido: {je}',
                'analysis_json': analysis_json
            }
        
    except Exception as e:
        print(f"❌ Erro no PAR Analyzer Agent: {e}")
        return {
            'success': False,
            'error': str(e),
            'analysis_json': None
        }


def test_complete_flow(proposal_text: str, test_name: str) -> Dict[str, Any]:
    """
    Testa o fluxo completo de análise com uma proposição.
    """
    print(f"\n🚀 Iniciando teste completo: {test_name}")
    print("=" * 60)
    
    results = {
        'test_name': test_name,
        'steps': {},
        'final_result': None
    }
    
    # Passo 1: Summarizer
    summarizer_result = test_summarizer_agent(proposal_text)
    results['steps']['summarizer'] = summarizer_result
    
    if not summarizer_result['success']:
        results['final_result'] = 'FAILED_AT_SUMMARIZER'
        return results
    
    summary = summarizer_result['summary']
    
    # Passo 2: Trivial Filter
    filter_result = test_trivial_filter_agent(summary)
    results['steps']['trivial_filter'] = filter_result
    
    if not filter_result['success']:
        results['final_result'] = 'FAILED_AT_FILTER'
        return results
    
    # Passo 3: PAR Analyzer (só se não for trivial)
    if filter_result['is_trivial']:
        print(f"\n⏹️ Fluxo interrompido: proposição considerada trivial")
        results['final_result'] = 'TRIVIAL_PROPOSAL'
        return results
    
    par_result = test_par_analyzer_agent(summary)
    results['steps']['par_analyzer'] = par_result
    
    if not par_result['success']:
        results['final_result'] = 'FAILED_AT_PAR_ANALYZER'
        return results
    
    results['final_result'] = 'SUCCESS'
    return results


def main():
    """
    Função principal que executa todos os testes.
    """
    print("🧪 Kritikos Agent Flow Test Suite")
    print("=" * 60)
    print("Testando o fluxo completo de agentes com texto dummy\n")
    
    # Teste 1: Proposta relevante
    relevant_text = get_dummy_proposal_text()
    relevant_results = test_complete_flow(relevant_text, "Proposta Relevante (Inclusão Digital)")
    
    # Teste 2: Proposta trivial
    trivial_text = get_trivial_proposal_text()
    trivial_results = test_complete_flow(trivial_text, "Proposta Trivial (Homenagem)")
    
    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test_results in [relevant_results, trivial_results]:
        print(f"\n📋 Teste: {test_results['test_name']}")
        print(f"🎯 Resultado Final: {test_results['final_result']}")
        
        for step_name, step_result in test_results['steps'].items():
            status = "✅" if step_result['success'] else "❌"
            print(f"   {status} {step_name.replace('_', ' ').title()}")
    
    print(f"\n🏁 Testes concluídos!")


if __name__ == "__main__":
    main()
