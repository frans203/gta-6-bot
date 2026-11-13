# 🌴 JASON_GTAVI_PIPELINE

Automação que pega clipes de GTA 6 do pack, **limpa os metadados** e **posta/agenda** no
**TikTok**, **YouTube Shorts** e **Instagram Reels** pelo navegador (Playwright + Chrome).

`baixar` → `limpar` → `agendar` → 💰

> Manual completo (instalação, login, horários, problemas): **[TUTORIAL.md](TUTORIAL.md)**
> Contexto para agentes de IA: **[CLAUDE.md](CLAUDE.md)** · Progresso: **[TODO.md](TODO.md)**

## Começo rápido

```powershell
python -m pip install playwright rich pyfiglet     # + Chrome e ffmpeg instalados
python jason.py login                              # 1x: loga nas 3 contas e FECHA o Chrome
python jason.py                                    # tela inicial com status
```

## Comandos

| Comando | O que faz |
|---|---|
| `python jason.py baixar --qtd 10` | Baixa os próximos 10 do pack, limpa metadados e gera a legenda `.txt` em `limpos/` |
| `python jason.py fila` | Tabela vídeo × plataforma (publicado / agendado / pendente / erro) |
| `python jason.py plano` | Mostra o que seria agendado e quando (**não envia nada**) |
| `python jason.py agendar [-y]` | Agenda **todos** os pendentes na grade de melhores horários (`horarios.json`) |
| `python jason.py agendar --por-hora 3 --ate 00:00 -y` | **Modo lote**: N posts por hora em cada plataforma até o horário limite |
| `python jason.py enviar -p tiktok,youtube` | Posta **agora** o próximo pendente de cada plataforma |
| `python jason.py enviar -p youtube --video limpos\gta6_004.mp4` | Posta um vídeo específico agora |
| `python jason.py enviar -p tiktok --revisar` | Preenche tudo e **não** publica (pra conferir) |
| `python jason.py tarefas` | Lista os agendamentos do Instagram no Agendador do Windows |
| `python jason.py login` | Abre o Chrome do script para logar de novo |

Todos aceitam `-p tiktok,youtube,instagram` para escolher plataformas.
`postar.py` tem os mesmos comandos sem visual e com `--json` (para automação/API).

## Modo lote (`--por-hora` / `--ate`)

```powershell
python jason.py plano   --por-hora 3 --ate 00:00      # confere
python jason.py agendar --por-hora 3 --ate 00:00 -y   # agenda
```

- `--por-hora N`: N horários por hora, espalhados com minutos múltiplos de 5 (o TikTok exige).
  3/h → `:00 :20 :40` · 5/h → `:00 :10 :25 :35 :50`.
- `--ate HH:MM`: limite (exclusivo). `00:00` = próxima meia-noite. Padrão: `00:00`.
- O 1º horário é **≥ 30 min a partir de agora** (tempo de upload).
- Vídeo que não couber **continua pendente** e é usado no próximo `plano`/`agendar`. Nada se perde,
  e o `pack_usados.json` impede baixar o mesmo clipe do pack de novo.
- Quantos vídeos preciso? `N × horas restantes` por plataforma. Ex.: 3/h das 18h à meia-noite = 18.
  Rode `baixar --qtd X` antes se faltar.

## Como cada plataforma é agendada

| Plataforma | Como | PC precisa ficar ligado? |
|---|---|---|
| ♪ TikTok | Agenda nativa do TikTok Studio ("Programar") | Não (só durante o upload) |
| ▶ YouTube | Agenda nativa do YouTube Studio | Não (só durante o upload) |
| ◎ Instagram | A web não agenda → tarefa no **Agendador do Windows** (`\JASON_GTAVI\`) que roda `postar.py enviar` no horário | **Sim** |

## ⚠️ Nunca versionar

`perfil-chrome/` (sessões logadas das contas), `postados.json` (histórico da sua conta), `limpos/`, `baixados/`, `logs/`.
O `pack_usados.json` **vai** pro git (os parceiros não repetem clipes): `git pull` antes de baixar, commit depois.
