"""criar tabela blocos_partidarios

Revision ID: criar_tabela_blocos_partidarios
Revises: ff0d9e1674b7
Create Date: 2025-10-25 01:39:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'criar_tabela_blocos_partidarios'
down_revision = 'ff0d9e1674b7'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela de blocos partidários
    op.create_table('blocos_partidarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(200), nullable=False),
        sa.Column('sigla', sa.String(20), nullable=True),
        sa.Column('data_criacao', sa.Date(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('blocos_partidarios')
