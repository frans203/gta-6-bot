# CLAUDE.md — contexto para agentes

Projeto pessoal (Windows 11, PowerShell, Python 3.11+, Node 24) com duas partes:
1. **Postagem**: posta/agenda vídeos em **TikTok, YouTube Shorts e Instagram Reels** controlando o Chrome com
   Playwright, com várias **contas** (cada conta = um perfil do Chrome + uma pasta de vídeos).
2. **Cortador**: transforma lives (Twitch/YouTube) em cortes verticais com legenda, **sem IA paga**
   (picos de áudio, heatmap do YouTube, clipes da Twitch via API oficial; Whisper local para legenda).

Idioma do projeto e do usuário: **português (BR)**. Fuso: America/Sao_Paulo (hora do PC).
Leia também: [README.md](README.md) (arquitetura e comandos), [TUTORIAL.md](TUTORIAL.md) (manual do usuário),
[TODO.md](TODO.md) (**fonte da verdade do progresso**; atualize ao concluir algo).

## Estrutura

```
jason.py / postar.py / baixar.py      atalhos na raiz (as tarefas do Windows chamam postar.py: NÃO mova/renomeie)
backend/app/
  config.py        configurações (env JASON_* ou .env na raiz). Caminhos: raiz, dados/, logs/, midia (JASON_MIDIA)
  models.py        SQLAlchemy 2.0: Conta, Post, Streamer, Fonte, Corte, Job. Mudou? gere migração Alembic
  db.py            SQLite (WAL) + preparar() = migrar + conta padrão + importar postados.json antigo
  cli/             jason.py (rich) e postar.py (sem visual, --json)
  api/             FastAPI: main.py, schemas.py, rotas/{postagem,jobs,cortador,sistema}.py  (docs em /docs)
  jobs/            fila.py (enfileirar/reivindicar/cancelar, Contexto), worker.py, jobs_postagem.py, registro.py
  servicos/        contas, historico (posts), agenda (plano), postagem (executar/trava), pack, importar
  plataformas/     tiktok, youtube, instagram (interface: NOME, LOGIN_URL, AGENDA_NATIVA, postar()),
                   comum (log, exceções, .txt da legenda), tarefas_windows
  cortes/          plugins (registros LAYOUTS/ESTILOS/DETECTORES), fontes (yt-dlp + Twitch Helix), detectores,
                   webcam (OpenCV), layouts (filtros ffmpeg 1080x1920), legendas (faster-whisper + .ass),
                   render, servico (CRUD), jobs
backend/tests/     pytest (banco temporário via fixture `banco`)
frontend/          Vite + React + TS + Tailwind + shadcn/ui + cult-ui + motion + TanStack Query; tipos do OpenAPI
```

Fluxo do cortador: `buscar_fontes` → `analisar_fonte` (cria Cortes "candidato") → revisão na **Biblioteca** →
`enquadrar_corte` (opcional: baixa o trecho em `midia/tmp/corte_<id>`, salva `midia/quadros/corte_<id>.jpg`,
detecta a webcam) → `renderizar_corte` (status "pronto", mp4 em `midia/cortes/`) → "Mandar para a fila" copia
mp4 + .txt para a pasta da conta (status "na_fila") → agendamento normal.

**Fluxo rápido** (página "Cortar vídeo"): `POST /api/identificar` (yt-dlp sem baixar: plataforma
twitch|youtube|kick|outro) → `POST /api/cortar` (cadastra streamer/fonte se novos) → job `cortar_video`
(`_analisar` + `render.preparar_enquadramento` por corte: webcam, `midia.area_util` = barras pretas → vira
`corte.jogo`, idioma falado via Whisper → `fonte.extra.idioma`) → `POST /api/fontes/{id}/aplicar`
(idioma_legenda, fundo, modelo para todos) → `POST /api/fontes/{id}/renderizar`.

**Interface (menu)**: Painel, Cortar vídeo, Biblioteca, Fila, Modelos, Contas, Jobs, Logs. Não há tela de
Agenda nem de Streamers no menu (agendar é pela CLI; `/cortador/streamers/:id` abre pelo modal). **Biblioteca**
(`pages/biblioteca.tsx`, estado na URL `?aba=&fonte=&corte=`): "Para revisar" = `GET /api/fontes?com_cortes=...`
(um card por vídeo original, modal com os cortes); Prontos/Na fila/Descartados = cortes (miniatura em
`GET /api/cortes/{id}/miniatura`). Mudar a webcam (PATCH ou `enquadrar_corte`) de um corte `pronto` re-renderiza
sozinho (`servico.rerenderizar`). Visual: tokens em `src/index.css` (nomes antigos rosa/ciano/laranja/roxo com
tons novos), fonte Bricolage Grotesque, utilitários `cartao-brilho`/`botao-brilho`/`texto-gradiente`.

