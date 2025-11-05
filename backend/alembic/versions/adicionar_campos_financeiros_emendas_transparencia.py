"""Adicionar campos financeiros do Portal da Transparência

Revision ID: f1a2b3c4d5e6
Revises: e9e1f7bc1c91
Create Date: 2025-10-29 13:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e9e1f7bc1c91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos financeiros faltantes do Portal da Transparência
    op.add_column('emendas_parlamentares', sa.Column('valor_resto_inscrito', sa.Numeric(15, 2), nullable=True))
    op.add_column('emendas_parlamentares', sa.Column('valor_resto_cancelado', sa.Numeric(15, 2), nullable=True))
    op.add_column('emendas_parlamentares', sa.Column('valor_resto_pago', sa.Numeric(15, 2), nullable=True))
    
    # Adicionar campos de otimização com códigos da API
    op.add_column('emendas_parlamentares', sa.Column('codigo_funcao_api', sa.String(20), nullable=True))
    op.add_column('emendas_parlamentares', sa.Column('codigo_subfuncao_api', sa.String(20), nullable=True))
    
    # Adicionar campos de documentação
    op.add_column('emendas_parlamentares', sa.Column('documentos_url', sa.Text, nullable=True))
    op.add_column('emendas_parlamentares', sa.Column('quantidade_documentos', sa.Integer, default=0))
    
    # Adicionar índices para performance
    op.create_index(op.f('ix_emendas_codigo_funcao'), 'emendas_parlamentares', ['codigo_funcao_api'])
    op.create_index(op.f('ix_emendas_codigo_subfuncao'), 'emendas_parlamentares', ['codigo_subfuncao_api'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remover índices
    op.drop_index(op.f('ix_emendas_codigo_subfuncao'), table_name='emendas_parlamentares')
    op.drop_index(op.f('ix_emendas_codigo_funcao'), table_name='emendas_parlamentares')
    
    # Remover campos
    op.drop_column('emendas_parlamentares', 'quantidade_documentos')
    op.drop_column('emendas_parlamentares', 'documentos_url')
    op.drop_column('emendas_parlamentares', 'codigo_subfuncao_api')
    op.drop_column('emendas_parlamentares', 'codigo_funcao_api')
    op.drop_column('emendas_parlamentares', 'valor_resto_pago')
    op.drop_column('emendas_parlamentares', 'valor_resto_cancelado')
    op.drop_column('emendas_parlamentares', 'valor_resto_inscrito')
