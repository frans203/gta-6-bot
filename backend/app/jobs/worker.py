"""Worker: processo que executa os jobs da fila. Roda cada job numa thread; jobs com o mesmo recurso esperam.
    python jason.py worker
"""
import os
import signal
import sys
import threading
import time
import traceback
from datetime import datetime

from sqlalchemy import select, update

from ..config import config
from ..db import preparar, sessao
from ..models import Job
from ..plataformas import comum
from . import registro  # noqa: F401  (registra os tipos de job)
from .fila import TIPOS, Cancelado, Contexto, reivindicar

MAX_PARALELO = 4
_parar = threading.Event()


def _pid_vivo(pid: int | None) -> bool:
    if not pid:
        return False
    if sys.platform != "win32":
        import os
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(codigo))
    ctypes.windll.kernel32.CloseHandle(h)
    return codigo.value == 259  # STILL_ACTIVE


def recuperar_orfaos():
    """Jobs 'rodando' de um worker que morreu viram erro (podem ser repetidos pela interface)."""
    with sessao() as s:
        for j in s.scalars(select(Job).where(Job.status.in_(("rodando", "cancelando")))):
            if j.pid != os.getpid() and not _pid_vivo(j.pid):
                j.status = "erro" if j.status == "rodando" else "cancelado"
                j.erro = j.erro or "o worker parou no meio deste job (reinício do PC ou do worker)"
                j.terminado_em = datetime.now()


def _executar(job: Job, fim: callable):
    ctx = Contexto(job.id)
    try:
        resultado = TIPOS[job.tipo].funcao(ctx, job.params or {})
        campos = {"status": "ok", "progresso": 1.0, "mensagem": "concluído", "resultado": resultado}
    except Cancelado:
        campos = {"status": "cancelado", "mensagem": "cancelado"}
    except Exception as e:
        tb = traceback.format_exc()
        ctx.log(tb)
        campos = {"status": "erro", "erro": str(e)[:2000] or type(e).__name__, "mensagem": "erro"}
    with sessao() as s:
        s.execute(update(Job).where(Job.id == job.id)
                  .values(terminado_em=datetime.now(), atualizado_em=datetime.now(), **campos))
    fim(job)


def rodar():
    preparar()
    comum.JSON_MODE = True
    recuperar_orfaos()
    comum.log(f"worker iniciado (pid {os.getpid()})", "worker")
    ocupados: dict[int, str | None] = {}
    trava = threading.Lock()

    def fim(job):
        with trava:
            ocupados.pop(job.id, None)

    signal.signal(signal.SIGINT, lambda *_: _parar.set())
    batimento = config.logs / "worker.alive"
    ultimo_batimento = 0.0
    while not _parar.is_set():
        if time.time() - ultimo_batimento > 5:
            batimento.write_text(str(os.getpid()))
            ultimo_batimento = time.time()
        with trava:
            livres = MAX_PARALELO - len(ocupados)
            em_uso = {r for r in ocupados.values() if r}
        if livres > 0:
            job = reivindicar(em_uso, os.getpid())
            if job:
                with trava:
                    ocupados[job.id] = job.recurso
                threading.Thread(target=_executar, args=(job, fim), daemon=True, name=f"job-{job.id}").start()
                continue
        _parar.wait(1.0)
    comum.log("worker parado", "worker")
    return 0
