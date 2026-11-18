"""Núcleo de envio: fila por conta, executar(tarefas) com Playwright, trava do perfil do Chrome."""
import contextlib
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..config import config
from ..plataformas import PLATAFORMAS, agendador
from ..plataformas.comum import LOGS, LimiteDiario, NaoLogado, ler_txt, log
from . import agenda, contas, historico

MIN_ANTECEDENCIA = timedelta(minutes=16)  # TikTok exige >= 15 min para agendar
OK = ("publicado", "agendado", "agendado_pc", "revisar", "fila_vazia", "pulado_reivindicacao")


class Cancelado(Exception):
    pass


def fila(conta) -> list[dict]:
    h = historico.carregar_hist(conta.id)
    itens = []
    for v in contas.videos(conta):
        feito = h.get(v.name, {})
        titulo, tags = ler_txt(v)
        itens.append({
            "video": v.name, "mb": round(v.stat().st_size / 1e6, 1), "titulo": titulo, "tags": tags,
            **{p: ("atrasado" if feito.get(p, {}).get("status") == "agendado_pc" and not agenda.feito(feito[p])
                   else feito.get(p, {}).get("status", "pendente")) for p in PLATAFORMAS},
            **{f"{p}_para": feito.get(p, {}).get("para") for p in PLATAFORMAS},
            **{f"{p}_link": feito.get(p, {}).get("link") for p in PLATAFORMAS},
        })
    return itens


def proximo(conta, plataforma) -> Path | None:
    h = historico.carregar_hist(conta.id)
    for v in contas.videos(conta):
        if not agenda.feito(h.get(v.name, {}).get(plataforma, {})):
            return v
    return None


if sys.platform == "win32":
    import msvcrt

    def _travar(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _destravar(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _travar(f):
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)  # ocupado -> BlockingIOError (é um OSError)

    def _destravar(f):
        fcntl.flock(f, fcntl.LOCK_UN)


@contextlib.contextmanager
def trava_perfil(conta, espera_max_min=55):
    """So um processo por vez usa o perfil do Chrome da conta (lote, web e envios agendados no PC)."""
    LOGS.mkdir(exist_ok=True)
    f = open(contas.arquivo_trava(conta), "a+")
    limite = time.time() + espera_max_min * 60
    avisou = False
    while True:
        try:
            f.seek(0)
            _travar(f)
            break
        except OSError:
            if time.time() > limite:
                f.close()
                raise RuntimeError("perfil do Chrome ocupado por outro envio ha muito tempo") from None
            if not avisou:
                log(f"perfil da conta {conta.id} em uso por outro envio; aguardando...")
                avisou = True
            time.sleep(15)
    try:
        yield
    finally:
        f.seek(0)
        _destravar(f)
        f.close()


def executar(conta, tarefas, revisar=False, ao_passo=None, ao_inicio=None, ao_fim=None, cancelado=None):
    """tarefas: [{plataforma, video: Path, quando: datetime|None}]. Navegador so abre se precisar.
    cancelado(): se devolver True, para entre um envio e outro (nunca no meio de um)."""
    resultados = []
    navegador = [t for t in tarefas if t.get("quando") is None or PLATAFORMAS[t["plataforma"]].AGENDA_NATIVA]
    locais = [t for t in tarefas if t not in navegador]

    def checar():
        if cancelado and cancelado():
            raise Cancelado("cancelado pelo usuário")

    for t in locais:  # Instagram agendado -> Agendador do Windows / launchd do Mac
        checar()
        if ao_inicio: ao_inicio(t)
        try:
            nome = agendador.criar(conta, t["plataforma"], t["video"], t["quando"])
            r = {"status": "agendado_pc", "para": t["quando"].isoformat(timespec="minutes"), "tarefa": nome}
            historico.registrar(conta.id, t["video"], t["plataforma"], r)
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
        with trava_perfil(conta, espera_max_min=espera), sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(contas.perfil(conta)), channel="chrome", headless=False,
                viewport={"width": 1366, "height": 850}, locale="pt-BR",
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            sem_login = set()
            bloqueadas = {}

            def vencidos_ig():
                agora = datetime.now()
                out = [x for x in ig_pendentes if x["quando"] <= agora]
                for x in out:
                    ig_pendentes.remove(x)
                return [{**x, "quando": None, "_inline": True} for x in out
                        if historico.status_de(conta.id, x["video"], x["plataforma"]) not in ("publicado",)]

            try:
                fila_nav = list(navegador)
                while fila_nav or (fila_nav := vencidos_ig()):
                    checar()
                    if not fila_nav[0].get("_inline"):
                        fila_nav[:0] = vencidos_ig()
                    t = fila_nav.pop(0)
                    if t.get("quando") and t["quando"] - datetime.now() < MIN_ANTECEDENCIA:
                        log(f"{t['video'].name}: horario {t['quando']:%H:%M} ficou perto demais; postando agora",
                            t["plataforma"])
                        t = {**t, "quando": None}
                    nome, video = t["plataforma"], t["video"]
                    if ao_inicio: ao_inicio(t)
                    if nome in sem_login:
                        r = {"status": "nao_logado", "erro": "pulado: plataforma sem login"}
                    elif nome in bloqueadas:
                        r = {"status": bloqueadas[nome], "erro": "pulado: limite diario da plataforma"}
                    else:
                        quando_txt = "agendar " + t["quando"].isoformat(timespec="minutes") if t.get("quando") else "agora"
                        log(f"[{conta.id}] {video.name} {quando_txt}", nome)
                        try:
                            r = PLATAFORMAS[nome].postar(page, video, revisar=revisar, quando=t.get("quando"),
                                                         progresso=(lambda m, t=t: ao_passo(t, m)) if ao_passo else None)
                            if r["status"] != "revisar":
                                historico.registrar(conta.id, video, nome, r)
                        except NaoLogado as e:
                            sem_login.add(nome)
                            r = {"status": "nao_logado", "erro": str(e)}
                        except LimiteDiario as e:
                            bloqueadas[nome] = "limite_diario"
                            r = {"status": "limite_diario", "erro": str(e)}
                            try:  # descarta o envio recusado para nao travar a proxima plataforma
                                page.keyboard.press("Escape")
                            except Exception:
                                pass
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
            finally:
                ctx.close()
    return resultados


def tarefas_envio(conta, plataformas, video: str | None = None) -> list[dict]:
    """Tarefas de 'postar agora': um vídeo específico ou o próximo pendente de cada plataforma."""
    if video:
        v = Path(video)
        if not v.is_absolute():
            v = contas.pasta_videos(conta) / v.name
        return [{"plataforma": n, "video": v, "quando": None} for n in plataformas
                if historico.status_de(conta.id, v, n) != "publicado"]
    return [{"plataforma": n, "video": v, "quando": None} for n in plataformas if (v := proximo(conta, n))]


def abrir_login(conta, plataformas):
    urls = [PLATAFORMAS[p].LOGIN_URL for p in plataformas]
    perfil = contas.perfil(conta)
    perfil.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(config.chrome), f"--user-data-dir={perfil}", "--no-first-run", *urls])