Tradução da legenda: `cortes/traducao.py` (Argos/OPUS-MT no CTranslate2, grátis e local; `sentencepiece` instalado em
`E:\jason-midia\libs`; modelos em `JASON_MIDIA/modelos/traducao`). Imagens de fundo: `JASON_MIDIA/fundos`
(`POST /api/fundos` com os bytes da imagem), usadas pelo layout `fundo_imagem`.

**Regra do usuário: nunca renderizar com a webcam errada.** Modelo cujo layout tem `precisa_webcam` só
renderiza com `corte.webcam.origem` = `auto` (detecção com confiança ≥ `webcam.CONFIANCA_MINIMA`) ou `manual`
(marcada na UI). Senão o corte vira status `enquadrar` com uma webcam `sugerida` e o usuário marca à mão.
Não há fallback silencioso para outro layout. **Modelos de corte** (tabela `modelos`): layout + estilo +
`params` (divisao, legenda_y, gancho_y em frações da altura; barra; credito). Corte → modelo do corte, senão
do streamer, senão o padrão. A prévia (`POST /api/previa`) usa o mesmo filtro ffmpeg + .ass do render.

## Estado (não apague sem perguntar)

- `dados/jason.db` — fonte da verdade do histórico (tabela `posts`, antigo `postados.json`, que foi importado
  em 14/11/2026 e renomeado para `postados.importado.json`; backups em `logs/`). Status: `publicado`,
  `agendado` (nativo), `agendado_pc` (Windows), `pulado_reivindicacao`, `erro`, `nao_logado`, `limite_diario`.
  Os 4 primeiros contam como **feito** (`agenda.FEITO`). Correção manual: tela Fila (menu do status) ou
  `PATCH /api/posts/{id}`; `python jason.py exportar` gera um JSON de backup.
- Conta padrão `gta6`: pasta `limpos/`, perfil `perfil-chrome/`, trava `logs/perfil-chrome.lock`, tarefas do
  Windows `instagram_gta6_NNN`. Contas novas: `JASON_MIDIA/contas/<id>/{videos,perfil-chrome}`,
  trava `logs/perfil-<id>.lock`, tarefas `<id>_instagram_<video>` com `--conta`.
- `pack_usados.json` — clipes do pack já baixados (versionado; evita repetir entre parceiros).
- `perfil-chrome/` e perfis das contas — sessões logadas. **Nunca** ler cookies, versionar ou compartilhar.
- `.env` — `JASON_MIDIA=E:\jason-midia` nesta máquina (o C: está quase cheio!). Mídia pesada, modelos do
  Whisper e libs CUDA (`E:\jason-midia\libs`) ficam lá.
- `logs/postar.log` + `logs/erro_<rede>_<data>.png` — primeiro lugar a olhar quando algo falha. Cada job também
  guarda o próprio log (tela Jobs ou `GET /api/jobs/{id}`).

## Receitas comuns

```powershell
python jason.py web                                     # interface + worker (http://127.0.0.1:8765)
python jason.py fila                                    # estado atual (CLI)
python jason.py baixar --qtd 20                         # mais vídeos do pack (conta gta6)
python jason.py plano   --por-hora 3 --ate 00:00        # "N vídeos por hora até meia-noite" — confira antes
python jason.py agendar --por-hora 3 --ate 00:00 -y     # executa (em segundo plano; demora)
python jason.py --conta gamer_en fila                   # outra conta
cd backend; python -m pytest; python -m ruff check app tests
cd frontend; npm run api:tipos; npm run build           # depois de mudar a API
```

Pedido tipo "X vídeos por hora até HH:MM": calcule `X × horas` por plataforma, compare com os pendentes
(`fila`), rode `baixar --qtd` para completar, mostre o `plano` e só então `agendar`. O que sobrar fica pendente.

## Regras e decisões já tomadas pelo usuário

- **Nunca envie/poste usando ferramentas do agente** (claude-in-chrome, computer use etc.). Todo envio passa por
  `jason.py`/`postar.py`/jobs da API. Se algo falhar ou faltar, **corrija o script** (`plataformas/*.py`) e rode
  de novo. O navegador do agente só serve para mapear um fluxo novo ou que mudou, antes de escrever o script.
- **Em testes, nunca dispare** `POST /enviar`, `/agendar`, `/login`, `/cortes/{id}/publicar` contra o banco real.
  Use `JASON_DADOS=<pasta temporária>` (e `JASON_LOGS`, `JASON_MIDIA`) para testar a API/worker.
- **Confirme com o usuário antes de publicar de verdade** em uma conta pela 1ª vez num fluxo novo, ou antes de
  aceitar diálogos de consentimento de uma plataforma. Para testar, use `--revisar` (preenche e não publica).
