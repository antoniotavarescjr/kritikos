#!/usr/bin/env python3
"""
Ferramentas de banco de dados para os agentes Kritikos.
Conecta os agentes com os dados de deputados e proposições.
"""

import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from models.db_utils import get_db_session
from sqlalchemy import text


def get_proposicao_completa(proposicao_id: int) -> Optional[Dict[str, Any]]:
    """
    Retorna dados completos de uma proposição incluindo texto e autores.
    
    Args:
        proposicao_id: ID da proposição no banco
        
    Returns:
        Dicionário com dados completos ou None se não encontrado
    """
    try:
        session = get_db_session()
        
        # Buscar proposição com dados básicos
        prop_data = session.execute(text("""
            SELECT 
                p.id,
                p.api_camara_id,
                p.tipo,
                p.numero,
                p.ano,
                p.ementa,
                p.keywords,
                p.data_apresentacao,
                p.situacao,
                p.explicacao,
                p.link_inteiro_teor
            FROM proposicoes p
            WHERE p.id = :id
        """), {"id": proposicao_id}).fetchone()
        
        if not prop_data:
            session.close()
            return None
        
        # Buscar autores da proposição
        autores_data = session.execute(text("""
            SELECT 
                d.id as deputado_id,
                d.nome as deputado_nome,
                d.email,
                d.foto_url,
                a.tipo_autoria
            FROM autorias a
            JOIN deputados d ON a.deputado_id = d.id
            WHERE a.proposicao_id = :prop_id
            AND a.deputado_id IS NOT NULL
            ORDER BY a.tipo_autoria
        """), {"prop_id": proposicao_id}).fetchall()
        
        # Montar dicionário de resposta
        result = {
            "id": prop_data[0],
            "api_camara_id": prop_data[1],
            "tipo": prop_data[2],
            "numero": prop_data[3],
            "ano": prop_data[4],
            "ementa": prop_data[5] or "",
            "keywords": prop_data[6] or "",
            "apresentacao": prop_data[7] or "",
            "situacao": prop_data[8] or "",
            "ementa_detalhada": prop_data[9] or "",
            "url_inteiro_teor": prop_data[10] or "",
            "autores": [
                {
                    "deputado_id": autor[0],
                    "nome": autor[1],
                    "email": autor[2],
                    "foto_url": autor[3],
                    "tipo_autoria": autor[4]
                }
                for autor in autores_data
            ]
        }
        
        session.close()
        return result
        
    except Exception as e:
        print(f"Erro ao buscar proposição {proposicao_id}: {e}")
        return None


def get_dados_deputado(deputado_id: int) -> Optional[Dict[str, Any]]:
    """
    Retorna dados completos de um deputado incluindo estatísticas.
    
    Args:
        deputado_id: ID do deputado no banco
        
    Returns:
        Dicionário com dados completos ou None se não encontrado
    """
    try:
        session = get_db_session()
        
        # Dados básicos do deputado
        dep_data = session.execute(text("""
            SELECT 
                d.id,
                d.nome,
                d.email,
                d.foto_url,
                d.situacao
            FROM deputados d
            WHERE d.id = :id
        """), {"id": deputado_id}).fetchone()
        
        if not dep_data:
            session.close()
            return None
        
        # Estatísticas do deputado
        stats_data = session.execute(text("""
            SELECT 
                COUNT(DISTINCT p.id) as total_proposicoes,
                COUNT(DISTINCT CASE WHEN p.ano = 2025 THEN p.id END) as props_2025,
                COUNT(a.id) as total_autorias,
                COUNT(DISTINCT CASE WHEN p.ano = 2025 THEN a.id END) as autorias_2025,
                STRING_AGG(DISTINCT p.tipo, ', ') as tipos_proposicoes
            FROM deputados d
            LEFT JOIN autorias a ON d.id = a.deputado_id
            LEFT JOIN proposicoes p ON a.proposicao_id = p.id
            WHERE d.id = :id
        """), {"id": deputado_id}).fetchone()
        
        # Ranking atual
        ranking_data = session.execute(text("""
            SELECT 
                COUNT(DISTINCT p2.id) + 1 as posicao
            FROM deputados d1
            JOIN autorias a1 ON d1.id = a1.deputado_id
            JOIN proposicoes p1 ON a1.proposicao_id = p1.id AND p1.ano = 2025
            CROSS JOIN deputados d2
            JOIN autorias a2 ON d2.id = a2.deputado_id
            JOIN proposicoes p2 ON a2.proposicao_id = p2.id AND p2.ano = 2025
            WHERE d1.id = :id
            GROUP BY d1.id, d1.nome
            HAVING COUNT(DISTINCT p1.id) < COUNT(DISTINCT p2.id)
            ORDER BY COUNT(DISTINCT p2.id) ASC
            LIMIT 1
        """), {"id": deputado_id}).fetchone()
        
        result = {
            "id": dep_data[0],
            "nome": dep_data[1],
            "email": dep_data[2],
            "foto_url": dep_data[3],
            "situacao": dep_data[4],
            "estatisticas": {
                "total_proposicoes": stats_data[0] or 0,
                "props_2025": stats_data[1] or 0,
                "total_autorias": stats_data[2] or 0,
                "autorias_2025": stats_data[3] or 0,
                "tipos_proposicoes": stats_data[4] or ""
            },
            "ranking_posicao": ranking_data[0] if ranking_data else None
        }
        
        session.close()
        return result
        
    except Exception as e:
        print(f"Erro ao buscar deputado {deputado_id}: {e}")
        return None


