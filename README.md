# 🌴 JASON_GTAVI_PIPELINE

Duas coisas num projeto só, controladas pela **interface web** ou pela CLI:

1. **Postagem**: posta/agenda vídeos no **TikTok**, **YouTube Shorts** e **Instagram Reels** controlando o
   Chrome (Playwright), com várias contas.
2. **Cortador**: pega lives da **Twitch/YouTube**, acha os melhores momentos **sem IA paga** (picos de áudio,
   partes mais assistidas, clipes da Twitch), identifica o streamer (ou você marca), monta o vertical num **modelo de corte** (padrão: jogo em cima + streamer embaixo), põe legenda
   palavra por palavra (Whisper local) e manda para a fila de postagem.

> Manual completo: **[TUTORIAL.md](TUTORIAL.md)** · Contexto para agentes: **[CLAUDE.md](CLAUDE.md)** ·
> Progresso: **[TODO.md](TODO.md)**

## Começo rápido

```powershell
python -m pip install -r backend/requirements.txt   # + Chrome, ffmpeg e Node.js 20+
copy .env.example .env                              # ajuste JASON_MIDIA (disco com espaço)
cd frontend; npm install; npm run build; cd ..      # uma vez (e depois de mudar o front)
python jason.py login                               # 1x: loga nas 3 redes e FECHA o Chrome
python jason.py web                                 # interface em http://127.0.0.1:8765
```

## Arquitetura

```
frontend/ (React + TS + Tailwind + shadcn/ui)  ──HTTP/SSE──►  backend/app/api (FastAPI)
                                                                     │ enfileira
                                                                     ▼
backend/app/jobs (fila no SQLite) ◄── worker (python jason.py worker; o "web" já sobe um)
        │
        ├─ servicos/   agenda, postagem, contas, pack ──► plataformas/{tiktok,youtube,instagram}.py
        └─ cortes/     fontes (yt-dlp/Twitch API) → detectores → webcam → layouts → legendas → render (ffmpeg)

dados/jason.db (SQLite + Alembic)   ·   midia/ ou JASON_MIDIA (VODs, cortes, modelos)   ·   logs/
```

- **Plugins**: plataformas (`plataformas/__init__.py`), layouts, estilos de legenda e detectores
  (`cortes/plugins.py`) são registros. Para criar um novo basta registrar uma função; a interface descobre
  sozinha por `GET /api/plugins`.
- **Jobs**: tudo que demora vira job (`@tarefa("nome", recurso=...)`). Jobs com o mesmo recurso
  (`navegador:<conta>`, `gpu`) rodam um por vez. Progresso e log ao vivo via SSE (`/api/eventos`).
- **API**: documentação interativa em `http://127.0.0.1:8765/docs`. Os tipos do front são gerados do
  OpenAPI (`cd frontend; npm run api:tipos`).

## Comandos (CLI)

| Comando | O que faz |
|---|---|
| `python jason.py web` | Interface web + worker |
| `python jason.py fila` | Tabela vídeo × plataforma |
| `python jason.py plano [--por-hora 3 --ate 00:00]` | O que seria agendado e quando (**não envia nada**) |
| `python jason.py agendar [-y] [--por-hora N --ate HH:MM]` | Agenda os pendentes |
| `python jason.py enviar -p tiktok,youtube [--video X] [--revisar]` | Posta agora |
| `python jason.py baixar --qtd 10` | Baixa do pack de GTA 6, limpa metadados, gera legenda |
| `python jason.py tarefas` | Agendamentos do Instagram no Agendador do Windows |
| `python jason.py login` | Abre o Chrome da conta para logar |
| `python jason.py exportar` | Exporta o histórico de posts para JSON em `logs/` |

Todos aceitam `--conta <id>` (padrão: a conta principal `gta6`). `postar.py` tem os mesmos comandos de
postagem sem visual e com `--json` (usado pelas tarefas do Windows).

## Desenvolvimento

```powershell
cd backend; python -m pytest; python -m ruff check app tests     # testes e lint do backend
cd frontend; npm run dev                                          # front com hot reload (porta 5173)
cd backend; alembic revision --autogenerate -m "o que mudou"      # mudou app/models.py? gere a migração
```

## ⚠️ Nunca versionar

`perfil-chrome/` e `midia/.../perfil-chrome` (sessões logadas), `dados/` (histórico da sua conta), `.env`,
`limpos/`, `baixados/`, `logs/`, `midia/`. O `pack_usados.json` **vai** pro git (os parceiros não repetem
clipes): `git pull` antes de baixar, commit depois.
