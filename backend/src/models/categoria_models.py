"""
Modelos de dados para categorização de emendas
Sistema inteligente de classificação por categoria de investimento
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class CategoriaEmenda(Base):
    """
    Tabela de categorias para classificação inteligente de emendas
    """
    __tablename__ = 'categorias_emendas'
    
    id = Column(Integer, primary_key=True, index=True)
    nome_categoria = Column(String(100), unique=True, nullable=False, index=True)
    descricao = Column(Text)
    tipo_categoria = Column(String(50), nullable=False, index=True)  # SAUDE, EDUCACAO, INFRAESTRUTURA, etc.
    cor_visualizacao = Column(String(7), default='#007bff')  # Cor para gráficos
    
    # Metadados
    created_at = Column(String(50), server_default='now()')
    
    def __repr__(self):
        return f"<CategoriaEmenda(id={self.id}, nome='{self.nome_categoria}', tipo='{self.tipo_categoria}')>"

class DetalheCategoriaEmenda(Base):
    """
    Detalhamento das categorias com exemplos e regras
    """
    __tablename__ = 'detalhes_categorias_emendas'
    
    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey('categorias_emendas.id'), nullable=False)
    funcao = Column(String(255), nullable=False)
    subfuncao = Column(String(255))
    palavras_chave = Column(Text)  # Palavras-chave para classificação automática
    exemplos = Column(Text)  # Exemplos concretos
    prioridade = Column(Integer, default=1)  # Prioridade na classificação
    
    categoria = relationship("CategoriaEmenda", backref="detalhes")
    
    def __repr__(self):
        return f"<DetalheCategoria(categoria='{self.categoria.nome_categoria}', funcao='{self.funcao}')>"

# Constantes de categorias
CATEGORIA_SAUDE = 1
CATEGORIA_EDUCACAO = 2
CATEGORIA_INFRAESTRUTURA = 3
CATEGORIA_SEGURANCA = 4
CATEGORIA_DESENVOLVIMENTO_SOCIAL = 5
CATEGORIA_CIENCIA_TECNOLOGIA = 6
CATEGORIA_CULTURA_ESPORTE = 7
CATEGORIA_MEIO_AMBIENTE = 8
CATEGORIA_ECONOMIA = 9
CATEGORIA_ADMINISTRACAO = 10

# Mapeamento de categorias
CATEGORIAS = {
    CATEGORIA_SAUDE: {
        'nome': 'Saúde e Bem-Estar',
        'cor': '#dc3545',
        'tipo': 'SAUDE'
    },
    CATEGORIA_EDUCACAO: {
        'nome': 'Educação e Cultura',
        'cor': '#28a745',
        'tipo': 'EDUCACAO'
    },
    CATEGORIA_INFRAESTRUTURA: {
        'nome': 'Infraestrutura e Urbanismo',
        'cor': '#ffc107',
        'tipo': 'INFRAESTRUTURA'
    },
    CATEGORIA_SEGURANCA: {
        'nome': 'Segurança e Defesa',
        'cor': '#6f42c1',
        'tipo': 'SEGURANCA'
    },
    CATEGORIA_DESENVOLVIMENTO_SOCIAL: {
        'nome': 'Desenvolvimento Social',
        'cor': '#e83e8c',
        'tipo': 'DESENVOLVIMENTO_SOCIAL'
    },
    CATEGORIA_CIENCIA_TECNOLOGIA: {
        'nome': 'Ciência e Tecnologia',
        'cor': '#17a2b8',
        'tipo': 'CIENCIA_TECNOLOGIA'
    },
    CATEGORIA_CULTURA_ESPORTE: {
        'nome': 'Cultura e Esporte',
        'cor': '#6610f2',
        'tipo': 'CULTURA_ESPORTE'
    },
    CATEGORIA_MEIO_AMBIENTE: {
        'nome': 'Meio Ambiente',
        'cor': '#198754',
        'tipo': 'MEIO_AMBIENTE'
    },
    CATEGORIA_ECONOMIA: {
        'nome': 'Economia e Trabalho',
        'cor': '#fd7e14',
        'tipo': 'ECONOMIA'
    },
    CATEGORIA_ADMINISTRACAO: {
        'nome': 'Administração Pública',
        'cor': '#6c757d',
        'tipo': 'ADMINISTRACAO'
    }
}
