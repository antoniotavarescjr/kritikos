"""
Router para endpoints de proposições legislativas
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.proposicao import ProposicaoResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def listar_proposicoes(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (PL, PDC, etc)"),
    deputado_id: Optional[int] = Query(None, description="Filtrar por deputado"),
    tem_analise: Optional[bool] = Query(None, description="Filtrar se tem análise"),
    relevancia: Optional[str] = Query(None, description="Filtrar por relevância")
):
    """
    Listar proposições com filtros e paginação
    """
    try:
        # TODO: Implementar lógica real de busca no banco
        proposicoes_mock = [
            {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
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
                "self": f"/api/proposicoes?page={page}&per_page={per_page}",
                "next": None,
                "prev": None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar proposições: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{proposicao_id}")
async def obter_proposicao(proposicao_id: int):
    """
    Obter detalhes de uma proposição específica
    """
    try:
        # TODO: Implementar busca real no banco
        if proposicao_id == 1:
            return {
                "id": 1,
                "deputado_id": 745,
                "deputado_nome": "Beto Faro",
                "tipo": "PL",
                "numero": "1234/2025",
                "ano": 2025,
                "ementa": "Dispõe sobre políticas de educação ambiental nas escolas de ensino fundamental e médio",
                "tem_analise": True,
                "resumo": "Proposta que implementa programas de educação ambiental, incluindo reciclagem, conservação e sustentabilidade no currículo escolar. A medida visa formar cidadãos mais conscientes ambientalmente desde a educação básica.",
                "analise_detalhada": {
                    "impacto_social": "Alto impacto potencial na formação de cidadãos conscientes",
                    "viabilidade_tecnica": "Viável com baixo custo de implementação",
                    "alinhamento_politicas_publicas": "Alinhado com políticas nacionais de educação e meio ambiente",
                    "inovacao": "Abordagem inovadora integrando educação e sustentabilidade"
                },
                "score_par": 75.5,
                "relevancia": "alta",
                "data_apresentacao": "2025-01-05",
                "data_analise": "2025-01-07T15:00:00Z",
                "situacao": "Em tramitação",
                "regime_tramitacao": "Urgência",
                "apensadas": [],
                "temas": ["Educação", "Meio Ambiente", "Sustentabilidade"],
                "autores": [
                    {
                        "id": 745,
                        "nome": "Beto Faro",
                        "sigla_partido": "PT",
                        "sigla_uf": "AC"
                    }
                ]
            }
        else:
            raise HTTPException(status_code=404, detail="Proposição não encontrada")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter proposição {proposicao_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
