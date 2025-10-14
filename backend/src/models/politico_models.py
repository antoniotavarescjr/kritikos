# backend/src/models/politico_models.py

from sqlalchemy import Column, Integer, String, Date, CHAR, TIMESTAMP, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class Deputado(Base):
    __tablename__ = 'deputados'
    id = Column(Integer, primary_key=True, index=True)
    api_camara_id = Column(Integer, unique=True, index=True)
    nome = Column(String(255), nullable=False)
    nome_civil = Column(String(255))
    cpf = Column(String(14), unique=True)
    sexo = Column(CHAR(1))
    data_nascimento = Column(Date)
    municipio_nascimento = Column(String(255))
    uf_nascimento = Column(CHAR(2))
    escolaridade = Column(String(100))
    profissao = Column(String(255))
    email = Column(String(255))
    telefone = Column(String(20))
    foto_url = Column(String)
    situacao = Column(String(50), default='Exercício')
    condicao = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    mandatos = relationship("Mandato", back_populates="deputado", cascade="all, delete-orphan")
    autorias = relationship("Autoria", back_populates="deputado", cascade="all, delete-orphan")
    votos = relationship("VotoDeputado", back_populates="deputado", cascade="all, delete-orphan")
    gastos = relationship("GastoParlamentar", back_populates="deputado", cascade="all, delete-orphan")
    calculos_idp = relationship("CalculoIDP", back_populates="deputado", cascade="all, delete-orphan")
    situacao_legal = relationship("SituacaoLegal", back_populates="deputado", cascade="all, delete-orphan")
    pareceres_relatados = relationship("ParecerCCJ", back_populates="relator")

class Mandato(Base):
    __tablename__ = 'mandatos'
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    legislatura_id = Column(Integer, ForeignKey('legislaturas.id'), nullable=False)
    partido_id = Column(Integer, ForeignKey('partidos.id'), nullable=False)
    estado_id = Column(Integer, ForeignKey('estados.id'), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)
    motivo_fim = Column(String(255))
    votos_recebidos = Column(Integer)
    posicao_lista = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    deputado = relationship("Deputado", back_populates="mandatos")
    legislatura = relationship("Legislatura", back_populates="mandatos")
    partido = relationship("Partido", back_populates="mandatos")
    estado = relationship("Estado", back_populates="mandatos")

    __table_args__ = (UniqueConstraint('deputado_id', 'legislatura_id', name='_deputado_legislatura_uc'),)
