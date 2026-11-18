# TODO — JASON_GTAVI_PIPELINE

## v2 (14/11/2026): interface web + cortador de lives
- [x] Pesquisa: como Opus Clip/Klap/Vizard funcionam; monetização em USD (clipping pago ~US$1/mil views >> RPM
      de Shorts); penalidade do Instagram para conteúdo não original (abr/2026)
- [x] Código movido para `backend/app` (pacote), atalhos `jason.py`/`postar.py`/`baixar.py` na raiz
- [x] SQLite + Alembic (`dados/jason.db`); `postados.json` importado (verificado idêntico) → `postados.importado.json`
- [x] Várias contas (perfil do Chrome, pasta de vídeos, trava e tarefas do Windows por conta); `--conta` na CLI
- [x] Fila de jobs no SQLite + worker (recurso exclusivo por conta/GPU, cancelar, repetir, log por job)
- [x] API FastAPI (`/docs`) + SSE (`/api/eventos`: jobs e log ao vivo); `python jason.py web`
- [x] Cortador: fontes (yt-dlp; Twitch Helix p/ clipes), detectores (áudio, heatmap YouTube, clipes Twitch),
      webcam automática (OpenCV), layouts (webcam em cima / só jogo / tela cheia desfocada), legenda palavra
      por palavra (faster-whisper + .ass), gancho, crédito, barra de progresso, NVENC
- [x] Testado de ponta a ponta: VOD real do alanzoka → corte 1080x1920 com webcam + legenda (106 s, Whisper CPU);
      análise de VOD de 2,7 h do Speed em 35 s
- [x] Testes (pytest) e lint (ruff)
- [x] Frontend React + TS + Tailwind + shadcn/ui (Painel, Fila, Cortar vídeo, Biblioteca, Modelos, Jobs, Logs, Contas)
- [x] Whisper na GPU (libs CUDA em E:\jason-midia\libs, modelo medium); streamers do MVP e conta gamer_en cadastrados
- [x] Enquadramento por corte: detecção do streamer (Haar frente + perfil) no próprio trecho; se não achar com
      segurança, status "marcar webcam" e marcação manual na revisão (render bloqueado até confirmar);
      área do jogo opcional; prévia real (ffmpeg) ao lado
- [x] Modelos de corte (tabela + página): padrão "jogo em cima + streamer embaixo", legenda na divisa ou
      embaixo/em cima/livre, altura do jogo, gancho, barra e crédito ajustáveis; streamer e corte escolhem
- [x] Fluxo rápido "Cortar vídeo": colar link (Twitch/YouTube/Kick/outros) → quantos cortes → prepara cada um
      (streamer, barras pretas, idioma) → legenda original ou traduzida (EN↔PT local, grátis) → imagem de
      fundo quando há espaço preto (layout fundo_imagem) → enquadramento manual dos não identificados → gerar
- [x] (18/11/2026) Biblioteca no lugar de "Revisar cortes": vídeos originais em grade (modal com os cortes,
      legenda/fundo/modelo para todos, renderizar todos), prontos em grade vertical que toca no hover, editor
      com abas Corte / Cara do streamer; "Detectar de novo" com progresso; mudar a webcam de um corte pronto
      gera o vídeo de novo sozinho. Saíram do menu: Agenda (CLI continua) e Streamers (página acessível pelo modal)
- [x] (18/11/2026) Visual novo: preto + roxo/rosa, fonte Bricolage Grotesque, componentes do cult-ui
      (GradientHeading, BgAnimateButton, RollingNumber, abas no estilo Direction Aware Tabs), animações
      com `motion` (respeitam "reduzir movimento"); tarefas antigas `instagram_gta6_*` do Windows removidas
- [ ] Tradução: o modelo grátis puxa para PT de Portugal ("O que raio..."); avaliar trocar o par en→pt
- [ ] **Usuário**: criar app grátis na Twitch (dev.twitch.tv) e pôr `JASON_TWITCH_CLIENT_ID/SECRET` no `.env`
- [ ] **Usuário**: criar a conta gamer em inglês nas 3 redes, `python jason.py --conta gamer_en login`
- [ ] Rodar o MVP: alanzoka + Flow Games (YouTube channel/UCUZfhX79dQrJvAgYefiXCCA; a Twitch deles não tem VODs),
      Kai Cenat, Speed + um streamer em ascensão com campanha de clipping ativa (escolher na Whop)
- [ ] Medir desempenho dos cortes (views por post) → tela de métricas
- [ ] Ideias: título automático a partir da transcrição (palavras-chave), zoom nos picos, música de fundo,
      modelo com 2 webcams, rastrear a webcam quando ela muda de lugar no meio da live, detector de risada/palavras-chave na transcrição, upload em lote para campanhas

## v1 — Automação de posts GTA 6

## Feito
- [x] `limpar-metadados.ps1`: remove metadados, recodifica com tamanho próximo do original e dá nomes `gta6_NNN.mp4`
- [x] `baixar.py`: baixa do pack (videos.json → Google Drive), limpa e gera a legenda `.txt` com título + tags
- [x] Mapear o fluxo de upload do TikTok Studio e publicar um vídeo de teste (`gta6_002`)
- [x] `postar_tiktok.py`: primeira versão (Playwright + perfil próprio em `perfil-chrome/`)
- [x] Pesquisar os melhores horários do TikTok → [horarios-tiktok.md](horarios-tiktok.md)

