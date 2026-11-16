"""App FastAPI. Documentação interativa em http://127.0.0.1:8765/docs"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .. import __version__
from ..db import preparar
from ..plataformas import comum
from .rotas import cortador, jobs, postagem, sistema

FRONT = Path(__file__).resolve().parents[3] / "frontend" / "dist"


@asynccontextmanager
async def ciclo(_app):
    comum.JSON_MODE = True
    preparar()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JASON_GTAVI_PIPELINE", version=__version__, lifespan=ciclo,
                  description="API local: postagem, agenda, jobs e cortador de lives.")
    # o front em desenvolvimento (vite, porta 5173) chama a API direto
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["*"], allow_headers=["*"])
    for r in (postagem.router, jobs.router, cortador.router, sistema.router):
        app.include_router(r, prefix="/api")

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        """Serve o front compilado (frontend/dist); qualquer rota desconhecida cai no index.html."""
        if caminho.startswith("api/"):
            raise HTTPException(404)
        if not FRONT.exists():
            return {"erro": "front não compilado: cd frontend; npm install; npm run build"}
        alvo = (FRONT / caminho).resolve()
        if caminho and alvo.is_file() and FRONT.resolve() in alvo.parents:
            return FileResponse(alvo)
        return FileResponse(FRONT / "index.html")

    return app


app = create_app()
