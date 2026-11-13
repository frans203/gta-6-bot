<div align="center">

```
     ██╗ █████╗ ███████╗ ██████╗ ███╗   ██╗
     ██║██╔══██╗██╔════╝██╔═══██╗████╗  ██║
     ██║███████║███████╗██║   ██║██╔██╗ ██║
██   ██║██╔══██║╚════██║██║   ██║██║╚██╗██║
╚█████╔╝██║  ██║███████║╚██████╔╝██║ ╚████║
 ╚════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
━━━━━━━  G T A  V I   ·   P I P E L I N E  ━━━━━━━
```

# 🌴 JASON_GTAVI_PIPELINE 🌅
### *Manual do parceiro — Bem-vindo a Vice City*

`baixar` → `limpar` → `agendar` → **💰 lucro**

</div>

---

## 📼 O QUE É ESSA PARADA

Uma automação que faz o trampo pesado por você:

| Etapa | O que rola |
|---|---|
| 🎬 **Baixar** | Puxa os vídeos do pack direto do Drive |
| 🧼 **Limpar** | Tira todos os metadados (localização, IDs, hash) e deixa o vídeo "saído do forno" |
| ✍️ **Legenda** | Gera título + as 12 tags de GTA 6 pra cada vídeo |
| ⏰ **Agendar** | Joga no **TikTok**, **YouTube Shorts** e **Instagram Reels** nos melhores horários |

> 🌅 Tudo pela linha de comando com a CLI estilizada `jason.py`.

---

## 🧰 MISSÃO 1 — EQUIPAMENTO

Antes de entrar na cidade, instala isso no **Windows**:

| Item | Como pegar |
|---|---|
| 🐍 **Python 3.11+** | https://www.python.org/downloads/ (marque **"Add Python to PATH"**) |
| 🌐 **Google Chrome** | https://www.google.com/chrome |
| 🎞️ **ffmpeg** | No PowerShell: `winget install Gyan.FFmpeg` |
| 🖥️ **Windows Terminal** | Já vem no Windows 11 (pra ver as cores neon direito) |

Depois, na pasta do projeto, instala as dependências:

```powershell
cd C:\caminho\da\pasta\gta6
python -m pip install playwright rich pyfiglet
```

> 💡 Não precisa rodar `playwright install`: o script usa o **seu Chrome instalado**.

### 📦 O que copiar da pasta

Copia a pasta do projeto inteira, **MENOS** estas:

| ❌ Não copiar | Por quê |
|---|---|
| `perfil-chrome/` | É o login de **outra pessoa** (cookies da conta dela) |
| `postados.json` | Histórico de postagem de **outra conta**. Você começa do zero |
| `baixados/`, `limpos/`, `logs/` | Arquivos gerados. Os seus serão criados aí |

---

## 🔐 MISSÃO 2 — ENTRAR NAS SUAS CONTAS

O script usa um **Chrome separado só dele** (a pasta `perfil-chrome`). Você loga nele **uma vez** e pronto: ele lembra pra sempre.

```powershell
python jason.py login
```

Abre um Chrome com 3 abas: **TikTok**, **YouTube Studio** e **Instagram**.

1. Faça login em cada aba com **o seu usuário e a sua senha**, digitando você mesmo.
2. Resolva captcha ou código de verificação (2FA) se aparecer.
3. Espere cada site carregar **já logado** (feed do TikTok, painel do YouTube, feed do Insta).
4. **Feche o Chrome inteiro.**

> ⚠️ **REGRAS DA CASA SOBRE SENHA**
> - A senha **nunca** vai em arquivo, script ou `.txt`. Você digita só no Chrome, na tela de login.
> - O script **não guarda senha nenhuma**. Ele só reaproveita a sessão (cookie) que o Chrome salvou.
> - Não compartilhe a pasta `perfil-chrome` com ninguém: quem tiver ela **entra nas suas contas**.
> - Se um dia o script reclamar de `nao_logado`, é só rodar `python jason.py login` de novo.

> 🧠 **Por que não usa o meu Chrome normal?** O Chrome não deixa programa nenhum controlar o perfil principal enquanto você usa ele. Por isso o script tem o Chrome próprio dele.

---

## 🏁 MISSÃO 3 — A ROTINA DO DIA

