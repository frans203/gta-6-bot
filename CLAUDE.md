# CLAUDE.md — contexto para agentes

Projeto pessoal (Windows 11, PowerShell, Python 3.11+, Node 24) com duas partes:
1. **Postagem**: posta/agenda vídeos em **TikTok, YouTube Shorts e Instagram Reels** controlando o Chrome com
   Playwright, com várias **contas** (cada conta = um perfil do Chrome + uma pasta de vídeos).
2. **Cortador**: transforma lives (Twitch/YouTube) em cortes verticais com legenda, **sem IA paga**
   (picos de áudio, heatmap do YouTube, clipes da Twitch via API oficial, fala transcrita e chat gravado do
   YouTube; Whisper local para legenda e para a análise).

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

**Melhores momentos (sem IA paga)**: `detectores.py` = curvas de 1 nota/s no tempo da live, somadas com pesos:
`audio` (1.0), `mais_assistidos` (1.5), `clipes_twitch` (2.0), `fala` (1.5: `cortes/fala.py`, Whisper
`whisper_modelo_analise`=small, só se o trecho ≤ `fala_max_h`=4h; ritmo, explosão depois de silêncio, risada,
`palavras_gancho.json`), `chat_youtube` (2.0: `cortes/chat.py`, legenda `live_chat` do yt-dlp; o YouTube entrega
~8x o tempo real, então o download **para no fim do trecho**; cache `midia/chat/fonte_<id>.npz` com `_ate`).
Curvas auxiliares (`fala_*`, `chat_*`) vão em `Analise.extras` → `corte.sinais` (não entram na nota).
**Trecho**: VOD > 3h pede na tela "Cortar vídeo" de qual pedaço cortar (barra sobre o `mapa` que o
`/api/identificar` devolve: clipes da Twitch ou heatmap, `fontes.mapa_momentos`); `inicio`/`fim` vão em
`CortarVideoIn`/`AnalisarIn` → `fonte.extra.trecho` (reanalisar sem trecho usa o último). `escolher_picos` ajusta
início/fim às frases (`fala.ajustar_as_frases`, `sinais.frase=1`) e a análise preenche `corte.gancho` com a frase
mais forte (`fala.sugerir_gancho`). Transcrição da análise em `midia/transcricoes/fonte_<id>_<ini>_<fim>.json`; o
idioma dela vira `fonte.extra.idioma` (o enquadramento não roda o Whisper de novo). **Aprendizado**
(`cortes/aprendizado.py`): regressão logística em numpy sobre `corte.sinais`; bons = aprovado/pronto/na_fila,
ruins = descartados **na revisão** (`extra.descartado_de` ∈ candidato/enquadrar, gravado pelo PATCH); com ≥ 30
exemplos (≥ 10 de cada) pega 3x candidatos e reordena (`sinais.aprendido`); `dados/pesos_aprendidos.json`,
`GET/PUT /api/aprendizado`, card na tela Modelos. Chat da Twitch de VOD: não (só sai por GQL, proibido).
Editor: ★ = `sinais.pico`; botão "Gancho no início" (`ganchoNoInicio`) copia ~3 s em volta dele para o começo.

**Interface (menu)**: Painel, Cortar vídeo, Biblioteca, Fila, Modelos, Contas, Jobs, Logs. Não há tela de
Agenda nem de Streamers no menu (`/cortador/streamers/:id` abre pelo modal). **Agendar um vídeo**: Fila → gaveta do
vídeo (`?video=X&aba=agendar`, `?conta=` troca a conta) → `components/agendar-video.tsx`: um horário por rede, sugeridos
por `GET /api/contas/{c}/horarios-sugeridos` (`agenda.sugestoes`: grade do `horarios.json`, ★ = `_destaques`,
ocupados marcados) → `POST /api/contas/{c}/videos/{v}/agendar` (`agenda.validar_itens`: ≥ 30 min, minuto múltiplo de 5,
rede ainda não feita) → job `enviar_agendado`. Biblioteca: "Mandar e agendar" / "Agendar" usam `corte.extra.fila`
({conta, video}, gravado por `publicar_na_fila`). "Voltar para pendente" num `agendado_pc` apaga a tarefa do
Agendador/launchd (`agendador.remover`); TikTok/YouTube agendados só se mudam no próprio site. **Biblioteca**
(`pages/biblioteca.tsx`, estado na URL `?aba=&fonte=&corte=`): "Para revisar" = `GET /api/fontes?com_cortes=...`
(um card por vídeo original, modal com os cortes); Prontos/Na fila/Descartados = cortes (miniatura em
`GET /api/cortes/{id}/miniatura`). Mudar a webcam (PATCH ou `enquadrar_corte`) de um corte `pronto` re-renderiza
sozinho (`servico.rerenderizar`). Visual: tokens em `src/index.css` (nomes antigos rosa/ciano/laranja/roxo com
tons novos), fonte Bricolage Grotesque, utilitários `cartao-brilho`/`botao-brilho`/`texto-gradiente`.

