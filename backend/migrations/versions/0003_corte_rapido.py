"""corte rápido: idioma da legenda, imagem de fundo e dados do enquadramento por corte; modelo com fundo

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14 22:00:00
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NOME_MODELO = "Imagem de fundo + vídeo + streamer embaixo"


def upgrade() -> None:
    with op.batch_alter_table("cortes") as b:
        b.add_column(sa.Column("idioma_legenda", sa.String(length=5), nullable=True))
        b.add_column(sa.Column("fundo", sa.String(length=200), nullable=True))
        b.add_column(sa.Column("extra", sa.JSON(), nullable=False, server_default="{}"))
    modelos = sa.table("modelos", sa.column("nome"), sa.column("layout"), sa.column("estilo_legenda"),
                       sa.column("params", sa.JSON()), sa.column("padrao"), sa.column("criado_em"))
    op.bulk_insert(modelos, [{
        "nome": NOME_MODELO, "layout": "fundo_imagem", "estilo_legenda": "destaque",
        "params": {"divisao": 0.62, "topo": None, "legenda_y": None, "gancho_y": None, "barra": True, "credito": True},
        "padrao": False, "criado_em": datetime.now().replace(microsecond=0)}])


def downgrade() -> None:
    op.execute(sa.text("UPDATE streamers SET modelo_id = NULL WHERE modelo_id IN "
                       "(SELECT id FROM modelos WHERE layout = 'fundo_imagem')"))
    op.execute(sa.text("UPDATE cortes SET modelo_id = NULL WHERE modelo_id IN "
                       "(SELECT id FROM modelos WHERE layout = 'fundo_imagem')"))
    op.execute(sa.text("DELETE FROM modelos WHERE layout = 'fundo_imagem'"))
    with op.batch_alter_table("cortes") as b:
        b.drop_column("extra")
        b.drop_column("fundo")
        b.drop_column("idioma_legenda")
