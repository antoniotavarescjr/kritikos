"""
Schemas Pydantic para Proposições Legislativas
Validação e serialização de dados de proposições e análises
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from pydantic import BaseModel, Field


class ProposicaoBase(BaseModel):
    """Schema base para dados de proposição legislativa"""
    api_camara_id: int = Field(..., description="ID da proposição na API da Câmara", gt=0)
    tipo: str = Field(..., description="Tipo da proposição (PL, PEC, etc)", max_length=20)
    numero: int = Field(..., description="Número da proposição", gt=0)
    ano: int = Field(..., description="Ano da proposição", ge=2020, le=2030)
    ementa: str = Field(..., description="Ementa da proposição", min_length=10, max_length=2000)
    descricao_tipo: Optional[str] = Field(None, description="Descrição do tipo", max_length=100)
    keywords: Optional[str] = Field(None, description="Palavras-chave", max_length=500)
    data_apresentacao: Optional[date] = Field(None, description="Data de apresentação")
    data_aprovacao: Optional[date] = Field(None, description="Data de aprovação")
    situacao: Optional[str] = Field(None, description="Situação atual", max_length=100)
    descricao_situacao: Optional[str] = Field(None, description="Descrição da situação", max_length=500)
    link_inteiro_teor: Optional[str] = Field(None, description="Link para o inteiro teor", max_length=500)
    url_documento: Optional[str] = Field(None, description="URL do documento", max_length=500)
    gcs_url: Optional[str] = Field(None, description="URL no GCS", max_length=500)
    ultimo_status_data: Optional[date] = Field(None, description="Data do último status")
    ultimo_status_descricao: Optional[str] = Field(None, description="Descrição do último status", max_length=500)


class ProposicaoCreate(ProposicaoBase):
    """Schema para criação de proposição"""
    pass


class ProposicaoUpdate(BaseModel):
    """Schema para atualização de proposição"""
    ementa: Optional[str] = Field(None, description="Ementa da proposição", min_length=10, max_length=2000)
    keywords: Optional[str] = Field(None, description="Palavras-chave", max_length=500)
    data_aprovacao: Optional[date] = Field(None, description="Data de aprovação")
    situacao: Optional[str] = Field(None, description="Situação atual", max_length=100)
    descricao_situacao: Optional[str] = Field(None, description="Descrição da situação", max_length=500)
    link_inteiro_teor: Optional[str] = Field(None, description="Link para o inteiro teor", max_length=500)
    url_documento: Optional[str] = Field(None, description="URL do documento", max_length=500)
    gcs_url: Optional[str] = Field(None, description="URL no GCS", max_length=500)
    ultimo_status_data: Optional[date] = Field(None, description="Data do último status")
    ultimo_status_descricao: Optional[str] = Field(None, description="Descrição do último status", max_length=500)


class ProposicaoResponse(ProposicaoBase):
    """Schema para resposta de dados de proposição"""
    id: int = Field(..., description="ID único da proposição", gt=0)
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data de atualização")
    
    # Campos opcionais que podem ser incluídos
    analise: Optional['AnaliseProposicaoResponse'] = Field(None, description="Análise da proposição")
    autores: Optional[List['AutoriaInfo']] = Field(None, description="Autores da proposição")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 12345,
                "api_camara_id": 2234567,
                "tipo": "PL",
                "numero": 1234,
                "ano": 2025,
                "ementa": "Dispõe sobre a criação de programa de incentivo à educação ambiental...",
                "descricao_tipo": "Projeto de Lei",
                "keywords": "educação, meio ambiente, incentivo",
                "data_apresentacao": "2025-01-05",
                "situacao": "Tramitando",
                "descricao_situacao": "Em tramitação na Câmara dos Deputados",
                "link_inteiro_teor": "https://www.camara.leg.br/proposicoesWeb/...",
                "created_at": "2025-01-07T15:00:00Z",
                "updated_at": "2025-01-07T15:00:00Z"
            }
        }
    }


class AnaliseProposicaoBase(BaseModel):
    """Schema base para análise de proposição"""
    resumo_texto: Optional[str] = Field(None, description="Resumo gerado por IA", max_length=5000)
    is_trivial: Optional[bool] = Field(None, description="Se a proposição é trivial")
    par_score: Optional[int] = Field(None, description="Score PAR (0-100)", ge=0, le=100)
    escopo_impacto: Optional[int] = Field(None, description="Escopo de impacto (0-100)", ge=0, le=100)
    alinhamento_ods: Optional[int] = Field(None, description="Alinhamento ODS (0-100)", ge=0, le=100)
    inovacao_eficiencia: Optional[int] = Field(None, description="Inovação e eficiência (0-100)", ge=0, le=100)
    sustentabilidade_fiscal: Optional[int] = Field(None, description="Sustentabilidade fiscal (0-100)", ge=0, le=100)
    penalidade_oneracao: Optional[int] = Field(None, description="Penalidade por oneração (0-100)", ge=0, le=100)
    ods_identificados: Optional[List[int]] = Field(None, description="ODS identificados")
    resumo_analise: Optional[str] = Field(None, description="Resumo da análise", max_length=3000)
    versao_analise: Optional[str] = Field(None, description="Versão da análise", max_length=20)


class AnaliseProposicaoResponse(AnaliseProposicaoBase):
    """Schema para resposta de análise de proposição"""
    id: int = Field(..., description="ID único da análise", gt=0)
    proposicao_id: int = Field(..., description="ID da proposição analisada", gt=0)
    data_resumo: Optional[datetime] = Field(None, description="Data do resumo")
    data_filtro_trivial: Optional[datetime] = Field(None, description="Data do filtro de trivialidade")
    data_analise: datetime = Field(..., description="Data da análise")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 54321,
                "proposicao_id": 12345,
                "resumo_texto": "A proposição estabelece um programa nacional de educação ambiental...",
                "data_resumo": "2025-01-07T10:00:00Z",
                "is_trivial": False,
                "data_filtro_trivial": "2025-01-07T10:30:00Z",
                "par_score": 75,
                "escopo_impacto": 80,
                "alinhamento_ods": 70,
                "inovacao_eficiencia": 75,
                "sustentabilidade_fiscal": 70,
                "penalidade_oneracao": 60,
                "ods_identificados": [4, 12, 13],
                "resumo_analise": "Proposição relevante com bom alinhamento aos ODS...",
                "versao_analise": "1.0",
                "data_analise": "2025-01-07T11:00:00Z"
            }
        }
    }


class AutoriaInfo(BaseModel):
    """Schema para informações de autoria"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    nome_deputado: str = Field(..., description="Nome do deputado")
    tipo_autoria: str = Field(..., description="Tipo de autoria", max_length=50)
    ordem_assinatura: Optional[int] = Field(None, description="Ordem de assinatura", gt=0)
    data_autoria: Optional[date] = Field(None, description="Data da autoria")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "tipo_autoria": "Autor",
                "ordem_assinatura": 1,
                "data_autoria": "2025-01-05"
            }
        }
    }


