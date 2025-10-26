"""
Função otimizada para buscar ID do deputado pelo nome
Usando mapeamento pré-calculado para melhor performance
"""

from sqlalchemy.orm import Session
from models.politico_models import Deputado
from sqlalchemy import func

# Importar mapeamento gerado
from mapeamento_nomes_api_banco import MAPEAMENTO_NOMES_API_BANCO

def buscar_deputado_por_nome_otimizado(nome_autor: str, ano: int, db: Session) -> int:
    """
    Busca ID do deputado usando mapeamento pré-calculado
    Fallback para busca no banco se não encontrar no mapeamento
    """
    if not nome_autor or 'BANCADA' in nome_autor.upper():
        return None
    
    # Normalizar nome
    nome_normalizado = nome_autor.strip().upper()
    
    # 1. Tentar mapeamento direto
    if ano in MAPEAMENTO_NOMES_API_BANCO:
        if nome_normalizado in MAPEAMENTO_NOMES_API_BANCO[ano]:
            return MAPEAMENTO_NOMES_API_BANCO[ano][nome_normalizado]
    
    # 2. Fallback para busca no banco (método original)
    deputado = db.query(Deputado).filter(
        func.upper(Deputado.nome) == func.upper(nome_autor.strip())
    ).first()
    
    if deputado:
        return deputado.id
    
    # 3. Busca parcial
    deputado = db.query(Deputado).filter(
        Deputado.nome.ilike(f"%{nome_autor.strip()}%")
    ).first()
    
    if deputado:
        return deputado.id
    
    # 4. Busca por primeiro nome
    partes_nome = nome_autor.strip().split()
    if len(partes_nome) >= 2:
        primeiro_nome = partes_nome[0]
        deputado = db.query(Deputado).filter(
            Deputado.nome.ilike(f"{primeiro_nome}%")
        ).first()
        
        if deputado:
            return deputado.id
    
    return None
