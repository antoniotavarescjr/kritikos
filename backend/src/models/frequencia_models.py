# backend/src/models/frequencia_models.py

from sqlalchemy import Column, Integer, String, Date, Boolean, TIMESTAMP, ForeignKey, func, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class FrequenciaDeputado(Base):
    """
    Tabela principal para armazenar dados de frequência mensal dos deputados.
    Contém resumos mensais de presença, faltas e dias trabalhados.
    """
    __tablename__ = 'frequencia_deputados'
    
    id = Column(Integer, primary_key=True, index=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    
    # Métricas principais
    dias_trabalhados = Column(Integer, default=0)
    dias_recesso = Column(Integer, default=0)
    faltas_justificadas = Column(Integer, default=0)
    faltas_nao_justificadas = Column(Integer, default=0)
    licencas = Column(Integer, default=0)
    sessoes_plenario = Column(Integer, default=0)
    sessoes_comissoes = Column(Integer, default=0)
    
    # Percentuais calculados
    percentual_presenca = Column(Numeric(precision=5, scale=2), default=0)
    percentual_comparecimento = Column(Numeric(precision=5, scale=2), default=0)
    
    # Metadados
    data_ultima_atualizacao = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    fonte_dados = Column(String(100), default='API_Camara')
    
    # Relacionamentos
    deputado = relationship("Deputado", back_populates="frequencias")
    detalhes = relationship("DetalheFrequencia", back_populates="frequencia_mensal", cascade="all, delete-orphan")
    rankings = relationship("RankingFrequencia", back_populates="frequencia", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('deputado_id', 'ano', 'mes', name='_frequencia_mensal_uc'),
    )

class DetalheFrequencia(Base):
    """
    Tabela para armazenar detalhes diários de frequência dos deputados.
    Contém informações específicas sobre cada sessão ou evento.
    """
    __tablename__ = 'detalhes_frequencia'
    
    id = Column(Integer, primary_key=True, index=True)
    frequencia_id = Column(Integer, ForeignKey('frequencia_deputados.id', ondelete="CASCADE"), nullable=False)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    
    # Informações do evento
    data_evento = Column(Date, nullable=False)
    tipo_evento = Column(String(50), nullable=False)  # 'Plenário', 'Comissão', 'Reunião', etc.
    descricao_evento = Column(String(255))
    
    # Status de presença
    presente = Column(Boolean, default=False)
    justificado = Column(Boolean, default=False)
    licenca = Column(Boolean, default=False)
    tipo_presenca = Column(String(50))  # 'Presente', 'Ausente', 'Licença', etc.
    
    # Metadados
    horario_inicio = Column(TIMESTAMP)
    horario_fim = Column(TIMESTAMP)
    duracao_minutos = Column(Integer)
    
    # Relacionamentos
    frequencia_mensal = relationship("FrequenciaDeputado", back_populates="detalhes")
    deputado = relationship("Deputado")
    
    __table_args__ = (
        UniqueConstraint('deputado_id', 'data_evento', 'tipo_evento', name='_detalhe_frequencia_uc'),
    )

class RankingFrequencia(Base):
    """
    Tabela para armazenar rankings mensais de frequência dos deputados.
    Permite análise comparativa e posicionamento.
    """
    __tablename__ = 'rankings_frequencia'
    
    id = Column(Integer, primary_key=True, index=True)
    frequencia_id = Column(Integer, ForeignKey('frequencia_deputados.id', ondelete="CASCADE"), nullable=False)
    deputado_id = Column(Integer, ForeignKey('deputados.id', ondelete="CASCADE"), nullable=False)
    
    # Período do ranking
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    
    # Posicionamentos
    posicao_geral = Column(Integer)
    posicao_partido = Column(Integer)
    posicao_estado = Column(Integer)
    
    # Métricas para ranking
    total_deputados = Column(Integer)
    total_deputados_partido = Column(Integer)
    total_deputados_estado = Column(Integer)
    
    # Percentuais para comparação
    percentil_geral = Column(Numeric(precision=5, scale=2))
    percentil_partido = Column(Numeric(precision=5, scale=2))
    percentil_estado = Column(Numeric(precision=5, scale=2))
    
    # Metadados
    data_calculo = Column(TIMESTAMP, server_default=func.now())
    versao_metodologia = Column(String(20), default='v1.0')
    
    # Relacionamentos
    frequencia = relationship("FrequenciaDeputado", back_populates="rankings")
    deputado = relationship("Deputado")
    
    __table_args__ = (
        UniqueConstraint('deputado_id', 'ano', 'mes', name='_ranking_frequencia_uc'),
    )

class ResumoFrequenciaMensal(Base):
    """
    Tabela de resumo estatístico mensal para análise agregada.
    Contém dados consolidados para relatórios e dashboards.
    """
    __tablename__ = 'resumos_frequencia_mensal'
    
    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    
    # Totais gerais
    total_deputados_ativos = Column(Integer, default=0)
    total_sessoes_realizadas = Column(Integer, default=0)
    total_presencas = Column(Integer, default=0)
    total_ausencias = Column(Integer, default=0)
    
    # Médias e percentuais
    media_presenca_percentual = Column(Numeric(precision=5, scale=2), default=0)
    media_dias_trabalhados = Column(Numeric(precision=5, scale=2), default=0)
    media_faltas_justificadas = Column(Numeric(precision=5, scale=2), default=0)
    media_faltas_nao_justificadas = Column(Numeric(precision=5, scale=2), default=0)
    
    # Distribuições
    deputados_acima_meta_presenca = Column(Integer, default=0)  # >= 95%
    deputados_abaixo_meta_presenca = Column(Integer, default=0)  # < 95%
    
    # Metadados
    data_geracao = Column(TIMESTAMP, server_default=func.now())
    fonte_dados = Column(String(100), default='Sistema_Kritikos')
    
    __table_args__ = (
        UniqueConstraint('ano', 'mes', name='_resumo_mensal_uc'),
    )
