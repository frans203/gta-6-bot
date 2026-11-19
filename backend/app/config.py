"""Configuração central. Valores podem ser trocados por variáveis JASON_* ou pelo arquivo .env na raiz."""
import sys
from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]

if sys.platform == "darwin":
    CHROME_PADRAO = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
else:
    CHROME_PADRAO = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JASON_", env_file=RAIZ / ".env", extra="ignore")

    raiz: Path = RAIZ
    dados: Path = RAIZ / "dados"          # banco SQLite
    logs: Path = RAIZ / "logs"
    midia: Path = RAIZ / "midia"          # VODs, cortes, perfis de contas novas (pode ficar em outro disco)
    chrome: Path = CHROME_PADRAO
    host: str = "127.0.0.1"
    porta: int = 8765

    whisper_modelo: str = "small"         # tiny | base | small | medium | large-v3
    whisper_dispositivo: str = "auto"     # auto | cuda | cpu
    whisper_modelo_analise: str = "small" # achar destaques (small na GPU: ~70x o tempo real); legenda = whisper_modelo
    fala_max_h: float = 4.0               # acima disso (trecho analisado), o detector da fala é pulado (demora)

    # API oficial da Twitch (grátis): crie um app em https://dev.twitch.tv/console/apps
    twitch_client_id: str = ""
    twitch_client_secret: str = ""

    @cached_property
    def banco(self) -> Path:
        return self.dados / "jason.db"

    @cached_property
    def modelos(self) -> Path:
        return self.midia / "modelos"

    def caminho(self, p: str | Path) -> Path:
        """Caminho relativo à raiz do projeto (ou absoluto, se já for)."""
        p = Path(p)
        return p if p.is_absolute() else self.raiz / p


config = Config()
