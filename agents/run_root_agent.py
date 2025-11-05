#!/usr/bin/env python3
"""
Orquestrador principal do Kritikos Root Agent.
Este script implementa o fluxo completo de análise de proposições legislativas
usando o Google ADK com Vertex AI.
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


def analyze_proposal(proposal_text: str, proposicao_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Executa o fluxo completo de análise de uma proposição legislativa.
    
    Args:
        proposal_text: Texto completo da proposição
        proposicao_id: ID da proposição (opcional, para persistência)
        
    Returns:
        Dicionário com resultados completos da análise
    """
    print(f"🚀 Iniciando análise da proposição {proposicao_id if proposicao_id else 'N/A'}")
    print("=" * 60)
    
    results = {
        'proposicao_id': proposicao_id,
        'success': False,
        'error': None,
        'steps': {}
    }
    
    try:
        # Passo 1: Summarizer
        print("📝 Passo 1: Gerando resumo...")
        summary = summarize_proposal_text(proposal_text, proposicao_id)
        
        if not summary:
            results['error'] = 'Falha ao gerar resumo'
            return results
        
        results['steps']['summarizer'] = {
            'success': True,
            'summary': summary,
            'length': len(summary)
        }
        print(f"✅ Resumo gerado: {len(summary)} caracteres")
        
        # Passo 2: Trivial Filter
        print("\n🔍 Passo 2: Verificando trivialidade...")
        is_trivial = is_summary_trivial(summary, proposicao_id)
        
        results['steps']['trivial_filter'] = {
            'success': True,
            'is_trivial': is_trivial,
            'result': 'TRIVIAL' if is_trivial else 'RELEVANTE'
        }
        print(f"✅ Resultado: {'TRIVIAL' if is_trivial else 'RELEVANTE'}")
        
        # Passo 3: PAR Analyzer (só se não for trivial)
        if not is_trivial:
            print("\n📊 Passo 3: Calculando PAR...")
            par_analysis = analyze_proposal_par(summary, proposicao_id)
            
            if par_analysis:
                try:
                    par_data = json.loads(par_analysis)
                    results['steps']['par_analyzer'] = {
                        'success': True,
                        'par_final': par_data.get('par_final'),
                        'analysis_data': par_data
                    }
                    print(f"✅ PAR Final: {par_data.get('par_final')}")
                    results['success'] = True
                except json.JSONDecodeError:
                    results['steps']['par_analyzer'] = {
                        'success': False,
                        'error': 'JSON inválido'
                    }
                    results['error'] = 'Falha ao processar análise PAR'
            else:
                results['steps']['par_analyzer'] = {
                    'success': False,
                    'error': 'Falha ao gerar análise PAR'
                }
                results['error'] = 'Falha na análise PAR'
        else:
            print("\n⏹️ Proposição considerada trivial - análise PAR não necessária")
            results['success'] = True
        
        return results
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        results['error'] = str(e)
        return results


def main():
    """
    Função principal para demonstração do orquestrador.
    """
    print("🧪 Kritikos Root Agent - Orquestrador Principal")
    print("=" * 60)
    print("Executando fluxo completo de análise de proposições legislativas\n")
    
    # Teste com proposição relevante
    relevant_proposal = """
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
    
    # Executar análise completa
    result = analyze_proposal(relevant_proposal, 12345)
    
    # Exibir resultados
    print("\n" + "=" * 60)
    print("📊 RESULTADO DA ANÁLISE")
    print("=" * 60)
    
    if result['success']:
        print(f"✅ Análise concluída com sucesso!")
        print(f"📋 ID Proposição: {result['proposicao_id']}")
        
        for step_name, step_data in result['steps'].items():
            status = "✅" if step_data['success'] else "❌"
            print(f"{status} {step_name.replace('_', ' ').title()}: {step_data}")
            
        if 'par_final' in result.get('steps', {}).get('par_analyzer', {}):
            par_final = result['steps']['par_analyzer']['par_final']
            print(f"\n🏆 PONTUAÇÃO FINAL (PAR): {par_final}/100")
            
            if par_final >= 80:
                print("🌟 PROPOSTA ALTAMENTE RELEVANTE")
            elif par_final >= 60:
                print("📈 PROPOSTA RELEVANTE")
            elif par_final >= 40:
                print("📉 PROPOSTA MODERADAMENTE RELEVANTE")
            else:
                print("📉 PROPOSTA BAIXA RELEVÂNCIA")
    else:
        print(f"❌ Falha na análise: {result['error']}")
    
    print("\n🏁 Análise concluída!")


if __name__ == "__main__":
    main()
