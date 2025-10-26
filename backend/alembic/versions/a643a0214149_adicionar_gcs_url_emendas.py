"""adicionar_gcs_url_emendas

Revision ID: a643a0214149
Revises: adicionar_gcs_url_proposicoes
Create Date: 2025-10-18 20:52:21.181794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a643a0214149'
down_revision: Union[str, Sequence[str], None] = 'adicionar_gcs_url_proposicoes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar coluna gcs_url na tabela emendas_parlamentares
    op.add_column('emendas_parlamentares', sa.Column('gcs_url', sa.String(500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover coluna gcs_url
    op.drop_column('emendas_parlamentares', 'gcs_url')
