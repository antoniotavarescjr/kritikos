"""merge_heads

Revision ID: 5b97b3c5d341
Revises: a643a0214149, fix_api_camara_id_str
Create Date: 2025-10-19 23:34:07.842154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b97b3c5d341'
down_revision: Union[str, Sequence[str], None] = ('a643a0214149', 'fix_api_camara_id_str')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
