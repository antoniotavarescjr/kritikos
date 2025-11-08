"""
Schemas Pydantic para Rankings e IDP
Validação e serialização de dados de rankings e Índice de Desempenho Parlamentar
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing_extensions import Annotated


# Helper type for decimal fields with 2 decimal places
Decimal2 = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


class RankingBase(BaseModel):
    """Schema base para dados de ranking"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    nome_deputado: str = Field(..., description="Nome do deputado", min_length=3, max_length=255)
    partido_sigla: Optional[str] = Field(None, description="Sigla do partido", max_length=20)
    uf: Optional[str] = Field(None, description="UF do deputado", pattern=r'^[A-Z]{2}$')
    foto_url: Optional[str] = Field(None, description="URL da foto", max_length=500)


class IDPRankingResponse(RankingBase):
    """Schema para resposta de ranking por IDP"""
    score_final: float = Field(..., description="IDP final (0-100)", ge=0, le=100)
    desempenho_legislativo: Optional[float] = Field(None, description="Score desempenho legislativo", ge=0, le=100)
    relevancia_social: Optional[float] = Field(None, description="Score relevância social", ge=0, le=100)
    responsabilidade_fiscal: Optional[float] = Field(None, description="Score responsabilidade fiscal", ge=0, le=100)
    etica_legalidade: Optional[float] = Field(None, description="Score ética e legalidade", ge=0, le=100)
    posicao_ranking: int = Field(..., description="Posição no ranking", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil: float = Field(..., description="Percentil no ranking", ge=0, le=100)
    data_calculo: Optional[datetime] = Field(None, description="Data do cálculo")
    total_proposicoes: int = Field(0, description="Total de proposições", ge=0)
    props_analisadas: int = Field(0, description="Proposições analisadas", ge=0)
    props_relevantes: int = Field(0, description="Proposições relevantes", ge=0)
    props_triviais: int = Field(0, description="Proposições triviais", ge=0)
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "partido_sigla": "PT",
                "uf": "SP",
                "foto_url": "https://www.camara.leg.br/internet/deputado/bandep/745.jpg",
                "score_final": 75.5,
                "desempenho_legislativo": 80.0,
                "relevancia_social": 70.0,
                "responsabilidade_fiscal": 75.0,
                "etica_legalidade": None,
                "posicao_ranking": 42,
                "total_deputados": 513,
                "percentil": 91.8,
                "data_calculo": "2025-01-07T10:00:00Z",
                "total_proposicoes": 25,
                "props_analisadas": 20,
                "props_relevantes": 15,
                "props_triviais": 5
            }
        }
    }


class EmendaRankingResponse(RankingBase):
    """Schema para resposta de ranking por emendas"""
    quantidade_emendas: int = Field(..., description="Quantidade de emendas", ge=0)
    valor_total_emendas: Decimal2 = Field(..., description="Valor total das emendas", ge=0)
    valor_medio_emenda: Decimal2 = Field(..., description="Valor médio das emendas", ge=0)
    valor_total_executado: Decimal2 = Field(..., description="Valor total executado", ge=0)
    percentual_execucao_medio: float = Field(..., description="Percentual de execução médio", ge=0, le=100)
    posicao_ranking_quantidade: int = Field(..., description="Posição no ranking por quantidade", gt=0)
    posicao_ranking_valor: int = Field(..., description="Posição no ranking por valor", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil_quantidade: float = Field(..., description="Percentil no ranking por quantidade", ge=0, le=100)
    percentil_valor: float = Field(..., description="Percentil no ranking por valor", ge=0, le=100)
    quantidade_municipios_beneficiados: int = Field(0, description="Municípios beneficiados", ge=0)
    quantidade_ufs_beneficiadas: int = Field(0, description="UFs beneficiadas", ge=0)
    ano_referencia: int = Field(..., description="Ano de referência", ge=2020, le=2030)
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "partido_sigla": "PT",
                "uf": "SP",
                "quantidade_emendas": 25,
                "valor_total_emendas": 10000000.00,
                "valor_medio_emenda": 400000.00,
                "valor_total_executado": 6000000.00,
                "percentual_execucao_medio": 60.0,
                "posicao_ranking_quantidade": 50,
                "posicao_ranking_valor": 75,
                "total_deputados": 513,
                "percentil_quantidade": 90.2,
                "percentil_valor": 85.4,
                "quantidade_municipios_beneficiados": 10,
                "quantidade_ufs_beneficiadas": 3,
                "ano_referencia": 2025
            }
        }
    }


