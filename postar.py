"""
CLI de envio de videos (nucleo do JASON_GTAVI_PIPELINE). Todos os comandos aceitam --json.

  python postar.py login                         # abre o Chrome do script (normal, sem automacao) p/ logar
  python postar.py fila                          # videos e status por plataforma
  python postar.py plano                         # mostra o que seria agendado e quando (nao envia nada)
  python postar.py agendar [-p tiktok,youtube,instagram]   # agenda TODOS os pendentes nos melhores horarios
  python postar.py enviar -p tiktok,youtube      # posta AGORA o proximo pendente de cada plataforma
  python postar.py enviar -p youtube --video limpos\\gta6_004.mp4
  python postar.py enviar -p tiktok --revisar    # preenche tudo mas nao publica
"""
import argparse
import contextlib
import json
import msvcrt
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from plataformas import PLATAFORMAS, agenda, comum, tarefas_windows
from plataformas.comum import LIMPOS, LOGS, PERFIL, NaoLogado, carregar_hist, log, registrar

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
MIN_ANTECEDENCIA = timedelta(minutes=16)  # TikTok exige >= 15 min para agendar
OK = ("publicado", "agendado", "agendado_pc", "revisar", "fila_vazia", "pulado_reivindicacao")


# ---------------------------------------------------------------- nucleo (usado pela CLI bonita / API)

def fila():
    h = carregar_hist()
    itens = []
    for v in sorted(LIMPOS.glob("*.mp4")):
        feito = h.get(v.name, {})
        itens.append({
            "video": v.name, "mb": round(v.stat().st_size / 1e6, 1),
            **{p: feito.get(p, {}).get("status", "pendente") for p in PLATAFORMAS},
            **{f"{p}_para": feito.get(p, {}).get("para") for p in PLATAFORMAS},
        })
    return itens


def proximo(plataforma):
    h = carregar_hist()
    for v in sorted(LIMPOS.glob("*.mp4")):
        if h.get(v.name, {}).get(plataforma, {}).get("status") not in agenda.FEITO:
            return v
    return None


@contextlib.contextmanager
def trava_perfil(espera_max_min=55):
    """So um processo por vez usa o perfil-chrome (lote + tarefas do Agendador do Windows)."""
    LOGS.mkdir(exist_ok=True)
    f = open(LOGS / "perfil-chrome.lock", "a+")
    limite = time.time() + espera_max_min * 60
    avisou = False
    while True:
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except OSError:
            if time.time() > limite:
                f.close()
                raise RuntimeError("perfil-chrome ocupado por outro envio ha muito tempo")
            if not avisou:
                log("perfil-chrome em uso por outro envio; aguardando...")
                avisou = True
            time.sleep(15)
    try:
        yield
    finally:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        f.close()


def status_de(video: Path, plataforma: str):
    return carregar_hist().get(video.name, {}).get(plataforma, {}).get("status")


def executar(tarefas, revisar=False, ao_passo=None, ao_inicio=None, ao_fim=None):
    """tarefas: [{plataforma, video: Path, quando: datetime|None}]. Navegador so abre se precisar."""
    resultados = []
    navegador = [t for t in tarefas if t.get("quando") is None or PLATAFORMAS[t["plataforma"]].AGENDA_NATIVA]
    locais = [t for t in tarefas if t not in navegador]

    for t in locais:  # Instagram agendado -> Agendador do Windows
        if ao_inicio: ao_inicio(t)
        try:
            nome = tarefas_windows.criar(t["plataforma"], t["video"], t["quando"])
            r = {"status": "agendado_pc", "para": t["quando"].isoformat(timespec="minutes"), "tarefa": nome}
            registrar(t["video"], t["plataforma"], r)
        except Exception as e:
            r = {"status": "erro", "erro": str(e)[:300]}
        log(f"{t['video'].name}: {r['status']} {r.get('para', '')}", t["plataforma"])
        resultados.append({"plataforma": t["plataforma"], "video": t["video"].name, **r})
        if ao_fim: ao_fim(t, r)

    # Instagram agendado no PC cujo horario chegar durante o lote e postado aqui mesmo
    # (a tarefa do Windows ficaria travada esperando o perfil; depois ela ve "publicado" e pula)
    ig_pendentes = [t for t in locais if t.get("quando")]

    if navegador:
        from playwright.sync_api import sync_playwright
        espera = 24 * 60 if any(t.get("quando") for t in navegador) else 55
        with trava_perfil(espera_max_min=espera), sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(PERFIL), channel="chrome", headless=False,
                viewport={"width": 1366, "height": 850}, locale="pt-BR",
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            sem_login = set()

            def vencidos_ig():
                agora = datetime.now()
                out = [x for x in ig_pendentes if x["quando"] <= agora]
                for x in out:
                    ig_pendentes.remove(x)
                return [{**x, "quando": None, "_inline": True} for x in out
                        if status_de(x["video"], x["plataforma"]) not in ("publicado",)]

            fila_nav = list(navegador)
            while fila_nav or (fila_nav := vencidos_ig()):
                if not fila_nav[0].get("_inline"):
                    fila_nav[:0] = vencidos_ig()
                t = fila_nav.pop(0)
                if t.get("quando") and t["quando"] - datetime.now() < MIN_ANTECEDENCIA:
                    log(f"{t['video'].name}: horario {t['quando']:%H:%M} ficou perto demais; postando agora", t["plataforma"])
                    t = {**t, "quando": None}
                nome, video = t["plataforma"], t["video"]
                if ao_inicio: ao_inicio(t)
                if nome in sem_login:
                    r = {"status": "nao_logado", "erro": "pulado: plataforma sem login"}
                else:
                    log(f"{video.name} {'agendar ' + t['quando'].isoformat(timespec='minutes') if t.get('quando') else 'agora'}", nome)
                    try:
                        r = PLATAFORMAS[nome].postar(page, video, revisar=revisar, quando=t.get("quando"),
                                                     progresso=(lambda m, t=t: ao_passo(t, m)) if ao_passo else None)
                        if r["status"] != "revisar":
                            registrar(video, nome, r)
                    except NaoLogado as e:
                        sem_login.add(nome)
                        r = {"status": "nao_logado", "erro": str(e)}
                    except Exception as e:
                        shot = LOGS / f"erro_{nome}_{datetime.now():%Y%m%d_%H%M%S}.png"
                        try:
                            page.screenshot(path=str(shot), full_page=True)
                        except Exception:
                            pass
                        r = {"status": "erro", "erro": str(e).splitlines()[0][:300], "print": shot.name}
                log(f"{video.name}: {r['status']} {r.get('para') or r.get('link') or r.get('erro') or ''}", nome)
                resultados.append({"plataforma": nome, "video": video.name, **r})
                if ao_fim: ao_fim(t, r)
            if revisar:
                log("--revisar: confira e feche o navegador quando terminar")
                page.wait_for_event("close", timeout=0)
            ctx.close()
    return resultados


