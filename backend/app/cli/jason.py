"""
JASON_GTAVI_PIPELINE — CLI estilizada da automacao.

  python jason.py                 tela inicial (logo + status)
  python jason.py fila            videos x plataformas
  python jason.py plano           o que seria agendado e quando
  python jason.py agendar [-y]    agenda todos os pendentes nos melhores horarios
  python jason.py agendar --por-hora 5 --ate 00:00 -y   lote: 5/hora em cada plataforma ate meia-noite
  python jason.py enviar -p tiktok [--video X] [--revisar]
  python jason.py baixar --qtd 5  baixa do pack, limpa metadados e gera legendas
  python jason.py tarefas         agendamentos locais (Instagram) no Windows
  python jason.py login           abre o Chrome do script para logar
  python jason.py web             interface web (API + worker) em http://127.0.0.1:8765
  python jason.py worker          só o worker de jobs (a web já sobe um)
  python jason.py exportar        exporta o histórico de posts para JSON (backup/inspeção)

  Todos aceitam --conta <id> (padrão: a conta principal).
"""
import argparse
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pyfiglet
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from ..config import config
from ..db import preparar
from ..plataformas import PLATAFORMAS, agendador, comum
from ..servicos import agenda, contas, historico, postagem
from ..servicos import pack as bx
from .postar import plats

CONTA = None  # conta escolhida por --conta (preenchida em main)

VERSAO = "2.0 \"Port Gellhorn\""
# Paleta Vice City
SOL = ["#FFE45C", "#FFC23D", "#FF9F2E", "#FF7A3D", "#FF5464", "#FF2E88", "#E02BB0", "#B026FF"]
ROSA, CIANO, LARANJA, ROXO, VERDE = "#FF2E88", "#00E5FF", "#FF8A00", "#B026FF", "#3DFFB0"
ICONE = {"tiktok": "♪ TikTok", "youtube": "▶ YouTube", "instagram": "◎ Instagram"}
COR_STATUS = {
    "publicado": f"bold {VERDE}", "agendado": f"bold {ROSA}", "agendado_pc": f"bold {LARANJA}",
    "pendente": "grey50", "erro": "bold red", "nao_logado": "bold red", "revisar": CIANO,
    "pulado_reivindicacao": "yellow", "limite_diario": "bold yellow", "atrasado": "bold red", "fila_vazia": "grey50",
}

con = Console(highlight=False)


# ------------------------------------------------------------------ visual

def gradiente(texto: str, cores: list[str]) -> Text:
    """Gradiente horizontal por caractere."""
    t = Text()
    n = max(len(texto) - 1, 1)
    for i, ch in enumerate(texto):
        t.append(ch, style=f"bold {cores[round(i / n * (len(cores) - 1))]}")
    return t


def _bezier(p0, p1, p2, n=40):
    for i in range(n + 1):
        t = i / n
        yield ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
               (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])