def buscar_proposicoes_por_criterio(
    ano: int = 2025,
    tipo: Optional[str] = None,
    limite: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Busca proposições com filtros avançados.
    
    Args:
        ano: Ano das proposições (padrão: 2025)
        tipo: Tipo específico (PL, PEC, etc.)
        limite: Limite de resultados
        offset: Offset para paginação
        
    Returns:
        Lista de dicionários com proposições
    """
    try:
        session = get_db_session()
        
        # Construir query dinâmica
        query = """
            SELECT 
                p.id,
                p.tipo,
                p.numero,
                p.ano,
                p.ementa,
                p.data_apresentacao,
                p.situacao,
                COUNT(a.id) as total_autores
            FROM proposicoes p
            LEFT JOIN autorias a ON p.id = a.proposicao_id AND a.deputado_id IS NOT NULL
            WHERE p.ano = :ano
        """
        params = {"ano": ano, "limite": limite, "offset": offset}
        
        if tipo:
            query += " AND p.tipo = :tipo"
            params["tipo"] = tipo
        
        query += """
            GROUP BY p.id, p.tipo, p.numero, p.ano, p.ementa, p.data_apresentacao, p.situacao
            ORDER BY p.data_apresentacao DESC
            LIMIT :limite OFFSET :offset
        """
        
        results = session.execute(text(query), params).fetchall()
        
        proposicoes = []
        for row in results:
            proposicoes.append({
                "id": row[0],
                "tipo": row[1],
                "numero": row[2],
                "ano": row[3],
                "ementa": row[4] or "",
                "apresentacao": str(row[5]) if row[5] else "",
                "situacao": row[6] or "",
                "total_autores": row[7] or 0
            })
        
        session.close()
        return proposicoes
        
    except Exception as e:
        print(f"Erro ao buscar proposições: {e}")
        return []


def get_ranking_atualizado(limite: int = 100) -> List[Dict[str, Any]]:
    """
    Retorna ranking atualizado de deputados por produtividade.
    
    Args:
        limite: Número de deputados no ranking
        
    Returns:
        Lista de dicionários com ranking
    """
    try:
        session = get_db_session()
        
        ranking_data = session.execute(text("""
            SELECT 
                d.id,
                d.nome,
                d.email,
                d.foto_url,
                COUNT(DISTINCT p.id) as total_proposicoes,
                COUNT(a.id) as total_autorias,
                STRING_AGG(DISTINCT p.tipo, ', ') as tipos_proposicoes,
                MIN(p.data_apresentacao) as primeira_prop,
                MAX(p.data_apresentacao) as ultima_prop
            FROM deputados d
            JOIN autorias a ON d.id = a.deputado_id
            JOIN proposicoes p ON a.proposicao_id = p.id
            WHERE p.ano = 2025
            AND a.deputado_id IS NOT NULL
            GROUP BY d.id, d.nome, d.email, d.foto_url
            HAVING COUNT(DISTINCT p.id) > 0
            ORDER BY total_proposicoes DESC, total_autorias DESC
            LIMIT :limite
        """), {"limite": limite}).fetchall()
        
        ranking = []
        for i, row in enumerate(ranking_data, 1):
            ranking.append({
                "posicao": i,
                "id_deputado": row[0],
                "nome": row[1],
                "email": row[2],
                "foto_url": row[3],
                "total_proposicoes": row[4],
                "total_autorias": row[5],
                "tipos_proposicoes": row[6],
                "primeira_proposicao": str(row[7]) if row[7] else "",
                "ultima_proposicao": str(row[8]) if row[8] else ""
            })
        
        session.close()
        return ranking
        
    except Exception as e:
        print(f"Erro ao gerar ranking: {e}")
        return []


def get_estatisticas_gerais() -> Dict[str, Any]:
    """
    Retorna estatísticas gerais do sistema.
    
    Returns:
        Dicionário com estatísticas completas
    """
    try:
        session = get_db_session()
        
        # Estatísticas gerais
        stats = session.execute(text("""
            SELECT 
                'deputados' as tabela, COUNT(*) as registros
            FROM deputados
            UNION ALL
            SELECT 
                'proposicoes_2025' as tabela, COUNT(*) as registros
            FROM proposicoes WHERE ano = 2025
            UNION ALL
            SELECT 
                'autorias_2025' as tabela, COUNT(*) as registros
            FROM autorias a
            JOIN proposicoes p ON a.proposicao_id = p.id
            WHERE p.ano = 2025 AND a.deputado_id IS NOT NULL
            UNION ALL
            SELECT 
                'partidos' as tabela, COUNT(*) as registros
            FROM partidos
        """)).fetchall()
        
        # Cobertura de autorias
        cobertura = session.execute(text("""
            SELECT 
                COUNT(DISTINCT p.id) as total_props,
                COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN p.id END) as com_autoria,
                ROUND(
                    COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN p.id END) * 100.0 / 
                    COUNT(DISTINCT p.id), 2
                ) as cobertura_percent
            FROM proposicoes p
            LEFT JOIN autorias a ON p.id = a.proposicao_id
            WHERE p.ano = 2025
        """)).fetchone()
        
        # Distribuição por tipo
        tipos = session.execute(text("""
            SELECT 
                tipo,
                COUNT(*) as quantidade
            FROM proposicoes
            WHERE ano = 2025
            GROUP BY tipo
            ORDER BY quantidade DESC
        """)).fetchall()
        
        result = {
            "totais": {stat[0]: stat[1] for stat in stats},
            "cobertura_autorias": {
                "total_proposicoes": cobertura[0],
                "com_autoria": cobertura[1],
                "percentual": cobertura[2]
            },
            "distribuicao_tipos": {tipo[0]: tipo[1] for tipo in tipos},
            "ultima_atualizacao": datetime.now().isoformat()
        }
        
        session.close()
        return result
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return {}


# Funções de conveniência para os agentes
def get_texto_completo_proposicao(proposicao_id: int) -> str:
    """
    Retorna o texto completo da proposição para análise.
    
    Args:
        proposicao_id: ID da proposição
        
    Returns:
        String com texto completo concatenado
    """
    prop = get_proposicao_completa(proposicao_id)
    if not prop:
        return ""
    
    # Montar texto completo para análise
    texto = f"""
    TIPO: {prop['tipo']} {prop['numero']}/{prop['ano']}
    
    EMENTA: {prop['ementa']}
    
    EMENTA DETALHADA: {prop['ementa_detalhada']}
    
    KEYWORDS: {prop['keywords']}
    
    SITUAÇÃO: {prop['situacao']}
    
    AUTORES: {', '.join([a['nome'] for a in prop['autores']])}
    """
    
    return texto.strip()


def get_proposicoes_para_analise(limite: int = 10) -> List[int]:
    """
    Retorna IDs de proposições para análise em lote.
    
    Args:
        limite: Número de proposições
        
    Returns:
        Lista de IDs de proposições
    """
    props = buscar_proposicoes_por_criterio(limite=limite)
    return [prop["id"] for prop in props]
