"""aumentar_tamanho_campos_uf_emendas

Revision ID: a5adc79af875
Revises: criar_tabelas_analise_scores
Create Date: 2025-11-04 21:12:43.922427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5adc79af875'
down_revision: Union[str, Sequence[str], None] = 'criar_tabelas_analise_scores'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
