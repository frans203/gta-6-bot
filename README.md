# 🌴 JASON_GTAVI_PIPELINE

Duas ferramentas num projeto só, controladas pela **interface web** (React) ou pela **CLI**:

1. **Postagem**: posta e agenda vídeos no **TikTok**, **YouTube Shorts** e **Instagram Reels**. Ela controla o
   Chrome de verdade (Playwright), com várias contas, e cada conta tem o próprio perfil do Chrome e a própria pasta
   de vídeos.
2. **Cortador**: transforma lives da **Twitch/YouTube** em cortes verticais 1080×1920 **sem IA paga**. Ele:
   - acha os momentos bons por picos de áudio, heatmap do YouTube e clipes da Twitch;
   - detecta a webcam do streamer (OpenCV);
   - monta o layout com ffmpeg;
   - legenda palavra por palavra com Whisper local (com tradução local opcional);
   - tem um editor de vídeo no navegador;
   - tem um **vigia** que transforma clipes novos da Twitch em cortes sozinho.

> 📘 Manual de uso: **[TUTORIAL.md](TUTORIAL.md)** (Windows) · **[TUTORIAL-MAC.md](TUTORIAL-MAC.md)** (Mac) ·
> 🤖 Contexto para agentes e pegadinhas: **[CLAUDE.md](CLAUDE.md)** · ✅ Progresso: **[TODO.md](TODO.md)**

---

## Sumário

