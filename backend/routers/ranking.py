"""
Router para endpoints de rankings e IDP
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.ranking import IDPRankingResponse, EmendaRankingResponse, GastoRankingResponse, ProposicaoRankingResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/idp")
async def ranking_idp(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    partido: Optional[str] = Query(None, description="Filtrar por partido"),
    uf: Optional[str] = Query(None, description="Filtrar por estado")
):
    """
    Ranking de deputados por Índice de Desempenho Parlamentar (IDP)
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        ranking_mock = [
            {
                "deputado_id": 745,
                "nome": "Beto Faro",
                "sigla_partido": "PT",
                "sigla_uf": "AC",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/745.jpg",
                "idp": 85.5,
                "idp_ranking": 1,
                "idp_desempenho_legislativo": 90.0,
                "idp_relevancia_social": 85.0,
                "idp_responsabilidade_fiscal": 80.0,
                "total_proposicoes": 45,
                "proposicoes_relevantes": 20,
                "media_score_par": 75.5,
                "total_emendas": 30,
                "valor_total_emendas": 2500000.00,
                "total_gastos": 180000.00
            },
            {
                "deputado_id": 123,
                "nome": "Ana Silva",
                "sigla_partido": "PSDB",
                "sigla_uf": "SP",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/123.jpg",
                "idp": 78.2,
                "idp_ranking": 2,
                "idp_desempenho_legislativo": 85.0,
                "idp_relevancia_social": 75.0,
                "idp_responsabilidade_fiscal": 75.0,
                "total_proposicoes": 38,
                "proposicoes_relevantes": 15,
                "media_score_par": 70.0,
                "total_emendas": 25,
                "valor_total_emendas": 2000000.00,
                "total_gastos": 160000.00
            }
        ]
        
        return {
            "data": ranking_mock,
            "meta": {
                "total": len(ranking_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/ranking/idp?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter ranking IDP: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/emendas")
async def ranking_emendas(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano")
):
    """
    Ranking de deputados por valor total de emendas
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        ranking_mock = [
            {
                "deputado_id": 745,
                "nome": "Beto Faro",
                "sigla_partido": "PT",
                "sigla_uf": "AC",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/745.jpg",
                "total_emendas": 30,
                "valor_total_emendas": 2500000.00,
                "ranking": 1,
                "media_valor_emenda": 83333.33
            }
        ]
        
        return {
            "data": ranking_mock,
            "meta": {
                "total": len(ranking_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/ranking/emendas?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter ranking de emendas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/gastos")
async def ranking_gastos(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano")
):
    """
    Ranking de deputados por total de gastos parlamentares
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        ranking_mock = [
            {
                "deputado_id": 123,
                "nome": "Ana Silva",
                "sigla_partido": "PSDB",
                "sigla_uf": "SP",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/123.jpg",
                "total_gastos": 250000.00,
                "ranking": 1,
                "media_mensal": 20833.33
            }
        ]
        
        return {
            "data": ranking_mock,
            "meta": {
                "total": len(ranking_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/ranking/gastos?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter ranking de gastos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/proposicoes")
async def ranking_proposicoes(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano")
):
    """
    Ranking de deputados por número de proposições
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        ranking_mock = [
            {
                "deputado_id": 745,
                "nome": "Beto Faro",
                "sigla_partido": "PT",
                "sigla_uf": "AC",
                "url_foto": "https://www.camara.leg.br/internet/deputado/bandep/745.jpg",
                "total_proposicoes": 45,
                "proposicoes_relevantes": 20,
                "ranking": 1,
                "media_score_par": 75.5
            }
        ]
        
        return {
            "data": ranking_mock,
            "meta": {
                "total": len(ranking_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/ranking/proposicoes?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter ranking de proposições: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
