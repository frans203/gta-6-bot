"""Agendamento local no macOS com o launchd (equivalente ao Agendador de Tarefas do Windows).
Cada envio vira um LaunchAgent em ~/Library/LaunchAgents/app.jason.<nome>.plist que roda
`postar.py enviar -p <plataforma> --video <arquivo>` no horário. Se o Mac estiver dormindo, roda quando acordar.
Depois de rodar, o próprio agente se apaga (o launchd repetiria todo ano na mesma data)."""
import os
import plistlib
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..config import config
from .tarefas_windows import nome_tarefa

PREFIXO = "app.jason."
PASTA = Path.home() / "Library" / "LaunchAgents"


def _dominio() -> str:
    return f"gui/{os.getuid()}"


def criar(conta, plataforma: str, video: Path, quando: datetime) -> str:
    nome = nome_tarefa(conta, plataforma, video)
    rotulo = PREFIXO + nome
    plist = PASTA / f"{rotulo}.plist"
    cmd = [sys.executable, str(config.raiz / "postar.py"), "enviar", "-p", plataforma, "--video", str(video)]
    if not conta.padrao:
        cmd += ["--conta", conta.id]
    # roda uma vez: apaga o próprio plist e se descarrega no fim
    script = f"{shlex.join(cmd)}; rm -f {shlex.quote(str(plist))}; launchctl bootout {_dominio()}/{rotulo}"
    config.logs.mkdir(parents=True, exist_ok=True)
    PASTA.mkdir(parents=True, exist_ok=True)
    with open(plist, "wb") as f:
        plistlib.dump({
            "Label": rotulo,
            "ProgramArguments": ["/bin/sh", "-c", script],
            "WorkingDirectory": str(config.raiz),
            "StartCalendarInterval": {"Month": quando.month, "Day": quando.day, "Hour": quando.hour,
                                      "Minute": quando.minute},
            "StandardOutPath": str(config.logs / "agendados_mac.log"),
            "StandardErrorPath": str(config.logs / "agendados_mac.log"),
        }, f)
    subprocess.run(["launchctl", "bootout", f"{_dominio()}/{rotulo}"], capture_output=True)  # se já existia
    r = subprocess.run(["launchctl", "bootstrap", _dominio(), str(plist)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"launchctl: {r.stderr.strip() or r.stdout.strip()}")
    return nome


def remover(nome: str) -> None:
    """Descarrega e apaga o LaunchAgent (se existir): o post agendado no Mac não sai mais."""
    rotulo = PREFIXO + nome
    subprocess.run(["launchctl", "bootout", f"{_dominio()}/{rotulo}"], capture_output=True)
    (PASTA / f"{rotulo}.plist").unlink(missing_ok=True)


def listar() -> list[dict]:
    tarefas = []
    agora = datetime.now()
    for plist in sorted(PASTA.glob(f"{PREFIXO}*.plist")):
        try:
            with open(plist, "rb") as f:
                d = plistlib.load(f)
            c = d["StartCalendarInterval"]
            quando = datetime(agora.year, c["Month"], c["Day"], c["Hour"], c["Minute"])
            if quando < agora:  # já passou neste ano: ou rodou e vai se apagar, ou o Mac estava desligado
                estado = "Atrasado"
            else:
                estado = "Pronto"
            tarefas.append({"nome": d["Label"][len(PREFIXO):], "proxima": quando.isoformat(timespec="minutes"),
                            "estado": estado})
        except Exception:
            continue
    return tarefas
