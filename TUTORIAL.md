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

🍎 **Usa Mac?** Siga o [TUTORIAL-MAC.md](TUTORIAL-MAC.md).

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
python -m pip install -r backend/requirements.txt
```

> Para a interface web também precisa do **Node.js 20+** (https://nodejs.org) e, uma vez só: `cd frontend; npm install; npm run build`.

> 💡 Não precisa rodar `playwright install`: o script usa o **seu Chrome instalado**.

### 📦 O que copiar da pasta

Copia a pasta do projeto inteira, **MENOS** estas:

| ❌ Não copiar | Por quê |
|---|---|
| `perfil-chrome/` | É o login de **outra pessoa** (cookies da conta dela) |
| `dados/` | Banco com o histórico de postagem de **outra conta**. Você começa do zero |
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

> 🧾 Ele **nunca repete**: tudo que foi postado ou agendado fica anotado no banco (`dados/jason.db`). Vídeo que já foi pro TikTok mas não pro Insta? Ele manda só pro Insta.

### 🔥 Modo lote: N por hora até um horário
```powershell
python jason.py plano   --por-hora 3 --ate 00:00      # confere
python jason.py agendar --por-hora 3 --ate 00:00 -y   # agenda
```
Ignora a grade do `horarios.json` e agenda **N posts por hora em cada plataforma** até o limite
(`00:00` = meia-noite). 3/h → `:00 :20 :40`. Precisa de `N × horas` vídeos pendentes: se faltar, rode
`baixar --qtd X` antes. **O que não couber fica pendente** e é usado no próximo agendamento.

> ⚠️ Muitos posts seguidos podem derrubar o alcance (cara de spam) e o YouTube tem limite diário de uploads. Comece com pouco e acompanhe o desempenho.

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
| 👶 **YouTube: "é conteúdo para crianças?"** | Sempre marca **NÃO**. Se o seu conteúdo for diferente, mude `FEITO_PARA_CRIANCAS` em `backend/app/plataformas/youtube.py` |
| ©️ **YouTube: "conteúdo reivindicado" (Content ID)** | **Publica mesmo assim**. Pra pular esses vídeos: `PUBLICAR_COM_REIVINDICACAO = False` |
| 🔍 **TikTok: "ativar verificações automáticas?"** | Fecha **sem ativar** |
| 🖼️ **Instagram: corte** | Sempre **Original** (vertical 9:16 inteiro) |
| 🏷️ **Tags** | `#gta6 #gtavi #gta #rockstargames #vicecity #gta6trailer #gameplay #gamer #viral #fyp #shorts #gaming` (mude em `backend/app/servicos/pack.py` e `backend/app/plataformas/comum.py`; nas contas novas, as tags ficam na tela **Contas**) |

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
| Site mudou o layout | Os passos de cada plataforma estão em `backend/app/plataformas/*.py` e no `TODO.md`. Pode ser preciso reajustar um seletor |

---

## 🖥️ MISSÃO 4 — A INTERFACE WEB

```powershell
python jason.py web
```

Abre `http://127.0.0.1:8765` no navegador com tudo num lugar só: **Painel**, **Cortar vídeo**, **Biblioteca**, **Fila**,
**Modelos de corte**, **Contas**, **Jobs** e **Logs**. Tarefas longas (postar, agendar, baixar, renderizar)
viram **jobs** que rodam em segundo plano. Dá para acompanhar o progresso ao vivo e cancelar.
Feche com `Ctrl+C` no terminal. Se um envio estiver no meio, espere ele terminar.

### 🗓️ Agendar um vídeo (horário diferente em cada rede)

Na **Fila**, clique no ícone de calendário do vídeo (ou abra o vídeo → aba **Agendar**). Na **Biblioteca**, o corte
pronto tem **Mandar e agendar** (manda para a fila e já abre aqui) e o que já está na fila tem **Agendar**.

- Uma coluna por rede (**TikTok**, **YouTube Shorts**, **Instagram Reels**) com os **melhores horários** dos
  próximos 3 dias (vêm do `horarios.json`). ★ = horário de pico; **ocupado** = outro vídeo já está nesse horário.
