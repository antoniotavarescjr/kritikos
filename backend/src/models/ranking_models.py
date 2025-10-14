# backend/src/models/ranking_models.py

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base

class CalculoIDP(Base):
    __tablename__ = 'calculos_idp'
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    data_calculo = Column(Date, nullable=False)
    periodo_referencia_inicio = Column(Date, nullable=False)
    periodo_referencia_fim = Column(Date, nullable=False)
    idp_final = Column(Numeric(5, 2), nullable=False)
    desempenho_legislativo = Column(Numeric(5, 2), nullable=False)
    par_relevancia_social = Column(Numeric(5, 2), nullable=False)
    responsabilidade_fiscal = Column(Numeric(5, 2), nullable=False)
    etica_legalidade = Column(Numeric(5, 2), nullable=False)
    versao_metodologia = Column(String(10), default='1.0')
    detalhes_calculo = Column(JSONB)

    deputado = relationship("Deputado", back_populates="calculos_idp")

    __table_args__ = (UniqueConstraint('deputado_id', 'data_calculo', 'periodo_referencia_inicio', name='_calculo_uc'),)

class AvaliacaoPAR(Base):
    __tablename__ = 'avaliacoes_par'
    id = Column(Integer, primary_key=True, index=True)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False, unique=True)
    data_avaliacao = Column(Date, nullable=False)
    escopo_impacto = Column(Integer, default=0)
    alinhamento_ods = Column(Integer, default=0)
    inovacao_eficiencia = Column(Integer, default=0)
    sustentabilidade_fiscal = Column(Integer, default=0)
    penalidade_oneracao = Column(Integer, default=0)
    par_final = Column(Integer, nullable=False)
    ods_identificados = Column(JSONB)
    metodo_avaliacao = Column(String(50), default='Automatico')
    avaliador_usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    observacoes = Column(Text)

    proposicao = relationship("Proposicao", back_populates="avaliacoes_par")
    avaliador = relationship("Usuario", back_populates="avaliacoes_realizadas")

class SituacaoLegal(Base):
    __tablename__ = 'situacao_legal'
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    tipo_situacao = Column(String(50), nullable=False)
    orgao_responsavel = Column(String(255))
    numero_processo = Column(String(100))
    descricao = Column(Text)
    data_inicio = Column(Date)
    data_fim = Column(Date)
    situacao_atual = Column(String(50), default='Em Andamento')
    fonte_informacao = Column(String(255))
    url_fonte = Column(Text)

    deputado = relationship("Deputado", back_populates="situacao_legal")

    __table_args__ = (UniqueConstraint('deputado_id', 'tipo_situacao', 'numero_processo', name='_situacao_legal_uc'),)
