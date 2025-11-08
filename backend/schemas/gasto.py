"""
Schemas Pydantic para Gastos Parlamentares
Validação e serialização de dados de gastos dos deputados
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing_extensions import Annotated


# Helper type for decimal fields with 2 decimal places
Decimal2 = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


class GastoBase(BaseModel):
    """Schema base para dados de gasto parlamentar"""
    ano: int = Field(..., description="Ano do gasto", ge=2020, le=2030)
    mes: int = Field(..., description="Mês do gasto", ge=1, le=12)
    tipo_despesa: str = Field(..., description="Tipo de despesa", min_length=3, max_length=255)
    descricao: Optional[str] = Field(None, description="Descrição detalhada", max_length=1000)
    fornecedor_nome: Optional[str] = Field(None, description="Nome do fornecedor", max_length=255)
    fornecedor_cnpj: Optional[str] = Field(None, description="CNPJ do fornecedor", pattern=r'^\d{14}$')
    valor_documento: Decimal2 = Field(..., description="Valor do documento", gt=0)
    valor_glosa: Decimal2 = Field(0, description="Valor da glosa", ge=0)
    valor_liquido: Decimal2 = Field(..., description="Valor líquido", gt=0)
    data_documento: Optional[date] = Field(None, description="Data do documento")
    numero_documento: Optional[str] = Field(None, description="Número do documento", max_length=255)
    numero_ressarcimento: Optional[str] = Field(None, description="Número do ressarcimento", max_length=255)
    parcela: Optional[int] = Field(None, description="Número da parcela", ge=1)


class GastoCreate(GastoBase):
    """Schema para criação de gasto"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)


class GastoUpdate(BaseModel):
    """Schema para atualização de gasto"""
    descricao: Optional[str] = Field(None, description="Descrição detalhada", max_length=1000)
    fornecedor_nome: Optional[str] = Field(None, description="Nome do fornecedor", max_length=255)
    fornecedor_cnpj: Optional[str] = Field(None, description="CNPJ do fornecedor", pattern=r'^\d{14}$')
    valor_documento: Optional[Decimal2] = Field(None, description="Valor do documento", gt=0)
    valor_glosa: Optional[Decimal2] = Field(None, description="Valor da glosa", ge=0)
    valor_liquido: Optional[Decimal2] = Field(None, description="Valor líquido", gt=0)
    data_documento: Optional[date] = Field(None, description="Data do documento")
    numero_documento: Optional[str] = Field(None, description="Número do documento", max_length=255)
    numero_ressarcimento: Optional[str] = Field(None, description="Número do ressarcimento", max_length=255)
    parcela: Optional[int] = Field(None, description="Número da parcela", ge=1)


class GastoResponse(GastoBase):
    """Schema para resposta de dados de gasto"""
    id: int = Field(..., description="ID único do gasto", gt=0)
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data de atualização")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 12345,
                "deputado_id": 745,
                "ano": 2025,
                "mes": 1,
                "tipo_despesa": "Passagens Aéreas",
                "descricao": "Passagem aérea São Paulo - Brasília",
                "fornecedor_nome": "TAM Linhas Aéreas S.A.",
                "fornecedor_cnpj": "02074983000160",
                "valor_documento": 1500.00,
                "valor_glosa": 0.00,
                "valor_liquido": 1500.00,
                "data_documento": "2025-01-05",
                "numero_documento": "123456",
                "numero_ressarcimento": None,
                "parcela": 1,
                "created_at": "2025-01-07T15:00:00Z",
                "updated_at": "2025-01-07T15:00:00Z"
            }
        }
    }


class GastoResumoMensal(BaseModel):
    """Schema para resumo mensal de gastos"""
    ano: int = Field(..., description="Ano", ge=2020, le=2030)
    mes: int = Field(..., description="Mês", ge=1, le=12)
    total_gastos: Decimal2 = Field(..., description="Total de gastos no mês", ge=0)
    quantidade_despesas: int = Field(..., description="Quantidade de despesas", ge=0)
    valor_medio_despesa: Decimal2 = Field(..., description="Valor médio das despesas", ge=0)
    maior_despesa: Optional[Decimal2] = Field(None, description="Maior despesa do mês", ge=0)
    menor_despesa: Optional[Decimal2] = Field(None, description="Menor despesa do mês", ge=0)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "ano": 2025,
                "mes": 1,
                "total_gastos": 25000.00,
                "quantidade_despesas": 15,
                "valor_medio_despesa": 1666.67,
                "maior_despesa": 5000.00,
                "menor_despesa": 150.00
            }
        }
    }


class GastoPorTipo(BaseModel):
    """Schema para gastos agrupados por tipo"""
    tipo_despesa: str = Field(..., description="Tipo de despesa")
    total_gastos: Decimal2 = Field(..., description="Total gasto no tipo", ge=0)
    quantidade_despesas: int = Field(..., description="Quantidade de despesas do tipo", ge=0)
    percentual_total: float = Field(..., description="Percentual sobre o total geral", ge=0, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "tipo_despesa": "Passagens Aéreas",
                "total_gastos": 15000.00,
                "quantidade_despesas": 8,
                "percentual_total": 60.0
            }
        }
    }


