"""
Router para endpoints de emendas parlamentares
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.emenda import EmendaResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def listar_emendas(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    deputado_id: Optional[int] = Query(None, description="Filtrar por deputado"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de emenda"),
    localidade: Optional[str] = Query(None, description="Filtrar por localidade")
):
    """
    Listar emendas parlamentares com filtros e paginação
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        emendas_mock = [
            {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
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
                "self": f"/api/emendas?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar emendas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{emenda_id}")
async def obter_emenda(emenda_id: int):
    """
    Obter detalhes de uma emenda específica
    """
    try:
        # TODO: Implementar busca real no banco
        if emenda_id == 1:
            return {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
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
                "descricao": "Equipamentos para hospitais da rede pública",
                "justificativa": "Investimento na melhoria da infraestrutura hospitalar",
                "status": "Em execução",
                "data_aprovacao": "2025-01-10",
                "beneficiarios": [
                    {
                        "nome": "Hospital Regional de Rio Branco",
                        "cnpj": "12345678000123"
                    }
                ]
            }
        else:
            raise HTTPException(status_code=404, detail="Emenda não encontrada")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter emenda {emenda_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
