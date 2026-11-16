"""modelos de corte + enquadramento por corte

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14 21:30:00

- tabela `modelos` (layout + posições + estilo), com os modelos iniciais;
- streamers: layout/estilo_legenda -> modelo_id;
- cortes: layout -> modelo_id; novos campos webcam e jogo (enquadramento do corte).
"""
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (nome, layout, estilo, params, padrao)
MODELOS = [
    ("Jogo em cima + streamer embaixo", "jogo_em_cima", "destaque",
     {"divisao": 0.55, "legenda_y": 0.55, "gancho_y": 0.05, "barra": True, "credito": True}, True),
    ("Webcam em cima + jogo embaixo", "webcam_em_cima", "destaque",
     {"divisao": 0.36, "legenda_y": 0.36, "gancho_y": 0.05, "barra": True, "credito": True}, False),
    ("Vídeo inteiro + fundo desfocado", "tela_cheia", "destaque",
     {"legenda_y": 0.72, "gancho_y": 0.12, "barra": True, "credito": True}, False),
    ("Só o jogo (recorte central)", "so_gameplay", "destaque",
     {"legenda_y": 0.68, "gancho_y": 0.08, "barra": True, "credito": True}, False),
]
# layout antigo -> modelo novo (o antigo "webcam_em_cima" vira o novo padrão, jogo em cima)
DE_PARA = {"webcam_em_cima": "jogo_em_cima", "tela_cheia": "tela_cheia", "so_gameplay": "so_gameplay"}


def upgrade() -> None:
    modelos = op.create_table(
        "modelos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("layout", sa.String(length=40), nullable=False),
        sa.Column("estilo_legenda", sa.String(length=40), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("padrao", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    agora = datetime.now().replace(microsecond=0)
    op.bulk_insert(modelos, [
        {"id": i, "nome": n, "layout": lay, "estilo_legenda": e, "params": p, "padrao": pad, "criado_em": agora}
        for i, (n, lay, e, p, pad) in enumerate(MODELOS, start=1)
    ])
    id_por_layout = {lay: i for i, (_, lay, *_r) in enumerate(MODELOS, start=1)}

    with op.batch_alter_table("streamers") as b:
        b.add_column(sa.Column("modelo_id", sa.Integer(), nullable=True))
        b.create_foreign_key("fk_streamers_modelo", "modelos", ["modelo_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("cortes") as b:
        b.add_column(sa.Column("modelo_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("webcam", sa.JSON(), nullable=True))
        b.add_column(sa.Column("jogo", sa.JSON(), nullable=True))
        b.create_foreign_key("fk_cortes_modelo", "modelos", ["modelo_id"], ["id"], ondelete="SET NULL")

    con = op.get_bind()
    for antigo, novo in DE_PARA.items():
        con.execute(sa.text("UPDATE streamers SET modelo_id = :m WHERE layout = :l"),
                    {"m": id_por_layout[novo], "l": antigo})
        con.execute(sa.text("UPDATE cortes SET modelo_id = :m WHERE layout = :l"),
                    {"m": id_por_layout[novo], "l": antigo})

    with op.batch_alter_table("streamers") as b:
        b.drop_column("layout")
        b.drop_column("estilo_legenda")
    with op.batch_alter_table("cortes") as b:
        b.drop_column("layout")


def downgrade() -> None:
    with op.batch_alter_table("cortes") as b:
        b.add_column(sa.Column("layout", sa.String(length=40), nullable=True))
        b.drop_constraint("fk_cortes_modelo", type_="foreignkey")
        b.drop_column("jogo")
        b.drop_column("webcam")
        b.drop_column("modelo_id")
    with op.batch_alter_table("streamers") as b:
        b.add_column(sa.Column("layout", sa.String(length=40), nullable=False, server_default="webcam_em_cima"))
        b.add_column(sa.Column("estilo_legenda", sa.String(length=40), nullable=False, server_default="destaque"))
        b.drop_constraint("fk_streamers_modelo", type_="foreignkey")
        b.drop_column("modelo_id")
    op.drop_table("modelos")
