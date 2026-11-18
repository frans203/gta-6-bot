"""editor de vídeo: edição livre por corte (trechos, layout, estilo do texto)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 10:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cortes") as b:
        b.add_column(sa.Column("edicao", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cortes") as b:
        b.drop_column("edicao")
