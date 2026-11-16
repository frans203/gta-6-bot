"""Jobs, eventos em tempo real (SSE) e logs."""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from ...config import config
from ...db import sessao
from ...jobs import cancelar, enfileirar
from ...models import Job
from .. import schemas as S

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[S.JobOut])
def listar(status: str | None = None, tipo: str | None = None, limite: int = 100):
    with sessao() as s:
        q = select(Job).order_by(Job.id.desc()).limit(limite)
        if status:
            q = q.where(Job.status.in_(status.split(",")))
        if tipo:
            q = q.where(Job.tipo.in_(tipo.split(",")))
        return list(s.scalars(q))


@router.get("/jobs/{job_id}", response_model=S.JobDetalheOut)
def obter(job_id: int):
    with sessao() as s:
        j = s.get(Job, job_id)
        if j is None:
            raise HTTPException(404)
        return j


@router.post("/jobs/{job_id}/cancelar", response_model=S.JobOut)
def cancelar_job(job_id: int):
    try:
        return cancelar(job_id)
    except KeyError:
        raise HTTPException(404) from None


@router.post("/jobs/{job_id}/repetir", response_model=S.JobOut, status_code=202)
def repetir(job_id: int):
    with sessao() as s:
        j = s.get(Job, job_id)
        if j is None:
            raise HTTPException(404)
        tipo, params, titulo = j.tipo, j.params, j.titulo
    return enfileirar(tipo, params, titulo)


@router.get("/eventos")
async def eventos(request: Request):
    """Server-Sent Events: `job` (cada mudança de job) e `log` (linhas novas do logs/postar.log)."""
    log_path = config.logs / "postar.log"

    async def gerar():
        desde = datetime.now()
        vistos: dict[int, tuple] = {}
        pos = log_path.stat().st_size if log_path.exists() else 0
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            with sessao() as s:
                jobs = list(s.scalars(select(Job).where(Job.atualizado_em >= desde - timedelta(seconds=2))))
            for j in jobs:
                chave = (j.status, j.progresso, j.mensagem, j.atualizado_em)
                if vistos.get(j.id) != chave:
                    vistos[j.id] = chave
                    dados = S.JobOut.model_validate(j).model_dump(mode="json")
                    yield f"event: job\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
                desde = max(desde, j.atualizado_em)
            if log_path.exists() and log_path.stat().st_size > pos:
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    novas = f.read()
                    pos = f.tell()
                for linha in novas.splitlines():
                    if linha.strip():
                        yield f"event: log\ndata: {json.dumps(linha, ensure_ascii=False)}\n\n"
            yield ": ping\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(gerar(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/logs", response_model=list[str])
def logs(linhas: int = 300):
    p = config.logs / "postar.log"
    if not p.exists():
        return []
    with open(p, "rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - linhas * 300))
        texto = f.read().decode("utf-8", "replace")
    return texto.splitlines()[-linhas:]


@router.get("/prints", response_model=list[str])
def prints(limite: int = 60):
    """Prints de erro/sucesso das plataformas (mais recentes primeiro)."""
    arqs = sorted(config.logs.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in arqs[:limite]]


@router.get("/prints/{nome}", response_class=FileResponse)
def print_(nome: str):
    p = (config.logs / Path(nome).name)
    if p.suffix != ".png" or not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/png")