### 🌅 Tela inicial
```powershell
python jason.py
```
Mostra o logo de Vice City, quantos vídeos tem, quantos já postou, os pendentes e o próximo agendamento.

### 🎬 1. Baixar + limpar vídeos novos
```powershell
python jason.py baixar --qtd 5
```
Baixa os **próximos 5** do pack (HD primeiro), limpa os metadados e cria a legenda `.txt` de cada um em `limpos\`. Nunca baixa o mesmo duas vezes.

> 🤝 **Sem repetir clipe entre parceiros:** tudo que é baixado do pack fica registrado no `pack_usados.json` (qual vídeo do pack, quando, e em qual `gta6_NNN` virou). Esse arquivo **vai pro git**: dê `git pull` antes de baixar e `git commit` + `git push` depois. Assim um nunca pega o mesmo vídeo que o outro.
> Quer marcar quem baixou? No PowerShell: `$env:JASON_OPERADOR = "seunome"` antes de rodar.

> ✍️ Quer mudar o título de algum vídeo? Abre o `limpos\gta6_XXX.txt` e edita antes de agendar.

### 📋 2. Ver a fila
```powershell
python jason.py fila
```
Tabela **vídeo × plataforma** com cores:

| Status | Significa |
|---|---|
| 🟢 `publicado` | Já está no ar |
| 🩷 `agendado` | Agendado na própria plataforma (TikTok/YouTube) |
| 🟠 `agendado pc` | Agendado no Windows (Instagram), **precisa do PC ligado** |
| ⚪ `pendente` | Ainda não foi |
| 🔴 `erro` / `nao logado` | Deu ruim. Veja a seção **WASTED** lá embaixo |

### 🗓️ 3. Conferir o plano (não envia nada)
```powershell
python jason.py plano
```
Mostra **qual vídeo vai pra qual plataforma e em que horário**.

### 🚀 4. Agendar tudo
```powershell
python jason.py agendar
```
Mostra o plano, pede confirmação e manda ver com a barra de progresso neon. O Chrome do script abre sozinho e faz tudo. **Não mexa nele enquanto trabalha.**

- 🩷 **TikTok e YouTube:** sobem na hora e ficam **agendados na própria plataforma**. Saem sozinhos no horário, mesmo com o PC desligado.
- 🟠 **Instagram:** a versão web **não tem agendamento**, então o script cria tarefas no **Agendador do Windows** (pasta `\JASON_GTAVI\`). **O PC precisa estar ligado e com você logado no Windows** nesses horários.

```powershell
python jason.py tarefas     # vê os agendamentos do Instagram no Windows
```

> 🧾 Ele **nunca repete**: tudo que foi postado ou agendado fica anotado em `postados.json`. Vídeo que já foi pro TikTok mas não pro Insta? Ele manda só pro Insta.

### ⚡ Postar AGORA (sem agendar)
```powershell
python jason.py enviar -p tiktok,youtube,instagram
python jason.py enviar -p youtube --video limpos\gta6_004.mp4
python jason.py enviar -p tiktok --revisar      # preenche tudo e NÃO publica (pra conferir)
```

---

## ⏰ OS HORÁRIOS — QUANDO A CIDADE ESTÁ ACORDADA

> 🎯 **A meta é uns 5 posts por dia em CADA plataforma.** O TikTok recomenda de 1 a 4 por dia, então 5 é o teto: dá alcance sem parecer spam. Mais que isso não ajuda e pode derrubar a entrega.

Horário de **Brasília**. O script escolhe sozinho o próximo horário livre:

### ♪ TikTok
| | 1º | 2º | 3º | 4º | 5º |
|---|---|---|---|---|---|
| **Seg–Sex** | 08:00 | 12:30 | 18:00 | 20:30 | 22:30 |
| **Sáb–Dom** | 09:30 | 12:30 | 18:00 | 20:30 | 22:30 |

### ▶ YouTube Shorts
| | 1º | 2º | 3º | 4º | 5º |
|---|---|---|---|---|---|
| **Seg–Sex** | 12:00 | 16:00 | 18:00 | 20:00 | 22:00 |
| **Sáb–Dom** | 10:00 | 12:00 | 15:00 | 18:00 | 21:00 |

### ◎ Instagram Reels
| | 1º | 2º | 3º | 4º | 5º |
|---|---|---|---|---|---|
| **Seg–Sex** | 09:00 | 11:30 | 13:00 | 19:00 | 21:00 |
| **Sáb–Dom** | 10:00 | 12:00 | 14:00 | 17:00 | 20:00 |

**Por que esses horários?**
- 🌙 **Noite (18h–22h)** é o pico geral no Brasil, e no nicho **games** o auge é **20h–22h**.
- 🍔 **Almoço (11h30–13h)** funciona muito pra Reels.
- ☀️ **Manhã cedo** pega o pessoal no trajeto/escola.
- 🎮 **Fim de semana** a galera gamer está mais livre, então dá pra começar mais cedo.

> 🔧 Quer mudar? Edita o `horarios.json`. O TikTok só aceita minutos de **5 em 5** (`08:00`, `08:05`...).

> 📈 **Dica de quem já jogou:** depois de 2 semanas, olha no **TikTok Studio → Análise → Seguidores** (e nos Insights do Insta/YouTube) em que horário o **seu** público está online e ajusta. Média de mercado < dado do seu perfil.

Pesquisa completa em `horarios-tiktok.md`.

### 🗓️ Rotina sugerida
```
☕ De manhã (1x por dia):
   python jason.py baixar --qtd 5
   python jason.py agendar

