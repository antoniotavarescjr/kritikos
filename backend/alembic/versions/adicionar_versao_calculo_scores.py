"""Adicionar versao_calculo na tabela scores_deputados

Revision ID: adicionar_versao_calculo_scores
Revises: 
Create Date: 2025-11-07 13:43:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'adicionar_versao_calculo_scores'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Adicionar coluna versao_calculo na tabela scores_deputados."""
    # Adicionar coluna versao_calculo
    op.add_column('scores_deputados', sa.Column('versao_calculo', sa.String(length=20), nullable=True, default='1.0'))
    
    # Atualizar registros existentes com versão padrão
    op.execute("UPDATE scores_deputados SET versao_calculo = '1.0' WHERE versao_calculo IS NULL")


def downgrade():
    """Remover coluna versao_calculo da tabela scores_deputados."""
    op.drop_column('scores_deputados', 'versao_calculo')
