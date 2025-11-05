"""Remover campo categoria_id da tabela emendas_parlamentares

Revision ID: g1h2i3j4k5l
Revises: f1a2b3c4d5e6
Create Date: 2025-10-29 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove campo categoria_id que não existe na tabela real."""
    # Remover campo categoria_id se existir
    try:
        op.drop_index('fk_emendas_parlamentares_categoria_id', table_name='emendas_parlamentares')
    except:
        pass
    
    try:
        op.drop_column('emendas_parlamentares', 'categoria_id')
    except:
        pass


def downgrade() -> None:
    """Recria campo categoria_id."""
    # Recriar campo categoria_id
    op.add_column('emendas_parlamentares', sa.Column('categoria_id', sa.Integer, nullable=True))
    
    # Recriar índice
    op.create_foreign_key(
        'fk_emendas_parlamentares_categoria_id', 'emendas_parlamentares', 'categorias_emendas', 
        ['categoria_id'], ['id']
    )
