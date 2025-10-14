# /agents/tools/document_summarizer_tool.py

import os
from typing import Annotated

# A importação correta e única para usar o SDK nativo do Vertex AI
import vertexai
from vertexai.generative_models import GenerativeModel

# Pega o ID do projeto e a localização a partir de variáveis de ambiente.
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

# Inicializa o cliente do Vertex AI.
# Isto usará as 'Application Default Credentials' (ADC) que você configurou
# com 'gcloud auth application-default login'.
vertexai.init(project=PROJECT_ID, location=LOCATION)


def summarize_proposal_text(
    full_text: Annotated[str, "O texto completo e bruto de uma proposta legislativa."]
) -> str:
    """
    Recebe o texto completo de uma proposta e usa o Gemini 2.5 Flash via Vertex AI
    para criar um resumo objetivo, focado na Metodologia Kritikos.
    """
    # Instancia o modelo a partir do Vertex AI, especificando o nome do modelo.
    model = GenerativeModel(model_name="gemini-2.5-flash-001")
    
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
    
    response = model.generate_content([prompt])
    
    summary = response.text.strip()
    print(f"DEBUG: Resumo gerado (SummarizerAgent via Vertex AI): {summary[:100]}...")
    return summary