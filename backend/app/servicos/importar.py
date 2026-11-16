"""Primeira execução: cria a conta padrão e importa o postados.json antigo para o SQLite (com backup)."""
import json
import shutil
from datetime import datetime

from sqlalchemy import func, select

from ..config import config
from ..db import sessao
from ..models import Conta, Post
from . import historico
from .contas import PADRAO

POSTADOS = config.raiz / "postados.json"


def inicial():
    with sessao() as s:
        if s.scalar(select(func.count()).select_from(Conta)) == 0:
            s.add(Conta(id=PADRAO, nome="JASON GTA VI", idioma="pt", pasta="limpos", perfil="perfil-chrome",
                        plataformas=["tiktok", "youtube", "instagram"], padrao=True,
                        tags="#gta6 #gtavi #gta #rockstargames #vicecity #gta6trailer #gameplay #gamer #viral "
                             "#fyp #shorts #gaming"))
        ja_tem = s.scalar(select(func.count()).select_from(Post)) > 0
    if not ja_tem and POSTADOS.exists():
        importar_postados()


def importar_postados() -> int:
    config.logs.mkdir(exist_ok=True)
    backup = config.logs / f"postados_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    shutil.copy2(POSTADOS, backup)
    dados = json.loads(POSTADOS.read_text("utf-8-sig"))
    n = 0
    with sessao() as s:
        for video, plats in dados.items():
            for plataforma, info in plats.items():
                historico.gravar(s, PADRAO, video, plataforma, info)
                n += 1
    # o JSON vira só histórico: renomeia para ninguém editar achando que ainda vale
    POSTADOS.rename(POSTADOS.with_name("postados.importado.json"))
    return n
