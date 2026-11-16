"""Fila de jobs no SQLite: enfileirar, reivindicar, atualizar, cancelar. Sem Redis/Celery: o worker é um processo
simples que lê a tabela `jobs`. Jobs com o mesmo `recurso` (ex.: navegador:gta6, gpu) rodam um de cada vez."""
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, update

from ..db import sessao
from ..models import Job

LOG_MAX = 20_000  # caracteres guardados do log de cada job


@dataclass
class TipoJob:
    nome: str
    funcao: Callable[["Contexto", dict], dict | None]
    recurso: Callable[[dict], str | None]


TIPOS: dict[str, TipoJob] = {}


def tarefa(nome: str, recurso: Callable[[dict], str | None] | str | None = None):
    """Decorador que registra uma função como tipo de job."""
    def deco(fn):
        rec = recurso if callable(recurso) else (lambda _p, r=recurso: r)
        TIPOS[nome] = TipoJob(nome, fn, rec)
        return fn
    return deco


def enfileirar(tipo: str, params: dict | None = None, titulo: str = "") -> Job:
    from . import registro  # noqa: F401  (garante que os tipos estão registrados)
    if tipo not in TIPOS:
        raise KeyError(f"tipo de job desconhecido: {tipo}")
    params = params or {}
    with sessao() as s:
        j = Job(tipo=tipo, params=params, titulo=titulo or tipo, recurso=TIPOS[tipo].recurso(params),
                status="fila", mensagem="na fila")
        s.add(j)
        s.flush()
        return j


def cancelar(job_id: int) -> Job:
    with sessao() as s:
        j = s.get(Job, job_id)
        if j is None:
            raise KeyError(job_id)
        if j.status == "fila":
            j.status, j.terminado_em, j.mensagem = "cancelado", datetime.now(), "cancelado antes de começar"
        elif j.status == "rodando":
            j.status, j.mensagem = "cancelando", "cancelando no próximo passo seguro..."
        return j


def reivindicar(ocupados: set[str], pid: int) -> Job | None:
    """Pega o job mais antigo da fila cujo recurso está livre (atômico: só um worker ganha)."""
    with sessao() as s:
        for j in s.scalars(select(Job).where(Job.status == "fila").order_by(Job.id)):
            if j.recurso and j.recurso in ocupados:
                continue
            r = s.execute(update(Job).where(Job.id == j.id, Job.status == "fila")
                          .values(status="rodando", iniciado_em=datetime.now(), pid=pid, mensagem="começando"))
            if r.rowcount:
                s.flush()
                s.refresh(j)
                return j
    return None


class Cancelado(Exception):
    pass


class Contexto:
    """O que um job recebe para avisar progresso, escrever log e saber se foi cancelado."""

    def __init__(self, job_id: int):
        self.job_id = job_id
        self._ultimo_check = 0.0
        self._cancelado = False
        self._ultima_msg: str | None = None
        self._ultimo_envio = 0.0

    def _set(self, **campos: Any):
        with sessao() as s:
            s.execute(update(Job).where(Job.id == self.job_id).values(atualizado_em=datetime.now(), **campos))

    def progresso(self, fracao: float | None = None, mensagem: str | None = None):
        campos: dict[str, Any] = {}
        if fracao is not None:
            campos["progresso"] = max(0.0, min(1.0, fracao))
        nova = mensagem is not None and mensagem != self._ultima_msg
        if nova:
            campos["mensagem"] = mensagem[:500]
            self._ultima_msg = mensagem
            self.log(mensagem)
        # só a barra mudou: no máximo 2 gravações por segundo (o ffmpeg avisa várias vezes por segundo)
        if campos and (nova or time.time() - self._ultimo_envio > 0.5 or fracao in (0.0, 1.0)):
            self._ultimo_envio = time.time()
            self._set(**campos)

    def log(self, msg: str):
        linha = f"[{datetime.now():%H:%M:%S}] {msg}\n"
        with sessao() as s:
            j = s.get(Job, self.job_id)
            j.log = ((j.log or "") + linha)[-LOG_MAX:]

    @property
    def cancelado(self) -> bool:
        if not self._cancelado and time.time() - self._ultimo_check > 1.5:
            self._ultimo_check = time.time()
            with sessao() as s:
                self._cancelado = s.scalar(select(Job.status).where(Job.id == self.job_id)) == "cancelando"
        return self._cancelado

    def checar(self):
        """Chame entre passos: levanta Cancelado se o usuário pediu para parar."""
        if self.cancelado:
            raise Cancelado("cancelado pelo usuário")
