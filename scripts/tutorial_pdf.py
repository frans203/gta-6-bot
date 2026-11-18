"""Gera o PDF de um tutorial (Markdown -> HTML estilizado -> PDF pelo Chrome sem janela).

Uso:
  python scripts/tutorial_pdf.py                         # TUTORIAL-MAC.md -> pdf/TUTORIAL-MAC.pdf
  python scripts/tutorial_pdf.py TUTORIAL.md             # o de Windows
  python scripts/tutorial_pdf.py TUTORIAL-MAC.md --saida C:/Users/fulano/Downloads/tutorial.pdf

Precisa do pacote `markdown` (já vem no requirements do backend) e do Google Chrome instalado.
O PDF sai em pdf/ (fora do git). Emojis, tabelas e blocos de código saem como no GitHub.
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parents[1]
REPO = "https://github.com/frans203/gta-6-bot"

CHROMES = {
    "win32": [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
              Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")],
    "darwin": [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")],
}

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm; }
:root { --roxo: #7c3aed; --rosa: #db2777; --tinta: #1d1530; --cinza: #6b6480; --fundo: #f6f3fb; --borda: #e4dcf3; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Segoe UI", -apple-system, "Helvetica Neue", Arial, "Segoe UI Emoji", "Apple Color Emoji", sans-serif;
       color: var(--tinta); font-size: 10.5pt; line-height: 1.55; margin: 0; }
h1, h2, h3, h4 { line-height: 1.25; break-after: avoid; page-break-after: avoid; }
h1 { font-size: 20pt; margin: .3em 0 .1em; color: var(--roxo); }
h2 { font-size: 15pt; margin: 1.6em 0 .55em; padding: .35em .6em; border-radius: 8px; color: #fff;
     background: linear-gradient(90deg, var(--roxo), var(--rosa)); }
h3 { font-size: 12pt; margin: 1.2em 0 .4em; color: var(--roxo); }
h4 { font-size: 11pt; margin: 1em 0 .3em; }
p, li { orphans: 3; widows: 3; }
a { color: var(--rosa); text-decoration: none; }
hr { border: 0; border-top: 1px solid var(--borda); margin: 1.4em 0; }
code { font-family: Consolas, Menlo, "SF Mono", monospace; font-size: 9pt; background: var(--fundo);
       border: 1px solid var(--borda); border-radius: 4px; padding: .05em .35em; }
pre { background: #1d1530; color: #f3edff; border-radius: 8px; padding: 10px 12px; overflow: hidden;
      white-space: pre-wrap; word-break: break-word; break-inside: avoid; page-break-inside: avoid; }
pre code { background: none; border: 0; color: inherit; padding: 0; font-size: 8.8pt; }
blockquote { margin: .9em 0; padding: .55em .9em; border-left: 4px solid var(--rosa); background: #fdf2f8;
             border-radius: 0 8px 8px 0; break-inside: avoid; }
blockquote p { margin: .25em 0; }
table { width: 100%; border-collapse: collapse; margin: .8em 0; font-size: 9.5pt; break-inside: avoid; }
th { background: var(--fundo); color: var(--roxo); text-align: left; }
th, td { border: 1px solid var(--borda); padding: 5px 8px; vertical-align: top; }
tr:nth-child(even) td { background: #fbf9fe; }
img { max-width: 100%; }
.centro { text-align: center; }
.centro pre { display: inline-block; text-align: left; background: none; color: var(--roxo); padding: 0;
              font-size: 8pt; line-height: 1; white-space: pre; }
.centro pre code { line-height: 1; font-family: Consolas, Menlo, monospace; }
.capa { text-align: center; padding: 6mm 0 2mm; }
.rodape { margin-top: 2.5em; padding-top: .8em; border-top: 1px solid var(--borda); color: var(--cinza);
          font-size: 8.5pt; text-align: center; }
"""


def achar_chrome() -> Path:
    for p in CHROMES.get(sys.platform, []):
        if p.exists():
            return p
    for nome in ("google-chrome", "chrome", "chromium", "chromium-browser"):
        if achado := shutil.which(nome):
            return Path(achado)
    raise SystemExit("Não achei o Google Chrome instalado (ele imprime o PDF).")


