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

# 🍎 JASON_GTAVI_PIPELINE — edição **Mac** 🌴
### *Manual do parceiro que usa macOS*

`baixar` → `limpar` → `agendar` → **💰 lucro**

</div>

> Este é o tutorial **só para Mac**. Quem usa Windows segue o [TUTORIAL.md](TUTORIAL.md).
> Os comandos do dia a dia são os mesmos. O que muda no Mac é a instalação, os caminhos (`/` em vez de `\`)
> e o agendamento do Instagram, que usa o **launchd** do macOS em vez do Agendador do Windows.

---

## 📼 O QUE É ESSA PARADA

| Etapa | O que rola |
|---|---|
| 🎬 **Baixar** | Puxa os vídeos do pack direto do Drive |
| 🧼 **Limpar** | Tira todos os metadados (localização, IDs, hash) e deixa o vídeo "saído do forno" |
| ✍️ **Legenda** | Gera título + as 12 tags de GTA 6 pra cada vídeo |
| ⏰ **Agendar** | Joga no **TikTok**, **YouTube Shorts** e **Instagram Reels** nos melhores horários |
| ✂️ **Cortador** | Transforma lives da Twitch/YouTube em cortes verticais com legenda |

---

## 🧰 MISSÃO 1 — EQUIPAMENTO

Abra o **Terminal** (⌘ + Espaço → digite `Terminal`). Tudo abaixo é colado lá.

### 1. Homebrew (o "instalador" do Mac)

Se ainda não tiver, instale pelo site **https://brew.sh** (copie o comando que aparece lá e cole no Terminal).
No fim, ele mostra 2 ou 3 linhas em **"Next steps"**. **Rode essas linhas**, senão o comando `brew` não funciona.

### 2. Programas

```bash
brew install python@3.12 ffmpeg node git
brew install --cask google-chrome      # pule se já tiver o Chrome
```

| Item | Para quê |
|---|---|
| 🐍 **Python 3.12** | Roda o projeto |
| 🎞️ **ffmpeg** | Limpa os metadados e renderiza os cortes |
| 🟩 **Node.js** | Monta a interface web |
| 🌐 **Google Chrome** | O script controla o **Chrome de verdade** (precisa estar em `/Applications`) |

### 3. Baixar o projeto

```bash
cd ~
git clone https://github.com/frans203/gta-6-bot.git gta6
cd ~/gta6
```

> 🔒 O repositório é privado: peça para o dono te adicionar como colaborador no GitHub antes.
> Se o `git` pedir senha, use um **token** do GitHub (Settings → Developer settings → Personal access tokens),
> não a sua senha.

### 4. Ambiente do Python (uma vez só)

```bash
cd ~/gta6
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

> ⚠️ **Toda vez que abrir um Terminal novo**, entre na pasta e ative o ambiente antes de usar:
> ```bash
> cd ~/gta6 && source .venv/bin/activate
> ```
> Você sabe que está ativo quando aparece `(.venv)` no começo da linha.

> 💡 Não precisa rodar `playwright install`: o script usa o **seu Chrome instalado**.

### 5. Interface web (uma vez só)

```bash
cd ~/gta6/frontend && npm install && npm run build && cd ..
```

### 6. Configuração (opcional)

```bash
cp .env.example .env
open -e .env
```

No Mac, **apague a linha `JASON_MIDIA=E:\jason-midia`** (isso é do Windows). Sem ela, os vídeos pesados ficam em
`~/gta6/midia`. Se quiser usar um HD externo, escreva por exemplo `JASON_MIDIA=/Volumes/MeuHD/jason-midia`.

> 🕒 **Fuso horário:** os horários de postagem usam o **relógio do Mac**. Confira em
> Ajustes do Sistema → Geral → Data e Hora que está em **Brasília (São Paulo)**.

---

## 🔐 MISSÃO 2 — ENTRAR NAS SUAS CONTAS

O script usa um **Chrome separado só dele** (a pasta `perfil-chrome`). Você loga nele **uma vez** e pronto.

```bash
python jason.py login
```

Abre um Chrome com 3 abas: **TikTok**, **YouTube Studio** e **Instagram**.

1. Faça login em cada aba com **o seu usuário e a sua senha**, digitando você mesmo.
2. Resolva captcha ou código de verificação (2FA) se aparecer.
3. Espere cada site carregar **já logado**.
4. **Feche o Chrome inteiro com ⌘ + Q** (só fechar a janela no ✕ deixa ele aberto no Mac!).

> 🇧🇷 **As três redes precisam estar em PORTUGUÊS** (o script procura os botões pelos textos em PT).
> Se alguma estiver em inglês, troque o idioma nas configurações da conta.

> ⚠️ **REGRAS DA CASA SOBRE SENHA**
> - A senha **nunca** vai em arquivo, script ou `.txt`. Você digita só no Chrome.
> - O script **não guarda senha nenhuma**. Ele só reaproveita a sessão que o Chrome salvou.
> - Não compartilhe a pasta `perfil-chrome` com ninguém: quem tiver ela **entra nas suas contas**.
> - Se o script reclamar de `nao_logado`, rode `python jason.py login` de novo.

---

## 🏁 MISSÃO 3 — A ROTINA DO DIA

Sempre comece com:

```bash
cd ~/gta6 && source .venv/bin/activate
git pull
```

### 🎬 1. Baixar + limpar vídeos novos
```bash
python jason.py baixar --qtd 5
```
Baixa os **próximos 5** do pack, limpa os metadados (no Mac isso é feito pelo ffmpeg, automático) e cria a
legenda `.txt` de cada um em `limpos/`.

> 🤝 **Sem repetir clipe entre parceiros:** o que é baixado fica registrado no `pack_usados.json`, que vai pro git.
> Depois de baixar, mande o registro para os outros:
> ```bash
> git add pack_usados.json && git commit -m "pack: baixei mais vídeos" && git push
> ```
> Quer marcar quem baixou? Rode `export JASON_OPERADOR=seunome` antes.

> ✍️ Quer mudar o título de um vídeo? `open -e limpos/gta6_XXX.txt` e edite antes de agendar.

### 📋 2. Ver a fila
```bash
python jason.py fila
```

| Status | Significa |
|---|---|
| 🟢 `publicado` | Já está no ar |
| 🩷 `agendado` | Agendado na própria plataforma (TikTok/YouTube) |
| 🟠 `agendado pc` | Agendado **no Mac** (Instagram), **precisa do Mac ligado** |
| ⚪ `pendente` | Ainda não foi |
| 🔴 `erro` / `nao logado` | Deu ruim. Veja a seção **WASTED** lá embaixo |

### 🗓️ 3. Conferir o plano (não envia nada)
```bash
python jason.py plano
```

### 🚀 4. Agendar tudo
```bash
python jason.py agendar
```
O Chrome do script abre sozinho e faz tudo. **Não mexa nele enquanto trabalha.**

- 🩷 **TikTok e YouTube:** ficam **agendados na própria plataforma**. Saem sozinhos, mesmo com o Mac desligado.
- 🟠 **Instagram:** a versão web **não tem agendamento**, então o script cria um agendamento no **launchd**
  (o agendador do macOS). **O Mac precisa estar ligado e com você logado** nesses horários.

```bash
python jason.py tarefas     # vê os agendamentos do Instagram no Mac
```

### 🔥 Modo lote: N por hora até um horário
```bash
python jason.py plano   --por-hora 3 --ate 00:00      # confere
python jason.py agendar --por-hora 3 --ate 00:00 -y   # agenda
```
Agenda **N posts por hora em cada plataforma** até o horário. Precisa de `N × horas` vídeos pendentes: se faltar,
rode `baixar --qtd X` antes. O que não couber fica pendente.

> ⚠️ Muitos posts seguidos podem derrubar o alcance e o YouTube tem limite diário de uploads. Comece com pouco.

### ⚡ Postar AGORA (sem agendar)
```bash
python jason.py enviar -p tiktok,youtube,instagram
python jason.py enviar -p youtube --video limpos/gta6_004.mp4
python jason.py enviar -p tiktok --revisar      # preenche tudo e NÃO publica (pra conferir)
```

---

## 🍎 O INSTAGRAM NO MAC (launchd) — LEIA ISSO

Cada post do Instagram vira um arquivo em `~/Library/LaunchAgents/app.jason.<nome>.plist`. No horário, o macOS
roda o `postar.py` sozinho, e depois o agendamento se apaga.

| Situação | O que acontece |
|---|---|
| Mac ligado e você logado | ✅ Posta no horário |
| Mac **dormindo** (tampa fechada, repouso) | ⏳ Posta **quando o Mac acordar** (atrasado) |
| Mac **desligado** no horário | ❌ Não posta. Rode `python jason.py enviar -p instagram` depois |
| Você **saiu da sessão** (logout) | ❌ Não posta |

**Dicas para não perder horário:**
- Ajustes do Sistema → **Bateria/Energia** → impeça o repouso automático quando estiver na tomada.
- Ou deixe um Terminal aberto com `caffeinate -i` (o Mac não dorme enquanto ele estiver rodando; `Ctrl + C` para).
- **Não mova nem renomeie a pasta `~/gta6`** nem apague o `.venv` depois de agendar: os agendamentos apontam
  para esse caminho.
- O que os agendamentos imprimem fica em `logs/agendados_mac.log`.

Para ver ou apagar agendamentos na mão:
```bash
ls ~/Library/LaunchAgents/ | grep app.jason          # lista
launchctl bootout gui/$(id -u)/app.jason.<nome>      # cancela um
rm ~/Library/LaunchAgents/app.jason.<nome>.plist
```

---

## ⏰ OS HORÁRIOS

São os mesmos do Windows (horário de **Brasília**, ~5 posts por dia em cada rede). A tabela completa está no
[TUTORIAL.md](TUTORIAL.md#-os-horários--quando-a-cidade-está-acordada). Para mudar: `open -e horarios.json`
(o TikTok só aceita minutos de 5 em 5).

### 🗓️ Rotina sugerida
```
☕ De manhã (1x por dia):
   cd ~/gta6 && source .venv/bin/activate && git pull
   python jason.py baixar --qtd 5
   python jason.py agendar
   git add pack_usados.json && git commit -m "pack" && git push

🌴 Pronto. 5 vídeos × 3 plataformas = 15 posts no dia.
   (Deixe o Mac ligado e acordado nos horários do Instagram.)
```

---

## 📜 AS REGRAS DO JOGO (já decididas)

| Regra | Como está |
|---|---|
| 👶 **YouTube: "é conteúdo para crianças?"** | Sempre **NÃO** (`FEITO_PARA_CRIANCAS` em `backend/app/plataformas/youtube.py`) |
| ©️ **YouTube: Content ID** | **Publica mesmo assim** (`PUBLICAR_COM_REIVINDICACAO`) |
| 🔍 **TikTok: "ativar verificações automáticas?"** | Fecha **sem ativar** |
| 🖼️ **Instagram: corte** | Sempre **Original** (9:16 inteiro) |

---

## 🖥️ MISSÃO 4 — A INTERFACE WEB

```bash
python jason.py web
```

Abra **http://127.0.0.1:8765** no navegador: **Painel**, **Fila**, **Agenda**, **Cortador**, **Jobs**, **Logs** e
**Contas**. Tarefas longas viram **jobs** em segundo plano (dá pra acompanhar e cancelar).
Para fechar: `Ctrl + C` no Terminal (é **Ctrl** mesmo, não ⌘). Se um envio estiver no meio, espere terminar.

## ✂️ MISSÃO 5 — O CORTADOR

Funciona igual ao Windows (passo a passo no [TUTORIAL.md](TUTORIAL.md#️-missão-5--o-cortador-cortes-de-lives)).
O que muda no Mac:

- 🎞️ **Render rápido:** em Mac com chip Apple (M1/M2/M3/M4), o vídeo é codificado pelo próprio chip
  (VideoToolbox), automático.
- 🗣️ **Legenda (Whisper):** no Mac roda no processador (não tem placa NVIDIA). O modelo `small` é um bom equilíbrio.
  Se ficar lento, coloque `JASON_WHISPER_MODELO=base` no `.env`.
- 📥 Na 1ª vez ele baixa os modelos (Whisper, detector de rosto, tradução) para `midia/modelos`. Precisa de internet.
- 🔑 **Clipes da Twitch:** crie um app grátis em https://dev.twitch.tv/console/apps e coloque
  `JASON_TWITCH_CLIENT_ID` e `JASON_TWITCH_CLIENT_SECRET` no `.env`.

### 👥 Mais de uma conta
Na tela **Contas** dá pra criar outra conta. Login dela: botão **Abrir Chrome para login** ou
`python jason.py --conta gamer_en login`. Todos os comandos aceitam `--conta`.

---

## 💀 WASTED — QUANDO DÁ RUIM (Mac)

| Sintoma | Solução |
|---|---|
| `command not found: python` | Ative o ambiente: `cd ~/gta6 && source .venv/bin/activate` |
| `command not found: brew` | Rode as linhas de **"Next steps"** que o instalador do Homebrew mostrou e abra um Terminal novo |
| `ModuleNotFoundError` | Ambiente não ativado, ou falta `python -m pip install -r backend/requirements.txt` |
| `nao_logado` | `python jason.py login`, loga de novo e **feche o Chrome com ⌘ + Q** |
| *"Target page, context or browser has been closed"* / perfil ocupado | O Chrome do script ainda está aberto. ⌘ + Q nele (ou `pkill -f perfil-chrome`) e rode de novo |
| Login não abre o Chrome | O Chrome não está em `/Applications`. Coloque no `.env`: `JASON_CHROME=/caminho/Google Chrome.app/Contents/MacOS/Google Chrome` |
| `ffmpeg: command not found` | `brew install ffmpeg` |
| Instagram não postou no horário | Mac desligado, dormindo ou deslogado. Rode `python jason.py enviar -p instagram` |
| `launchctl: ...` ao agendar | Rode `python jason.py tarefas` e apague agendamentos velhos com o mesmo nome (veja a seção do launchd) |
| Captcha / "confirme que é você" | `python jason.py login` e resolva **na mão** |
| Botão não encontrado / timeout | Confira se a rede está em **português**. Veja o print em `logs/erro_<rede>_<data>.png` e o `logs/postar.log` |
| Parar um lote no meio | Na interface: cancele o job na tela **Jobs**. No Terminal: `Ctrl + C` |

Para abrir a pasta de logs no Finder: `open logs`.

---

## 🗺️ MAPA DA CIDADE (arquivos)

```
~/gta6/
├── jason.py / postar.py / baixar.py   atalhos (o código está em backend/)
├── horarios.json          ⏰ grade de horários
├── .env                   ⚙️ configuração deste Mac (copie do .env.example)
├── .venv/                 🐍 ambiente do Python (não apague depois de agendar)
├── backend/app/           🧠 o código (plataformas, agenda, cortador, API)
├── frontend/              🖥️ a interface
├── dados/jason.db         🧾 o que já foi pra onde (SEU histórico, não vai pro git)
├── limpos/                ✨ vídeos prontos + legendas .txt
├── midia/                 💾 cortes, VODs e modelos
├── logs/                  📜 logs e prints de erro
└── perfil-chrome/         🔐 SEU login (não compartilhe!)

~/Library/LaunchAgents/app.jason.*.plist   🟠 agendamentos do Instagram
```

---

<div align="center">

### 🌴 MISSION PASSED 🌴
**RESPECT +**

*Bem-vindo a Leonida, parceiro do Mac.*

</div>
