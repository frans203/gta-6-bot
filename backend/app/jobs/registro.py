"""Importa todos os módulos que definem tipos de job (cada um usa o decorador @tarefa)."""
from ..cortes import jobs as jobs_cortes  # noqa: F401
from . import jobs_postagem  # noqa: F401