def logo() -> Text:
    """Por do sol listrado de Vice City + palmeira em silhueta + mar (arte original, meio-blocos)."""
    W, PH = 38, 26                      # largura x altura em "pixels" (2 pixels por linha de texto)
    cx, cy, r = 17.5, 25.5, 17.0
    px = [[None] * W for _ in range(PH)]
    topo = cy - r
    for y in range(PH):
        cor = SOL[min(max(int((y - topo) / (cy - topo) * len(SOL)), 0), len(SOL) - 1)]
        for x in range(W):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                # listras horizontais que engrossam perto do horizonte
                if y >= 14 and (y - 14) % 4 in ((2,) if y < 20 else (2, 3)):
                    continue
                px[y][x] = cor

    silhueta = "#4A1670"
    def ponto(x, y, cor=silhueta):
        xi, yi = round(x), round(y)
        if 0 <= xi < W and 0 <= yi < PH:
            px[yi][xi] = cor
    # tronco curvo (2 px)
    for x, y in _bezier((29, 25.5), (31, 16), (25, 8)):
        ponto(x, y); ponto(x + 1, y)
    # folhas da copa
    copa = (25, 8)
    for fim, ctrl in [((12, 12), (17, 3)), ((15, 4), (19, 1)), ((24, 0), (23, 1)),
                      ((33, 3), (30, 0)), ((37, 11), (34, 3)), ((31, 14), (32, 8))]:
        for x, y in _bezier(copa, ctrl, fim):
            ponto(x, y); ponto(x, y + 0.6)

    t = Text()
    for linha in range(PH // 2):
        cima, baixo = px[2 * linha], px[2 * linha + 1]
        for x in range(W):
            a, b = cima[x], baixo[x]
            if a and b:
                t.append("▀", style=f"{a} on {b}")
            elif a:
                t.append("▀", style=a)
            elif b:
                t.append("▄", style=b)
            else:
                t.append(" ")
        t.append("\n")
    mar = [("▔" * W, f"bold {CIANO}"), (" ≈≈ ≈≈≈≈ ≈≈ ≈≈≈≈≈≈ ≈≈≈ ≈≈≈≈ ≈≈ ≈≈≈ ≈ ", ROSA),
           ("    ~~  ~~~   ~~ ~~~~  ~~  ~~~      ", ROXO)]
    for l, cor in mar:
        t.append(l + "\n", style=cor)
    t.append_text(gradiente("      V  I  C  E     C  I  T  Y", [ROSA, LARANJA, ROSA]))
    return t


def titulo() -> Group:
    fig = pyfiglet.figlet_format("JASON", font="ansi_shadow").rstrip("\n").splitlines()
    linhas = [gradiente(l, [ROSA, "#FF5A6E", LARANJA, "#FFC23D"]) for l in fig]
    sub = gradiente("━━━━━━━  G T A  V I   ·   P I P E L I N E  ━━━━━━━", [CIANO, ROXO, ROSA])
    return Group(*linhas, sub)


def info() -> Table:
    itens = postagem.fila(CONTA)
    pend = {p: sum(1 for i in itens if i[p] == "pendente") for p in PLATAFORMAS}
    agendados = []
    for i in itens:
        for p in PLATAFORMAS:
            if i[p] in ("agendado", "agendado_pc") and i.get(f"{p}_para"):
                agendados.append((i[f"{p}_para"], p, i["video"]))
    futuros = sorted(a for a in agendados if a[0] >= datetime.now().isoformat(timespec="minutes"))
    publicados = sum(1 for i in itens for p in PLATAFORMAS if i[p] == "publicado")

    g = Table.grid(padding=(0, 1))
    g.add_column(style=f"bold {ROSA}", justify="right")
    g.add_column()
    g.add_row(Text("jason", style=f"bold {ROSA}"), Text("@", style="white") + Text("gtavi_pipeline", style=f"bold {CIANO}"))
    g.add_row("Conta", Text(f"{CONTA.nome} ({CONTA.id})", style="white"))
    g.add_row("", Text("─" * 26, style=ROXO))
    g.add_row("Versão", Text(VERSAO, style="white"))
    g.add_row("Plataformas", Text("  ".join(ICONE[p] for p in PLATAFORMAS), style=CIANO))
    g.add_row("Vídeos", Text(str(len(itens)), style="white"))
    g.add_row("Publicados", Text(str(publicados), style=VERDE))
    g.add_row("Pendentes", Text("  ".join(f"{ICONE[p].split()[0]} {n}" for p, n in pend.items()), style=LARANJA))
    g.add_row("Agendados", Text(str(len(futuros)), style=ROSA))
    if futuros:
        q, p, v = futuros[0]
        g.add_row("Próximo", Text(f"{datetime.fromisoformat(q):%a %d/%m %H:%M}  {ICONE[p]}  {v}", style="white"))
    g.add_row("Hora local", Text(f"{datetime.now():%a %d/%m/%Y %H:%M}", style="white"))
    g.add_row("", Text(""))
    blocos = Text()
    for c in [ROSA, LARANJA, "#FFE45C", VERDE, CIANO, ROXO, "#FF5464", "white"]:
        blocos.append("███", style=c)
    g.add_row("", blocos)
    return g


def banner():
    con.print()
    con.print(Align.center(titulo()))
    con.print()
    lado = Table.grid(padding=(0, 4))
    lado.add_column()
    lado.add_column(vertical="middle")
    lado.add_row(logo(), info())
    con.print(Align.center(lado))
    con.print()


def chip(status: str) -> Text:
    return Text(status.replace("_", " "), style=COR_STATUS.get(status, "white"))


def barra(**kw) -> Progress:
    return Progress(
        SpinnerColumn("dots12", style=ROSA),
        TextColumn("{task.description}"),
        BarColumn(bar_width=36, style="#2a1638", complete_style=ROSA, finished_style=CIANO, pulse_style=LARANJA),
        TaskProgressColumn(style=f"bold {LARANJA}"),
        TimeElapsedColumn(),
        console=con, **kw,
    )


# ------------------------------------------------------------------ comandos

def cmd_fila(a):
    t = Table(title=gradiente("FILA DE VÍDEOS", [ROSA, LARANJA]), border_style=ROXO, header_style=f"bold {CIANO}")
    t.add_column("vídeo", style="white")
    t.add_column("MB", justify="right", style="grey62")
    for p in PLATAFORMAS:
        t.add_column(ICONE[p], justify="center")
    for i in postagem.fila(CONTA):
        cel = []
        for p in PLATAFORMAS:
            c = chip(i[p])
            if i.get(f"{p}_para") and i[p] != "publicado":
                c.append(f"\n{datetime.fromisoformat(i[f'{p}_para']):%d/%m %H:%M}", style="grey62")
            cel.append(c)
        t.add_row(i["video"], f"{i['mb']}", *cel)
    con.print(t)


def tabela_plano(plano) -> Table:
    t = Table(title=gradiente("PLANO DE POSTAGEM", [CIANO, ROSA]), border_style=ROXO, header_style=f"bold {CIANO}")
    t.add_column("quando", style=f"bold {LARANJA}")
    t.add_column("plataforma")
    t.add_column("vídeo", style="white")
    t.add_column("como", style="grey62")
    for x in plano:
        nativo = PLATAFORMAS[x["plataforma"]].AGENDA_NATIVA
        t.add_row(f"{x['quando']:%a %d/%m %H:%M}", Text(ICONE[x["plataforma"]], style=CIANO), x["video"].name,
                  "agenda da plataforma" if nativo else "Agendador do Windows (PC ligado)")
    return t


def rodar(tarefas, revisar=False):
    resultados = []
    with barra() as prog:
        geral = prog.add_task(gradiente("JASON está na rua", [ROSA, LARANJA]).markup, total=len(tarefas))
        atual = prog.add_task("", total=None)

        def inicio(t):
            prog.update(atual, description=f"[{CIANO}]{ICONE[t['plataforma']]}[/] [white]{t['video'].name}[/]")

        def passo(t, msg):
            prog.update(atual, description=f"[{CIANO}]{ICONE[t['plataforma']]}[/] [white]{t['video'].name}[/] [grey62]· {msg}[/]")

        def fim(t, r):
            prog.advance(geral)
            extra = r.get("para") or r.get("link") or r.get("erro") or ""
            prog.console.print(f"  {ICONE[t['plataforma']]:<12} {t['video'].name:<14} ", chip(r["status"]), f"[grey62]{extra}[/]")

        resultados = postagem.executar(CONTA, tarefas, revisar=revisar, ao_passo=passo, ao_inicio=inicio, ao_fim=fim)
        prog.update(atual, visible=False)
    ok = sum(r["status"] in postagem.OK for r in resultados)
    cor = VERDE if ok == len(resultados) else LARANJA
    con.print(Panel(Text(f"{ok}/{len(resultados)} concluídos", style=f"bold {cor}", justify="center"),
                    border_style=ROSA, title="MISSÃO", title_align="left"))
    if any(r["status"] == "limite_diario" for r in resultados):
        con.print(f"[{LARANJA}]YouTube no limite diário de envios: verifique o canal (telefone) ou espere 24h. Os vídeos ficaram pendentes.[/]")
    if any(r["status"] == "nao_logado" for r in resultados):
        con.print(f"[{LARANJA}]Alguma plataforma está sem login no perfil do script → [bold]python jason.py login[/][/]")
    return 0 if ok == len(resultados) else 1


def cmd_plano(a):
    p = agenda.plano(CONTA, a.plataformas, por_hora=a.por_hora, ate=a.ate)
    con.print(tabela_plano(p) if p else f"[{VERDE}]Nada pendente. Tudo postado ou agendado.[/]")


def cmd_agendar(a):
    p = agenda.plano(CONTA, a.plataformas, por_hora=a.por_hora, ate=a.ate)
    if not p:
        con.print(f"[{VERDE}]Nada pendente. Tudo postado ou agendado.[/]")
        return 0
    con.print(tabela_plano(p))
    if not a.yes and not Confirm.ask(f"[{ROSA}]Agendar esses {len(p)} posts?[/]", console=con):
        return 0
    return rodar(p)


def cmd_enviar(a):
    tarefas = postagem.tarefas_envio(CONTA, a.plataformas, a.video)
    if not tarefas:
        con.print(f"[{VERDE}]Fila vazia.[/]")
        return 0
    return rodar(tarefas, revisar=a.revisar)


def cmd_baixar(a):
    fila, estado, total_pack = bx.selecionar(a.qtd, a.ids)
    con.print(f"[{CIANO}]Pack:[/] {total_pack} vídeos · [{CIANO}]já usados (pack_usados.json):[/] {len(estado)} · [{ROSA}]agora:[/] {len(fila)}")
    bx.BAIXADOS.mkdir(exist_ok=True)
    novos = []
    with Progress(SpinnerColumn("dots12", style=ROSA), TextColumn("{task.description}"),
                  BarColumn(bar_width=36, style="#2a1638", complete_style=ROSA, finished_style=CIANO),
                  DownloadColumn(), TransferSpeedColumn(), console=con) as prog:
        for v in fila:
            destino = bx.BAIXADOS / f"video_{v['num']:04d}.mp4"
            t = prog.add_task(f"[white]Vídeo {v['num']:04d}[/] {'[' + LARANJA + ']HD[/]' if v['hd'] else ''}", total=None)
            try:
                bx.baixar_drive(v["drive"], destino, lambda f, tot, t=t: prog.update(t, completed=f, total=tot))
                bx.marcar_baixado(estado, v, destino)
                novos.append(destino)
            except Exception as e:
                prog.update(t, description=f"[red]Vídeo {v['num']:04d} erro: {e}[/]")
    if not novos:
        return 0
    with con.status(f"[{ROSA}]Limpando metadados de {len(novos)} vídeo(s) (ffmpeg)...[/]", spinner="dots12"):
        limpos = bx.limpar(novos)
    bx.vincular_limpos(estado, novos, limpos)
    for p in limpos:
        bx.gerar_legenda(p)
        con.print(f"  [{VERDE}]✓[/] {p.name} [grey62]+ legenda[/]")
    return 0


def cmd_tarefas(a):
    t = Table(title=gradiente("AGENDADOR DO WINDOWS", [LARANJA, ROSA]), border_style=ROXO, header_style=f"bold {CIANO}")
    for c in ("tarefa", "próxima execução", "estado"):
        t.add_column(c)
    for x in agendador.listar():
        t.add_row(x["nome"], x["proxima"], x["estado"])
    con.print(t)


def cmd_login(a):
    postagem.abrir_login(CONTA, a.plataformas)
    con.print(f"[{CIANO}]Chrome do script aberto.[/] Faça login em cada aba e depois [bold]feche o Chrome inteiro[/].")


def cmd_web(a):
    from ..servidor import rodar_web
    return rodar_web(abrir=not a.sem_navegador)


def cmd_worker(a):
    from ..jobs.worker import rodar
    return rodar()


def cmd_exportar(a):
    destino = config.raiz / "logs" / f"postados_{CONTA.id}_{datetime.now():%Y%m%d_%H%M%S}.json"
    historico.exportar(CONTA.id, destino)
    con.print(f"[{VERDE}]✓[/] {destino}")


def main():
    global CONTA
    ap = argparse.ArgumentParser(prog="jason", description="JASON_GTAVI_PIPELINE")
    ap.add_argument("--conta", help="id da conta (padrão: a principal)")
    sub = ap.add_subparsers(dest="cmd")
    todas = ",".join(PLATAFORMAS)
    for nome in ("plano", "agendar", "enviar", "login"):
        s = sub.add_parser(nome)
        s.add_argument("-p", "--plataformas", type=plats, default=plats(todas))
        if nome == "agendar":
            s.add_argument("-y", "--yes", action="store_true", help="não pedir confirmação")
        if nome in ("plano", "agendar"):
            s.add_argument("--por-hora", type=int, help="modo lote: N posts por hora em cada plataforma")
            s.add_argument("--ate", help="modo lote: até HH:MM (padrão 00:00 = meia-noite)")
        if nome == "enviar":
            s.add_argument("--video")
            s.add_argument("--revisar", action="store_true")
    s = sub.add_parser("baixar")
    s.add_argument("--qtd", type=int, default=5)
    s.add_argument("--ids", type=int, nargs="+")
    sub.add_parser("fila")
    sub.add_parser("tarefas")
    s = sub.add_parser("web")
    s.add_argument("--sem-navegador", action="store_true", help="não abrir o navegador")
    sub.add_parser("worker")
    sub.add_parser("exportar")
    a = ap.parse_args()
    comum.JSON_MODE = True  # o log continua indo para logs/postar.log; a tela fica com o rich
    preparar()
    CONTA = contas.obter(a.conta)

    if not a.cmd:
        banner()
        con.print(Align.center(Text("comandos: web · fila · plano · agendar · enviar · baixar · tarefas · login",
                                    style="grey62")))
        con.print()
        return 0
    banner() if a.cmd in ("agendar", "enviar", "baixar") else None
    return {"fila": cmd_fila, "plano": cmd_plano, "agendar": cmd_agendar, "enviar": cmd_enviar,
            "baixar": cmd_baixar, "tarefas": cmd_tarefas, "login": cmd_login, "web": cmd_web,
            "worker": cmd_worker, "exportar": cmd_exportar}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
