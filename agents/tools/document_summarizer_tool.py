# /agents/tools/document_summarizer_tool.py

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Adicionar backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from models.db_utils import get_db_session
from models.analise_models import AnaliseProposicao, LogProcessamento

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


def save_summary_to_db(proposicao_id: int, resumo_texto: str) -> bool:
    """
    Salva o resumo da proposição no banco de dados.
    
    Args:
        proposicao_id: ID da proposição
        resumo_texto: Texto do resumo gerado
        
    Returns:
        True se salvo com sucesso, False caso contrário
    """
    try:
        session = get_db_session()
        
        # Verificar se já existe análise para esta proposição
        analise = session.query(AnaliseProposicao).filter_by(proposicao_id=proposicao_id).first()
        
        if analise:
            # Atualizar resumo existente
            analise.resumo_texto = resumo_texto
            analise.data_resumo = datetime.utcnow()
        else:
            # Criar nova análise
            analise = AnaliseProposicao(
                proposicao_id=proposicao_id,
                resumo_texto=resumo_texto,
                data_resumo=datetime.utcnow()
            )
            session.add(analise)
        
        session.commit()
        
        # Registrar log
        log = LogProcessamento(
            tipo_processo='resumo',
            proposicao_id=proposicao_id,
            status='sucesso',
            dados_saida={'resumo_texto': resumo_texto[:500]}  # Primeiros 500 chars
        )
        session.add(log)
        session.commit()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"Erro ao salvar resumo no banco: {e}")
        return False


def summarize_proposal_text(full_text: str, proposicao_id: Optional[int] = None) -> str:
    """
    Recebe o texto completo de uma proposta e usa o Gemini 2.5 Flash via Google GenAI
    para criar um resumo objetivo, focado na Metodologia Kritikos.
    
    Args:
        full_text: Texto completo da proposição
        proposicao_id: ID da proposição (opcional, para persistência)
        
    Returns:
        Resumo gerado
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
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        summary = response.text.strip()
        print(f"DEBUG: Resumo gerado (SummarizerAgent via Google GenAI): {summary[:100]}...")
        
        # Salvar no banco se proposicao_id foi fornecido
        if proposicao_id:
            save_summary_to_db(proposicao_id, summary)
        
        return summary
        
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        
        # Registrar erro no log
        if proposicao_id:
            try:
                session = get_db_session()
                log = LogProcessamento(
                    tipo_processo='resumo',
                    proposicao_id=proposicao_id,
                    status='erro',
                    mensagem=str(e),
                    dados_entrada={'texto_tamanho': len(full_text)}
                )
                session.add(log)
                session.commit()
                session.close()
            except:
                pass  # Evitar recursão de erros
        
        return ""


def analyze_proposal_par(summary: str, proposicao_id: Optional[int] = None) -> str:
    """
    Analisa o resumo de uma proposta não-trivial e calcula a Pontuação de Relevância (PAR)
    usando a Metodologia Kritikos, retornando um JSON estruturado.
    
    Args:
        summary: Resumo da proposição
        proposicao_id: ID da proposição (opcional, para persistência)
        
    Returns:
        Análise PAR em formato JSON
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
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        analysis = response.text.strip()
        print(f"DEBUG: Análise PAR gerada: {analysis[:100]}...")
        
        # Salvar no banco se proposicao_id foi fornecido
        if proposicao_id:
            save_par_to_db(proposicao_id, analysis)
        
        return analysis
        
    except Exception as e:
        print(f"Erro ao gerar análise PAR: {e}")
        
        # Registrar erro no log
        if proposicao_id:
            try:
                session = get_db_session()
                log = LogProcessamento(
                    tipo_processo='par',
                    proposicao_id=proposicao_id,
                    status='erro',
                    mensagem=str(e),
                    dados_entrada={'resumo_tamanho': len(summary)}
                )
                session.add(log)
                session.commit()
                session.close()
            except:
                pass
        
        return ""


def save_par_to_db(proposicao_id: int, analysis_json: str) -> bool:
    """
    Salva a análise PAR no banco de dados.
    
    Args:
        proposicao_id: ID da proposição
        analysis_json: Análise em formato JSON string
        
    Returns:
        True se salvo com sucesso, False caso contrário
    """
    try:
        import json
        
        # Parse do JSON
        analysis_data = json.loads(analysis_json)
        
        session = get_db_session()
        
        # Verificar se já existe análise para esta proposição
        analise = session.query(AnaliseProposicao).filter_by(proposicao_id=proposicao_id).first()
        
        if analise:
            # Atualizar análise existente
            analise.par_score = analysis_data.get('par_final')
            analise.escopo_impacto = analysis_data.get('escopo_impacto')
            analise.alinhamento_ods = analysis_data.get('alinhamento_ods')
            analise.inovacao_eficiencia = analysis_data.get('inovacao_eficiencia')
            analise.sustentabilidade_fiscal = analysis_data.get('sustentabilidade_fiscal')
            analise.penalidade_oneracao = analysis_data.get('penalidade_oneracao')
            analise.ods_identificados = analysis_data.get('ods_identificados')
            analise.resumo_analise = analysis_data.get('resumo_analise')
            analise.data_analise = datetime.utcnow()
        else:
            # Criar nova análise
            analise = AnaliseProposicao(
                proposicao_id=proposicao_id,
                par_score=analysis_data.get('par_final'),
                escopo_impacto=analysis_data.get('escopo_impacto'),
                alinhamento_ods=analysis_data.get('alinhamento_ods'),
                inovacao_eficiencia=analysis_data.get('inovacao_eficiencia'),
                sustentabilidade_fiscal=analysis_data.get('sustentabilidade_fiscal'),
                penalidade_oneracao=analysis_data.get('penalidade_oneracao'),
                ods_identificados=analysis_data.get('ods_identificados'),
                resumo_analise=analysis_data.get('resumo_analise'),
                data_analise=datetime.utcnow()
            )
            session.add(analise)
        
        session.commit()
        
        # Registrar log
        log = LogProcessamento(
            tipo_processo='par',
            proposicao_id=proposicao_id,
            status='sucesso',
            dados_saida={'par_final': analysis_data.get('par_final')}
        )
        session.add(log)
        session.commit()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"Erro ao salvar análise PAR no banco: {e}")
        return False
