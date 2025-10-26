"""
Modelos de dados para remuneração e benefícios dos deputados
Focus em APIs gratuitas da Câmara dos Deputados
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text, Boolean, TIMESTAMP, func
from sqlalchemy.orm import relationship
from .database import Base

class Remuneracao(Base):
    """
    Tabela principal de remuneração e benefícios dos deputados
    Inclui salário base + verbas indenizatórias + benefícios
    """
    __tablename__ = 'remuneracoes'
    
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    
    # Salário e verbas principais
    salario_base = Column(Numeric(10, 2))  # Salário padrão de Deputado Federal
    auxilio_moradia = Column(Numeric(10, 2), default=0)
    auxilio_saude = Column(Numeric(10, 2), default=0)
    auxilio_alimentacao = Column(Numeric(10, 2), default=0)
    
    # Verbas indenizatórias
    verbas_indenizatorias_total = Column(Numeric(10, 2), default=0)
    diarias_total = Column(Numeric(10, 2), default=0)
    passagens_total = Column(Numeric(10, 2), default=0)
    
    # Cargos em comissões (afeta remuneração)
    possui_cargo_comissao = Column(Boolean, default=False)
    cargo_comissao = Column(String(255))
    adicional_comissao = Column(Numeric(10, 2), default=0)
    
    # Totais
    total_bruto = Column(Numeric(10, 2))
    total_liquido = Column(Numeric(10, 2))
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    deputado = relationship("Deputado", backref="remuneracoes")
    
    __table_args__ = (
        {'schema': None},  # Usar schema default
    )

class VerbaIndenizatoria(Base):
    """
    Detalhamento das verbas indenizatórias recebidas
    Dados obtidos da API gratuita /deputados/{id}/verbas
    """
    __tablename__ = 'verbas_indenizatorias'
    
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    remuneracao_id = Column(Integer, ForeignKey('remuneracoes.id', ondelete="CASCADE"))
    
    # Dados da verba
    tipo_verba = Column(String(100), nullable=False, index=True)  # Ex: "Auxílio-Moradia", "Auxílio-Saúde"
    codigo_verba = Column(String(20))  # Código interno da Câmara
    descricao = Column(Text)
    
    # Valores
    valor = Column(Numeric(10, 2), nullable=False)
    valor_reembolsado = Column(Numeric(10, 2), default=0)
    
    # Período
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    data_referencia = Column(Date)
    
    # Metadados
    api_camara_id = Column(String(50))  # ID de referência da API
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    deputado = relationship("Deputado", backref="verbas_indenizatorias")
    remuneracao = relationship("Remuneracao", backref="verbas_detalhadas")

class CargoComissao(Base):
    """
    Cargos ocupados em comissões e órgãos
    Afeta a remuneração e benefícios do deputado
    """
    __tablename__ = 'cargos_comissoes'
    
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    
    # Dados do cargo
    orgao_id = Column(Integer)  # ID do órgão na API
    orgao_nome = Column(String(255), nullable=False)
    orgao_sigla = Column(String(20))
    cargo = Column(String(100), nullable=False)  # Ex: "Presidente", "Relator", "Membro"
    
    # Período do cargo
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)
    cargo_ativo = Column(Boolean, default=True)
    
    # Benefícios associados
    adicional_remuneratorio = Column(Numeric(10, 2), default=0)
    auxilio_presenca = Column(Numeric(10, 2), default=0)
    
    # Metadados
    api_camara_id = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    deputado = relationship("Deputado", backref="cargos_comissoes")

class SalarioPadrao(Base):
    """
    Tabela de referência para salários padrão de Deputado Federal
    Atualizada manualmente quando há reajustes
    """
    __tablename__ = 'salarios_padrao'
    
    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, unique=True, nullable=False)
    mes_inicio = Column(Integer, default=1)  # Mês em que o salário passou a vigorar
    
    # Valores do salário
    salario_bruto = Column(Numeric(10, 2), nullable=False)
    auxilio_moradia_maximo = Column(Numeric(10, 2))
    auxilio_saude_maximo = Column(Numeric(10, 2))
    diaria_maxima = Column(Numeric(10, 2))
    
    # Informações de referência
    fonte_informacao = Column(String(255))  # Ex: "Diário Oficial da Câmara"
    data_publicacao = Column(Date)
    observacoes = Column(Text)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