**Editor de vídeo** (`/editor/:id`, botão "Editar vídeo" no modal do corte): edição livre salva em `cortes.edicao`
(schema `Edicao`): `segmentos` em segundos **da live** (na ordem do vídeo), `layout` (jogo/webcam: `fonte` = recorte
do original, `saida` = caixa no 1080x1920; fundo desfocado/preto/imagem), `legenda`/`gancho` (fonte, cor, tamanho,
y), `sincronizado`/`atraso_streamer`. O trecho é baixado com `edicao.MARGEM` (10 s) de folga e **não é apagado**
depois do render (`midia/tmp/corte_<id>/trecho.mp4`, servido em `/api/cortes/{id}/bruto`); a transcrição do arquivo
inteiro fica em `corte.transcricao.arquivo` (job `preparar_editor`). Render com edição: `edicao.filtro_segmentos`
(trim+concat) → `edicao.montar_livre` → `.ass` com as palavras remapeadas (`edicao.remapear`). A prévia do editor é
um canvas que repete as mesmas contas (`frontend/src/lib/editor/`); "Conferir no render" usa `/api/previa` com a
edição. Webcam marcada no editor (`layout.webcam.fonte`) vale como "manual"; sem ela, vale a regra de sempre.
Fontes do texto: as do Windows + `.ttf/.otf` enviadas para `JASON_MIDIA/fontes` (copiadas para `tmp/fontes`
porque o `ass=` não aceita caminho com `E:`).

**Vigia de clipes** (`cortes/vigia.py`, aba "Vigia de clipes" na página do streamer da Twitch, card no Painel):
o worker enfileira `vigiar_clipes` a cada `intervalo_min` por streamer com `streamers.vigia.config.ativo`. Cada
ciclo pega na Helix os clipes das últimas `OBSERVAR_H` h, espera passarem de `min_views`, junta clipes do mesmo
momento (mesmo VOD), espera o VOD cobrir clipe + `depois` + folga e cria o corte no VOD (`vod_offset` − `antes` até
fim + `depois`), com `extra.origem="vigia"`; sem VOD usa o próprio clipe. Só prepara (`enquadrar_corte`): nunca
renderiza nem posta sozinho. Estado (vistos, recentes, aguardando, momentos) em `streamers.vigia.estado`. Jobs do
vigia sem resultado somem depois de 2 h. Credenciais da Twitch no `.env`. Adicionar canal: card do Painel →
`POST /api/vigia {canal}` (`vigia.adicionar_canal`: confere na Helix, cadastra, liga). VOD só para inscritos: o
download falha, `render._trecho` chama `vigia.usar_clipe_se_vod_fechado` (corte vira o clipe; `estado.vod_fechado`).

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
  `agendado` (nativo), `agendado_pc` (Windows), `pulado_reivindicacao`, `removido` ("não postar nesta rede", menu
  da Fila ou `PUT /api/contas/{c}/videos/{v}/redes/{rede}`), `erro`, `nao_logado`, `limite_diario`.
  Os 5 primeiros contam como **feito** (`agenda.FEITO`). Falhas (`erro`, `nao_logado`, `limite_diario`) são
  gravadas só se o vídeo não tinha status bom naquela rede (`postagem._registrar_falha`); continuam pendentes.
  `tests/test_plataformas.py` roda os 3 fluxos numa página falsa: rode antes de mexer em `plataformas/*.py`.
- **Textos do post**: `<video>.txt` (título + hashtags; o pack e os cortes só escrevem ele) + `<video>.meta.json`
  (descrição e texto próprio por rede: youtube {titulo, descricao}, tiktok/instagram {legenda}). As plataformas usam
  `comum.textos_rede(video, rede)` (numa linha só: Enter fecharia sugestões). Tela Fila → gaveta do vídeo;
  `GET/PUT /api/contas/{c}/videos/{v}/textos`; hashtags em lote: `POST /api/contas/{c}/videos/hashtags`. Correção manual: tela Fila (menu do status) ou
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
  feche os `chrome.exe` com `*perfil-chrome*` na linha de comando. Parar o `jason.py web` mata o worker (fechado à força,
  o worker percebe pelo `JASON_PAI` em até 5 s e sai: antes ficavam workers órfãos rodando código velho).
- **Perfil do Chrome é exclusivo**: só um processo por vez por conta. `trava_perfil(conta)` serializa lote, jobs
  e tarefas do Windows. Se o Chrome do script estiver aberto à mão, o envio falha ("browser has been closed").
- Durante um lote, Instagram cujo horário chegar é postado **pelo próprio lote**; a tarefa do Windows depois vê
  `publicado` e não reposta (`enviar --video` pula o que já está publicado).
- **yt-dlp no Windows**: o downloader HLS nativo perde fragmentos ("Frag… No such file"). O áudio usa formato
  HTTP direto ou o ffmpeg para HLS; `fontes._baixar` tenta de novo sem paralelismo.
- **Lives longas** (Kai Cenat faz VODs de 30h+): o detector de áudio processa em blocos de 3h; escolher um trecho
  na tela evita baixar/analisar a live inteira. Whisper `medium` na RTX 3050 é ~2,5x o tempo real (lento para
  análise): por isso a análise usa o `small` (~70x), e a legenda continua no `whisper_modelo` do `.env`.
- **ffmpeg `ass=`** no Windows: o render roda o ffmpeg com `cwd` na pasta temporária e usa caminho relativo
  (caminho absoluto com `C:` quebra o filtro).
- Muitos posts por hora podem ser tratados como spam (queda de alcance). O usuário está testando 3/h.
- Instagram (abr/2026) tira das recomendações contas que postam principalmente conteúdo não original:
  cortes precisam de transformação (layout, legenda, gancho, seleção) — não só repost.
