"""Adicionar coluna gcs_url na tabela proposicoes

Revision ID: adicionar_gcs_url_proposicoes
Revises: e9e1f7bc1c91
Create Date: 2025-10-17 14:23:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'adicionar_gcs_url_proposicoes'
down_revision = 'e9e1f7bc1c91'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna gcs_url na tabela proposicoes
    op.add_column('proposicoes', sa.Column('gcs_url', sa.String(), nullable=True))


def downgrade():
    # Remover coluna gcs_url
    op.drop_column('proposicoes', 'gcs_url')
