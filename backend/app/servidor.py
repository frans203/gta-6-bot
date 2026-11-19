"""`python jason.py web`: sobe o worker (processo separado) + a API/front num comando só."""
import os
import subprocess
import sys
import threading
import webbrowser

from .config import config


def rodar_web(abrir: bool = True) -> int:
    import uvicorn

    # JASON_PAI: se este processo morrer sem o finally (fechado à força), o worker percebe e sai sozinho
    worker = subprocess.Popen([sys.executable, str(config.raiz / "jason.py"), "worker"], cwd=config.raiz,
                              env={**os.environ, "JASON_PAI": str(os.getpid())})
    url = f"http://{config.host}:{config.porta}"
    print(f"JASON web em {url}  (docs da API: {url}/docs)  ·  Ctrl+C para sair", flush=True)
    if abrir:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    try:
        uvicorn.run("app.api.main:app", host=config.host, port=config.porta, log_level="warning")
    finally:
        worker.terminate()
    return 0