🌴 Pronto. São 5 vídeos × 3 plataformas = 15 posts no dia, cada um no horário certo.
   (Deixe o PC ligado nos horários do Instagram.)
```

---

## 📜 AS REGRAS DO JOGO (configurações já decididas)

| Regra | Como está |
|---|---|
| 👶 **YouTube: "é conteúdo para crianças?"** | Sempre marca **NÃO**. Se o seu conteúdo for diferente, mude `FEITO_PARA_CRIANCAS` em `plataformas/youtube.py` |
| ©️ **YouTube: "conteúdo reivindicado" (Content ID)** | **Publica mesmo assim**. Pra pular esses vídeos: `PUBLICAR_COM_REIVINDICACAO = False` |
| 🔍 **TikTok: "ativar verificações automáticas?"** | Fecha **sem ativar** |
| 🖼️ **Instagram: corte** | Sempre **Original** (vertical 9:16 inteiro) |
| 🏷️ **Tags** | `#gta6 #gtavi #gta #rockstargames #vicecity #gta6trailer #gameplay #gamer #viral #fyp #shorts #gaming` (mude em `baixar.py` e `plataformas/comum.py`) |

---

## 💀 WASTED — QUANDO DÁ RUIM

| Sintoma | Solução |
|---|---|
| `nao_logado` | `python jason.py login`, loga de novo e **fecha o Chrome** |
| Erro *"Target page, context or browser has been closed"* | O Chrome do script ainda está aberto. Feche ele e rode de novo |
| `erro` numa plataforma | Tem um **print da tela** em `logs\erro_<plataforma>_<data>.png` e o histórico em `logs\postar.log` |
| Instagram não postou no horário | O PC estava desligado/bloqueado. Rode `python jason.py enviar -p instagram` |
| Captcha / "confirme que é você" | Rode `python jason.py login` e resolva **na mão** |
| Cores feias / caracteres estranhos | Use o **Windows Terminal** e deixe a janela larga (110+ colunas) |
| Site mudou o layout | Os passos de cada plataforma estão em `plataformas/*.py` e no `TODO.md`. Pode ser preciso reajustar um seletor |

---

## 🗺️ MAPA DA CIDADE (arquivos)

```
gta6/
├── jason.py               🌅 a CLI estilizada (use essa)
├── postar.py              ⚙️ núcleo de envio (aceita --json, pra futura página React)
├── baixar.py              🎬 baixa do pack
├── limpar-metadados.ps1   🧼 limpa metadados (ffmpeg)
├── horarios.json          ⏰ grade de horários
├── plataformas/
│   ├── tiktok.py          ♪
│   ├── youtube.py         ▶
│   ├── instagram.py       ◎
│   ├── agenda.py          🗓️ monta o plano
│   └── tarefas_windows.py 🪟 agendamento local do Instagram
├── limpos/                ✨ vídeos prontos + legendas .txt
├── postados.json          🧾 o que já foi pra onde
└── perfil-chrome/         🔐 SEU login (não compartilhe!)
```

---

<div align="center">

### 🌴 MISSION PASSED 🌴
**RESPECT +**

*Bem-vindo a Leonida, parceiro.*

</div>
