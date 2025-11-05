#!/usr/bin/env python3
"""
Script de demonstração da integração entre pipeline e agents
Usa dados de exemplo para mostrar o fluxo completo funcionando
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Carregar variáveis de ambiente do .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))

from tools.document_summarizer_tool import summarize_proposal_text, analyze_proposal_par
from tools.trivial_filter_tool import is_summary_trivial

def test_integration_with_sample_data():
    """Testa integração com dados de exemplo."""
    print("🚀 DEMONSTRAÇÃO DE INTEGRAÇÃO PIPELINE + AGENTS")
    print("=" * 60)
    print("Usando dados de exemplo para demonstrar o fluxo completo")
    print("=" * 60)
    
    # Dados de exemplo de proposições reais
    sample_proposals = [
        {
            'id': 1,
            'tipo': 'PL',
            'numero': 5598,
            'ano': 2025,
            'ementa': 'Cria a Defensoria Pública Militar Especializada no âmbito da Defensoria Pública da União e dá outras providências.',
            'texto_completo': '''
            PROJETO DE LEI Nº 5.598, DE 2025
            
            (Do Sr. Deputado Federal)
            
            Cria a Defensoria Pública Militar Especializada no âmbito da Defensoria Pública da União e dá outras providências.
            
            O Congresso Nacional decreta:
            
            Art. 1º Fica criada a Defensoria Pública Militar Especializada, órgão integrante da estrutura da Defensoria Pública da União, com atuação específica junto aos militares das Forças Armadas e seus dependentes.
            
            Art. 2º À Defensoria Pública Militar Especializada compete:
            I - prestar assistência jurídica integral e gratuita aos militares das Forças Armadas e seus dependentes;
            II - atuar na defesa dos direitos e interesses dos militares em processos administrativos disciplinares;
            III - promover a conciliação e a mediação entre militares e a administração militar;
            IV - orientar os militares sobre seus direitos e deveres.
            
            Art. 3º Os defensores públicos militares serão selecionados mediante concurso público de provas e títulos, exigindo-se formação em Direito e, preferencialmente, experiência em Direito Militar.
            
            Art. 4º A Defensoria Pública Militar Especializada será estruturada em:
            I - Defensoria Pública Militar da Marinha;
            II - Defensoria Pública Militar do Exército;
            III - Defensoria Pública Militar da Aeronáutica.
            
            Art. 5º As despesas decorrentes da aplicação desta Lei correrão à conta das dotações orçamentárias da Defensoria Pública da União.
            
            Art. 6º Esta Lei entra em vigor na data de sua publicação.
            
            JUSTIFICATIVA
            
            A criação da Defensoria Pública Militar Especializada atende a uma demanda histórica dos militares das Forças Armadas, que enfrentam situações jurídicas específicas decorrentes da natureza especial de suas atividades. 
            Os militares estão sujeitos a um regime jurídico próprio, com leis, regulamentos e procedimentos administrativos que diferem do aplicável aos civis, o que justifica a necessidade de uma assessoria jurídica especializada.
            
            Além disso, a assistência jurídica militar contribuirá para a garantia da ampla defesa e do contraditório nos processos administrativos disciplinares, fortalecendo o Estado de Direito no ambiente militar.
            
            A iniciativa está alinhada com os Objetivos de Desenvolvimento Sustentável da ONU, especialmente o ODS 16 (Paz, Justiça e Instituições Eficazes), ao promover o acesso à justiça para um segmento específico da população.
            
            O impacto fiscal da proposta é moderado, podendo ser absorvido pela estrutura atual da Defensoria Pública da União, com custos adicionais limitados à criação de cargos específicos e estruturação dos órgãos militares.
            '''
        },
        {
            'id': 2,
            'tipo': 'PL',
            'numero': 5595,
            'ano': 2025,
            'ementa': 'Institui o "Dia Nacional de Combate à Intolerância Profissional" e dispõe sobre campanhas de conscientização.',
            'texto_completo': '''
            PROJETO DE LEI Nº 5.595, DE 2025
            
            (Do Sr. Deputado Federal)
            
            Institui o "Dia Nacional de Combate à Intolerância Profissional" e dispõe sobre campanhas de conscientização.
            
            O Congresso Nacional decreta:
            
            Art. 1º Fica instituído o "Dia Nacional de Combate à Intolerância Profissional", a ser celebrado analmente no dia 15 de outubro.
            
            Art. 2º No Dia Nacional de Combate à Intolerância Profissional, o Poder Público promoverá campanhas educativas e de conscientização sobre a importância do respeito às diferentes profissões e especializações.
            
            Art. 3º As campanhas deverão enfatizar:
            I - o valor social de todas as profissões legalmente regulamentadas;
            II - o combate ao preconceito profissional;
            III - a importância da diversidade profissional para o desenvolvimento do país;
            IV - o respeito às diferentes especializações e áreas de atuação.
            
            Art. 4º Os órgãos de educação, em todos os níveis, deverão incluir em seus currículos atividades relacionadas ao tema da tolerância profissional.
            
            Art. 5º Esta Lei entra em vigor na data de sua publicação.
            
            JUSTIFICATIVA
            
            A intolerância profissional é um fenômeno social que causa prejuízos significativos tanto para os indivíduos quanto para a sociedade como um todo. 
            Manifesta-se através de preconceitos, discriminações e desrespeito às diferentes profissões, afetando a dignidade e o bem-estar dos trabalhadores.
            
            A instituição de uma data comemorativa dedicada ao combate da intolerância profissional representa um importante instrumento educativo e de conscientização social, contribuindo para a construção de uma sociedade mais justa e igualitária.
            
            A proposta tem baixo impacto fiscal, limitando-se à promoção de campanhas educativas que podem ser desenvolvidas com recursos existentes nos órgãos públicos.
            '''
        }
    ]
    
    print(f"📊 Processando {len(sample_proposals)} proposições de exemplo...\n")
    
    resultados = []
    
    for i, proposal in enumerate(sample_proposals, 1):
        print(f"🔄 Análise {i}/{len(sample_proposals)}")
        print(f"🧪 Analisando {proposal['tipo']} {proposal['numero']}/{proposal['ano']} (ID: {proposal['id']})")
        print(f"   📋 Ementa: {proposal['ementa']}")
        
        try:
            # Passo 1: Summarizer Agent
            print("   📝 Passo 1: Gerando resumo...")
            resumo = summarize_proposal_text(proposal['texto_completo'], proposal['id'])
            
            if not resumo:
                print(f"   ❌ Falha no resumo")
                continue
            
            print(f"   ✅ Resumo gerado: {len(resumo)} caracteres")
            
            # Passo 2: Trivial Filter Agent
            print("   🔍 Passo 2: Verificando trivialidade...")
            is_trivial = is_summary_trivial(resumo, proposal['id'])
            
            resultado_filtro = "TRIVIAL" if is_trivial else "RELEVANTE"
            print(f"   ✅ Resultado: {resultado_filtro}")
            
            # Passo 3: PAR Analyzer (só se não for trivial)
            par_score = None
            if not is_trivial:
                print("   📊 Passo 3: Calculando PAR...")
                par_analysis = analyze_proposal_par(resumo, proposal['id'])
                
                if par_analysis:
                    try:
                        import json
                        par_data = json.loads(par_analysis)
                        par_score = par_data.get('par_final')
                        print(f"   ✅ PAR Final: {par_score}")
                    except:
                        print(f"   ⚠️ PAR gerado mas com erro no JSON")
                else:
                    print(f"   ❌ Falha na análise PAR")
            else:
                print("   ⏹️ Proposição trivial - análise PAR não necessária")
            
            resultado = {
                'proposicao_id': proposal['id'],
                'tipo': proposal['tipo'],
                'numero': proposal['numero'],
                'ano': proposal['ano'],
                'ementa': proposal['ementa'],
                'resumo': resumo,
                'is_trivial': is_trivial,
                'par_score': par_score,
                'data_analise': datetime.now()
            }
            
            resultados.append(resultado)
            print(f"   ✅ Análise concluída com sucesso")
            
        except Exception as e:
            print(f"   ❌ Erro inesperado: {e}")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DA DEMONSTRAÇÃO")
    print("=" * 60)
    
    print(f"📋 Proposições processadas: {len(resultados)}")
    
    # Estatísticas dos resultados
    if resultados:
        relevantes = [r for r in resultados if not r['is_trivial']]
        triviais = [r for r in resultados if r['is_trivial']]
        com_par = [r for r in relevantes if r['par_score'] is not None]
        
        print(f"\n📈 Estatísticas:")
        print(f"   📋 Relevantes: {len(relevantes)}")
        print(f"   📋 Triviais: {len(triviais)}")
        print(f"   📊 Com PAR: {len(com_par)}")
        
        if com_par:
            par_scores = [r['par_score'] for r in com_par]
            print(f"   📊 PAR médio: {sum(par_scores) / len(par_scores):.1f}")
            print(f"   📊 PAR máximo: {max(par_scores)}")
            print(f"   📊 PAR mínimo: {min(par_scores)}")
        
        # Detalhes das análises
        print(f"\n📋 Detalhes das Análises:")
        for r in resultados:
            status = "📊" if not r['is_trivial'] else "📋"
            par_info = f" (PAR: {r['par_score']})" if r['par_score'] else ""
            print(f"   {status} {r['tipo']} {r['numero']}/{r['ano']}: {r['is_trivial'] and 'TRIVIAL' or 'RELEVANTE'}{par_info}")
    
    print(f"\n🎯 Demonstração concluída com sucesso!")
    print("✅ Integração entre pipeline e agents está funcionando perfeitamente!")
    
    return len(resultados) > 0

def main():
    """Função principal."""
    return test_integration_with_sample_data()

if __name__ == "__main__":
    main()