class ProposicaoResumo(BaseModel):
    """Schema para resumo de proposição"""
    id: int = Field(..., description="ID único da proposição", gt=0)
    tipo: str = Field(..., description="Tipo da proposição", max_length=20)
    numero: int = Field(..., description="Número da proposição", gt=0)
    ano: int = Field(..., description="Ano da proposição", ge=2020, le=2030)
    ementa: str = Field(..., description="Ementa resumida", max_length=200)
    data_apresentacao: Optional[date] = Field(None, description="Data de apresentação")
    situacao: Optional[str] = Field(None, description="Situação atual", max_length=100)
    tem_analise: bool = Field(..., description="Se possui análise")
    par_score: Optional[int] = Field(None, description="Score PAR se analisada", ge=0, le=100)
    is_trivial: Optional[bool] = Field(None, description="Se é trivial se analisada")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 12345,
                "tipo": "PL",
                "numero": 1234,
                "ano": 2025,
                "ementa": "Dispõe sobre programa de educação ambiental...",
                "data_apresentacao": "2025-01-05",
                "situacao": "Tramitando",
                "tem_analise": True,
                "par_score": 75,
                "is_trivial": False
            }
        }
    }


class ProposicaoEstatisticas(BaseModel):
    """Schema para estatísticas de proposições de um deputado"""
    periodo_analise: str = Field(..., description="Período analisado")
    total_proposicoes: int = Field(..., description="Total de proposições", ge=0)
    proposicoes_analisadas: int = Field(..., description="Proposições analisadas", ge=0)
    proposicoes_relevantes: int = Field(..., description="Proposições relevantes", ge=0)
    proposicoes_triviais: int = Field(..., description="Proposições triviais", ge=0)
    taxa_analise: float = Field(..., description="Taxa de análise (%)", ge=0, le=100)
    taxa_relevancia: float = Field(..., description="Taxa de relevância (%)", ge=0, le=100)
    par_medio: Optional[float] = Field(None, description="Score PAR médio", ge=0, le=100)
    proposicoes_por_tipo: Dict[str, int] = Field(..., description="Proposições por tipo")
    proposicoes_por_ano: Dict[str, int] = Field(..., description="Proposições por ano")
    ods_mais_frequentes: List[Dict[str, Any]] = Field(..., description="ODS mais frequentes")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "periodo_analise": "2023-2025",
                "total_proposicoes": 25,
                "proposicoes_analisadas": 20,
                "proposicoes_relevantes": 15,
                "proposicoes_triviais": 5,
                "taxa_analise": 80.0,
                "taxa_relevancia": 75.0,
                "par_medio": 72.5,
                "proposicoes_por_tipo": {
                    "PL": 20,
                    "PEC": 3,
                    "PLP": 2
                },
                "proposicoes_por_ano": {
                    "2023": 8,
                    "2024": 10,
                    "2025": 7
                },
                "ods_mais_frequentes": [
                    {"ods": 4, "nome": "Educação de Qualidade", "frequencia": 12},
                    {"ods": 13, "nome": "Ação Contra a Mudança Global do Clima", "frequencia": 8}
                ]
            }
        }
    }


