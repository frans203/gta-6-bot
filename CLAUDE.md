# CLAUDE.md — contexto para agentes

Projeto pessoal (Windows 11, PowerShell, Python 3.11+) que baixa clipes de GTA 6 de um pack, limpa os
metadados e posta/agenda em **TikTok, YouTube Shorts e Instagram Reels** controlando o Chrome com
Playwright. Idioma do projeto e do usuário: **português (BR)**. Fuso: America/Sao_Paulo (hora do PC).

Leia também: [README.md](README.md) (comandos), [TUTORIAL.md](TUTORIAL.md) (manual do usuário),
[TODO.md](TODO.md) (**fonte da verdade do progresso**; atualize ao concluir algo).

## Fluxo e arquivos

```
baixar.py ──► baixados/video_NNNN.mp4 ──► limpar-metadados.ps1 (ffmpeg) ──► limpos/gta6_NNN.mp4 + .txt (legenda)
                                                                                   │
jason.py (CLI bonita, rich)  ─┐                                                    ▼
postar.py (núcleo + --json) ──┴─► plataformas/agenda.py (plano) ─► postar.executar() ─► plataformas/{tiktok,youtube,instagram}.py
                                                                     │  └─ Instagram agendado → plataformas/tarefas_windows.py
                                                                     └─ registra em postados.json
```

| Arquivo | Papel |
|---|---|
| `jason.py` | CLI que o usuário usa (logo, cores, barras). Comandos: `fila plano agendar enviar baixar tarefas login` |
| `postar.py` | Núcleo: `fila()`, `proximo()`, `executar(tarefas)`, `trava_perfil()`. CLI sem visual, aceita `--json` (futura API/React) |
| `baixar.py` | `selecionar(qtd, ids)`, `baixar_drive`, `gerar_legenda`. Lê `videos.json` do site do pack → Google Drive |
| `limpar-metadados.ps1` | Recodifica sem metadados e nomeia `gta6_NNN.mp4` em `limpos/` |
| `plataformas/agenda.py` | `plano(plataformas, por_hora=None, ate=None)` → `[{plataforma, video, quando}]` |
| `plataformas/comum.py` | Caminhos, `log()`, `carregar_hist/registrar` (postados.json), `textos(video)` (título+tags do .txt) |
| `plataformas/<rede>.py` | Interface comum: `NOME`, `LOGIN_URL`, `AGENDA_NATIVA`, `postar(page, video, revisar, quando, progresso) -> dict` |
| `plataformas/tarefas_windows.py` | Cria/lista tarefas em `\JASON_GTAVI\` no Agendador do Windows |
| `horarios.json` | Grade de horários por plataforma (semana / fim de semana) |

## Estado (não apague sem perguntar)

- `postados.json` — `{ "gta6_001.mp4": { "tiktok": {"status", "para", "link", "em"...}, ... } }`.
  Status: `publicado`, `agendado` (nativo), `agendado_pc` (Windows), `pulado_reivindicacao`, `erro`, `nao_logado`.
  Os 4 primeiros contam como **feito** (`agenda.FEITO`); `erro`/ausente = **pendente**. Faça backup em `logs/` antes de editar à mão.
- `pack_usados.json` — clipes do pack já baixados (versionado; evita repetir entre parceiros).
- `perfil-chrome/` — sessões logadas das contas. **Nunca** ler cookies, versionar ou compartilhar.
- `logs/postar.log` + `logs/erro_<rede>_<data>.png` (print em cada erro) — primeiro lugar a olhar quando algo falha.

## Receitas comuns

```powershell
python jason.py fila                                    # estado atual
python jason.py baixar --qtd 20                         # pega mais vídeos do pack (rápido; a limpeza ffmpeg demora mais)
python jason.py plano   --por-hora 3 --ate 00:00        # "N vídeos por hora até meia-noite" — confira antes
python jason.py agendar --por-hora 3 --ate 00:00 -y     # executa (deixe rodando em segundo plano; demora)
python jason.py agendar -y                              # grade normal do horarios.json (até ~5/dia/plataforma)
python postar.py fila --json                            # saída para máquina
```

Pedido tipo "X vídeos por hora até HH:MM": calcule `X × horas` por plataforma, compare com os pendentes
(`fila`), rode `baixar --qtd` para completar, mostre o `plano` e só então `agendar`. O que sobrar fica pendente.

## Regras e decisões já tomadas pelo usuário

- **Nunca envie/poste usando ferramentas do agente** (claude-in-chrome, computer use etc.). Todo envio passa por
  `jason.py`/`postar.py`. Se algo falhar ou faltar, **corrija o script** (`plataformas/*.py`) e rode a CLI de novo:
  o pipeline existe justamente para não gastar tokens com skills a cada post. O navegador do agente só serve para
  mapear um fluxo novo ou que mudou, antes de escrever o script.
- **Confirme com o usuário antes de publicar de verdade** em uma conta pela 1ª vez num fluxo novo, ou antes de
  aceitar diálogos de consentimento de uma plataforma. Para testar, use `--revisar` (preenche e não publica).
- YouTube: sempre "não é conteúdo para crianças"; publicar mesmo com Content ID (`youtube.py`, constantes no topo).
- TikTok: fechar o popup de "verificações automáticas" sem ativar; aceitar o aviso "Permitir" do agendamento.
- Instagram: corte sempre **Original**; terminar a legenda com espaço (Escape fecha o modal!).
- Senhas nunca em arquivo: login só manual via `python jason.py login` (e depois fechar o Chrome).
- Novas plataformas: mapear o fluxo no Chrome real do usuário (claude-in-chrome) e depois escrever o módulo
  Playwright. O upload pela claude-in-chrome tem limite de 10 MB, por isso os vídeos sobem pelo script.

## Pegadinhas técnicas

- **TikTok** só agenda com minutos múltiplos de 5 e com ≥ 15 min de antecedência. `executar()` troca para
  "postar agora" se o horário ficar a < 16 min durante um lote longo.
- **YouTube**: ao agendar, às vezes aparece o diálogo **"Processando vídeo… ficará público em…"** em vez do de
  compartilhar. Isso é **sucesso** (já tratado). O canal tem limite diário de uploads; lotes grandes podem falhar no fim.
- **Perfil do Chrome é exclusivo**: só um processo por vez. `trava_perfil()` (`logs/perfil-chrome.lock`) serializa
  o lote e as tarefas do Windows. Se o Chrome do script estiver aberto à mão, o envio falha ("browser has been closed").
- Durante um lote, Instagram cujo horário chegar é postado **pelo próprio lote**; a tarefa do Windows depois vê
  `publicado` e não reposta (`enviar --video` pula o que já está publicado).
- `jason.py` força UTF-8 no stdout. Rode comandos longos (agendar/baixar) em segundo plano e acompanhe por `logs/postar.log`.
- Muitos posts por hora podem ser tratados como spam (queda de alcance). O usuário está testando 3/h para medir o desempenho.
