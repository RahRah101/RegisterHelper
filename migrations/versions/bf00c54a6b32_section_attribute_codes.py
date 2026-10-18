"""section attribute codes

Revision ID: bf00c54a6b32
Revises: 6fc4b886afff
Create Date: 2026-10-18 03:31:04.855503

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bf00c54a6b32"
down_revision: str | Sequence[str] | None = "6fc4b886afff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("sections", schema=None) as batch_op:
        # server_default so existing rows get [] (SQLite refuses NOT NULL without one)
        batch_op.add_column(
            sa.Column("attribute_codes", sa.JSON(), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("sections", schema=None) as batch_op:
        batch_op.drop_column("attribute_codes")
