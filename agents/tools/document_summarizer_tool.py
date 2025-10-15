# /agents/tools/document_summarizer_tool.py

import os

# Nova importação para usar o SDK de IA Generativa do Google
from google import genai

# Pega o ID do projeto e a localização a partir de variáveis de ambiente.
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# Inicializa o cliente do Google GenAI com suporte a Vertex AI.
# Isto usará as 'Application Default Credentials' (ADC) que você configurou
# com 'gcloud auth application-default login'.
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)


def summarize_proposal_text(full_text: str) -> str:
    """
    Recebe o texto completo de uma proposta e usa o Gemini 2.5 Flash via Google GenAI
    para criar um resumo objetivo, focado na Metodologia Kritikos.
    """
    prompt = f"""
    Você é um assistente de IA especializado em análise legislativa para o projeto Kritikos.
    Sua tarefa é ler o texto completo de uma proposta legislativa e gerar um resumo conciso e objetivo em português.

    O resumo DEVE focar EXCLUSIVAMENTE em extrair informações que ajudem a avaliar os seguintes critérios:
    - **Propósito Central:** Qual problema a lei resolve?
    - **Escopo e Impacto:** Quem são os principais beneficiados ou afetados? (Ex: 'todos os cidadãos', 'trabalhadores de uma categoria', 'uma cidade específica').
    - **Mecanismo de Ação:** Como a lei pretende atingir seu objetivo? (Ex: 'cria um incentivo fiscal', 'aumenta uma penalidade', 'estabelece um programa social').
    - **Sustentabilidade Fiscal:** O texto menciona fontes de custeio, criação de novas despesas ou impacto orçamentário?

    Ignore jargões legais, artigos de revogação e formalidades. Vá direto ao ponto.
    O resumo não deve passar de 250 palavras.

    Texto da proposta para resumir:
    ---
    {full_text}
    ---
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    summary = response.text.strip()
    print(f"DEBUG: Resumo gerado (SummarizerAgent via Google GenAI): {summary[:100]}...")
    return summary


def analyze_proposal_par(summary: str) -> str:
    """
    Analisa o resumo de uma proposta não-trivial e calcula a Pontuação de Relevância (PAR)
    usando a Metodologia Kritikos, retornando um JSON estruturado.
    """
    prompt = f"""
    Você é um analista legislativo imparcial e especialista do Projeto Kritikos.
    Sua única função é avaliar o resumo de uma proposta legislativa e retornar uma análise estruturada em formato JSON, sem nenhum texto, explicação ou formatação de markdown adicional.

    Siga rigorosamente a Metodologia Kritikos para calcular a Pontuação de Relevância (PAR):
    1.  **Escopo e Impacto (0-30 pts):** Avalie se a proposta afeta a maioria da população.
    2.  **Alinhamento com ODS (0-30 pts):** Identifique a quais dos 17 ODS da ONU a proposta se alinha.
    3.  **Inovação/Eficiência (0-20 pts):** Verifique se a proposta é original e eficiente.
    4.  **Sustentabilidade Fiscal (0-20 pts):** Analise se a proposta tem fontes de custeio claras ou impacto neutro.
    5.  **Penalidade por Oneração (0-15 pts):** Subtraia pontos se a proposta criar despesas insustentáveis.

    O JSON de saída DEVE ter EXATAMENTE a seguinte estrutura:
    {{
      "escopo_impacto": <int>,
      "alinhamento_ods": <int>,
      "inovacao_eficiencia": <int>,
      "sustentabilidade_fiscal": <int>,
      "penalidade_oneracao": <int>,
      "par_final": <int>,
      "resumo_analise": "<string>",
      "ods_identificados": [<int>]
    }}

    Resumo da proposta para analisar:
    ---
    {summary}
    ---
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    analysis = response.text.strip()
    print(f"DEBUG: Análise PAR gerada: {analysis[:100]}...")
    return analysis
