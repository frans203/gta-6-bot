"""Agendamento local (Agendador de Tarefas do Windows) para plataformas sem agenda nativa (Instagram web).
O PC precisa estar ligado e com o usuario logado no horario."""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .comum import RAIZ

PASTA = "\\JASON_GTAVI\\"


def _ps(script: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


def criar(plataforma: str, video: Path, quando: datetime) -> str:
    nome = f"{plataforma}_{video.stem}"
    args = f'"{RAIZ / "postar.py"}" enviar -p {plataforma} --video "{video}"'
    _ps(
        f"$a = New-ScheduledTaskAction -Execute '{sys.executable}' -Argument '{args}' -WorkingDirectory '{RAIZ}';"
        f"$t = New-ScheduledTaskTrigger -Once -At ([datetime]'{quando:%Y-%m-%dT%H:%M:%S}');"
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 1);"
        f"Register-ScheduledTask -TaskName '{nome}' -TaskPath '{PASTA}' -Action $a -Trigger $t -Settings $s -Force | Out-Null"
    )
    return nome


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
