# backend/src/models/financeiro_models.py

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class GastoParlamentar(Base):
    __tablename__ = 'gastos_parlamentares'
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    tipo_despesa = Column(String(255), nullable=False)
    descricao = Column(Text)
    fornecedor_nome = Column(String(255))
    fornecedor_cnpj = Column(String(18))
    valor_documento = Column(Numeric(10, 2))
    valor_glosa = Column(Numeric(10, 2), default=0)
    valor_liquido = Column(Numeric(10, 2))
    data_documento = Column(Date)
    numero_documento = Column(String(255))
    numero_ressarcimento = Column(String(255))
    parcela = Column(Integer)

    deputado = relationship("Deputado", back_populates="gastos")
