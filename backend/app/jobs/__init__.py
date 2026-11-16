"""Fila de jobs guardada no SQLite + worker que executa. Para criar um tipo novo de job:

    from app.jobs import tarefa

    @tarefa("meu_tipo", recurso=lambda p: "gpu")
    def meu_job(ctx, params) -> dict:
        ctx.progresso(0.5, "metade")
        return {"ok": True}

e importe o módulo em app/jobs/registro.py.
"""
from .fila import Contexto, cancelar, enfileirar, tarefa

__all__ = ["Contexto", "cancelar", "enfileirar", "tarefa"]
