"""Saúde e informações do sistema."""
import shutil
import subprocess
from datetime import datetime, timedelta
from functools import lru_cache

from fastapi import APIRouter
from sqlalchemy import func, select

from ... import __version__
from ...config import config
from ...db import sessao
from ...models import Job
from .. import schemas as S

router = APIRouter(tags=["sistema"])


@lru_cache
def _gpu() -> str | None:
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                           text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def _worker_ativo() -> bool:
    """O worker grava um 'batimento' em logs/worker.alive a cada poucos segundos."""
    p = config.logs / "worker.alive"
    return p.exists() and datetime.fromtimestamp(p.stat().st_mtime) > datetime.now() - timedelta(seconds=20)


@router.get("/sistema", response_model=S.SistemaOut)
def sistema():
    discos = {}
    for nome, p in (("projeto", config.raiz), ("midia", config.midia)):
        try:
            discos[nome] = round(shutil.disk_usage(p if p.exists() else p.anchor).free / 1e9, 1)
        except OSError:
            pass
    return {"versao": __version__, "agora": datetime.now(), "midia": str(config.midia), "disco_livre_gb": discos,
            "worker_ativo": _worker_ativo(), "gpu": _gpu(),
            "twitch_api": bool(config.twitch_client_id and config.twitch_client_secret),
            "whisper_modelo": config.whisper_modelo}


@router.get("/sistema/resumo")
def resumo():
    """Contagem de jobs por status (para o painel)."""
    with sessao() as s:
        return dict(s.execute(select(Job.status, func.count()).group_by(Job.status)).all())
