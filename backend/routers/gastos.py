"""
Router para endpoints de gastos parlamentares
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.gasto import GastoResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def listar_gastos(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    mes: Optional[int] = Query(None, description="Filtrar por mês"),
    deputado_id: Optional[int] = Query(None, description="Filtrar por deputado"),
    tipo_despesa: Optional[str] = Query(None, description="Filtrar por tipo de despesa")
):
    """
    Listar gastos parlamentares com filtros e paginação
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        gastos_mock = [
            {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
                "ano": 2025,
                "mes": 1,
                "tipo_despesa": "Passagens aéreas",
                "valor": 2500.00,
                "descricao": "Passagem Rio - Brasília",
                "data_documento": "2025-01-05",
                "fornecedor": "TAM Airlines",
                "cnpj_fornecedor": "02000000000123"
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
                "self": f"/api/gastos?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar gastos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{gasto_id}")
async def obter_gasto(gasto_id: int):
    """
    Obter detalhes de um gasto específico
    """
    try:
        # TODO: Implementar busca real no banco
        if gasto_id == 1:
            return {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
                "ano": 2025,
                "mes": 1,
                "tipo_despesa": "Passagens aéreas",
                "valor": 2500.00,
                "descricao": "Passagem Rio - Brasília",
                "data_documento": "2025-01-05",
                "fornecedor": "TAM Airlines",
                "cnpj_fornecedor": "02000000000123",
                "numero_documento": "123456",
                "tipo_documento": "Nota Fiscal",
                "url_documento": "https://www.camara.leg.br/cota-parlamentar/documento/123456"
            }
        else:
            raise HTTPException(status_code=404, detail="Gasto não encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter gasto {gasto_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
