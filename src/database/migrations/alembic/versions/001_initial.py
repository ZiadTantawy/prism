"""Initial revision; creates alembic_version only.

Revision ID: 001_initial
Revises:
Create Date: Initial
"""
from typing import Sequence, Union

from alembic import op


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op; bootstrap revision."""
    pass


def downgrade() -> None:
    """No-op; bootstrap revision."""
    pass
