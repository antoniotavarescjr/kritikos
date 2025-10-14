# backend/src/models/sistema_models.py

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='Viewer')
    ativo = Column(Boolean, default=True)

    avaliacoes_realizadas = relationship("AvaliacaoPAR", back_populates="avaliador")
    logs = relationship("LogSistema", back_populates="usuario")

class LogSistema(Base):
    __tablename__ = 'logs_sistema'
    id = Column(Integer, primary_key=True, index=True) # BIGSERIAL é automático com Integer + primary_key=True
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    operacao = Column(String(100), nullable=False)
    tabela_afetada = Column(String(100))
    registro_id = Column(Integer)
    dados_anteriores = Column(JSONB)
    dados_novos = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())

    usuario = relationship("Usuario", back_populates="logs")