class GastoEstatisticas(BaseModel):
    """Schema para estatísticas de gastos de um deputado"""
    periodo_analise: str = Field(..., description="Período analisado")
    total_geral: Decimal2 = Field(..., description="Total geral de gastos", ge=0)
    media_mensal: Decimal2 = Field(..., description="Média mensal de gastos", ge=0)
    maior_gasto_mensal: Optional[Decimal2] = Field(None, description="Maior gasto mensal", ge=0)
    menor_gasto_mensal: Optional[Decimal2] = Field(None, description="Menor gasto mensal", ge=0)
    total_despesas: int = Field(..., description="Total de despesas registradas", ge=0)
    tipos_despesa: List[GastoPorTipo] = Field(..., description="Gastos por tipo de despesa")
    gastos_mensais: List[GastoResumoMensal] = Field(..., description="Resumo mensal de gastos")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "periodo_analise": "2025",
                "total_geral": 300000.00,
                "media_mensal": 25000.00,
                "maior_gasto_mensal": 35000.00,
                "menor_gasto_mensal": 18000.00,
                "total_despesas": 180,
                "tipos_despesa": [
                    {
                        "tipo_despesa": "Passagens Aéreas",
                        "total_gastos": 150000.00,
                        "quantidade_despesas": 80,
                        "percentual_total": 50.0
                    },
                    {
                        "tipo_despesa": "Hospedagem",
                        "total_gastos": 90000.00,
                        "quantidade_despesas": 45,
                        "percentual_total": 30.0
                    }
                ],
                "gastos_mensais": [
                    {
                        "ano": 2025,
                        "mes": 1,
                        "total_gastos": 25000.00,
                        "quantidade_despesas": 15,
                        "valor_medio_despesa": 1666.67
                    }
                ]
            }
        }
    }


class GastoList(BaseModel):
    """Schema para lista de gastos (paginada)"""
    gastos: List[GastoResponse]
    total: int = Field(..., description="Total de registros", ge=0)
    page: int = Field(..., description="Página atual", ge=1)
    per_page: int = Field(..., description="Registros por página", ge=1, le=100)
    total_pages: int = Field(..., description="Total de páginas", ge=1)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "gastos": [
                    {
                        "id": 12345,
                        "deputado_id": 745,
                        "ano": 2025,
                        "mes": 1,
                        "tipo_despesa": "Passagens Aéreas",
                        "valor_liquido": 1500.00,
                        "data_documento": "2025-01-05"
                    }
                ],
                "total": 180,
                "page": 1,
                "per_page": 20,
                "total_pages": 9
            }
        }
    }


class GastoSearchParams(BaseModel):
    """Schema para parâmetros de busca de gastos"""
    deputado_id: Optional[int] = Field(None, description="ID do deputado", gt=0)
    ano: Optional[int] = Field(None, description="Ano do gasto", ge=2020, le=2030)
    mes: Optional[int] = Field(None, description="Mês do gasto", ge=1, le=12)
    tipo_despesa: Optional[str] = Field(None, description="Tipo de despesa", min_length=3)
    fornecedor_nome: Optional[str] = Field(None, description="Nome do fornecedor", min_length=3)
    valor_minimo: Optional[float] = Field(None, description="Valor mínimo", ge=0)
    valor_maximo: Optional[float] = Field(None, description="Valor máximo", gt=0)
    data_inicio: Optional[date] = Field(None, description="Data de início")
    data_fim: Optional[date] = Field(None, description="Data de fim")
    page: int = Field(1, description="Página", ge=1)
    per_page: int = Field(20, description="Registros por página", ge=1, le=100)
    sort_by: Optional[str] = Field("data_documento", description="Campo de ordenação")
    sort_order: Optional[str] = Field("desc", description="Ordem (asc/desc)", pattern=r'^(asc|desc)$')
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "ano": 2025,
                "mes": 1,
                "tipo_despesa": "Passagens",
                "valor_minimo": 1000.0,
                "valor_maximo": 5000.0,
                "data_inicio": "2025-01-01",
                "data_fim": "2025-01-31",
                "page": 1,
                "per_page": 20,
                "sort_by": "valor_liquido",
                "sort_order": "desc"
            }
        }
    }


class GastoComparativo(BaseModel):
    """Schema para comparativo de gastos entre deputados"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    nome_deputado: str = Field(..., description="Nome do deputado")
    total_gastos: Decimal2 = Field(..., description="Total de gastos", ge=0)
    media_mensal: Decimal2 = Field(..., description="Média mensal", ge=0)
    posicao_ranking: int = Field(..., description="Posição no ranking", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil: float = Field(..., description="Percentil no ranking", ge=0, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "total_gastos": 300000.00,
                "media_mensal": 25000.00,
                "posicao_ranking": 150,
                "total_deputados": 513,
                "percentil": 70.8
            }
        }
    }
