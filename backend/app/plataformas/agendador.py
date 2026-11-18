"""Agendamento local para plataformas sem agenda nativa (Instagram web): o computador posta sozinho no horário.
Windows: Agendador de Tarefas (tarefas_windows). macOS: launchd (tarefas_mac). O computador precisa estar ligado
(ou acordar) e com o usuário logado no horário."""
import sys

if sys.platform == "win32":
    from .tarefas_windows import criar, listar, nome_tarefa, remover

    NOME_SISTEMA = "Agendador do Windows"
elif sys.platform == "darwin":
    from .tarefas_mac import criar, listar, nome_tarefa, remover

    NOME_SISTEMA = "launchd do macOS"
else:
    from .tarefas_windows import nome_tarefa

    NOME_SISTEMA = "indisponível neste sistema"

    def criar(conta, plataforma, video, quando):
        raise RuntimeError("agendar o Instagram no PC só funciona no Windows e no macOS; poste na hora")

    def listar() -> list[dict]:
        return []

    def remover(nome: str) -> None:
        pass

__all__ = ["NOME_SISTEMA", "criar", "listar", "nome_tarefa", "remover"]
