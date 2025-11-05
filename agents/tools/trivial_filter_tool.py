# /agents/tools/trivial_filter_tool.py

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
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)


def save_trivial_result_to_db(proposicao_id: int, is_trivial: bool) -> bool:
    """
    Salva o resultado do filtro de trivialidade no banco de dados.
    
    Args:
        proposicao_id: ID da proposição
        is_trivial: Resultado do filtro
        
    Returns:
        True se salvo com sucesso, False caso contrário
    """
    try:
        session = get_db_session()
        
        # Verificar se já existe análise para esta proposição
        analise = session.query(AnaliseProposicao).filter_by(proposicao_id=proposicao_id).first()
        
        if analise:
            # Atualizar análise existente
            analise.is_trivial = is_trivial
            analise.data_filtro_trivial = datetime.utcnow()
        else:
            # Criar nova análise
            analise = AnaliseProposicao(
                proposicao_id=proposicao_id,
                is_trivial=is_trivial,
                data_filtro_trivial=datetime.utcnow()
            )
            session.add(analise)
        
        session.commit()
        
        # Registrar log
        log = LogProcessamento(
            tipo_processo='filtro',
            proposicao_id=proposicao_id,
            status='sucesso',
            dados_saida={'is_trivial': is_trivial}
        )
        session.add(log)
        session.commit()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"Erro ao salvar resultado do filtro no banco: {e}")
        return False


def is_summary_trivial(summary: str, proposicao_id: Optional[int] = None) -> bool:
    """
    Usa o Gemini 2.5 Flash para determinar se um resumo de proposta legislativa é trivial.
    Uma proposta é considerada trivial se:
    1. Tem impacto geográfico muito limitado (ex: uma única cidade, bairro, ou instituição específica).
    2. Trata de assuntos administrativos internos do governo sem impacto direto na vida dos cidadãos.
    3. Concede homenagens, títulos ou nomes de locais.
    4. Tem escopo extremamente técnico ou burocrático que não afeta o público geral.
    
    Args:
        summary: Resumo da proposta legislativa.
        proposicao_id: ID da proposição (opcional, para persistência)
        
    Returns:
        True se a proposta for trivial, False caso contrário.
    """
    prompt = f"""
    Você é um assistente de IA especializado em análise legislativa para o projeto Kritikos.
    Sua única tarefa é analisar o resumo de uma proposta legislativa e determinar se ela é TRIVIAL ou RELEVANTE.

    Uma proposta é TRIVIAL se:
    1. Tem impacto geográfico muito limitado (ex: uma única cidade, bairro, ou instituição específica).
    2. Trata de assuntos administrativos internos do governo sem impacto direto na vida dos cidadãos.
    3. Concede homenagens, títulos ou nomes de locais.
    4. Tem escopo extremamente técnico ou burocrático que não afeta o público geral.
    5. Autoriza abertura de crédito ou destinação de recursos sem detalhar o impacto social.

    Uma proposta é RELEVANTE se:
    1. Afeta um número significativo de cidadãos em múltiplas localidades.
    2. Cria direitos, deveres ou obrigações para a população em geral.
    3. Estabelece políticas públicas com impacto social, econômico ou ambiental.
    4. Modifica legislação que afeta o cotidiano das pessoas.
    5. Tem potencial de impacto nacional ou estadual.

    Responda APENAS com a palavra "TRIVIAL" ou "RELEVANTE". Nenhuma explicação adicional.

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
        
        result = response.text.strip().upper()
        is_trivial = result == "TRIVIAL"
        
        print(f"DEBUG: Filtro de trivialidade: {result} -> {'Trivial' if is_trivial else 'Relevante'}")
        
        # Salvar no banco se proposicao_id foi fornecido
        if proposicao_id:
            save_trivial_result_to_db(proposicao_id, is_trivial)
        
        return is_trivial
        
    except Exception as e:
        print(f"Erro ao verificar trivialidade: {e}")
        
        # Registrar erro no log
        if proposicao_id:
            try:
                session = get_db_session()
                log = LogProcessamento(
                    tipo_processo='filtro',
                    proposicao_id=proposicao_id,
                    status='erro',
                    mensagem=str(e),
                    dados_entrada={'resumo_tamanho': len(summary)}
                )
                session.add(log)
                session.commit()
                session.close()
            except:
                pass  # Evitar recursão de erros
        
        # Em caso de erro, considerar como não trivial para não perder análises importantes
        return False


def get_trivial_statistics() -> Dict[str, Any]:
    """
    Retorna estatísticas sobre o filtro de trivialidade.
    
    Returns:
        Dicionário com estatísticas
    """
    try:
        session = get_db_session()
        
        # Total de análises
        total_analises = session.query(AnaliseProposicao).count()
        
        # Análises com filtro aplicado
        com_filtro = session.query(AnaliseProposicao).filter(
            AnaliseProposicao.is_trivial.isnot(None)
        ).count()
        
        # Proposições triviais
        triviais = session.query(AnaliseProposicao).filter(
            AnaliseProposicao.is_trivial == True
        ).count()
        
        # Proposições relevantes
        relevantes = session.query(AnaliseProposicao).filter(
            AnaliseProposicao.is_trivial == False
        ).count()
        
        session.close()
        
        return {
            'total_analises': total_analises,
            'com_filtro_aplicado': com_filtro,
            'proposicoes_triviais': triviais,
            'proposicoes_relevantes': relevantes,
            'percentual_triviais': (triviais / com_filtro * 100) if com_filtro > 0 else 0,
            'percentual_relevantes': (relevantes / com_filtro * 100) if com_filtro > 0 else 0
        }
        
    except Exception as e:
        print(f"Erro ao obter estatísticas de trivialidade: {e}")
        return {
            'total_analises': 0,
            'com_filtro_aplicado': 0,
            'proposicoes_triviais': 0,
            'proposicoes_relevantes': 0,
            'percentual_triviais': 0,
            'percentual_relevantes': 0
        }
