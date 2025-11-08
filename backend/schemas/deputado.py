"""
Schemas Pydantic para Deputados
Validação e serialização de dados de deputados parlamentares
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field


class DeputadoBase(BaseModel):
    """Schema base para dados de deputado"""
    nome: str = Field(..., description="Nome completo do deputado", min_length=3, max_length=255)
    nome_civil: Optional[str] = Field(None, description="Nome civil do deputado", max_length=255)
    cpf: Optional[str] = Field(None, description="CPF do deputado", pattern=r'^\d{11}$')
    sexo: Optional[str] = Field(None, description="Sexo (M/F)", pattern=r'^[MF]$')
    data_nascimento: Optional[date] = Field(None, description="Data de nascimento")
    municipio_nascimento: Optional[str] = Field(None, description="Município de nascimento", max_length=255)
    uf_nascimento: Optional[str] = Field(None, description="UF de nascimento", pattern=r'^[A-Z]{2}$')
    escolaridade: Optional[str] = Field(None, description="Escolaridade", max_length=100)
    profissao: Optional[str] = Field(None, description="Profissão", max_length=255)
    email: Optional[str] = Field(None, description="Email de contato", pattern=r'^[^@]+@[^@]+\.[^@]+$')
    telefone: Optional[str] = Field(None, description="Telefone", max_length=20)
    foto_url: Optional[str] = Field(None, description="URL da foto", max_length=500)
    situacao: Optional[str] = Field("Exercício", description="Situação atual", max_length=50)
    condicao: Optional[str] = Field(None, description="Condição", max_length=100)


class DeputadoCreate(DeputadoBase):
    """Schema para criação de deputado"""
    api_camara_id: int = Field(..., description="ID na API da Câmara", gt=0)
    codigo_autor_emenda: Optional[int] = Field(None, description="Código de autor de emenda", gt=0)


class DeputadoUpdate(BaseModel):
    """Schema para atualização de deputado"""
    nome: Optional[str] = Field(None, description="Nome completo do deputado", min_length=3, max_length=255)
    email: Optional[str] = Field(None, description="Email de contato", pattern=r'^[^@]+@[^@]+\.[^@]+$')
    telefone: Optional[str] = Field(None, description="Telefone", max_length=20)
    foto_url: Optional[str] = Field(None, description="URL da foto", max_length=500)
    situacao: Optional[str] = Field(None, description="Situação atual", max_length=50)
    condicao: Optional[str] = Field(None, description="Condição", max_length=100)


class MandatoInfo(BaseModel):
    """Schema para informações de mandato"""
    legislatura_id: int
    partido: str
    partido_sigla: str
    estado: str
    estado_sigla: str
    data_inicio: date
    data_fim: Optional[date]
    votos_recebidos: Optional[int]
    posicao_lista: Optional[int]


class IDPInfo(BaseModel):
    """Schema para informações do IDP"""
    score_final: float = Field(..., description="IDP final (0-100)", ge=0, le=100)
    desempenho_legislativo: Optional[float] = Field(None, description="Score desempenho legislativo", ge=0, le=100)
    relevancia_social: Optional[float] = Field(None, description="Score relevância social", ge=0, le=100)
    responsabilidade_fiscal: Optional[float] = Field(None, description="Score responsabilidade fiscal", ge=0, le=100)
    etica_legalidade: Optional[float] = Field(None, description="Score ética e legalidade", ge=0, le=100)
    posicao_ranking: Optional[int] = Field(None, description="Posição no ranking geral", gt=0)
    total_proposicoes: int = Field(0, description="Total de proposições", ge=0)
    props_analisadas: int = Field(0, description="Proposições analisadas", ge=0)
    props_relevantes: int = Field(0, description="Proposições relevantes", ge=0)
    props_triviais: int = Field(0, description="Proposições triviais", ge=0)
    data_calculo: Optional[datetime] = Field(None, description="Data do cálculo")


class EstatisticasDeputado(BaseModel):
    """Schema para estatísticas do deputado"""
    total_proposicoes: int = Field(0, description="Total de proposições autoria", ge=0)
    total_emendas: int = Field(0, description="Total de emendas propostas", ge=0)
    valor_total_emendas: float = Field(0.0, description="Valor total das emendas", ge=0)
    total_gastos: float = Field(0.0, description="Total de gastos parlamentares", ge=0)
    media_gastos_mensal: float = Field(0.0, description="Média de gastos mensais", ge=0)
    quantidade_municipios_beneficiados: int = Field(0, description="Municípios beneficiados por emendas", ge=0)
    quantidade_ufs_beneficiadas: int = Field(0, description="UFs beneficiadas por emendas", ge=0)


class DeputadoResponse(DeputadoBase):
    """Schema para resposta de dados de deputado"""
    id: int = Field(..., description="ID único do deputado", gt=0)
    api_camara_id: int = Field(..., description="ID na API da Câmara", gt=0)
    codigo_autor_emenda: Optional[int] = Field(None, description="Código de autor de emenda", gt=0)
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data de atualização")
    
    # Campos opcionais que podem ser incluídos
    mandato_atual: Optional[MandatoInfo] = Field(None, description="Informações do mandato atual")
    idp_info: Optional[IDPInfo] = Field(None, description="Informações do IDP")
    estatisticas: Optional[EstatisticasDeputado] = Field(None, description="Estatísticas gerais")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 745,
                "api_camara_id": 204534,
                "nome": "João da Silva",
                "nome_civil": "João Silva Santos",
                "cpf": "12345678901",
                "sexo": "M",
                "data_nascimento": "1980-05-15",
                "municipio_nascimento": "São Paulo",
                "uf_nascimento": "SP",
                "escolaridade": "Superior Completo",
                "profissao": "Advogado",
                "email": "joao.silva@camara.leg.br",
                "telefone": "(61) 3215-5454",
                "foto_url": "https://www.camara.leg.br/internet/deputado/bandep/745.jpg",
                "situacao": "Exercício",
                "condicao": "Titular",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2025-01-07T15:00:00Z",
                "mandato_atual": {
                    "legislatura_id": 57,
                    "partido": "Partido dos Trabalhadores",
                    "partido_sigla": "PT",
                    "estado": "São Paulo",
                    "estado_sigla": "SP",
                    "data_inicio": "2023-02-01",
                    "data_fim": "2027-01-31",
                    "votos_recebidos": 150000,
                    "posicao_lista": 1
                },
                "idp_info": {
                    "score_final": 75.5,
                    "desempenho_legislativo": 80.0,
                    "relevancia_social": 70.0,
                    "responsabilidade_fiscal": 75.0,
                    "etica_legalidade": None,
                    "posicao_ranking": 42,
                    "total_proposicoes": 25,
                    "props_analisadas": 20,
                    "props_relevantes": 15,
                    "props_triviais": 5,
                    "data_calculo": "2025-01-07T10:00:00Z"
                },
                "estatisticas": {
                    "total_proposicoes": 25,
                    "total_emendas": 10,
                    "valor_total_emendas": 5000000.0,
                    "total_gastos": 300000.0,
                    "media_gastos_mensal": 25000.0,
                    "quantidade_municipios_beneficiados": 5,
                    "quantidade_ufs_beneficiadas": 2
                }
            }
        }
    }


class DeputadoList(BaseModel):
    """Schema para lista de deputados (paginada)"""
    deputados: List[DeputadoResponse]
    total: int = Field(..., description="Total de registros", ge=0)
    page: int = Field(..., description="Página atual", ge=1)
    per_page: int = Field(..., description="Registros por página", ge=1, le=100)
    total_pages: int = Field(..., description="Total de páginas", ge=1)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputados": [
                    {
                        "id": 745,
                        "api_camara_id": 204534,
                        "nome": "João da Silva",
                        "situacao": "Exercício",
                        "idp_info": {
                            "score_final": 75.5,
                            "posicao_ranking": 42
                        }
                    }
                ],
                "total": 513,
                "page": 1,
                "per_page": 20,
                "total_pages": 26
            }
        }
    }


class DeputadoSearchParams(BaseModel):
    """Schema para parâmetros de busca de deputados"""
    nome: Optional[str] = Field(None, description="Nome ou parte do nome", min_length=2)
    estado: Optional[str] = Field(None, description="UF (sigla)", pattern=r'^[A-Z]{2}$')
    partido: Optional[str] = Field(None, description="Partido (sigla)", min_length=2, max_length=20)
    situacao: Optional[str] = Field(None, description="Situação", max_length=50)
    min_idp: Optional[float] = Field(None, description="IDP mínimo", ge=0, le=100)
    max_idp: Optional[float] = Field(None, description="IDP máximo", ge=0, le=100)
    page: int = Field(1, description="Página", ge=1)
    per_page: int = Field(20, description="Registros por página", ge=1, le=100)
    sort_by: Optional[str] = Field("nome", description="Campo de ordenação")
    sort_order: Optional[str] = Field("asc", description="Ordem (asc/desc)", pattern=r'^(asc|desc)$')
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "nome": "João",
                "estado": "SP",
                "partido": "PT",
                "min_idp": 70.0,
                "max_idp": 90.0,
                "page": 1,
                "per_page": 20,
                "sort_by": "idp_final",
                "sort_order": "desc"
            }
        }
    }
