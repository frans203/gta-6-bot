# TODO — Automação de posts GTA 6

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
