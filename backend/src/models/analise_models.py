#!/usr/bin/env python3
"""
Modelos de dados para análise de proposições e scores de deputados.
Implementa persistência completa do fluxo de agentes Kritikos.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, DECIMAL, JSON, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base_models import Base
from .politico_models import Deputado
from .proposicao_models import Proposicao


class AnaliseProposicao(Base):
    """
    Armazena resultados completos da análise de proposições.
    Inclui resumo, filtro de trivialidade e PAR completo.
    """
    __tablename__ = 'analise_proposicoes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False, unique=True)
    
    # Dados do resumo
    resumo_texto = Column(Text, nullable=True)
    data_resumo = Column(DateTime, default=datetime.utcnow)
    
    # Resultado do filtro de trivialidade
    is_trivial = Column(Boolean, nullable=True)
    data_filtro_trivial = Column(DateTime, nullable=True)
    
    # Análise PAR completa
    par_score = Column(Integer, nullable=True)
    escopo_impacto = Column(Integer, nullable=True)
    alinhamento_ods = Column(Integer, nullable=True)
    inovacao_eficiencia = Column(Integer, nullable=True)
    sustentabilidade_fiscal = Column(Integer, nullable=True)
    penalidade_oneracao = Column(Integer, nullable=True)
    ods_identificados = Column(ARRAY(Integer), nullable=True)
    resumo_analise = Column(Text, nullable=True)
    
    # Controle
    data_analise = Column(DateTime, default=datetime.utcnow)
    versao_analise = Column(String(20), default='1.0')
    
    # Relacionamentos
    proposicao = relationship("Proposicao", back_populates="analise")
    
    def __repr__(self):
        return f"<AnaliseProposicao(id={self.id}, prop_id={self.proposicao_id}, par={self.par_score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável."""
        return {
            'id': self.id,
            'proposicao_id': self.proposicao_id,
            'resumo_texto': self.resumo_texto,
            'data_resumo': self.data_resumo.isoformat() if self.data_resumo else None,
            'is_trivial': self.is_trivial,
            'data_filtro_trivial': self.data_filtro_trivial.isoformat() if self.data_filtro_trivial else None,
            'par_score': self.par_score,
            'escopo_impacto': self.escopo_impacto,
            'alinhamento_ods': self.alinhamento_ods,
            'inovacao_eficiencia': self.inovacao_eficiencia,
            'sustentabilidade_fiscal': self.sustentabilidade_fiscal,
            'penalidade_oneracao': self.penalidade_oneracao,
            'ods_identificados': self.ods_identificados,
            'resumo_analise': self.resumo_analise,
            'data_analise': self.data_analise.isoformat() if self.data_analise else None,
            'versao_analise': self.versao_analise
        }


class ScoreDeputado(Base):
    """
    Armazena scores finais dos deputados calculados pela metodologia Kritikos.
    Inclui todos os eixos de análise e score final ponderado.
    """
    __tablename__ = 'scores_deputados'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id'), nullable=False, unique=True)
    
    # Scores por eixo (0-100)
    desempenho_legislativo = Column(DECIMAL(5, 2), nullable=True)
    relevancia_social = Column(DECIMAL(5, 2), nullable=True)  # Média dos PARs
    responsabilidade_fiscal = Column(DECIMAL(5, 2), nullable=True)
    etica_legalidade = Column(DECIMAL(5, 2), nullable=True)
    
    # Score final ponderado (0-100)
    score_final = Column(DECIMAL(5, 2), nullable=False)
    
    # Estatísticas utilizadas no cálculo
    total_proposicoes = Column(Integer, default=0)
    props_analisadas = Column(Integer, default=0)
    props_triviais = Column(Integer, default=0)
    props_relevantes = Column(Integer, default=0)
    
    # Controle
    data_calculo = Column(DateTime, default=datetime.utcnow)
    versao_calculo = Column(String(20), default='1.0')
    
    # Relacionamentos
    deputado = relationship("Deputado", back_populates="score")
    
    def __repr__(self):
        return f"<ScoreDeputado(id={self.id}, dep_id={self.deputado_id}, score={self.score_final})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável."""
        return {
            'id': self.id,
            'deputado_id': self.deputado_id,
            'desempenho_legislativo': float(self.desempenho_legislativo) if self.desempenho_legislativo else None,
            'relevancia_social': float(self.relevancia_social) if self.relevancia_social else None,
            'responsabilidade_fiscal': float(self.responsabilidade_fiscal) if self.responsabilidade_fiscal else None,
            'etica_legalidade': float(self.etica_legalidade) if self.etica_legalidade else None,
            'score_final': float(self.score_final),
            'total_proposicoes': self.total_proposicoes,
            'props_analisadas': self.props_analisadas,
            'props_triviais': self.props_triviais,
            'props_relevantes': self.props_relevantes,
            'data_calculo': self.data_calculo.isoformat() if self.data_calculo else None,
            'versao_calculo': self.versao_calculo
        }


class LogProcessamento(Base):
    """
    Registra logs detalhados do processamento de análises.
    Permite auditoria e rastreabilidade completa.
    """
    __tablename__ = 'logs_processamento'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação
    tipo_processo = Column(String(50), nullable=False)  # 'resumo', 'filtro', 'par', 'score'
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id'), nullable=True)
    
    # Detalhes
    status = Column(String(20), nullable=False)  # 'sucesso', 'erro', 'pulado'
    mensagem = Column(Text, nullable=True)
    dados_entrada = Column(JSONB, nullable=True)
    dados_saida = Column(JSONB, nullable=True)
    
    # Controle
    data_inicio = Column(DateTime, default=datetime.utcnow)
    data_fim = Column(DateTime, nullable=True)
    duracao_segundos = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<LogProcessamento(id={self.id}, tipo={self.tipo_processo}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável."""
        return {
            'id': self.id,
            'tipo_processo': self.tipo_processo,
            'proposicao_id': self.proposicao_id,
            'deputado_id': self.deputado_id,
            'status': self.status,
            'mensagem': self.mensagem,
            'dados_entrada': self.dados_entrada,
            'dados_saida': self.dados_saida,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'duracao_segundos': self.duracao_segundos
        }


# Adicionar relacionamentos aos modelos existentes
Proposicao.analise = relationship("AnaliseProposicao", uselist=False, back_populates="proposicao")
Deputado.score = relationship("ScoreDeputado", uselist=False, back_populates="deputado")
