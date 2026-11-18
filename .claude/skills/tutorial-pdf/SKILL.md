---
name: tutorial-pdf
description: Gera o PDF do tutorial do projeto (padrão TUTORIAL-MAC.md, para mandar a parceiros que usam Mac; também serve para o TUTORIAL.md de Windows). Use quando o usuário pedir "pdf do tutorial", "gera o tutorial de mac", "manda o tutorial pro meu amigo", "atualiza o pdf" ou /tutorial-pdf.
---

# PDF do tutorial

Gera um PDF bonito (capa, seções em faixa roxo→rosa, tabelas, código) a partir do Markdown, usando o
`scripts/tutorial_pdf.py` (Markdown → HTML → PDF pelo Google Chrome sem janela, com perfil temporário: não mexe
no Chrome aberto do usuário nem nos perfis das contas).

## Passos

1. **Qual tutorial?** Padrão: `TUTORIAL-MAC.md`. Se o usuário falar em Windows, use `TUTORIAL.md`.
2. **Confira se o tutorial está em dia** antes de gerar (o PDF vai para outra pessoa):
   - Compare os títulos `##`/`###` com o `TUTORIAL.md` e com o que mudou recentemente (`git log --oneline -15`,
     `TODO.md`). Se o Mac estiver sem algo importante para quem só usa o app (telas novas, comandos, regras de
     postagem), atualize o `TUTORIAL-MAC.md` primeiro: só o que vale para o Mac (Homebrew, `/` nos caminhos,
     launchd no lugar do Agendador do Windows, ⌘ no lugar de Ctrl onde for o caso).
   - Nunca coloque senha, token, `.env` real ou dados das contas no tutorial.
3. **Gere**:
   ```bash
   python scripts/tutorial_pdf.py                      # TUTORIAL-MAC.md -> pdf/TUTORIAL-MAC.pdf
   python scripts/tutorial_pdf.py TUTORIAL.md          # versão Windows
   python scripts/tutorial_pdf.py TUTORIAL-MAC.md --saida "C:/Users/<usuário>/Downloads/Tutorial JASON (Mac).pdf"
   ```
   Se o usuário pedir para "mandar"/"salvar nos downloads", use `--saida` para a pasta Downloads dele.
4. **Confira o resultado** (o PDF vai para outra pessoa, então olhe antes de entregar):
   ```bash
   python -c "import pypdfium2 as p; d=p.PdfDocument('pdf/TUTORIAL-MAC.pdf'); print(len(d), 'páginas'); d[0].render(scale=1.2).to_pil().save('<scratchpad>/capa.png')"
   ```
   (`pip install pypdfium2` se faltar.) Veja a capa e 1–2 páginas do meio: listas em tópicos (não corridas no
   parágrafo), blocos de código escuros, tabelas inteiras. A bandeira 🇧🇷 sai como "BR" no Windows; no Mac sai a
   bandeira (normal).
5. **Entregue**: diga o caminho completo do PDF, o número de páginas e o que mudou no tutorial (se mudou).
   O PDF fica em `pdf/` (fora do git). Se você editou o `TUTORIAL-MAC.md`, faça commit dele
   (push só se o usuário pedir).

## Se der errado

- `Não achei o Google Chrome`: no Windows o script procura em `C:\Program Files\Google\Chrome\Application`; no Mac
  em `/Applications/Google Chrome.app`.
- Algo do Markdown saiu estranho: o script já trata `<div align="center">`, lista colada em parágrafo e
  bloco de código dentro de citação (`> ```...```` `). Outros casos: ajuste `para_html()` no script, não o
  tutorial (o tutorial também é lido no GitHub).
