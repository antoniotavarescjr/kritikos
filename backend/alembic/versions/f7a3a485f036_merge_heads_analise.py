"""merge_heads_analise

Revision ID: f7a3a485f036
Revises: add_cols_fallback_votacoes, criar_frequencia, permitir_deputado_id_nulo, g1h2i3j4k5l
Create Date: 2025-11-02 21:01:19.832025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a3a485f036'
down_revision: Union[str, Sequence[str], None] = ('add_cols_fallback_votacoes', 'criar_frequencia', 'permitir_deputado_id_nulo', 'g1h2i3j4k5l')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
