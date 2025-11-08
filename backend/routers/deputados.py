"""
Router para endpoints de deputados
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging

from src.models.database import get_db
from services.deputado_service import get_deputado_service
from schemas.deputado import DeputadoResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def listar_deputados(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    partido: Optional[str] = Query(None, description="Filtrar por partido"),
    uf: Optional[str] = Query(None, description="Filtrar por estado"),
    nome: Optional[str] = Query(None, description="Buscar por nome")
):
    """
    Listar todos os deputados com paginação e filtros
    """
    try:
        deputado_service = get_deputado_service()
        return deputado_service.listar_deputados(
            page=page,
            per_page=per_page,
            partido=partido,
            uf=uf,
            nome=nome
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar deputados: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{deputado_id}")
async def obter_deputado(deputado_id: int):
    """
    Obter dados completos de um deputado específico
    """
    try:
        deputado_service = get_deputado_service()
        result = deputado_service.obter_deputado(deputado_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Deputado não encontrado")
            
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter deputado {deputado_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{deputado_id}/gastos")
async def obter_gastos_deputado(
    deputado_id: int,
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    mes: Optional[int] = Query(None, description="Filtrar por mês"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Obter gastos parlamentares de um deputado
    """
    try:
        # TODO: Implementar busca real no banco
        gastos_mock = [
            {
                "id": 1,
                "deputado_id": deputado_id,
                "ano": 2025,
                "mes": 1,
                "tipo_despesa": "Passagens aéreas",
                "valor": 2500.00,
                "descricao": "Passagem Rio - Brasília",
                "data_documento": "2025-01-05",
                "fornecedor": "TAM Airlines"
            }
        ]
        
        return {
            "data": gastos_mock,
            "meta": {
                "total": len(gastos_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/deputados/{deputado_id}/gastos?page={page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter gastos do deputado {deputado_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{deputado_id}/emendas")
async def obter_emendas_deputado(
    deputado_id: int,
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Obter emendas parlamentares de um deputado
    """
    try:
        # TODO: Implementar busca real no banco
        emendas_mock = [
            {
                "id": 1,
                "deputado_id": deputado_id,
                "ano": 2025,
                "numero": "20250001",
                "tipo": "Individual",
                "valor_emenda": 100000.00,
                "valor_empenhado": 85000.00,
                "valor_liquidado": 70000.00,
                "valor_pago": 50000.00,
                "localidade": "Rio Branco - AC",
                "funcao": "Saúde",
                "subfuncao": "Atenção Básica",
                "descricao": "Equipamentos para hospitais",
                "status": "Em execução"
            }
        ]
        
        return {
            "data": emendas_mock,
            "meta": {
                "total": len(emendas_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/deputados/{deputado_id}/emendas?page={page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter emendas do deputado {deputado_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{deputado_id}/proposicoes")
async def obter_proposicoes_deputado(
    deputado_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Obter proposições de autoria de um deputado
    """
    try:
        # TODO: Implementar busca real no banco
        proposicoes_mock = [
            {
                "id": 1,
                "deputado_id": deputado_id,
                "tipo": "PL",
                "numero": "1234/2025",
                "ano": 2025,
                "ementa": "Dispõe sobre políticas de educação ambiental",
                "tem_analise": True,
                "resumo": "Proposta que implementa educação ambiental nas escolas",
                "score_par": 75.5,
                "relevancia": "alta",
                "data_apresentacao": "2025-01-05",
                "situacao": "Em tramitação"
            }
        ]
        
        return {
            "data": proposicoes_mock,
            "meta": {
                "total": len(proposicoes_mock),
                "page": page,
                "per_page": per_page,
                "total_pages": 1
            },
            "links": {
                "self": f"/api/deputados/{deputado_id}/proposicoes?page={page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter proposições do deputado {deputado_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
