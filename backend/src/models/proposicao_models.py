# backend/src/models/proposicao_models.py

from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, ForeignKey, Boolean, func, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class Proposicao(Base):
    __tablename__ = 'proposicoes'
    id = Column(Integer, primary_key=True, index=True)
    api_camara_id = Column(Integer, unique=True, index=True)
    tipo = Column(String(10), nullable=False)
    numero = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    ementa = Column(Text, nullable=False)
    explicacao = Column(Text)
    data_apresentacao = Column(Date, nullable=False)
    situacao = Column(String(100))
    link_inteiro_teor = Column(String)
    keywords = Column(Text)
    gcs_url = Column(String)  # URL do arquivo completo no Google Cloud Storage
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    autores = relationship("Autoria", back_populates="proposicao", cascade="all, delete-orphan")
    votacoes = relationship("Votacao", back_populates="proposicao")
    pareceres_ccj = relationship("ParecerCCJ", back_populates="proposicao")
    avaliacoes_par = relationship("AvaliacaoPAR", back_populates="proposicao")

    __table_args__ = (UniqueConstraint('tipo', 'numero', 'ano', name='_proposicao_uc'),)

class Autoria(Base):
    __tablename__ = 'autorias'
    id = Column(Integer, primary_key=True, index=True)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id', ondelete="CASCADE"), nullable=False)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    tipo_autoria = Column(String(50), nullable=False)
    ordem = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())

    proposicao = relationship("Proposicao", back_populates="autores")
    deputado = relationship("Deputado", back_populates="autorias")

    __table_args__ = (UniqueConstraint('proposicao_id', 'deputado_id', 'tipo_autoria', name='_autoria_uc'),)

class Votacao(Base):
    __tablename__ = 'votacoes'
    id = Column(Integer, primary_key=True, index=True)
    api_camara_id = Column(Integer, unique=True, index=True)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'))  # Manter para compatibilidade
    data_votacao = Column(TIMESTAMP, nullable=False)
    objeto_votacao = Column(Text, nullable=False)
    tipo_votacao = Column(String(50))
    resultado = Column(String(50))
    votos_sim = Column(Integer, default=0)
    votos_nao = Column(Integer, default=0)
    abstencoes = Column(Integer, default=0)
    ausencias = Column(Integer, default=0)
    quorum_minimo = Column(Integer)
    
    # Novos campos dos arquivos JSON (tornados nullable para compatibilidade)
    sigla_orgao = Column(String(20), nullable=True)  # PLEN, CCEX, etc.
    uri_orgao = Column(String(500), nullable=True)  # URI pode ser nulo
    data_hora_registro = Column(TIMESTAMP, nullable=True)  # Data/hora de registro nos sistemas
    descricao_tipo_votacao = Column(String(100), nullable=True)  # Nominal, Simbólica
    descricao_resultado = Column(String(200), nullable=True)  # Descrição detalhada
    aprovacao = Column(Boolean, nullable=True)  # Boolean explícito
    uri_votacao = Column(String(500), nullable=True)  # URI completa da votação
    
    # Relacionamentos existentes (manter)
    proposicao = relationship("Proposicao", back_populates="votacoes")
    votos_deputados = relationship("VotoDeputado", back_populates="votacao", cascade="all, delete-orphan")
    
    # Novos relacionamentos
    objetos = relationship("VotacaoObjeto", back_populates="votacao", cascade="all, delete-orphan")
    proposicoes_afetadas = relationship("VotacaoProposicao", back_populates="votacao", cascade="all, delete-orphan")
    orientacoes_bancada = relationship("OrientacaoBancada", back_populates="votacao", cascade="all, delete-orphan")

class VotoDeputado(Base):
    __tablename__ = 'votos_deputados'
    id = Column(Integer, primary_key=True, index=True)
    votacao_id = Column(Integer, ForeignKey('votacoes.id', ondelete="CASCADE"), nullable=False)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    voto = Column(String(50), nullable=False)
    orientacao_partido = Column(String(50))
    seguiu_orientacao = Column(Boolean)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    votacao = relationship("Votacao", back_populates="votos_deputados")
    deputado = relationship("Deputado", back_populates="votos")

    __table_args__ = (UniqueConstraint('votacao_id', 'deputado_id', name='_voto_uc'),)

class VotacaoObjeto(Base):
    __tablename__ = 'votacoes_objetos'
    id = Column(Integer, primary_key=True, index=True)
    votacao_id = Column(Integer, ForeignKey('votacoes.id', ondelete="CASCADE"), nullable=False)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False)
    descricao_efeito = Column(Text)
    
    votacao = relationship("Votacao", back_populates="objetos")
    proposicao = relationship("Proposicao")
    
    __table_args__ = (UniqueConstraint('votacao_id', 'proposicao_id', name='_votacao_objeto_uc'),)

class VotacaoProposicao(Base):
    __tablename__ = 'votacoes_proposicoes'
    id = Column(Integer, primary_key=True, index=True)
    votacao_id = Column(Integer, ForeignKey('votacoes.id', ondelete="CASCADE"), nullable=False)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False)
    descricao_efeito = Column(Text)
    
    votacao = relationship("Votacao", back_populates="proposicoes_afetadas")
    proposicao = relationship("Proposicao")
    
    __table_args__ = (UniqueConstraint('votacao_id', 'proposicao_id', name='_votacao_proposicao_uc'),)

class OrientacaoBancada(Base):
    __tablename__ = 'orientacoes_bancada'
    id = Column(Integer, primary_key=True, index=True)
    votacao_id = Column(Integer, ForeignKey('votacoes.id', ondelete="CASCADE"), nullable=False)
    partido_id = Column(Integer, ForeignKey('partidos.id'))
    bloco_id = Column(Integer, ForeignKey('blocos_partidarios.id'))
    orientacao = Column(String(50))  # Sim, Não, Liberada
    tipo_bancada = Column(String(50))  # Governo, Minoria, Maioria, Oposição
    
    votacao = relationship("Votacao", back_populates="orientacoes_bancada")
    partido = relationship("Partido")
    bloco = relationship("BlocoPartidario")
    
    __table_args__ = (UniqueConstraint('votacao_id', 'partido_id', 'tipo_bancada', name='_orientacao_bancada_uc'),)

class ParecerCCJ(Base):
    __tablename__ = 'pareceres_ccj'
    id = Column(Integer, primary_key=True, index=True)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False)
    data_parecer = Column(Date, nullable=False)
    relator_deputado_id = Column(Integer, ForeignKey('deputados.id'))
    parecer = Column(String(50))
    constitucionalidade = Column(String(50))
    juridicidade = Column(String(50))
    tecnica_legislativa = Column(String(50))
    observacoes = Column(Text)

    proposicao = relationship("Proposicao", back_populates="pareceres_ccj")
    relator = relationship("Deputado", back_populates="pareceres_relatados")