def abrir_login(plataformas):
    urls = [PLATAFORMAS[p].LOGIN_URL for p in plataformas]
    subprocess.Popen([CHROME, f"--user-data-dir={PERFIL}", "--no-first-run", *urls])


# ---------------------------------------------------------------- CLI simples

def _plats(s):
    ps = [p.strip() for p in s.split(",") if p.strip()]
    for p in ps:
        if p not in PLATAFORMAS:
            raise argparse.ArgumentTypeError(f"plataforma desconhecida: {p}")
    return ps


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Envio de videos GTA 6")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    todas = ",".join(PLATAFORMAS)
    for nome in ("login", "plano", "agendar", "enviar"):
        s = sub.add_parser(nome)
        s.add_argument("-p", "--plataformas", type=_plats, default=_plats(todas))
        if nome == "enviar":
            s.add_argument("--video")
            s.add_argument("--revisar", action="store_true")
        if nome in ("plano", "agendar"):
            s.add_argument("--por-hora", type=int, help="modo lote: N posts por hora por plataforma")
            s.add_argument("--ate", help="modo lote: horario limite HH:MM (padrao 00:00 = meia-noite)")
    sub.add_parser("fila")
    a = ap.parse_args()
    comum.JSON_MODE = a.json
    dump = lambda d: print(json.dumps(d, ensure_ascii=False, indent=1, default=str))

    if a.cmd == "login":
        abrir_login(a.plataformas)
        print("Chrome do script aberto. Faca login em cada aba e depois feche o Chrome inteiro.")
        return 0

    if a.cmd == "fila":
        itens = fila()
        if a.json:
            return dump(itens) or 0
        print(f"{'video':<16}{'MB':>6}  " + "  ".join(f"{p:<14}" for p in PLATAFORMAS))
        for i in itens:
            print(f"{i['video']:<16}{i['mb']:>6}  " + "  ".join(f"{i[p]:<14}" for p in PLATAFORMAS))
        return 0

    if a.cmd in ("plano", "agendar"):
        p = agenda.plano(a.plataformas, por_hora=a.por_hora, ate=a.ate)
        if a.cmd == "plano" or not p:
            if a.json:
                return dump([{**x, "video": x["video"].name} for x in p]) or 0
            for x in p:
                print(f"{x['quando']:%a %d/%m %H:%M}  {x['plataforma']:<10} {x['video'].name}")
            return 0
        res = executar(p)
    else:
        if a.video:
            v = Path(a.video).resolve()
            tarefas = [{"plataforma": n, "video": v, "quando": None} for n in a.plataformas
                       if status_de(v, n) != "publicado"]
            if not tarefas:
                log(f"{v.name}: ja publicado em {','.join(a.plataformas)}; nada a fazer")
                return 0
        else:
            tarefas = [{"plataforma": n, "video": v, "quando": None} for n in a.plataformas if (v := proximo(n))]
        res = executar(tarefas, revisar=a.revisar)

    if a.json:
        dump(res)
    return 0 if all(r["status"] in OK for r in res) else 1


if __name__ == "__main__":
    sys.exit(main())