class GastoRankingResponse(RankingBase):
    """Schema para resposta de ranking por gastos"""
    total_gastos: Decimal2 = Field(..., description="Total de gastos", ge=0)
    media_mensal: Decimal2 = Field(..., description="Média mensal de gastos", ge=0)
    total_despesas: int = Field(..., description="Total de despesas registradas", ge=0)
    maior_gasto_mensal: Optional[Decimal2] = Field(None, description="Maior gasto mensal", ge=0)
    menor_gasto_mensal: Optional[Decimal2] = Field(None, description="Menor gasto mensal", ge=0)
    posicao_ranking: int = Field(..., description="Posição no ranking", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil: float = Field(..., description="Percentil no ranking", ge=0, le=100)
    periodo_analise: str = Field(..., description="Período analisado", max_length=50)
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "partido_sigla": "PT",
                "uf": "SP",
                "total_gastos": 300000.00,
                "media_mensal": 25000.00,
                "total_despesas": 180,
                "maior_gasto_mensal": 35000.00,
                "menor_gasto_mensal": 18000.00,
                "posicao_ranking": 150,
                "total_deputados": 513,
                "percentil": 70.8,
                "periodo_analise": "2025"
            }
        }
    }


class ProposicaoRankingResponse(RankingBase):
    """Schema para resposta de ranking por proposições"""
    total_proposicoes: int = Field(..., description="Total de proposições", ge=0)
    proposicoes_analisadas: int = Field(..., description="Proposições analisadas", ge=0)
    proposicoes_relevantes: int = Field(..., description="Proposições relevantes", ge=0)
    proposicoes_triviais: int = Field(..., description="Proposições triviais", ge=0)
    taxa_analise: float = Field(..., description="Taxa de análise (%)", ge=0, le=100)
    taxa_relevancia: float = Field(..., description="Taxa de relevância (%)", ge=0, le=100)
    par_medio: Optional[float] = Field(None, description="Score PAR médio", ge=0, le=100)
    posicao_ranking_quantidade: int = Field(..., description="Posição no ranking por quantidade", gt=0)
    posicao_ranking_qualidade: int = Field(..., description="Posição no ranking por qualidade", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil_quantidade: float = Field(..., description="Percentil no ranking por quantidade", ge=0, le=100)
    percentil_qualidade: float = Field(..., description="Percentil no ranking por qualidade", ge=0, le=100)
    periodo_analise: str = Field(..., description="Período analisado", max_length=50)
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "partido_sigla": "PT",
                "uf": "SP",
                "total_proposicoes": 25,
                "proposicoes_analisadas": 20,
                "proposicoes_relevantes": 15,
                "proposicoes_triviais": 5,
                "taxa_analise": 80.0,
                "taxa_relevancia": 75.0,
                "par_medio": 72.5,
                "posicao_ranking_quantidade": 100,
                "posicao_ranking_qualidade": 50,
                "total_deputados": 513,
                "percentil_quantidade": 80.5,
                "percentil_qualidade": 90.2,
                "periodo_analise": "2023-2025"
            }
        }
    }


class RankingList(BaseModel):
    """Schema para lista de rankings (paginada)"""
    rankings: List[Dict[str, Any]]
    total: int = Field(..., description="Total de registros", ge=0)
    page: int = Field(..., description="Página atual", ge=1)
    per_page: int = Field(..., description="Registros por página", ge=1, le=100)
    total_pages: int = Field(..., description="Total de páginas", ge=1)
    tipo_ranking: str = Field(..., description="Tipo do ranking", max_length=50)
    periodo: str = Field(..., description="Período do ranking", max_length=50)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "rankings": [
                    {
                        "posicao": 1,
                        "deputado_id": 745,
                        "nome_deputado": "João da Silva",
                        "partido_sigla": "PT",
                        "uf": "SP",
                        "score_final": 85.5,
                        "percentil": 98.5
                    }
                ],
                "total": 513,
                "page": 1,
                "per_page": 20,
                "total_pages": 26,
                "tipo_ranking": "IDP",
                "periodo": "2025"
            }
        }
    }


class RankingSearchParams(BaseModel):
    """Schema para parâmetros de busca de rankings"""
    tipo_ranking: str = Field(..., description="Tipo do ranking (idp, emendas, gastos, proposicoes)", pattern=r'^(idp|emendas|gastos|proposicoes)$')
    estado: Optional[str] = Field(None, description="UF para filtro", pattern=r'^[A-Z]{2}$')
    partido: Optional[str] = Field(None, description="Partido para filtro", min_length=2, max_length=20)
    min_score: Optional[float] = Field(None, description="Score mínimo", ge=0)
    max_score: Optional[float] = Field(None, description="Score máximo", le=100)
    ano: Optional[int] = Field(None, description="Ano para rankings anuais", ge=2020, le=2030)
    page: int = Field(1, description="Página", ge=1)
    per_page: int = Field(20, description="Registros por página", ge=1, le=100)
    sort_by: Optional[str] = Field("posicao_ranking", description="Campo de ordenação")
    sort_order: Optional[str] = Field("asc", description="Ordem (asc/desc)", pattern=r'^(asc|desc)$')
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "tipo_ranking": "idp",
                "estado": "SP",
                "partido": "PT",
                "min_score": 70.0,
                "max_score": 90.0,
                "ano": 2025,
                "page": 1,
                "per_page": 20,
                "sort_by": "score_final",
                "sort_order": "desc"
            }
        }
    }


