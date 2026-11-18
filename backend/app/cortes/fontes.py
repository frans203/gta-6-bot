"""Onde os vídeos vêm: listar VODs/clipes de um canal, ler dados de uma URL e baixar trechos.
Usa o yt-dlp (Twitch e YouTube) e, se configurada, a API oficial da Twitch (Helix) para os clipes."""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yt_dlp

from ..config import config

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _ydl(**opts) -> yt_dlp.YoutubeDL:
    return yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noprogress": True, **opts})


def _data(ts) -> str | None:
    if not ts:
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).isoformat(timespec="minutes")
    if isinstance(ts, str) and len(ts) == 8 and ts.isdigit():  # upload_date 20261113
        return f"{ts[:4]}-{ts[4:6]}-{ts[6:]}"
    return str(ts)[:16]


# ------------------------------------------------------------------ Twitch Helix (opcional)

class TwitchAPI:
    """API oficial. Precisa de JASON_TWITCH_CLIENT_ID e JASON_TWITCH_CLIENT_SECRET no .env."""
    _token: tuple[str, float] | None = None

    @classmethod
    def disponivel(cls) -> bool:
        return bool(config.twitch_client_id and config.twitch_client_secret)

    @classmethod
    def _tok(cls) -> str:
        if cls._token and cls._token[1] > time.time() + 60:
            return cls._token[0]
        dados = urllib.parse.urlencode({"client_id": config.twitch_client_id,
                                        "client_secret": config.twitch_client_secret,
                                        "grant_type": "client_credentials"}).encode()
        with urllib.request.urlopen("https://id.twitch.tv/oauth2/token", dados, timeout=30) as r:
            j = json.load(r)
        cls._token = (j["access_token"], time.time() + j["expires_in"])
        return cls._token[0]

    @classmethod
    def get(cls, caminho: str, **params) -> dict:
        url = f"https://api.twitch.tv/helix/{caminho}?{urllib.parse.urlencode(params, doseq=True)}"
        req = urllib.request.Request(url, headers={"Client-Id": config.twitch_client_id,
                                                   "Authorization": f"Bearer {cls._tok()}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    _ids: dict[str, str] = {}

    @classmethod
    def user_id(cls, login: str) -> str:
        if login.lower() in cls._ids:
            return cls._ids[login.lower()]
        d = cls.get("users", login=login)["data"]
        if not d:
            raise ValueError(f"canal da Twitch não encontrado: {login}")
        cls._ids[login.lower()] = d[0]["id"]
        return d[0]["id"]

    @classmethod
    def clipes_entre(cls, login: str, inicio: datetime, fim: datetime, limite: int = 100) -> list[dict]:
        """Clipes criados entre `inicio` e `fim` (UTC), os mais vistos primeiro (o vigia usa)."""
        params = {"broadcaster_id": cls.user_id(login), "first": min(limite, 100),
                  "started_at": inicio.strftime("%Y-%m-%dT%H:%M:%SZ"), "ended_at": fim.strftime("%Y-%m-%dT%H:%M:%SZ")}
        out, cursor = [], None
        while len(out) < limite:
            if cursor:
                params["after"] = cursor
            r = cls.get("clips", **params)
            out += r["data"]
            cursor = r.get("pagination", {}).get("cursor")
            if not cursor or not r["data"]:
                break
        return out[:limite]

    @classmethod
    def video(cls, video_id: str) -> dict | None:
        """VOD: {id, titulo, duracao (s), miniatura, criado_em} ou None se não existe/sumiu.
        Enquanto a live está no ar, a duração cresce (o VOD vai sendo gravado)."""
        d = cls.get("videos", id=video_id)["data"]
        if not d:
            return None
        v = d[0]
        return {"id": v["id"], "titulo": v.get("title") or "", "duracao": duracao_twitch(v.get("duration", "0s")),
                "miniatura": v.get("thumbnail_url"), "criado_em": v.get("created_at"), "url": v.get("url")}

    @classmethod
    def clipes(cls, login: str, dias: int = 7, limite: int = 20, video_id: str | None = None) -> list[dict]:
        """Clipes mais vistos do período (a Helix já ordena por views)."""
        fim = datetime.now(UTC)
        params = {"broadcaster_id": cls.user_id(login), "first": min(limite, 100),
                  "started_at": (fim - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "ended_at": fim.strftime("%Y-%m-%dT%H:%M:%SZ")}
        out, cursor = [], None
        while len(out) < limite:
            if cursor:
                params["after"] = cursor
            r = cls.get("clips", **params)
            out += [c for c in r["data"] if not video_id or c.get("video_id") == video_id]
            cursor = r.get("pagination", {}).get("cursor")
            if not cursor or not r["data"]:
                break
        return out[:limite]


def duracao_twitch(texto: str) -> int:
    """'3h2m10s' -> 10930"""
    total = 0
    for n, u in re.findall(r"(\d+)([hms])", texto or ""):
        total += int(n) * {"h": 3600, "m": 60, "s": 1}[u]
    return total


# ------------------------------------------------------------------ listar canal

def url_canal(plataforma: str, canal: str, tipo: str, dias: int = 7) -> str:
    if plataforma == "twitch":
        if tipo == "clipe":
            rng = "24hr" if dias <= 1 else "7d" if dias <= 7 else "30d" if dias <= 30 else "all"
            return f"https://www.twitch.tv/{canal}/clips?filter=clips&range={rng}"
        return f"https://www.twitch.tv/{canal}/videos?filter=archives&sort=time"
    aba = "streams" if tipo == "vod" else "videos"
    return f"https://www.youtube.com/{canal}/{aba}"


def listar_canal(plataforma: str, canal: str, tipo: str = "vod", limite: int = 5, dias: int = 7) -> list[dict]:
    """[{url, tipo, titulo, duracao, views, publicado_em, miniatura, extra}]"""
    if plataforma not in ("twitch", "youtube"):
        raise ValueError("buscar VODs automaticamente só funciona com Twitch e YouTube; cole o link do vídeo")
    if plataforma == "twitch" and tipo == "clipe":
        if not TwitchAPI.disponivel():
            raise RuntimeError("Para listar clipes da Twitch configure a API oficial (grátis): crie um app em "
                               "https://dev.twitch.tv/console/apps e coloque JASON_TWITCH_CLIENT_ID e "
                               "JASON_TWITCH_CLIENT_SECRET no arquivo .env")
        return [{"url": c["url"], "tipo": "clipe", "titulo": c["title"], "duracao": c["duration"],
                 "views": c["view_count"], "publicado_em": c["created_at"][:16], "miniatura": c["thumbnail_url"],
                 "extra": {"video_id": c.get("video_id"), "vod_offset": c.get("vod_offset")}}
                for c in TwitchAPI.clipes(canal, dias, limite)]

    with _ydl(extract_flat="in_playlist", playlistend=limite, skip_download=True) as y:
        try:
            info = y.extract_info(url_canal(plataforma, canal, tipo, dias), download=False)
        except yt_dlp.utils.DownloadError as e:
            if plataforma != "youtube" or "streams tab" not in str(e):
                raise
            # canal sem aba "Ao vivo": as lives/episódios ficam na aba de vídeos
            info = y.extract_info(url_canal(plataforma, canal, "clipe", dias), download=False)
    out = []
    for e in list(info.get("entries") or [])[:limite]:
        url = e.get("url") or e.get("webpage_url")
        if not url:
            continue
        thumbs = e.get("thumbnails") or []
        out.append({"url": url, "tipo": tipo, "titulo": e.get("title") or "", "duracao": e.get("duration"),
                    "views": e.get("view_count"), "publicado_em": _data(e.get("timestamp") or e.get("upload_date")),
                    "miniatura": thumbs[-1]["url"] if thumbs else e.get("thumbnail")})
    return out


def info(url: str) -> dict:
    """Metadados completos de um vídeo (duração, título, heatmap do YouTube...)."""
    with _ydl(skip_download=True) as y:
        i = y.extract_info(url, download=False)
    thumbs = i.get("thumbnails") or []
    return {"titulo": i.get("title") or "", "duracao": i.get("duration"), "views": i.get("view_count"),
            "publicado_em": _data(i.get("timestamp") or i.get("upload_date")),
            "miniatura": thumbs[-1]["url"] if thumbs else i.get("thumbnail"),
            "heatmap": i.get("heatmap") or [], "id": i.get("id"), "largura": i.get("width"), "altura": i.get("height")}


# ------------------------------------------------------------------ baixar

def _baixar(opts: dict, url: str, destino: Path, paralelo: int) -> dict:
    """Baixa com fragmentos em paralelo; se o yt-dlp tropeçar nos arquivos temporários (acontece no Windows),
    limpa e tenta de novo baixando um fragmento por vez."""
    for n in (paralelo, 1):
        try:
            with _ydl(**opts, concurrent_fragment_downloads=n, fragment_retries=10, retries=5) as y:
                i = y.extract_info(url, download=True)
                return {"info": i, "arquivo": Path(y.prepare_filename(i))}
        except yt_dlp.utils.YoutubeDLError:
            if n == 1:
                raise
            for resto in destino.parent.glob(destino.stem + ".*"):
                resto.unlink(missing_ok=True)
    raise RuntimeError("download falhou")


def baixar_trecho(url: str, inicio: float | None, fim: float | None, destino: Path, altura: int = 1080,
                  ao_progresso=None) -> Path:
    """Baixa só o trecho [inicio, fim] (ou o vídeo todo, se None) em mp4."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    def gancho(d):
        if ao_progresso and d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate")
            if tot:
                ao_progresso(d.get("downloaded_bytes", 0) / tot)

    opts = {"format": f"bv*[height<={altura}]+ba/b[height<={altura}]/b", "outtmpl": str(destino.with_suffix(".%(ext)s")),
            "merge_output_format": "mp4", "overwrites": True, "progress_hooks": [gancho]}
    if inicio is not None and fim is not None:
        opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(inicio, fim)])
    _baixar(opts, url, destino, paralelo=4)
    if not destino.exists():
        candidatos = sorted(destino.parent.glob(destino.stem + ".*"), key=lambda p: p.stat().st_mtime)
        candidatos = [p for p in candidatos if p.suffix in (".mp4", ".mkv", ".webm")]
        if not candidatos:
            raise RuntimeError("o yt-dlp não gerou o arquivo do trecho")
        candidatos[-1].replace(destino)
    return destino


def baixar_audio(url: str, destino: Path, ao_progresso=None, inicio: float | None = None,
                 fim: float | None = None) -> Path:
    """Áudio do vídeo (ou do trecho [inicio, fim]) na menor qualidade: só serve para achar picos."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    def gancho(d):
        if ao_progresso and d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate")
            if tot:
                ao_progresso(d.get("downloaded_bytes", 0) / tot)

    # prefere um arquivo HTTP direto; se só houver HLS (Twitch), quem baixa é o ffmpeg (o HLS nativo do yt-dlp
    # perde fragmentos no Windows)
    opts = {"format": "worstaudio[protocol^=http]/worstaudio/audio_only/bestaudio/worst",
            "outtmpl": str(destino.with_suffix(".%(ext)s")), "overwrites": True, "progress_hooks": [gancho],
            "external_downloader": {"m3u8": "ffmpeg"}}
    if inicio is not None and fim is not None:
        opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(inicio, fim)])
    real = _baixar(opts, url, destino, paralelo=8)["arquivo"]
    if not real.exists():
        achados = [p for p in destino.parent.glob(destino.stem + ".*") if p.suffix not in (".part", ".ytdl")]
        if not achados:
            raise RuntimeError("o yt-dlp não gerou o áudio")
        real = achados[0]
    return real


# ------------------------------------------------------------------ identificar um link qualquer

# extractor do yt-dlp -> plataforma do projeto
_PLATAFORMAS = {"twitch": "twitch", "youtube": "youtube", "kick": "kick"}


def identificar(url: str) -> dict:
    """Lê um link (Twitch, YouTube, Kick ou outro site que o yt-dlp aceite) sem baixar o vídeo.
    Devolve plataforma, tipo (vod/clipe), canal (login/@handle), nome do canal, título, duração, idioma..."""
    url = url.strip()
    # extract_flat: se for um canal/lista, não abre cada vídeo (seria lento); um vídeo só é lido inteiro
    with _ydl(skip_download=True, extract_flat="in_playlist", playlistend=1) as y:
        try:
            i = y.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            raise ValueError(f"não consegui ler este link: {str(e).replace('ERROR: ', '')[:300]}") from None
    if i.get("_type") == "playlist":
        raise ValueError("isto é uma lista/canal: cole o link de UM vídeo, live gravada ou clipe")
    if i.get("is_live") or i.get("live_status") == "is_live":
        raise ValueError("a live ainda está no ar: espere terminar e use o VOD")
    chave = (i.get("extractor_key") or i.get("extractor") or "").lower()
    plataforma = next((p for k, p in _PLATAFORMAS.items() if chave.startswith(k)), "outro")
    clipe = "clip" in chave or "/clip/" in url or "clips.twitch.tv" in url or "/shorts/" in url
    if plataforma == "twitch":
        canal = (i.get("uploader_id") or i.get("channel") or i.get("uploader") or "").lower()
    elif plataforma == "youtube":
        canal = i.get("uploader_id") or (f"channel/{i['channel_id']}" if i.get("channel_id") else "")
    else:
        canal = i.get("uploader_id") or i.get("channel") or i.get("uploader") or ""
    thumbs = i.get("thumbnails") or []
    return {
        "url": i.get("webpage_url") or url,
        "plataforma": plataforma,
        "site": i.get("extractor_key") or plataforma,
        "tipo": "clipe" if clipe else "vod",
        "canal": canal,
        "canal_nome": i.get("channel") or i.get("uploader") or canal,
        "titulo": i.get("title") or "",
        "duracao": i.get("duration"),
        "views": i.get("view_count"),
        "publicado_em": _data(i.get("timestamp") or i.get("upload_date")),
        "miniatura": thumbs[-1]["url"] if thumbs else i.get("thumbnail"),
        "idioma": (i.get("language") or "")[:2] or None,   # nem todo site informa; o Whisper confirma depois
        "largura": i.get("width"),
        "altura": i.get("height"),
    }
