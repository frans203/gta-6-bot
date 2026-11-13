"""
Baixa videos do pack (videos.json -> Google Drive), limpa os metadados com
limpar-metadados.ps1 e gera um .txt de legenda (titulo + tags) para cada video.

Uso:
  python baixar.py --qtd 10            # proximos 10 videos ainda nao baixados (HD primeiro)
  python baixar.py --ids 1 2 15        # videos especificos ("Video 0001" = 1)
  python baixar.py --qtd 5 --sem-limpar
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

SITE = "https://monetizecomgta6.netlify.app"
JSON_URL = f"{SITE}/x7k9c4f2e8b1/videos.json"
TAGS = "#gta6 #gtavi #gta #rockstargames #vicecity #gta6trailer #gameplay #gamer #viral #fyp #shorts #gaming"
TITULOS = [
    "GTA 6: o detalhe que NINGUÉM percebeu 👀",
    "VAZOU?! Novidade do GTA 6 que mudou tudo 🔥",
    "10 detalhes INSANOS que provam o capricho do GTA 6",
    "GTA 6 vs GTA 5: a evolução é ABSURDA 🤯",
    "Isso muda TUDO no GTA 6...",
    "GTA 6 tá chegando e ninguém tá pronto 😱",
    "O que a Rockstar ESCONDEU no trailer do GTA 6",
    "A REAL sobre a data de lançamento do GTA 6 📅",
    "Vice City nunca foi tão real — GTA 6 é surreal",
    "Jason e Lucia: tudo sobre a dupla do GTA 6",
    "Por que o GTA 6 vai ser o MAIOR jogo da história",
    "Easter eggs do GTA 6 que você NÃO viu 🤫",
    "O mapa do GTA 6 é GIGANTE — prepara o queixo",
]

RAIZ = Path(__file__).resolve().parent
BAIXADOS = RAIZ / "baixados"
LIMPOS = RAIZ / "limpos"
ESTADO = RAIZ / "pack_usados.json"     # versionado no git: compartilhado entre parceiros
ESTADO_ANTIGO = RAIZ / "baixados.json"
OPERADOR = os.environ.get("JASON_OPERADOR", "")  # opcional: quem baixou (ex.: set JASON_OPERADOR=parceiro)


def carregar_estado() -> dict:
    """{drive_id: {num, titulo_pack, baixado_em, por, bruto, limpo}}. Migra o formato antigo."""
    if ESTADO.exists():
        return json.loads(ESTADO.read_text("utf-8-sig"))
    estado = {}
    if ESTADO_ANTIGO.exists():
        for drive, arq in json.loads(ESTADO_ANTIGO.read_text("utf-8-sig")).items():
            m = re.search(r"(\d+)", arq)
            estado[drive] = {"num": int(m.group(1)) if m else None, "bruto": arq}
    return estado


def salvar_estado(estado: dict):
    ESTADO.write_text(json.dumps(dict(sorted(estado.items(), key=lambda kv: kv[1].get("num") or 0)),
                                 indent=1, ensure_ascii=False), "utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)


def carregar_lista():
    with get(JSON_URL) as r:
        dados = json.load(r)
    vids = []
    for v in dados:
        if v.get("type") == "img" or not v.get("drive"):
            continue
        m = re.search(r"(\d+)", v.get("t", ""))
        vids.append({"num": int(m.group(1)) if m else None, "drive": v["drive"], "hd": bool(v.get("hd"))})
    return vids


def baixar_drive(file_id, destino, ao_progresso=None):
    """ao_progresso(baixados, total_ou_None) e chamado a cada bloco."""
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    resp = get(url)
    # Arquivos grandes podem voltar uma pagina HTML de confirmacao com um form
    if "text/html" in resp.headers.get("Content-Type", ""):
        html = resp.read().decode("utf-8", "replace")
        campos = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', html))
        if not campos:
            raise RuntimeError("Drive devolveu HTML (limite de downloads ou arquivo privado)")
        acao = re.search(r'action="([^"]+)"', html)
        resp = get((acao.group(1) if acao else url.split("?")[0]) + "?" + urllib.parse.urlencode(campos))
        if "text/html" in resp.headers.get("Content-Type", ""):
            raise RuntimeError("Drive ainda devolveu HTML apos confirmacao")
    tmp = destino.with_suffix(".part")
    total = int(resp.headers.get("Content-Length") or 0) or None
    feito = 0
    with resp, open(tmp, "wb") as f:
        while bloco := resp.read(1 << 18):
            f.write(bloco)
            feito += len(bloco)
            if ao_progresso:
                ao_progresso(feito, total)
    tmp.replace(destino)


def selecionar(qtd=None, ids=None):
    """Lista de videos do pack a baixar (pendentes, HD primeiro) + estado atual."""
    estado = carregar_estado()
    vids = carregar_lista()
    if ids:
        return [v for v in vids if v["num"] in set(ids)], estado, len(vids)
    pend = [v for v in vids if v["drive"] not in estado]
    pend.sort(key=lambda v: (not v["hd"], v["num"] or 0))
    return pend[:qtd], estado, len(vids)


def marcar_baixado(estado, v, destino):
    estado[v["drive"]] = {
        "num": v["num"], "titulo_pack": f"Vídeo {v['num']:04d}", "hd": v["hd"],
        "baixado_em": datetime.now().isoformat(timespec="seconds"),
        **({"por": OPERADOR} if OPERADOR else {}),
        "bruto": destino.name, "limpo": None,
    }
    salvar_estado(estado)


def vincular_limpos(estado, brutos, limpos):
    """O limpador processa na ordem recebida: brutos[i] -> limpos[i]."""
    por_bruto = {info.get("bruto"): info for info in estado.values()}
    for b, l in zip(brutos, limpos):
        if b.name in por_bruto:
            por_bruto[b.name]["limpo"] = l.name
    salvar_estado(estado)


def gerar_legenda(video: Path):
    video.with_suffix(".txt").write_text(f"{random.choice(TITULOS)}\n\n{TAGS}\n", "utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap =argparse.ArgumentParser()
    ap.add_argument("--qtd", type=int, help="quantos videos novos baixar")
    ap.add_argument("--ids", type=int, nargs="+", help="numeros especificos (Video 0001 = 1)")
    ap.add_argument("--sem-limpar", action="store_true", help="so baixa, nao roda o limpador")
    a = ap.parse_args()
    if not a.qtd and not a.ids:
        ap.error("use --qtd N ou --ids ...")

    fila, estado, total = selecionar(a.qtd, a.ids)
    print(f"{total} videos no pack, {len(estado)} ja usados (pack_usados.json).")

    BAIXADOS.mkdir(exist_ok=True)
    novos = []
    for v in fila:
        destino = BAIXADOS / f"video_{v['num']:04d}.mp4"
        print(f"⬇  Video {v['num']:04d} {'(HD)' if v['hd'] else ''} ...", end=" ", flush=True)
        try:
            baixar_drive(v["drive"], destino)
        except Exception as e:
            print(f"ERRO: {e}")
            continue
        print(f"{destino.stat().st_size / 1e6:.1f} MB")
        marcar_baixado(estado, v, destino)
        novos.append(destino)
        time.sleep(random.uniform(1, 3))

    if not novos or a.sem_limpar:
        return

    antes = {p.name for p in LIMPOS.glob("*.mp4")} if LIMPOS.exists() else set()
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(RAIZ / "limpar-metadados.ps1"), *map(str, novos)],
        check=True,
    )
    limpos = sorted(p for p in LIMPOS.glob("*.mp4") if p.name not in antes)
    vincular_limpos(estado, novos, limpos)
    for p in limpos:
        gerar_legenda(p)
        print(f"✓ {p.name} + legenda")


if __name__ == "__main__":
    sys.exit(main())
