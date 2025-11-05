#!/usr/bin/env python3
"""
Utilitários de normalização de nomes para matching exato
Foco em normalizar nomes do CSV do Portal da Transparência com nomes do banco de dados
"""

import unicodedata
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from src.models.politico_models import Deputado


def normalizar_nome_para_matching(nome: str) -> str:
    """
    Normaliza nome para matching exato conforme padrão do CSV:
    - CAIXA ALTA
    - Sem acentos
    - Sem caracteres especiais
    - Espaços únicos
    
    Args:
        nome: Nome original a ser normalizado
        
    Returns:
        Nome normalizado para comparação
    """
    if not nome:
        return ""
    
    # Converter para string (caso venha número ou outro tipo)
    nome = str(nome).strip()
    
    if not nome:
        return ""
    
    # Remover acentos usando NFKD (mais robusto que NFD)
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    
    # Manter apenas letras e espaços, converter para maiúsculo
    nome = ''.join(c for c in nome if c.isalpha() or c.isspace()).upper()
    
    # Normalizar espaços (remover múltiplos e espaços nas extremidades)
    nome = ' '.join(nome.split())
    
    return nome


def criar_indice_nomes_normalizados(db: Session) -> dict:
    """
    Cria um índice em memória de nomes normalizados para performance
    Mapeia nome_normalizado -> deputado_id
    
    Args:
        db: Sessão do banco de dados
        
    Returns:
        Dicionário com mapeamento de nomes normalizados para IDs
    """
    print("🔍 Criando índice de nomes normalizados...")
    
    # Buscar todos os deputados
    deputados = db.query(Deputado).all()
    
    indice = {}
    for deputado in deputados:
        nome_normalizado = normalizar_nome_para_matching(deputado.nome)
        if nome_normalizado:
            indice[nome_normalizado] = deputado.id
    
    print(f"✅ Índice criado com {len(indice)} nomes normalizados")
    return indice


def buscar_deputado_por_nome_normalizado(nome_autor: str, db: Session, indice_nomes: dict = None) -> Optional[int]:
    """
    Busca ID do deputado pelo nome normalizado com matching exato apenas
    
    Args:
        nome_autor: Nome do autor do CSV
        db: Sessão do banco de dados
        indice_nomes: Índice opcional para performance
        
    Returns:
        ID do deputado ou None se não encontrado
    """
    if not nome_autor or 'bancada' in nome_autor.lower():
        return None
    
    nome_normalizado = normalizar_nome_para_matching(nome_autor)
    
    # Estratégia 1: Usar índice em memória (mais rápido) - MATCHING EXATO APENAS
    if indice_nomes and nome_normalizado in indice_nomes:
        print(f"      ✅ Match exato (índice): {nome_autor} -> ID {indice_nomes[nome_normalizado]}")
        return indice_nomes[nome_normalizado]
    
    # Estratégia 2: Busca direta no banco com normalização Python - MATCHING EXATO APENAS
    deputado = db.query(Deputado).filter(
        func.upper(Deputado.nome) == nome_normalizado
    ).first()
    
    if deputado:
        print(f"      ✅ Match exato (banco): {nome_autor} -> ID {deputado.id} ({deputado.nome})")
        return deputado.id
    
    # SEM FALLBACKS - apenas matching exato como solicitado
    print(f"      ❌ Nenhum match exato encontrado para: {nome_autor} (normalizado: {nome_normalizado})")
    return None


def testar_normalizacao(nome_csv: str, nome_banco: str) -> dict:
    """
    Testa a normalização entre um nome do CSV e um nome do banco
    
    Args:
        nome_csv: Nome do autor no CSV
        nome_banco: Nome do deputado no banco
        
    Returns:
        Dicionário com resultados do teste
    """
    nome_csv_norm = normalizar_nome_para_matching(nome_csv)
    nome_banco_norm = normalizar_nome_para_matching(nome_banco)
    
    return {
        'nome_csv': nome_csv,
        'nome_banco': nome_banco,
        'nome_csv_normalizado': nome_csv_norm,
        'nome_banco_normalizado': nome_banco_norm,
        'match_exato': nome_csv_norm == nome_banco_norm,
        'similaridade': nome_csv_norm == nome_banco_norm
    }


def analisar_qualidade_matching(db: Session, amostra_csv: list = None) -> dict:
    """
    Analisa a qualidade do matching com amostra de dados
    
    Args:
        db: Sessão do banco de dados
        amostra_csv: Amostra de nomes do CSV para testar
        
    Returns:
        Estatísticas da qualidade do matching
    """
    print("📊 Analisando qualidade do matching...")
    
    # Criar índice
    indice = criar_indice_nomes_normalizados(db)
    
    # Se não tiver amostra, usar nomes comuns
    if not amostra_csv:
        amostra_csv = [
            "JULIO CESAR", "ZUCCO", "JORGE BRAZ", "ALEX MANENTE", 
            "JOSEILDO RAMOS", "CARLOS ZARATTINI", "MARILDA ROCHA"
        ]
    
    resultados = {
        'total_testados': len(amostra_csv),
        'matches_encontrados': 0,
        'matches_nao_encontrados': 0,
        'detalhes': []
    }
    
    for nome_csv in amostra_csv:
        deputado_id = buscar_deputado_por_nome_normalizado(nome_csv, db, indice)
        
        if deputado_id:
            resultados['matches_encontrados'] += 1
            status = '✅ Encontrado'
        else:
            resultados['matches_nao_encontrados'] += 1
            status = '❌ Não encontrado'
        
        resultados['detalhes'].append({
            'nome_csv': nome_csv,
            'deputado_id': deputado_id,
            'status': status
        })
    
    resultados['percentual_sucesso'] = (resultados['matches_encontrados'] / resultados['total_testados']) * 100
    
    print(f"📊 Resultados: {resultados['matches_encontrados']}/{resultados['total_testados']} ({resultados['percentual_sucesso']:.1f}%)")
    
    return resultados


if __name__ == "__main__":
    # Teste rápido do módulo
    print("🧪 Testando módulo de normalização...")
    
    # Testes básicos
    testes = [
        ("JULIO CESAR", "Júlio César"),
        ("ZUCCO", "Zucco"),
        ("JORGE BRAZ", "Jorge Braz"),
        ("ALEX MANENTE", "Alex Manente")
    ]
    
    for nome_csv, nome_banco in testes:
        resultado = testar_normalizacao(nome_csv, nome_banco)
        print(f"\n📋 Teste: {nome_csv} vs {nome_banco}")
        print(f"   CSV normalizado: {resultado['nome_csv_normalizado']}")
        print(f"   Banco normalizado: {resultado['nome_banco_normalizado']}")
        print(f"   Match exato: {resultado['match_exato']}")
    
    print("\n✅ Testes concluídos!")