- [Instalação](#instalação) (Mac e Windows)
- [Configuração (.env)](#configuração-env)
- [O que a ferramenta faz](#o-que-a-ferramenta-faz) (tela por tela)
- [CLI](#cli)
- [Arquitetura](#arquitetura)
- [API](#api)
- [Estendendo](#estendendo) (rede nova, layout, detector, job)
- [Desenvolvimento](#desenvolvimento) (testes, migrações, front)
- [Regras do projeto](#regras-do-projeto-leia-antes-de-mexer)
- [Pegadinhas](#pegadinhas)

---

## Instalação

Precisa de: **Python 3.11+**, **Node 20+**, **ffmpeg**, **git** e **Google Chrome** instalado (o Playwright usa o
seu Chrome, não precisa de `playwright install`).

### macOS

```bash
brew install python@3.12 ffmpeg node git
brew install --cask google-chrome            # se ainda não tiver (precisa estar em /Applications)

git clone https://github.com/frans203/gta-6-bot.git ~/gta6 && cd ~/gta6
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cp .env.example .env                          # APAGUE a linha JASON_MIDIA=E:\... (é do Windows)
(cd frontend && npm install && npm run build)

python jason.py login                         # 1x: loga nas 3 redes no Chrome que abrir e FECHA ele
python jason.py web                           # http://127.0.0.1:8765 (interface + worker)
```

### Windows (PowerShell)

```powershell
git clone https://github.com/frans203/gta-6-bot.git gta6; cd gta6
python -m pip install -r backend/requirements.txt
copy .env.example .env                        # ajuste JASON_MIDIA para um disco com espaço
cd frontend; npm install; npm run build; cd ..
python jason.py login
python jason.py web
```

> O passo a passo para leigo, com prints e problemas comuns, está nos tutoriais. O PDF do tutorial de Mac é gerado
> com `python scripts/tutorial_pdf.py` (ou com a skill `/tutorial-pdf` no Claude Code).

---

## Configuração (.env)

Todas as opções estão em [`backend/app/config.py`](backend/app/config.py). Elas são lidas de variáveis `JASON_*` ou
do `.env` na raiz.

| Variável | Padrão | Para quê |
|---|---|---|
| `JASON_MIDIA` | `./midia` | VODs, cortes, trechos, modelos do Whisper e de tradução, fontes, fundos e perfis de contas novas. **Pesado**: use um disco com espaço |
| `JASON_DADOS` | `./dados` | Banco SQLite (`jason.db`) |
| `JASON_LOGS` | `./logs` | `postar.log`, prints de erro e logs dos agendamentos |
| `JASON_WHISPER_MODELO` | `small` | `tiny` · `base` · `small` · `medium` · `large-v3` |
| `JASON_WHISPER_DISPOSITIVO` | `auto` | `auto` · `cuda` · `cpu` (no Mac roda em CPU) |
| `JASON_TWITCH_CLIENT_ID` / `_SECRET` | vazio | API oficial da Twitch, grátis, em [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps). A redirect URL pode ser `http://localhost`, e a conta da Twitch precisa ter 2FA. Sem ela, não há clipes nem vigia |
| `JASON_PORTA` / `JASON_HOST` | `8765` / `127.0.0.1` | Servidor web |
| `JASON_CHROME` | caminho padrão do SO | Executável do Chrome |

---

## O que a ferramenta faz

Menu da interface: **Painel · Cortar vídeo · Biblioteca · Fila · Modelos · Contas · Jobs · Logs**.

### Postagem

- **Contas** (tela Contas): cada conta tem um perfil do Chrome, uma pasta de vídeos, um idioma e hashtags próprios.
  - A conta padrão é `gta6`: pasta `limpos/`, perfil `perfil-chrome/`.
  - As contas novas ficam em `JASON_MIDIA/contas/<id>/`.
  - O login é **manual** (botão "Logar" ou `python jason.py --conta X login`). Nenhuma senha vai para arquivo.
- **Fila**: uma tabela vídeo × rede com o status de cada post.
  - A gaveta do vídeo tem player, **título, descrição e legenda próprios por rede**, hashtags e envio imediato.
  - Também dá para **editar hashtags em lote**.
  - O menu do status corrige o status à mão ou marca **"não postar nesta rede"**.
- **Agendar um vídeo** (Fila → aba Agendar, ou "Mandar e agendar" na Biblioteca): melhores horários de cada rede
  (grade do `horarios.json`, ★ pico), um horário diferente por rede para o mesmo vídeo, ou horário livre.
- **Agendamento**: o TikTok e o YouTube agendam no próprio site.
  - O Instagram não tem agenda no site, então o post vira uma tarefa do SO: o **Agendador de Tarefas** no Windows,
    o **launchd** no Mac (`~/Library/LaunchAgents/app.jason.*.plist`).
  - O PC precisa estar ligado no horário.
- **Modo lote**: "N por hora até HH:MM" (`plano`/`agendar --por-hora 3 --ate 00:00`).
- **Pack**: `baixar --qtd N` puxa clipes de GTA 6 do Drive, limpa os metadados (ffmpeg) e gera título e tags.
  - O `pack_usados.json` vai pro git para os parceiros não repetirem clipes: dê `git pull` antes e faça commit
    depois.
- **Histórico**: fica em `dados/jason.db` (tabela `posts`). As falhas (`erro`, `nao_logado`, `limite_diario`)
  ficam registradas e o vídeo continua pendente.

### Cortador

- **Cortar vídeo**: cole o link de uma live ou vídeo (Twitch, YouTube ou Kick) e o job `cortar_video` faz tudo:
  1. analisa e cria os candidatos;
  2. baixa os trechos;
  3. detecta a webcam e as barras pretas;
  4. descobre o idioma falado.

  Depois você escolhe o idioma da legenda, o fundo e o modelo, e renderiza tudo.
- **Biblioteca** (o estado fica na URL: `?aba=&fonte=&corte=`):
  - **Para revisar**: um card por vídeo original. O modal mostra os cortes sugeridos dele (trecho, nota, por que
    foi escolhido) e a aba da webcam (detectar de novo, com barra de progresso, ou marcar à mão).
  - **Prontos / Na fila / Descartados**: grade de cortes renderizados. "Mandar para a fila" copia o mp4 e o .txt
    para a pasta de uma conta.
  - Se você muda a webcam de um corte pronto, ele **re-renderiza sozinho**.
- **Editor de vídeo** (`/editor/:id`, botão "Editar vídeo"):
  - linha do tempo com cortes e reordenação (arrastar);
  - início e fim;
  - posição e tamanho do jogo e da webcam no 1080×1920;
  - fundo (desfocado, preto ou imagem);
  - legenda e gancho (fonte, cor, tamanho, altura);
  - webcam sincronizada ou com atraso;
  - desfazer e refazer.

  A prévia é um canvas que repete as contas do ffmpeg, e "Conferir no render" gera a prévia real. Dá para enviar
  as suas fontes `.ttf`/`.otf`.
- **Modelos**: layout + estilo de legenda + parâmetros (divisão, altura da legenda e do gancho, barra, crédito
  `twitch.tv/<canal>`). Vale o modelo do corte, depois o do streamer, depois o padrão.
- **Vigia de clipes** (Twitch): fica na aba "Vigia de clipes" na página do streamer, e há um card no Painel.
  - **Ciclo**: a cada N min o vigia olha os clipes das últimas 3 h. Os clipes acima de X views viram corte; os do
    mesmo momento viram um só.
  - **Contexto**: ele corta do **VOD** com Y s antes e Z s depois e espera a live gravar o "depois". Sem VOD, usa
    o próprio clipe.
  - **Limite**: ele só **prepara** (baixa e acha a webcam); **nunca renderiza nem posta sozinho**.
  - No corte, os botões **"+10 s antes / depois"** aumentam o contexto.
- **Jobs / Logs**: tudo que demora é um job, com progresso e log ao vivo (SSE) e botão de cancelar.

---

## CLI

| Comando | O que faz |
|---|---|
| `python jason.py web [--sem-navegador]` | Interface web + worker |
| `python jason.py worker` | Só o worker (sem servidor) |
| `python jason.py fila` | Tabela vídeo × plataforma |
| `python jason.py plano [-p tiktok,youtube] [--por-hora 3 --ate 00:00]` | O que seria agendado e quando (**não envia nada**) |
| `python jason.py agendar [-y] [--por-hora N --ate HH:MM]` | Agenda os pendentes |
| `python jason.py enviar -p tiktok,youtube [--video X] [--revisar]` | Posta agora. `--revisar` preenche tudo e **não publica** |
| `python jason.py baixar --qtd 10` / `--ids 3 7` | Baixa do pack, limpa e gera a legenda |
| `python jason.py tarefas` | Agendamentos do Instagram no SO |
| `python jason.py login` | Abre o Chrome da conta para logar (feche depois) |
| `python jason.py exportar` | Backup do histórico em JSON (`logs/`) |

Todos aceitam `--conta <id>`. O `postar.py` tem os mesmos comandos de postagem sem visual e com `--json`; é ele
que as tarefas agendadas chamam (**não mova nem renomeie**).

---

## Arquitetura

```
frontend/ (Vite + React 19 + TS + Tailwind 4 + shadcn/ui + cult-ui + motion + TanStack Query)
        │  HTTP + SSE (/api/eventos)
        ▼
backend/app/api (FastAPI)  ── enfileira ──►  backend/app/jobs (fila no SQLite)  ◄── worker (thread do "web")
                                                        │
        ┌───────────────────────────────────────────────┴──────────────────────────────┐
        ▼                                                                              ▼
servicos/  contas · historico · agenda · postagem (trava do perfil) · pack       cortes/  fontes (yt-dlp, Twitch Helix)
        │                                                                         → detectores → webcam → layouts
        ▼                                                                         → legendas (Whisper) → traducao
plataformas/ tiktok · youtube · instagram (Playwright)                            → edicao → render (ffmpeg) · vigia
             comum (textos por rede) · tarefas_windows / launchd

dados/jason.db (SQLite WAL + Alembic) · JASON_MIDIA (VODs, cortes, tmp, modelos) · logs/
```

```
jason.py / postar.py / baixar.py   atalhos na raiz
backend/app/
  config.py   models.py (Conta, Post, Streamer, Fonte, Corte, Modelo, Job)   db.py (migra no start)
  cli/        jason.py (rich), postar.py (--json)
  api/        main.py, schemas.py, rotas/{postagem,jobs,cortador,sistema}.py
  jobs/       fila.py, worker.py, registro.py (@tarefa), jobs_postagem.py
  servicos/   contas, historico, agenda, postagem, pack, importar
  plataformas/ tiktok, youtube, instagram, comum, tarefas_windows
  cortes/     plugins, fontes, detectores, webcam, midia, layouts, legendas, traducao, edicao, render, servico, jobs, vigia
backend/migrations/   Alembic
backend/tests/        pytest (banco temporário)
frontend/src/         pages/, components/, api/ (hooks, chaves, eventos SSE, schema.d.ts gerado), lib/editor/
scripts/tutorial_pdf.py   .claude/skills/   (skill do PDF)
```

**Fluxo do corte:** `buscar_fontes` → `analisar_fonte` (cria Cortes `candidato`) → revisão → `enquadrar_corte`
(trecho em `midia/tmp/corte_<id>`, quadro, webcam) → `renderizar_corte` (`pronto`, mp4 em `midia/cortes/`) →
`publicar` (`na_fila`, copia mp4 + .txt para a pasta da conta) → agendamento normal.

**Jobs:** uma função com `@tarefa("tipo", recurso="...")`. Jobs com o mesmo recurso rodam um por vez
(`navegador:<conta>` para o Chrome de cada conta, `gpu` para Whisper e render, `vigia:<streamer>`). O progresso
e o log vão para o banco e saem por SSE.

---

## API

Documentação interativa em **http://127.0.0.1:8765/docs** (OpenAPI em `/openapi.json`). Grupos principais:

- **Postagem:** `/api/contas`, `/api/contas/{c}/{plano,enviar,agendar,login}`, `/api/contas/{c}/videos`
  (+ `/textos`, `/legenda`, `/hashtags`, `/redes/{rede}`), `/api/posts`, `/api/historico/{c}`, `/api/pack/baixar`,
  `/api/tarefas-windows`.
- **Cortador:** `/api/streamers` (+ `/vigia`), `/api/fontes`, `/api/cortes` (+ `/editor`, `/miniatura`, `/bruto`,
  `/publicar`), `/api/identificar`, `/api/cortar`, `/api/previa`, `/api/modelos`, `/api/fundos`,
  `/api/fontes-texto`, `/api/vigia`.
- **Sistema:** `/api/jobs` (+ `/cancelar`, `/repetir`), `/api/eventos` (SSE), `/api/plugins`, `/api/sistema`,
  `/api/logs`, `/api/prints`.

---

## Estendendo

- **Rede social nova:** crie `plataformas/<rede>.py` com `NOME`, `LOGIN_URL`, `AGENDA_NATIVA` e
  `postar(page, video, revisar, quando, progresso) -> dict`, e registre em `plataformas/__init__.py`.
  - Use `comum.textos_rede(video, rede)` para os textos.
  - Mapeie o fluxo no Chrome real antes. Os seletores usam os textos **em português** da interface.
  - Acrescente o caso em `tests/test_plataformas.py` (página falsa).
- **Layout, estilo de legenda ou detector de momentos:** registre uma função nos registros `LAYOUTS`, `ESTILOS` e
  `DETECTORES` de `cortes/plugins.py` (`registrar(id, nome, descricao, **opcoes)`). A interface descobre sozinha
  por `GET /api/plugins`.
- **Job novo:** use `@tarefa(...)` em `jobs/` ou `cortes/jobs.py`. No front, acrescente o tipo em
  `INVALIDAR_POR_TIPO` (`frontend/src/api/eventos.ts`) para recarregar o que ele muda.
- **Mudou a API:** regenere os tipos do front (veja abaixo).

---

## Desenvolvimento

```bash
# backend
cd backend && python -m pytest && python -m ruff check app tests
cd backend && alembic revision --autogenerate -m "o que mudou"   # mudou models.py? (aplica sozinho no start)

# front
cd frontend && npm run dev            # hot reload em :5173 (proxy para o backend em :8765)
cd frontend && npm run typecheck && npm run lint && npm run build

# mudou a API → regenera openapi.json + tipos
cd backend && python -c "import json; from app.api.main import app; open('../frontend/openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=1))"
cd frontend && npm run api:tipos
```

**Testar sem estragar nada:** aponte `JASON_DADOS`, `JASON_LOGS` e `JASON_MIDIA` para pastas temporárias. Os
testes já usam um banco temporário (fixture `banco`). `tests/test_edicao.py` roda o ffmpeg de verdade e
`tests/test_plataformas.py` roda os 3 fluxos de postagem numa página falsa.

---

## Regras do projeto (leia antes de mexer)

- **Nunca** dispare `/enviar`, `/agendar`, `/login` ou `/cortes/{id}/publicar` contra o banco real em testes. Para
  conferir um envio, use `--revisar` (preenche e não publica).
- **Postagem só pelos scripts** (`jason.py`, `postar.py`, jobs). Se falhar, corrija `plataformas/*.py`.
- **Senhas nunca em arquivo.** Perfis do Chrome (`perfil-chrome/`, `midia/contas/*/perfil-chrome`) nunca vão para o
  git e ninguém lê os cookies.
- **Cortador sem LLM/API paga.** Na Twitch, só a API oficial **Helix** (GQL/endpoints internos não). Sempre dê
  crédito ao streamer.
- **Nunca renderizar com a webcam errada.** Um modelo que precisa da webcam só renderiza com a webcam `auto`
  (confiança ≥ 0,45) ou `manual`; senão o corte vai para `enquadrar`.
- **Não versionar:** `perfil-chrome/`, `dados/`, `.env`, `limpos/`, `baixados/`, `logs/`, `midia/`. O
  `pack_usados.json` **vai** para o git.

## Pegadinhas

- **Perfil do Chrome é exclusivo:** um processo por conta por vez (`trava_perfil`). Se você deixar o Chrome do
  script aberto à mão, o envio falha.
- **YouTube:**
  - nunca use `Escape` nos campos (fecha o upload);
  - não use `networkidle` no Studio;
  - o diálogo "Processando vídeo…" é sucesso;
  - canal sem verificação por telefone tem limite diário baixo (`limite_diario`).
- **TikTok:** só agenda com minutos múltiplos de 5 e ≥ 15 min de antecedência.
- **Instagram:**
  - o corte é sempre "Original";
  - a legenda termina com espaço;
  - no Mac, o post agendado precisa do Mac acordado e logado (veja `caffeinate -i`).
- **ffmpeg `ass=`:** use caminho relativo, com `cwd` na pasta temporária (caminho absoluto com `C:` quebra o
  filtro). Por isso as fontes são copiadas para `tmp/fontes`.
- **Navegador:** o limite é de ~6 conexões por endereço somando todas as abas. Por isso a aba escondida solta o
  SSE depois de 30 s.
- Mais detalhes no [CLAUDE.md](CLAUDE.md).