- [x] Trackear YouTube: mapear o fluxo do YouTube Studio e publicar um teste (`gta6_003` → https://youtube.com/shorts/EgHHuMbQjiI)

- [x] Trackear Instagram: mapear o fluxo e publicar um Reel de teste (`gta6_002` em @jason_vicecity)
- [x] CLI única `postar.py` (`login` / `fila` / `enviar`, com `--json`) + `plataformas/{tiktok,youtube,instagram}.py`
- [x] `plataformas/instagram.py`. Fluxo: `svg[aria-label='Novo post']` → "Postar" → `input[type=file]` → Cortar: "Selecionar corte" → **Original** → Avançar → Editar → Avançar → legenda `[contenteditable][aria-label^='Adicione uma legenda']` + **espaço** no fim (Escape fecha o modal!) → Compartilhar → espera "Seu reel foi compartilhado." → Concluir

- [x] Agendamento: `horarios.json` (grade por plataforma, dia útil/fim de semana) + `plataformas/agenda.py`
  - TikTok e YouTube: agenda da própria plataforma ("Programar")
  - Instagram (a web não agenda): Agendador do Windows, pasta `\JASON_GTAVI\` (PC ligado no horário)
- [x] CLI estilizada `jason.py` (JASON_GTAVI_PIPELINE): logo de Vice City, cores neon, barras de progresso

- [x] Modo lote: `python jason.py agendar --por-hora 3 --ate 00:00 -y` (N posts/hora por plataforma até o limite; minutos múltiplos de 5 → :00 :10 :25 :35 :50; o que não couber fica pendente)
  - trava `logs/perfil-chrome.lock`: lote e tarefas do Agendador do Windows não abrem o perfil ao mesmo tempo
  - Instagram que vence durante o lote é postado na hora pelo próprio lote; a tarefa do Windows depois vê "publicado" e pula
  - horário que ficou a < 16 min durante o lote → posta agora
- [x] YouTube: diálogo "Processando vídeo" (agendado aguardando SD) agora conta como sucesso (antes dava timeout falso)

## Em andamento
- [ ] Rodar `python jason.py agendar -y` (7 vídeos × 3 plataformas) assim que o login do perfil do script estiver feito
- [ ] **Login único no perfil do script**: `python postar.py login` (abre um Chrome normal com TikTok, YouTube e Instagram) e depois fechar o Chrome
- [ ] Validar `postar.py enviar` em cada plataforma (1º com `--revisar`)
- [ ] TikTok: login no perfil `perfil-chrome` (`python postar_tiktok.py --login`) e validar o script com 1 post. A 1ª tentativa não salvou a sessão
- [ ] `postar_youtube.py` com o fluxo mapeado:
  1. Painel → `#upload-icon` (abre o modal "Enviar vídeos")
  2. `ytcp-uploads-dialog input[type=file][name=Filedata]` (o vídeo vira rascunho privado na hora)
  3. 1º `#textbox` = título (máx. 100): `título + #gta6 #shorts`
  4. 2º `#textbox` = descrição: título + 12 tags, depois **Escape** (fecha as sugestões de hashtag)
  5. `tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]`: sempre "não é para crianças" (autorizado pelo usuário em 13/11/2026)
  6. `#next-button` ×3 (Elementos → Verificações → Visibilidade)
  7. `tp-yt-paper-radio-button[name=PUBLIC]` → `#done-button` (o texto vira "Publicar")
  8. Sucesso = aparece `ytcp-video-share-dialog` ("Vídeo publicado") com o link do Short; fechar
  - O rodapé do modal pode dizer "Conteúdo reivindicado encontrado" (Content ID). Decidir: pular ou publicar mesmo assim
  - O YouTube também tem agendamento próprio (seção "Programar" na etapa Visibilidade)

## A fazer
- [ ] Pesquisar os melhores horários do YouTube Shorts e do Instagram Reels (somar ao `horarios-*.md`)
- [ ] CLI única de envio (`postar.py`), pensada para virar uma página em React no futuro:
  - [ ] Um módulo por plataforma (`plataformas/tiktok.py`, `youtube.py`, `instagram.py`), todos com a mesma interface: `postar(page, video, legenda) -> resultado`
  - [ ] Comandos: `postar.py enviar --plataforma tiktok,youtube,instagram [--video X] [--revisar]`, `postar.py fila`, `postar.py status`, `postar.py login --plataforma X`
  - [ ] Opção `--json` em todos os comandos (saída legível por máquina, para a futura API/React)
  - [ ] Estado num único arquivo/SQLite (fila, postados por plataforma, erros), sem um JSON separado por plataforma
  - [ ] Logs + print da tela em caso de erro (`logs/`)
- [ ] Agendamento: Agendador do Windows rodando `postar.py enviar` nos 5 horários da grade (com variação de ±15 min)
- [ ] Futuro: API local (FastAPI) em cima da CLI + página em React (fila, preview, legenda editável, histórico, botão "postar agora")