class ProposicaoList(BaseModel):
    """Schema para lista de proposições (paginada)"""
    proposicoes: List[ProposicaoResponse]
    total: int = Field(..., description="Total de registros", ge=0)
    page: int = Field(..., description="Página atual", ge=1)
    per_page: int = Field(..., description="Registros por página", ge=1, le=100)
    total_pages: int = Field(..., description="Total de páginas", ge=1)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "proposicoes": [
                    {
                        "id": 12345,
                        "api_camara_id": 2234567,
                        "tipo": "PL",
                        "numero": 1234,
                        "ano": 2025,
                        "ementa": "Dispõe sobre programa de educação ambiental...",
                        "data_apresentacao": "2025-01-05",
                        "situacao": "Tramitando",
                        "analise": {
                            "par_score": 75,
                            "is_trivial": False
                        }
                    }
                ],
                "total": 25,
                "page": 1,
                "per_page": 20,
                "total_pages": 2
            }
        }
    }


class ProposicaoSearchParams(BaseModel):
    """Schema para parâmetros de busca de proposições"""
    deputado_id: Optional[int] = Field(None, description="ID do deputado autor", gt=0)
    tipo: Optional[str] = Field(None, description="Tipo da proposição", max_length=20)
    ano: Optional[int] = Field(None, description="Ano da proposição", ge=2020, le=2030)
    numero: Optional[int] = Field(None, description="Número da proposição", gt=0)
    ementa: Optional[str] = Field(None, description="Texto na ementa", min_length=3)
    keywords: Optional[str] = Field(None, description="Palavras-chave", min_length=3)
    situacao: Optional[str] = Field(None, description="Situação", max_length=100)
    tem_analise: Optional[bool] = Field(None, description="Se possui análise")
    is_trivial: Optional[bool] = Field(None, description="Se é trivial")
    par_minimo: Optional[int] = Field(None, description="Score PAR mínimo", ge=0, le=100)
    par_maximo: Optional[int] = Field(None, description="Score PAR máximo", ge=0, le=100)
    data_inicio: Optional[date] = Field(None, description="Data de início")
    data_fim: Optional[date] = Field(None, description="Data de fim")
    ods: Optional[List[int]] = Field(None, description="Lista de ODS")
    page: int = Field(1, description="Página", ge=1)
    per_page: int = Field(20, description="Registros por página", ge=1, le=100)
    sort_by: Optional[str] = Field("data_apresentacao", description="Campo de ordenação")
    sort_order: Optional[str] = Field("desc", description="Ordem (asc/desc)", pattern=r'^(asc|desc)$')
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "tipo": "PL",
                "ano": 2025,
                "ementa": "educação",
                "tem_analise": True,
                "is_trivial": False,
                "par_minimo": 70,
                "par_maximo": 90,
                "data_inicio": "2025-01-01",
                "data_fim": "2025-12-31",
                "ods": [4, 13],
                "page": 1,
                "per_page": 20,
                "sort_by": "par_score",
                "sort_order": "desc"
            }
        }
    }


class ProposicaoComparativo(BaseModel):
    """Schema para comparativo de proposições entre deputados"""
    deputado_id: int = Field(..., description="ID do deputado", gt=0)
    nome_deputado: str = Field(..., description="Nome do deputado")
    total_proposicoes: int = Field(..., description="Total de proposições", ge=0)
    proposicoes_analisadas: int = Field(..., description="Proposições analisadas", ge=0)
    proposicoes_relevantes: int = Field(..., description="Proposições relevantes", ge=0)
    taxa_analise: float = Field(..., description="Taxa de análise (%)", ge=0, le=100)
    taxa_relevancia: float = Field(..., description="Taxa de relevância (%)", ge=0, le=100)
    par_medio: Optional[float] = Field(None, description="Score PAR médio", ge=0, le=100)
    posicao_ranking_quantidade: int = Field(..., description="Posição no ranking por quantidade", gt=0)
    posicao_ranking_qualidade: int = Field(..., description="Posição no ranking por qualidade", gt=0)
    total_deputados: int = Field(..., description="Total de deputados no ranking", gt=0)
    percentil_quantidade: float = Field(..., description="Percentil no ranking por quantidade", ge=0, le=100)
    percentil_qualidade: float = Field(..., description="Percentil no ranking por qualidade", ge=0, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "deputado_id": 745,
                "nome_deputado": "João da Silva",
                "total_proposicoes": 25,
                "proposicoes_analisadas": 20,
                "proposicoes_relevantes": 15,
                "taxa_analise": 80.0,
                "taxa_relevancia": 75.0,
                "par_medio": 72.5,
                "posicao_ranking_quantidade": 100,
                "posicao_ranking_qualidade": 50,
                "total_deputados": 513,
                "percentil_quantidade": 80.5,
                "percentil_qualidade": 90.2
            }
        }
    }


# Importações forward para evitar referências circulares
if TYPE_CHECKING:
    from .deputado import DeputadoResponse