class RankingEstatisticas(BaseModel):
    """Schema para estatísticas gerais de rankings"""
    tipo_ranking: str = Field(..., description="Tipo do ranking", max_length=50)
    periodo: str = Field(..., description="Período analisado", max_length=50)
    total_deputados: int = Field(..., description="Total de deputados analisados", gt=0)
    media_score: float = Field(..., description="Média do score", ge=0)
    mediana_score: float = Field(..., description="Mediana do score", ge=0)
    desvio_padrao: float = Field(..., description="Desvio padrão", ge=0)
    min_score: float = Field(..., description="Score mínimo", ge=0)
    max_score: float = Field(..., description="Score máximo", ge=0)
    quartil_25: float = Field(..., description="Primeiro quartil", ge=0)
    quartil_75: float = Field(..., description="Terceiro quartil", ge=0)
    distribuicao_por_estado: Dict[str, int] = Field(..., description="Distribuição por estado")
    distribuicao_por_partido: Dict[str, int] = Field(..., description="Distribuição por partido")
    top_10: List[Dict[str, Any]] = Field(..., description="Top 10 do ranking")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "tipo_ranking": "IDP",
                "periodo": "2025",
                "total_deputados": 513,
                "media_score": 65.5,
                "mediana_score": 68.0,
                "desvio_padrao": 15.2,
                "min_score": 25.0,
                "max_score": 95.0,
                "quartil_25": 55.0,
                "quartil_75": 78.0,
                "distribuicao_por_estado": {
                    "SP": 80,
                    "RJ": 60,
                    "MG": 50
                },
                "distribuicao_por_partido": {
                    "PT": 90,
                    "PL": 85,
                    "PSDB": 70
                },
                "top_10": [
                    {
                        "posicao": 1,
                        "deputado_id": 745,
                        "nome_deputado": "João da Silva",
                        "score_final": 95.0
                    }
                ]
            }
        }
    }


class IDPHistorico(BaseModel):
    """Schema para histórico de IDP de um deputado"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    data_calculo: datetime = Field(..., description="Data do cálculo")
    score_final: float = Field(..., description="IDP final", ge=0, le=100)
    desempenho_legislativo: Optional[float] = Field(None, description="Score desempenho legislativo", ge=0, le=100)
    relevancia_social: Optional[float] = Field(None, description="Score relevância social", ge=0, le=100)
    responsabilidade_fiscal: Optional[float] = Field(None, description="Score responsabilidade fiscal", ge=0, le=100)
    etica_legalidade: Optional[float] = Field(None, description="Score ética e legalidade", ge=0, le=100)
    posicao_ranking: Optional[int] = Field(None, description="Posição no ranking", gt=0)
    total_deputados: Optional[int] = Field(None, description="Total de deputados no ranking", gt=0)
    versao_metodologia: Optional[str] = Field(None, description="Versão da metodologia", max_length=20)
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "data_calculo": "2025-01-07T10:00:00Z",
                "score_final": 75.5,
                "desempenho_legislativo": 80.0,
                "relevancia_social": 70.0,
                "responsabilidade_fiscal": 75.0,
                "etica_legalidade": None,
                "posicao_ranking": 42,
                "total_deputados": 513,
                "versao_metodologia": "1.0"
            }
        }
    }


class ComparativoDeputados(BaseModel):
    """Schema para comparativo entre deputados"""
    deputados: List[Dict[str, Any]]
    metricas_comparadas: List[str] = Field(..., description="Métricas comparadas")
    periodo: str = Field(..., description="Período da comparação", max_length=50)
    data_comparacao: datetime = Field(..., description="Data da comparação")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputados": [
                    {
                        "deputado_id": 745,
                        "nome_deputado": "João da Silva",
                        "partido_sigla": "PT",
                        "uf": "SP",
                        "idp_score": 75.5,
                        "posicao_idp": 42,
                        "total_emendas": 25,
                        "posicao_emendas": 50,
                        "total_gastos": 300000.00,
                        "posicao_gastos": 150
                    }
                ],
                "metricas_comparadas": ["idp_score", "total_emendas", "total_gastos"],
                "periodo": "2025",
                "data_comparacao": "2025-01-07T15:00:00Z"
            }
        }
    }