LISTA = re.compile(r"^(\s*(?:>\s*)*)(?:[-*+]|\d+\.)\s")


def separar_listas(md_texto: str) -> str:
    """O GitHub aceita lista colada num parágrafo; o python-markdown precisa de uma linha em branco antes
    (vale também dentro de citações "> ..."). Fora de blocos de código."""
    out, em_codigo = [], False
    for linha in md_texto.splitlines():
        if linha.lstrip("> ").startswith("```"):
            em_codigo = not em_codigo
        m = LISTA.match(linha)
        if not em_codigo and m and out:
            ant = out[-1]
            prefixo = m.group(1)
            texto_ant = ant[len(prefixo):].strip() if ant.startswith(prefixo.rstrip()) else ant.strip()
            if texto_ant and not LISTA.match(ant) and not ant.startswith("    "):
                out.append(prefixo.rstrip())
        out.append(linha)
    return "\n".join(out)


def codigo_em_citacoes(md_texto: str) -> str:
    """```bloco``` dentro de "> ..." vira código indentado (o fenced_code não entra em citações)."""
    out, dentro = [], False
    for linha in md_texto.splitlines():
        m = re.match(r"^(\s*>\s?)(.*)$", linha)
        if m and m.group(2).lstrip().startswith("```"):
            if not dentro:
                out.append(m.group(1).rstrip())  # linha em branco na citação antes do código
            dentro = not dentro
            continue
        if dentro and m:
            out.append(f"{m.group(1).rstrip()}     {m.group(2)}")
            continue
        out.append(linha)
    return "\n".join(out)


def para_html(md_texto: str, titulo: str) -> str:
    md_texto = separar_listas(codigo_em_citacoes(md_texto))
    # blocos <div align="center"> com markdown dentro (o GitHub renderiza; o python-markdown precisa do aviso)
    md_texto = re.sub(r'<div align="center">', '<div class="centro" markdown="1">', md_texto)
    # links para outros .md do repositório viram links do GitHub (no PDF não existe o arquivo ao lado)
    md_texto = re.sub(r"\]\((?!https?://|#)([^)]+\.md)\)", rf"]({REPO}/blob/main/\1)", md_texto)
    corpo = markdown.markdown(md_texto, extensions=["tables", "fenced_code", "md_in_html", "sane_lists", "attr_list"])
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{html.escape(titulo)}</title><style>{CSS}</style></head>
<body>{corpo}
<div class="rodape">Gerado em {gerado} a partir de {html.escape(titulo)} · {REPO}</div>
</body></html>"""


def gerar(entrada: Path, saida: Path) -> Path:
    html_txt = para_html(entrada.read_text("utf-8"), entrada.name)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tutorial_pdf_") as tmp:
        pagina = Path(tmp) / "tutorial.html"
        pagina.write_text(html_txt, "utf-8")
        temp_pdf = Path(tmp) / "saida.pdf"
        # perfil temporário: não mexe no Chrome aberto do usuário nem nos perfis das contas
        cmd = [str(achar_chrome()), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={Path(tmp) / 'perfil'}", "--no-pdf-header-footer",
               f"--print-to-pdf={temp_pdf}", pagina.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if not temp_pdf.exists() or temp_pdf.stat().st_size == 0:
            raise SystemExit(f"O Chrome não gerou o PDF.\n{r.stderr[-1500:]}")
        shutil.move(str(temp_pdf), saida)
    return saida


def main():
    ap = argparse.ArgumentParser(description="Gera o PDF de um tutorial em Markdown.")
    ap.add_argument("entrada", nargs="?", default="TUTORIAL-MAC.md", help="arquivo .md (padrão: TUTORIAL-MAC.md)")
    ap.add_argument("--saida", help="caminho do PDF (padrão: pdf/<nome>.pdf)")
    a = ap.parse_args()
    entrada = Path(a.entrada)
    if not entrada.is_absolute():
        entrada = RAIZ / entrada
    if not entrada.exists():
        raise SystemExit(f"Arquivo não encontrado: {entrada}")
    saida = Path(a.saida) if a.saida else RAIZ / "pdf" / f"{entrada.stem}.pdf"
    feito = gerar(entrada, saida)
    print(f"PDF gerado: {feito} ({feito.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
