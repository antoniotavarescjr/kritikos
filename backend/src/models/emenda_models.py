"""
Modelos de dados para emendas parlamentares
Focus em APIs gratuitas da Câmara dos Deputados
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text, Boolean, TIMESTAMP, func
from sqlalchemy.orm import relationship
from .database import Base

class EmendaParlamentar(Base):
    """
    Tabela principal de emendas parlamentares
    Dados obtidos da API gratuita de proposições
    """
    __tablename__ = 'emendas_parlamentares'
    
    id = Column(Integer, primary_key=True, index=True)
    api_camara_id = Column(String(50), unique=True, index=True)  # ID da proposição na API
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=True)  # Pode ser None para emendas de comissão
    
    # Identificação da emenda
    tipo_emenda = Column(String(50), nullable=False, index=True)  # EMD, EMP, etc
    numero = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False, index=True)
    emenda = Column(Text, nullable=False)  # Texto completo da emenda
    
    # Classificação
    local = Column(String(100))  # LOA, LDO, PPA, etc
    natureza = Column(String(100))  # Individual, Bancada, Comissão
    tema = Column(String(255))
    area_tematica = Column(String(100))
    
    # Valores
    valor_emenda = Column(Numeric(15, 2))
    valor_empenhado = Column(Numeric(15, 2), default=0)
    valor_liquidado = Column(Numeric(15, 2), default=0)
    valor_pago = Column(Numeric(15, 2), default=0)
    
    # Beneficiários
    beneficiario_principal = Column(Text)  # Município/Estado/Entidade principal
    beneficiarios_secundarios = Column(Text)  # Outros beneficiários
    uf_beneficiario = Column(String(2))
    municipio_beneficiario = Column(String(255))
    
    # Situação
    situacao = Column(String(100), index=True)
    data_apresentacao = Column(Date)
    data_aprovacao = Column(Date)
    data_publicacao = Column(Date)
    
    # Autoria
    autor = Column(String(255))
    partido_autor = Column(String(20))
    uf_autor = Column(String(2))
    
    # Metadados
    url_documento = Column(String(500))
    gcs_url = Column(String(500))  # URL do arquivo completo no GCS
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    deputado = relationship("Deputado", backref="emendas_parlamentares")

class ExecucaoEmenda(Base):
    """
    Acompanhamento da execução financeira das emendas
    """
    __tablename__ = 'execucao_emendas'
    
    id = Column(Integer, primary_key=True, index=True)
    emenda_id = Column(Integer, ForeignKey('emendas_parlamentares.id', ondelete="CASCADE"), nullable=False)
    
    # Período de execução
    ano_execucao = Column(Integer, nullable=False, index=True)
    mes_execucao = Column(Integer, index=True)
    data_referencia = Column(Date)
    
    # Valores financeiros
    valor_empenhado_acumulado = Column(Numeric(15, 2), default=0)
    valor_liquidado_acumulado = Column(Numeric(15, 2), default=0)
    valor_pago_acumulado = Column(Numeric(15, 2), default=0)
    
    # Métricas de execução
    percentual_empenhado = Column(Numeric(5, 2), default=0)
    percentual_liquidado = Column(Numeric(5, 2), default=0)
    percentual_pago = Column(Numeric(5, 2), default=0)
    
    # Status da execução
    status_execucao = Column(String(50))  # Em execução, Concluída, Paralisada, etc
    observacoes = Column(Text)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    emenda = relationship("EmendaParlamentar", backref="execucoes")

class DetalheEmenda(Base):
    """
    Detalhes específicos de cada emenda
    Informações complementares obtidas dos detalhes da proposição
    """
    __tablename__ = 'detalhes_emendas'
    
    id = Column(Integer, primary_key=True, index=True)
    emenda_id = Column(Integer, ForeignKey('emendas_parlamentares.id', ondelete="CASCADE"), nullable=False)
    
    # Detalhes técnicos
    numero_lei = Column(String(20))
    ementa = Column(Text)
    justificativa = Column(Text)
    objetivo = Column(Text)
    
    # Informações orçamentárias
    funcao = Column(String(100))
    subfuncao = Column(String(100))
    programa = Column(String(100))
    acao = Column(String(100))
    
    # Localização da despesa
    orgao_responsavel = Column(String(255))
    unidade_orcamentaria = Column(String(255))
    
    # Classificação
    categoria_economica = Column(String(100))
    fonte_recursos = Column(String(100))
    
    # Documentação
    texto_completo = Column(Text)
    pdf_url = Column(String(500))
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    emenda = relationship("EmendaParlamentar", backref="detalhes")

class VotacaoEmenda(Base):
    """
    Registro de votações das emendas
    """
    __tablename__ = 'votacoes_emendas'
    
    id = Column(Integer, primary_key=True, index=True)
    emenda_id = Column(Integer, ForeignKey('emendas_parlamentares.id', ondelete="CASCADE"), nullable=False)
    
    # Dados da votação
    data_votacao = Column(Date)
    hora_votacao = Column(String(10))
    tipo_votacao = Column(String(100))
    
    # Resultado
    resultado = Column(String(50))  # Aprovada, Rejeitada, etc
    votos_sim = Column(Integer, default=0)
    votos_nao = Column(Integer, default=0)
    votos_abstencao = Column(Integer, default=0)
    total_votantes = Column(Integer, default=0)
    
    # Contexto
    orgao_votacao = Column(String(255))
    plenario = Column(Boolean, default=True)
    
    # Metadados
    api_camara_id = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    emenda = relationship("EmendaParlamentar", backref="votacoes")

class RankingEmendas(Base):
    """
    Tabela de ranking consolidado de emendas por período
    Estrutura correspondente ao banco de dados real
    """
    __tablename__ = 'ranking_emendas'
    
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    
    # Período do ranking
    ano_referencia = Column(Integer, nullable=False, index=True)
    mes_referencia = Column(Integer, index=True)  # Null para ranking anual
    
    # Métricas de emendas
    quantidade_emendas = Column(Integer, default=0)
    valor_total_emendas = Column(Numeric(15, 2), default=0)
    valor_medio_emenda = Column(Numeric(15, 2), default=0)
    
    # Métricas de execução
    valor_total_executado = Column(Numeric(15, 2), default=0)
    percentual_execucao_medio = Column(Numeric(5, 2), default=0)
    
    # Campos de ranking existentes no banco
    ranking_quantidade = Column(Integer, default=0)
    ranking_valor = Column(Integer, default=0)
    ranking_execucao = Column(Integer, default=0)
    
    # Beneficiários
    quantidade_municipios_beneficiados = Column(Integer, default=0)
    quantidade_ufs_beneficiadas = Column(Integer, default=0)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    deputado = relationship("Deputado", backref="rankings_emendas")
