"""
Router para endpoints de busca avançada
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.deputado import DeputadoResponse
from schemas.proposicao import ProposicaoResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/proposicoes")
async def buscar_proposicoes(
    q: str = Query(..., description="Termo de busca obrigatório"),
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de proposição"),
    tem_analise: Optional[bool] = Query(None, description="Filtrar se tem análise"),
    par_minimo: Optional[float] = Query(None, description="Score PAR mínimo"),
    relevancia: Optional[str] = Query(None, description="Filtrar por relevância")
):
    """
    Buscar proposições por texto com filtros avançados
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        # Simulação de busca
        proposicoes_mock = [
            {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
                "tipo": "PL",
                "numero": "1234/2025",
                "ano": 2025,
                "ementa": "Dispõe sobre políticas de educação ambiental nas escolas",
                "tem_analise": True,
                "resumo": "Proposta que implementa educação ambiental nas escolas",
                "score_par": 75.5,
                "relevancia": "alta",
                "data_apresentacao": "2025-01-05",
                "situacao": "Em tramitação"
            },
            {
                "id": 2,
                "deputado_id": 123,
                "deputado_nome": "Ana Silva",
                "tipo": "PL",
                "numero": "5678/2025",
                "ano": 2025,
                "ementa": "Programa de incentivo à reciclagem",
                "tem_analise": True,
                "resumo": "Cria programa nacional de incentivo fiscal para empresas de reciclagem",
                "score_par": 68.0,
                "relevancia": "média",
                "data_apresentacao": "2025-01-10",
                "situacao": "Em tramitação"
            }
        ]
        
        # Aplicar filtros (simulação)
        if tem_analise is not None:
            proposicoes_mock = [p for p in proposicoes_mock if p["tem_analise"] == tem_analise]
        
        if par_minimo is not None:
            proposicoes_mock = [p for p in proposicoes_mock if p["score_par"] >= par_minimo]
        
        if relevancia is not None:
            proposicoes_mock = [p for p in proposicoes_mock if p["relevancia"].lower() == relevancia.lower()]
        
        return {
            "data": proposicoes_mock,
            "meta": {
                "total": len(proposicoes_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1,
                "query": q,
                "filtros": {
                    "ano": ano,
                    "tipo": tipo,
                    "tem_analise": tem_analise,
                    "par_minimo": par_minimo,
                    "relevancia": relevancia
                }
            },
            "links": {
                "self": f"/api/busca/proposicoes?q={q}&page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar proposições: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/deputados")
async def buscar_deputados(
    q: str = Query(..., description="Termo de busca obrigatório"),
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    partido: Optional[str] = Query(None, description="Filtrar por partido"),
    uf: Optional[str] = Query(None, description="Filtrar por estado"),
    idp_minimo: Optional[float] = Query(None, description="IDP mínimo")
):
    """
    Buscar deputados por nome com filtros avançados
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        # Simulação de busca
        deputados_mock = [
            {
                "id": 745,
                "nome": "Beto Faro",
                "sigla_partido": "PT",
                "sigla_uf": "AC",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/745.jpg",
                "email": "dep.beto.faro@camara.leg.br",
                "idp": 75.5,
                "idp_ranking": 15,
                "total_gastos": 150000.00,
                "total_emendas": 25,
                "total_proposicoes": 42,
                "status": "ativo",
                "ultima_atualizacao": "2025-01-07T15:00:00Z"
            },
            {
                "id": 123,
                "nome": "Ana Silva",
                "sigla_partido": "PSDB",
                "sigla_uf": "SP",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/123.jpg",
                "email": "dep.ana.silva@camara.leg.br",
                "idp": 82.3,
                "idp_ranking": 8,
                "total_gastos": 180000.00,
                "total_emendas": 30,
                "total_proposicoes": 38,
                "status": "ativo",
                "ultima_atualizacao": "2025-01-07T15:00:00Z"
            }
        ]
        
        # Aplicar filtros (simulação)
        if partido is not None:
            deputados_mock = [d for d in deputados_mock if d["sigla_partido"].lower() == partido.lower()]
        
        if uf is not None:
            deputados_mock = [d for d in deputados_mock if d["sigla_uf"].lower() == uf.lower()]
        
        if idp_minimo is not None:
            deputados_mock = [d for d in deputados_mock if d["idp"] >= idp_minimo]
        
        # Busca por nome (contém o termo)
        if q:
            deputados_mock = [d for d in deputados_mock if q.lower() in d["nome"].lower()]
        
        return {
            "data": deputados_mock,
            "meta": {
                "total": len(deputados_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1,
                "query": q,
                "filtros": {
                    "partido": partido,
                    "uf": uf,
                    "idp_minimo": idp_minimo
                }
            },
            "links": {
                "self": f"/api/busca/deputados?q={q}&page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar deputados: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/sugestoes")
async def sugestoes_busca(
    q: str = Query(..., description="Termo parcial para sugestões"),
    limit: int = Query(5, ge=1, le=20, description="Número máximo de sugestões")
):
    """
    Obter sugestões de termos de busca populares
    """
    try:
        # TODO: Implementar lógica real de sugestões
        # Simulação de sugestões baseadas no termo
        sugestoes_mock = []
        
        if "educação" in q.lower():
            sugestoes_mock.extend([
                {"termo": "educação ambiental", "tipo": "proposicao", "count": 15},
                {"termo": "educação básica", "tipo": "proposicao", "count": 8},
                {"termo": "educação infantil", "tipo": "proposicao", "count": 5}
            ])
        
        if "saúde" in q.lower():
            sugestoes_mock.extend([
                {"termo": "saúde pública", "tipo": "proposicao", "count": 12},
                {"termo": "saúde mental", "tipo": "proposicao", "count": 7},
                {"termo": "hospital", "tipo": "proposicao", "count": 10}
            ])
        
        if "meio ambiente" in q.lower():
            sugestoes_mock.extend([
                {"termo": "reciclagem", "tipo": "proposicao", "count": 9},
                {"termo": "sustentabilidade", "tipo": "proposicao", "count": 6},
                {"termo": "energia limpa", "tipo": "proposicao", "count": 4}
            ])
        
        return {
            "data": sugestoes_mock[:limit],
            "meta": {
                "query": q,
                "total": len(sugestoes_mock),
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter sugestões: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