- Escolha **um horário em cada rede** (podem ser diferentes), digite **outro horário** ou marque **Não agendar nesta rede**.
- **Agendar** abre o Chrome do script e agenda em cada rede. Mínimo de 30 min de antecedência; minutos de 5 em 5.
- Instagram: quem posta no horário é o computador (precisa estar ligado). Para desistir, use **Desmarcar**.
  TikTok/YouTube já agendados só mudam no próprio site.

## ✂️ MISSÃO 5 — O CORTADOR (cortes de lives)

### ⚡ Jeito rápido: **Cortar vídeo** (menu lateral)

1. Cole o **link** (Twitch, YouTube, Kick ou outro site) → **Ler link**: ele mostra a plataforma, o canal,
   a duração e se o streamer já está cadastrado (se não estiver, cadastra sozinho).
2. **Quantos cortes?** (1 a 20), a duração de cada um e o modelo → **Fazer os cortes**.
3. Ele acha os melhores trechos e já prepara cada um: procura o **streamer**, mede as **barras pretas** e
   descobre o **idioma falado**. Quando termina, abre o vídeo direto na **Biblioteca**.

### 📚 Biblioteca (revisar, renderizar, mandar para a fila)

- **Para revisar**: um card por **vídeo original** (capa, título, quantos cortes, aviso de webcam pendente).
  Clique para abrir o modal do vídeo:
  - **Cortes para gerar**: os trechos encontrados (#1, #2... na ordem em que aparecem no vídeo). O selo
    amarelo **“marcar a webcam”** quer dizer que o streamer não foi identificado com segurança.
  - **Renderizar todos** gera os que já estão liberados.
  - **Ajustes para todos os cortes**: legenda (original ou traduzida, tradução grátis no seu PC; na 1ª vez
    baixa ~80 MB), modelo de corte e **imagem de fundo** (quando há muito espaço preto: imagem atrás, vídeo
    em cima, legenda, streamer embaixo).
- Clique num corte para abrir o editor, com duas abas:
  - **Corte**: trecho original, início/fim, título, **gancho** (texto dos primeiros segundos), modelo,
    legenda, score e **Renderizar**.
  - **Cara do streamer**: o quadro com o retângulo **STREAMER** e a **prévia** do vertical. Arraste o
    retângulo até a webcam (puxe o canto para o tamanho). **Detectar de novo** procura de novo e mostra a
    barra de progresso. Sem o streamer identificado ou marcado à mão, o Renderizar fica bloqueado: nunca
    sai um corte com a webcam errada.
- **Prontos**: um card por corte gerado (`#N · data · título do vídeo original`). Passe o mouse para ver o
  vídeo. Clique para abrir: mesmo editor, com **Mandar para a fila** (entra na fila da conta e é agendado
  igual aos outros vídeos). Mudou a região do streamer de um corte pronto? Ele **gera o vídeo de novo sozinho**.
- **Na fila** e **Descartados**: os que já foram para a fila e os que você descartou (dá para restaurar).

### 📡 Vigia de clipes (Twitch)

Na página do streamer da Twitch, aba **Vigia de clipes**: ligue e ele olha os clipes que o público faz a cada
poucos minutos. Quando um clipe passa do **mínimo de views**, vira um corte **com contexto da live** (por padrão
20 s antes e 10 s depois, tirados do VOD) e aparece na Biblioteca para você revisar. Vários clipes do mesmo momento
viram um corte só. Se a live ainda está no ar, ele **espera** o VOD gravar o contexto "depois". No corte, os botões
**+10 s antes / +10 s depois** puxam mais contexto. Ele **nunca** renderiza nem posta sozinho.
Precisa da API oficial da Twitch no `.env` (`JASON_TWITCH_CLIENT_ID` e `JASON_TWITCH_CLIENT_SECRET`).

### 🎬 Editor de vídeo

No modal de qualquer corte, **Editar vídeo**. Na 1ª vez ele prepara o corte: baixa o trecho com 10 s de folga
de cada lado e transcreve a fala (leva até ~1 minuto). Depois:

- **Prévia** (esquerda): arraste as caixas **JOGO** e **STREAMER** para mover e puxe os cantos para o tamanho
  (**Shift** mantém a proporção, **Alt** desliga o ímã das bordas/centro). Arraste a linha **LEGENDA** ou
  **GANCHO** para subir/descer o texto.
- **Texto**: fonte, cor do texto e da palavra falada, tamanho, contorno, palavras por vez, CAIXA ALTA; o gancho
  com cor do texto e da caixa. **↑ fonte** envia um arquivo `.ttf`/`.otf` seu.
- **Layout**: arrumações prontas (jogo em cima, streamer em cima, streamer no canto, só o jogo), mostrar/esconder
  o streamer, quem fica na frente, fundo (vídeo desfocado, preto ou sua imagem) e **o que recortar** do vídeo
  original. Se o streamer não tiver sido confirmado, marque o retângulo (nunca sai com a webcam errada).
- **Tempo**: **manter streamer e jogo sincronizados** (ligado: os dois vêm do mesmo vídeo, então todo corte vale
  para os dois). Desligado, aparece um ajuste de atraso para quando a câmera da live vem adiantada/atrasada.
- **Linha do tempo** (embaixo): **S** corta no cursor, **Delete** apaga o trecho selecionado, arraste um trecho
  para mudar a ordem e puxe as pontas para aparar (dá para usar a folga baixada). A barra de baixo mostra de onde
  cada trecho saiu do vídeo original.
- **Conferir no render** mostra 1 quadro gerado pelo mesmo ffmpeg do vídeo final. **Salvar e gerar vídeo**
  renderiza. **Ctrl+Z** desfaz; se fechar sem salvar, o rascunho fica guardado neste navegador.

> 🎯 **Por streamer**: no modal, clique no nome do streamer para abrir a página dele (buscar VODs, analisar
> uma live inteira, modelo e webcam padrão).

> 🧩 **Modelos de corte** (menu lateral): o padrão é **jogo em cima + streamer embaixo**, com a legenda na
> divisa. Lá você ajusta a altura do jogo, a posição da legenda (em cima / no meio / embaixo ou no slider),
> a posição do gancho, a barra de progresso e o crédito, vendo a prévia real. Dá para duplicar e ter
> vários modelos; cada streamer usa um, e cada corte pode trocar.
>
> 🔑 **Clipes da Twitch** precisam da API oficial (grátis): crie um app em https://dev.twitch.tv/console/apps
> e coloque `JASON_TWITCH_CLIENT_ID` e `JASON_TWITCH_CLIENT_SECRET` no arquivo `.env` (veja o `.env.example`).
>
> 💾 Vídeos e modelos ficam na pasta `JASON_MIDIA` do `.env`. Use um disco com espaço.

### 👥 Mais de uma conta

Na tela **Contas** dá para criar outra conta (ex.: uma gamer em inglês). Cada conta tem a própria
pasta de vídeos e o próprio Chrome. Faça o login dela com o botão **Abrir Chrome para login** ou com
`python jason.py --conta gamer_en login`. Todos os comandos aceitam `--conta`.

---

## 🗺️ MAPA DA CIDADE (arquivos)

```
gta6/
├── jason.py / postar.py / baixar.py   atalhos (o código está em backend/)
├── horarios.json          ⏰ grade de horários
├── .env                   ⚙️ configuração desta máquina (copie do .env.example)
├── backend/app/
│   ├── cli/               🌅 jason.py (CLI bonita) e postar.py (sem visual, --json)
│   ├── api/               🌐 API da interface web (FastAPI)
│   ├── jobs/              🧵 fila de jobs + worker
│   ├── servicos/          🗓️ agenda, postagem, contas, pack
│   ├── plataformas/       ♪ tiktok ▶ youtube ◎ instagram + Agendador do Windows
│   └── cortes/            ✂️ cortador: fontes, detectores, webcam, layouts, legendas, render
├── frontend/              🖥️ a interface (React)
├── dados/jason.db         🧾 o que já foi pra onde (banco)
├── limpos/                ✨ vídeos prontos da conta principal + legendas .txt
└── perfil-chrome/         🔐 SEU login (não compartilhe!)
```

---

<div align="center">

### 🌴 MISSION PASSED 🌴
**RESPECT +**

*Bem-vindo a Leonida, parceiro.*

</div>
