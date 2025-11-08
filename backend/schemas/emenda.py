"""
Schemas Pydantic para Emendas Parlamentares
Validação e serialização de dados de emendas dos deputados
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing_extensions import Annotated


# Helper type for decimal fields with 2 decimal places
Decimal2 = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


class EmendaBase(BaseModel):
    """Schema base para dados de emenda parlamentar"""
    api_camara_id: str = Field(..., description="ID da emenda na API da Câmara", max_length=50)
    tipo_emenda: str = Field(..., description="Tipo da emenda (EMD, EMP, etc)", max_length=50)
    numero: int = Field(..., description="Número da emenda", gt=0)
    ano: int = Field(..., description="Ano da emenda", ge=2020, le=2030)
    emenda: str = Field(..., description="Texto completo da emenda", min_length=10)
    local: Optional[str] = Field(None, description="Local (LOA, LDO, PPA)", max_length=100)
    natureza: Optional[str] = Field(None, description="Natureza (Individual, Bancada, Comissão)", max_length=100)
    tema: Optional[str] = Field(None, description="Tema da emenda", max_length=255)
    area_tematica: Optional[str] = Field(None, description="Área temática", max_length=100)
    valor_emenda: Optional[Decimal2] = Field(None, description="Valor da emenda", ge=0)
    valor_empenhado: Decimal2 = Field(0, description="Valor empenhado", ge=0)
    valor_liquidado: Decimal2 = Field(0, description="Valor liquidado", ge=0)
    valor_pago: Decimal2 = Field(0, description="Valor pago", ge=0)
    beneficiario_principal: Optional[str] = Field(None, description="Beneficiário principal", max_length=1000)
    beneficiarios_secundarios: Optional[str] = Field(None, description="Beneficiários secundários", max_length=2000)
    uf_beneficiario: Optional[str] = Field(None, description="UF do beneficiário", max_length=50)
    municipio_beneficiario: Optional[str] = Field(None, description="Município do beneficiário", max_length=255)
    cidade_destino: Optional[str] = Field(None, description="Cidade de destino", max_length=255)
    estado_destino: Optional[str] = Field(None, description="Estado de destino", max_length=50)
    situacao: Optional[str] = Field(None, description="Situação atual", max_length=100)
    data_apresentacao: Optional[date] = Field(None, description="Data de apresentação")
    data_aprovacao: Optional[date] = Field(None, description="Data de aprovação")
    data_publicacao: Optional[date] = Field(None, description="Data de publicação")
    autor: Optional[str] = Field(None, description="Nome do autor", max_length=255)
    partido_autor: Optional[str] = Field(None, description="Partido do autor", max_length=20)
    uf_autor: Optional[str] = Field(None, description="UF do autor", max_length=50)
    url_documento: Optional[str] = Field(None, description="URL do documento", max_length=500)
    gcs_url: Optional[str] = Field(None, description="URL no GCS", max_length=500)
    valor_resto_inscrito: Optional[Decimal2] = Field(None, description="Valor resto inscrito", ge=0)
    valor_resto_cancelado: Optional[Decimal2] = Field(None, description="Valor resto cancelado", ge=0)
    valor_resto_pago: Optional[Decimal2] = Field(None, description="Valor resto pago", ge=0)
    codigo_funcao_api: Optional[str] = Field(None, description="Código função API", max_length=20)
    codigo_subfuncao_api: Optional[str] = Field(None, description="Código subfunção API", max_length=20)
    documentos_url: Optional[str] = Field(None, description="URL dos documentos", max_length=2000)
    quantidade_documentos: int = Field(0, description="Quantidade de documentos", ge=0)


class EmendaCreate(EmendaBase):
    """Schema para criação de emenda"""
    deputado_id: Optional[int] = Field(None, description="ID do deputado autor", gt=0)


class EmendaUpdate(BaseModel):
    """Schema para atualização de emenda"""
    valor_empenhado: Optional[Decimal2] = Field(None, description="Valor empenhado", ge=0)
    valor_liquidado: Optional[Decimal2] = Field(None, description="Valor liquidado", ge=0)
    valor_pago: Optional[Decimal2] = Field(None, description="Valor pago", ge=0)
    situacao: Optional[str] = Field(None, description="Situação atual", max_length=100)
    data_aprovacao: Optional[date] = Field(None, description="Data de aprovação")
    data_publicacao: Optional[date] = Field(None, description="Data de publicação")
    url_documento: Optional[str] = Field(None, description="URL do documento", max_length=500)
    gcs_url: Optional[str] = Field(None, description="URL no GCS", max_length=500)
    valor_resto_inscrito: Optional[Decimal2] = Field(None, description="Valor resto inscrito", ge=0)
    valor_resto_cancelado: Optional[Decimal2] = Field(None, description="Valor resto cancelado", ge=0)
    valor_resto_pago: Optional[Decimal2] = Field(None, description="Valor resto pago", ge=0)
    documentos_url: Optional[str] = Field(None, description="URL dos documentos", max_length=2000)
    quantidade_documentos: Optional[int] = Field(None, description="Quantidade de documentos", ge=0)


class EmendaResponse(EmendaBase):
    """Schema para resposta de dados de emenda"""
    id: int = Field(..., description="ID único da emenda", gt=0)
    deputado_id: Optional[int] = Field(None, description="ID do deputado autor", gt=0)
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data de atualização")
    
    # Campos calculados
    percentual_execucao: Optional[float] = Field(None, description="Percentual de execução", ge=0, le=100)
    valor_executado: Optional[Decimal2] = Field(None, description="Valor executado", ge=0)
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 12345,
                "deputado_id": 745,
                "api_camara_id": "2025_12345",
                "tipo_emenda": "EMD",
                "numero": 123,
                "ano": 2025,
                "emenda": "Texto completo da emenda...",
                "local": "LOA 2025",
                "natureza": "Individual",
                "tema": "Saúde",
                "area_tematica": "Atenção Básica",
                "valor_emenda": 1000000.00,
                "valor_empenhado": 800000.00,
                "valor_liquidado": 600000.00,
                "valor_pago": 500000.00,
                "beneficiario_principal": "Prefeitura de São Paulo",
                "uf_beneficiario": "SP",
                "municipio_beneficiario": "São Paulo",
                "cidade_destino": "São Paulo",
                "estado_destino": "SP",
                "situacao": "Executando",
                "data_apresentacao": "2025-01-05",
                "data_aprovacao": "2025-01-10",
                "autor": "João da Silva",
                "partido_autor": "PT",
                "uf_autor": "SP",
                "percentual_execucao": 50.0,
                "valor_executado": 500000.00,
                "created_at": "2025-01-07T15:00:00Z",
                "updated_at": "2025-01-07T15:00:00Z"
            }
        }
    }


class EmendaResumoAnual(BaseModel):
    """Schema para resumo anual de emendas"""
    ano: int = Field(..., description="Ano", ge=2020, le=2030)
    quantidade_emendas: int = Field(..., description="Quantidade de emendas", ge=0)
    valor_total_emendas: Decimal2 = Field(..., description="Valor total das emendas", ge=0)
    valor_medio_emenda: Decimal2 = Field(..., description="Valor médio das emendas", ge=0)
    valor_total_executado: Decimal2 = Field(..., description="Valor total executado", ge=0)
    percentual_execucao_geral: float = Field(..., description="Percentual de execução geral", ge=0, le=100)
    quantidade_municipios_beneficiados: int = Field(..., description="Municípios beneficiados", ge=0)
    quantidade_ufs_beneficiadas: int = Field(..., description="UFs beneficiadas", ge=0)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "ano": 2025,
                "quantidade_emendas": 10,
                "valor_total_emendas": 5000000.00,
                "valor_medio_emenda": 500000.00,
                "valor_total_executado": 2500000.00,
                "percentual_execucao_geral": 50.0,
                "quantidade_municipios_beneficiados": 5,
                "quantidade_ufs_beneficiadas": 2
            }
        }
    }


class EmendaPorLocal(BaseModel):
    """Schema para emendas agrupadas por local"""
    local: str = Field(..., description="Local (LOA, LDO, PPA)")
    quantidade_emendas: int = Field(..., description="Quantidade de emendas", ge=0)
    valor_total: Decimal2 = Field(..., description="Valor total", ge=0)
    percentual_valor: float = Field(..., description="Percentual sobre o valor total", ge=0, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "local": "LOA 2025",
                "quantidade_emendas": 8,
                "valor_total": 4000000.00,
                "percentual_valor": 80.0
            }
        }
    }


class EmendaPorBeneficiario(BaseModel):
    """Schema para emendas agrupadas por beneficiário"""
    beneficiario: str = Field(..., description="Nome do beneficiário")
    municipio: str = Field(..., description="Município")
    uf: str = Field(..., description="UF")
    quantidade_emendas: int = Field(..., description="Quantidade de emendas", ge=0)
    valor_total: Decimal2 = Field(..., description="Valor total recebido", ge=0)
    valor_executado: Decimal2 = Field(..., description="Valor executado", ge=0)
    percentual_execucao: float = Field(..., description="Percentual de execução", ge=0, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "beneficiario": "Prefeitura de São Paulo",
                "municipio": "São Paulo",
                "uf": "SP",
                "quantidade_emendas": 3,
                "valor_total": 1500000.00,
                "valor_executado": 750000.00,
                "percentual_execucao": 50.0
            }
        }
    }


class EmendaEstatisticas(BaseModel):
    """Schema para estatísticas de emendas de um deputado"""
    periodo_analise: str = Field(..., description="Período analisado")
    total_emendas: int = Field(..., description="Total de emendas", ge=0)
    valor_total_emendas: Decimal2 = Field(..., description="Valor total das emendas", ge=0)
    valor_medio_emenda: Decimal2 = Field(..., description="Valor médio das emendas", ge=0)
    valor_total_executado: Decimal2 = Field(..., description="Valor total executado", ge=0)
    percentual_execucao_geral: float = Field(..., description="Percentual de execução geral", ge=0, le=100)
    quantidade_municipios_beneficiados: int = Field(..., description="Municípios beneficiados", ge=0)
    quantidade_ufs_beneficiadas: int = Field(..., description="UFs beneficiadas", ge=0)
    emendas_por_local: List[EmendaPorLocal] = Field(..., description="Emendas por local")
    principais_beneficiarios: List[EmendaPorBeneficiario] = Field(..., description="Principais beneficiários")
    resumo_anual: List[EmendaResumoAnual] = Field(..., description="Resumo anual")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "periodo_analise": "2023-2025",
                "total_emendas": 25,
                "valor_total_emendas": 10000000.00,
                "valor_medio_emenda": 400000.00,
                "valor_total_executado": 6000000.00,
                "percentual_execucao_geral": 60.0,
                "quantidade_municipios_beneficiados": 10,
                "quantidade_ufs_beneficiadas": 3,
                "emendas_por_local": [
                    {
                        "local": "LOA 2025",
                        "quantidade_emendas": 15,
                        "valor_total": 7500000.00,
                        "percentual_valor": 75.0
                    }
                ],
                "principais_beneficiarios": [
                    {
                        "beneficiario": "Prefeitura de São Paulo",
                        "municipio": "São Paulo",
                        "uf": "SP",
                        "quantidade_emendas": 5,
                        "valor_total": 3000000.00,
                        "valor_executado": 1800000.00,
                        "percentual_execucao": 60.0
                    }
                ],
                "resumo_anual": [
                    {
                        "ano": 2025,
                        "quantidade_emendas": 10,
                        "valor_total_emendas": 5000000.00,
                        "valor_medio_emenda": 500000.00,
                        "valor_total_executado": 2500000.00,
                        "percentual_execucao_geral": 50.0,
                        "quantidade_municipios_beneficiados": 5,
                        "quantidade_ufs_beneficiadas": 2
                    }
                ]
            }
        }
    }


class EmendaList(BaseModel):
    """Schema para lista de emendas (paginada)"""
    emendas: List[EmendaResponse]
    total: int = Field(..., description="Total de registros", ge=0)
    page: int = Field(..., description="Página atual", ge=1)
    per_page: int = Field(..., description="Registros por página", ge=1, le=100)
    total_pages: int = Field(..., description="Total de páginas", ge=1)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "emendas": [
                    {
                        "id": 12345,
                        "deputado_id": 745,
                        "api_camara_id": "2025_12345",
                        "tipo_emenda": "EMD",
                        "numero": 123,
                        "ano": 2025,
                        "valor_emenda": 1000000.00,
                        "valor_pago": 500000.00,
                        "beneficiario_principal": "Prefeitura de São Paulo",
                        "situacao": "Executando",
                        "percentual_execucao": 50.0
                    }
                ],
                "total": 25,
                "page": 1,
                "per_page": 20,
                "total_pages": 2
            }
        }
    }


class EmendaSearchParams(BaseModel):
    """Schema para parâmetros de busca de emendas"""
    deputado_id: Optional[int] = Field(None, description="ID do deputado", gt=0)
    ano: Optional[int] = Field(None, description="Ano da emenda", ge=2020, le=2030)
    tipo_emenda: Optional[str] = Field(None, description="Tipo da emenda", max_length=50)
    local: Optional[str] = Field(None, description="Local (LOA, LDO, PPA)", max_length=100)
    natureza: Optional[str] = Field(None, description="Natureza", max_length=100)
    tema: Optional[str] = Field(None, description="Tema", min_length=3)
    uf_beneficiario: Optional[str] = Field(None, description="UF do beneficiário", pattern=r'^[A-Z]{2}$')
    municipio_beneficiario: Optional[str] = Field(None, description="Município do beneficiário", min_length=3)
    situacao: Optional[str] = Field(None, description="Situação", max_length=100)
    valor_minimo: Optional[float] = Field(None, description="Valor mínimo", ge=0)
    valor_maximo: Optional[float] = Field(None, description="Valor máximo", gt=0)
    data_inicio: Optional[date] = Field(None, description="Data de início")
    data_fim: Optional[date] = Field(None, description="Data de fim")
    page: int = Field(1, description="Página", ge=1)
    per_page: int = Field(20, description="Registros por página", ge=1, le=100)
    sort_by: Optional[str] = Field("data_apresentacao", description="Campo de ordenação")
    sort_order: Optional[str] = Field("desc", description="Ordem (asc/desc)", pattern=r'^(asc|desc)$')
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "ano": 2025,
                "tipo_emenda": "EMD",
                "local": "LOA",
                "uf_beneficiario": "SP",
                "municipio_beneficiario": "São Paulo",
                "situacao": "Executando",
                "valor_minimo": 100000.0,
                "valor_maximo": 5000000.0,
                "data_inicio": "2025-01-01",
                "data_fim": "2025-12-31",
                "page": 1,
                "per_page": 20,
                "sort_by": "valor_emenda",
                "sort_order": "desc"
            }
        }
    }


class EmendaComparativo(BaseModel):
    """Schema para comparativo de emendas entre deputados"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    nome_deputado: str = Field(..., description="Nome do deputado")
    total_emendas: int = Field(..., description="Total de emendas", ge=0)
    valor_total_emendas: Decimal2 = Field(..., description="Valor total das emendas", ge=0)
    valor_medio_emenda: Decimal2 = Field(..., description="Valor médio das emendas", ge=0)
    percentual_execucao_geral: float = Field(..., description="Percentual de execução geral", ge=0, le=100)
    posicao_ranking_quantidade: int = Field(..., description="Posição no ranking por quantidade", gt=0)
    posicao_ranking_valor: int = Field(..., description="Posição no ranking por valor", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil_quantidade: float = Field(..., description="Percentil no ranking por quantidade", ge=0, le=100)
    percentil_valor: float = Field(..., description="Percentil no ranking por valor", ge=0, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "total_emendas": 25,
                "valor_total_emendas": 10000000.00,
                "valor_medio_emenda": 400000.00,
                "percentual_execucao_geral": 60.0,
                "posicao_ranking_quantidade": 50,
                "posicao_ranking_valor": 75,
                "total_deputados": 513,
                "percentil_quantidade": 90.2,
                "percentil_valor": 85.4
            }
        }
    }
