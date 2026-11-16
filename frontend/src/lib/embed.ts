import { idVodTwitch, idYoutube, slugClipeTwitch, tempoTwitch } from '@/lib/formatos'

/** Domínios onde a interface roda (o player da Twitch exige `parent`). */
function parents() {
  const hosts = new Set(['localhost', '127.0.0.1', window.location.hostname])
  return [...hosts].map((h) => `parent=${encodeURIComponent(h)}`).join('&')
}

/** URL de embed da fonte (YouTube, VOD ou clipe da Twitch) já no ponto certo. */
export function urlEmbed(url: string, inicio: number, fim: number): string | null {
  const yt = idYoutube(url)
  if (yt) return `https://www.youtube.com/embed/${yt}?start=${Math.floor(inicio)}&end=${Math.ceil(fim)}&rel=0`
  const vod = idVodTwitch(url)
  if (vod) return `https://player.twitch.tv/?video=v${vod}&time=${tempoTwitch(inicio)}&${parents()}&autoplay=false`
  const clipe = slugClipeTwitch(url)
  if (clipe) return `https://clips.twitch.tv/embed?clip=${clipe}&${parents()}&autoplay=false`
  return null
}
