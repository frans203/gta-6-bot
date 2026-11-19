"""Agendamento local (Agendador de Tarefas do Windows) para plataformas sem agenda nativa (Instagram web).
O PC precisa estar ligado e com o usuario logado no horario."""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..config import config

PASTA = "\\JASON_GTAVI\\"


def _ps(script: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


def nome_tarefa(conta, plataforma: str, video: Path) -> str:
    # a conta padrão mantém o nome antigo (instagram_gta6_001)
    return f"{plataforma}_{video.stem}" if conta.padrao else f"{conta.id}_{plataforma}_{video.stem}"


def criar(conta, plataforma: str, video: Path, quando: datetime) -> str:
    nome = nome_tarefa(conta, plataforma, video)
    extra = "" if conta.padrao else f" --conta {conta.id}"
    args = f'"{config.raiz / "postar.py"}" enviar -p {plataforma} --video "{video}"{extra}'
    _ps(
        f"$a = New-ScheduledTaskAction -Execute '{sys.executable}' -Argument '{args}' -WorkingDirectory '{config.raiz}';"
        f"$t = New-ScheduledTaskTrigger -Once -At ([datetime]'{quando:%Y-%m-%dT%H:%M:%S}');"
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1);"
        f"Register-ScheduledTask -TaskName '{nome}' -TaskPath '{PASTA}' -Action $a -Trigger $t -Settings $s -Force | Out-Null"
    )
    return nome


def remover(nome: str) -> None:
    """Apaga a tarefa (se existir): o post agendado no PC não sai mais."""
    _ps(f"Unregister-ScheduledTask -TaskName '{nome}' -TaskPath '{PASTA}' -Confirm:$false -ErrorAction SilentlyContinue")


def listar() -> list[dict]:
    out = _ps(
        f"Get-ScheduledTask -TaskPath '{PASTA}' -ErrorAction SilentlyContinue | ForEach-Object {{"
        " $i = $_ | Get-ScheduledTaskInfo; '{0}|{1:yyyy-MM-ddTHH:mm}|{2}' -f $_.TaskName, $i.NextRunTime, $_.State }"
    )
    tarefas = []
    for linha in out.splitlines():
        if linha.count("|") == 2:
            nome, prox, estado = linha.split("|")
            tarefas.append({"nome": nome, "proxima": prox, "estado": estado})
    return tarefas
