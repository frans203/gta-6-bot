"""Registros de plugins do cortador. Cada plugin tem id, nome, descrição e é descoberto pela interface via
GET /api/plugins. Para criar um layout/estilo/detector novo basta registrar aqui (ou num módulo que use @registrar)."""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Plugin:
    id: str
    nome: str
    descricao: str
    funcao: Callable[..., Any] | None = None
    opcoes: dict[str, Any] = field(default_factory=dict)

    def info(self) -> dict:
        return {"id": self.id, "nome": self.nome, "descricao": self.descricao, "opcoes": self.opcoes}


class Registro:
    def __init__(self, tipo: str):
        self.tipo = tipo
        self.itens: dict[str, Plugin] = {}

    def registrar(self, id: str, nome: str, descricao: str = "", **opcoes):
        def deco(fn):
            self.itens[id] = Plugin(id, nome, descricao, fn, opcoes)
            return fn
        return deco

    def __getitem__(self, id: str) -> Plugin:
        if id not in self.itens:
            raise KeyError(f"{self.tipo} desconhecido: {id}")
        return self.itens[id]

    def __contains__(self, id: str) -> bool:
        return id in self.itens

    def listar(self) -> list[dict]:
        return [p.info() for p in self.itens.values()]


LAYOUTS = Registro("layout")
ESTILOS = Registro("estilo de legenda")
DETECTORES = Registro("detector")


def carregar():
    """Importa os módulos que registram plugins."""
    from . import detectores, layouts, legendas  # noqa: F401