- YouTube: sempre "não é conteúdo para crianças"; publicar mesmo com Content ID (`youtube.py`, constantes no topo).
- TikTok: fechar o popup de "verificações automáticas" sem ativar; aceitar o aviso "Permitir" do agendamento.
- Instagram: corte sempre **Original**; terminar a legenda com espaço (Escape fecha o modal!).
- Senhas nunca em arquivo: login só manual (`python jason.py [--conta X] login` ou botão na tela Contas) e
  depois fechar o Chrome. As interfaces das redes devem ficar em **português** nas contas (os seletores usam os
  textos em PT), mesmo numa conta que posta em inglês.
- Cortador: **sem LLM/API paga**. Twitch: só a API oficial Helix (usar endpoints internos/GQL da Twitch foi
  bloqueado por política e não deve ser contornado). Dar crédito ao streamer (o render já escreve
  `twitch.tv/<canal>` no vídeo). Preferir streamers que autorizam cortes / têm campanha de clipping.
- Novas plataformas: mapear o fluxo no Chrome real do usuário (claude-in-chrome) e depois escrever o módulo
  Playwright. O upload pela claude-in-chrome tem limite de 10 MB, por isso os vídeos sobem pelo script.

## Pegadinhas técnicas

- **Webcam**: detector de rosto YuNet (OpenCV, modelo em `JASON_MIDIA/modelos/rosto`, baixa sozinho; Haar só
  se não der para baixar) + agrupamento por posição + `_moldura` (borda parada do overlay ao longo do tempo).
  Regra: confiança ≥ 0,45 usa sozinho; dúvida → status `enquadrar`; nenhum rosto fixo → segue sem o streamer
  (`extra.webcam = "nenhuma"`), a não ser que outro corte do mesmo vídeo tenha achado a câmera
  (`jobs._sugerir_pela_mesma_live`). Ler quadros com `grab()` em sequência (seek no mp4 do yt-dlp é lentíssimo).
- **Disco C: cheio**: banco e logs ficam em `E:\jason-midia\{dados,logs}` (`JASON_DADOS`/`JASON_LOGS` no `.env`).
  Ao gravar arquivos do projeto, grave num `.novo` e troque (`replace`): um `write_text` que falha no meio deixa
  o arquivo vazio (já aconteceu com `cortes/jobs.py`).

- **TikTok** só agenda com minutos múltiplos de 5 e com ≥ 15 min de antecedência. `executar()` troca para
  "postar agora" se o horário ficar a < 16 min durante um lote longo.
- **YouTube**: ao agendar, às vezes aparece o diálogo **"Processando vídeo… ficará público em…"** em vez do de
  compartilhar. Isso é **sucesso** (detectado pelo texto da página inteira, não por um seletor de diálogo).
- **YouTube: nunca usar `Escape`** nos campos do upload. Sem sugestão de hashtag aberta, ele fecha o diálogo
  inteiro (o vídeo vira rascunho e o próximo clique dá timeout). O script termina o texto com espaço.
- **YouTube: não usar `networkidle`** no Studio (nunca fica ocioso); esperar `#upload-icon`/`#create-icon`.
- **YouTube: limite diário de envios.** Canal sem verificação por telefone tem teto baixo (estourou em ~10 uploads
  em 13/11/2026). `LimiteDiario` → status `limite_diario` (fica pendente) e pula o YouTube no resto do lote.
- **Rodar lote longo**: pela interface (job) ou em processo independente (`Start-Process`), não como comando com
  timeout do agente. Para parar: cancele o job na tela Jobs (para entre um envio e outro). Na CLI: filtre por
  `Name='python.exe'` + `*agendar*` (um filtro só por linha de comando casa com o próprio shell do agente) e
  feche os `chrome.exe` com `*perfil-chrome*` na linha de comando. Parar o `jason.py web` mata o worker.
- **Perfil do Chrome é exclusivo**: só um processo por vez por conta. `trava_perfil(conta)` serializa lote, jobs
  e tarefas do Windows. Se o Chrome do script estiver aberto à mão, o envio falha ("browser has been closed").
- Durante um lote, Instagram cujo horário chegar é postado **pelo próprio lote**; a tarefa do Windows depois vê
  `publicado` e não reposta (`enviar --video` pula o que já está publicado).
- **yt-dlp no Windows**: o downloader HLS nativo perde fragmentos ("Frag… No such file"). O áudio usa formato
  HTTP direto ou o ffmpeg para HLS; `fontes._baixar` tenta de novo sem paralelismo.
- **Lives longas** (Kai Cenat faz VODs de 30h+): o detector de áudio processa em blocos de 3h.
- **ffmpeg `ass=`** no Windows: o render roda o ffmpeg com `cwd` na pasta temporária e usa caminho relativo
  (caminho absoluto com `C:` quebra o filtro).
- Muitos posts por hora podem ser tratados como spam (queda de alcance). O usuário está testando 3/h.
- Instagram (abr/2026) tira das recomendações contas que postam principalmente conteúdo não original:
  cortes precisam de transformação (layout, legenda, gancho, seleção) — não só repost.
