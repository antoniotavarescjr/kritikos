# backend/src/models/base_models.py

from sqlalchemy import Column, Integer, String, Date, Boolean, TIMESTAMP, CHAR, func
from sqlalchemy.orm import relationship
from .database import Base

class Partido(Base):
    __tablename__ = 'partidos'
    id = Column(Integer, primary_key=True, index=True)
    sigla = Column(String(10), unique=True, nullable=False)
    nome = Column(String(255), nullable=False)
    numero = Column(Integer)
    fundacao = Column(Date)
    status = Column(String(50), default='Ativo')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    mandatos = relationship("Mandato", back_populates="partido")

class Estado(Base):
    __tablename__ = 'estados'
    id = Column(Integer, primary_key=True, index=True)
    sigla = Column(CHAR(2), unique=True, nullable=False)
    nome = Column(String(100), nullable=False)
    regiao = Column(String(50), nullable=False)
    codigo_ibge = Column(Integer)

    mandatos = relationship("Mandato", back_populates="estado")

class Legislatura(Base):
    __tablename__ = 'legislaturas'
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    ativa = Column(Boolean, default=False)

    mandatos = relationship("Mandato", back_populates="legislatura")

class ODS(Base):
    __tablename__ = 'ods'
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(String)
    cor_oficial = Column(CHAR(7))
    icone_url = Column(String)
    ativo = Column(Boolean, default=True)
