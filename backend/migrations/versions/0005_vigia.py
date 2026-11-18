"""vigia de clipes: configuração e estado por streamer

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 12:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("streamers") as b:
        b.add_column(sa.Column("vigia", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("streamers") as b:
        b.drop_column("vigia")
