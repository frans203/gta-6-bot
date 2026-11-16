/** Formatadores pt-BR e utilitários de tempo/URL usados em várias telas. */

const dataHora = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'short',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})
const hora = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })
const diaLongo = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })
const numero = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

const paraData = (v: string | Date) => (v instanceof Date ? v : new Date(v))

export const fmtDataHora = (v?: string | Date | null) => (v ? dataHora.format(paraData(v)) : '—')
export const fmtHora = (v?: string | Date | null) => (v ? hora.format(paraData(v)) : '—')
export const fmtDia = (v: string | Date) => diaLongo.format(paraData(v))
export const fmtNumero = (n?: number | null) => (n == null ? '—' : numero.format(n))

/** "há 5 min", "há 2 h"... */
export function fmtRelativo(v?: string | null) {
  if (!v) return '—'
  const s = Math.round((Date.now() - new Date(v).getTime()) / 1000)
  if (s < 60) return 'agora'
  if (s < 3600) return `há ${Math.floor(s / 60)} min`
  if (s < 86400) return `há ${Math.floor(s / 3600)} h`
  return `há ${Math.floor(s / 86400)} d`
}

/** 3725 -> "1:02:05"; 65 -> "1:05" */
export function fmtTempo(seg?: number | null) {
  if (seg == null || Number.isNaN(seg)) return '—'
  const t = Math.max(0, Math.round(seg))
  const h = Math.floor(t / 3600)
  const m = Math.floor((t % 3600) / 60)
  const s = t % 60
  const ss = String(s).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`
}

/** "1:02:05" | "62:05" | "125" -> segundos (null se inválido) */
export function lerTempo(texto: string): number | null {
  const partes = texto.trim().split(':').map(Number)
  if (!partes.length || partes.some((p) => Number.isNaN(p) || p < 0)) return null
  return partes.reduce((acc, p) => acc * 60 + p, 0)
}

/** Duração legível: 23474 -> "6h31" ; 45 -> "45s" */
export function fmtDuracao(seg?: number | null) {
  if (seg == null) return '—'
  if (seg < 60) return `${Math.round(seg)}s`
  const h = Math.floor(seg / 3600)
  const m = Math.round((seg % 3600) / 60)
  return h ? `${h}h${String(m).padStart(2, '0')}` : `${m} min`
}

/** Formato do parâmetro `time` do player da Twitch: 3725 -> "1h2m5s" */
export function tempoTwitch(seg: number) {
  const t = Math.max(0, Math.floor(seg))
  return `${Math.floor(t / 3600)}h${Math.floor((t % 3600) / 60)}m${t % 60}s`
}

export const idYoutube = (url: string) =>
  url.match(/(?:v=|youtu\.be\/|\/shorts\/|\/live\/|\/embed\/)([\w-]{11})/)?.[1] ?? null
export const idVodTwitch = (url: string) => url.match(/twitch\.tv\/videos\/(\d+)/)?.[1] ?? null
export const slugClipeTwitch = (url: string) =>
  url.match(/clips\.twitch\.tv\/([\w-]+)/)?.[1] ?? url.match(/twitch\.tv\/[^/]+\/clip\/([\w-]+)/)?.[1] ?? null

/** Chave de dia local (YYYY-MM-DD) para agrupar listas. */
export function chaveDia(v: string | Date) {
  const d = paraData(v)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Agrupa itens por dia mantendo a ordem. */
export function agruparPorDia<T>(itens: T[], data: (x: T) => string | Date): [string, T[]][] {
  const mapa = new Map<string, T[]>()
  for (const x of itens) {
    const k = chaveDia(data(x))
    mapa.set(k, [...(mapa.get(k) ?? []), x])
  }
  return [...mapa.entries()]
}
