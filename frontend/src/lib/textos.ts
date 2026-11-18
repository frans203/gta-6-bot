/**
 * Texto final que cada rede recebe (espelha plataformas/comum.py: textos_rede). Usado na prévia ao vivo.
 * O robô digita tudo numa linha só: quebras de linha viram espaço.
 */
import type { TextosVideo } from '@/api/hooks/postagem'

export const LIMITES = { youtubeTitulo: 100, youtubeDescricao: 5000, tiktok: 2200, instagram: 2200, instagramHashtags: 30 }
export type Rede = 'tiktok' | 'youtube' | 'instagram'

export const linha = (s: string) => s.split(/\s+/).filter(Boolean).join(' ')
export const juntar = (...partes: (string | null | undefined)[]) => linha(partes.filter((p) => p && p.trim()).join(' '))

export function tituloYoutubePadrao(titulo: string, tags: string) {
  const t = `${titulo} ${tags.toLowerCase().includes('#gta6') ? '#gta6 #shorts' : '#shorts'}`
  return t.length <= 99 ? t : titulo.slice(0, 99)
}

export function textosFinais(t: TextosVideo) {
  const yt = t.redes?.youtube ?? {}
  return {
    youtube: {
      titulo: linha(yt.titulo || tituloYoutubePadrao(t.titulo, t.tags)).slice(0, LIMITES.youtubeTitulo),
      descricao: linha(yt.descricao || juntar(t.descricao || t.titulo, t.tags)).slice(0, LIMITES.youtubeDescricao),
    },
    tiktok: { legenda: linha(t.redes?.tiktok?.legenda || juntar(t.titulo, t.descricao, t.tags)).slice(0, LIMITES.tiktok) },
    instagram: { legenda: linha(t.redes?.instagram?.legenda || juntar(t.titulo, t.descricao, t.tags)).slice(0, LIMITES.instagram) },
  }
}

export const contarHashtags = (s: string) => (s.match(/#[\p{L}\p{N}_]+/gu) ?? []).length

/** "gta6, #fyp viral" -> ["#gta6", "#fyp", "#viral"] (sem repetir) */
export function normalizarHashtags(texto: string): string[] {
  const vistas = new Set<string>()
  const out: string[] = []
  for (const bruto of texto.split(/[\s,;]+/)) {
    const limpo = bruto.replace(/^#+/, '').replace(/[^\p{L}\p{N}_]/gu, '')
    if (!limpo) continue
    const tag = `#${limpo}`
    if (vistas.has(tag.toLowerCase())) continue
    vistas.add(tag.toLowerCase())
    out.push(tag)
  }
  return out
}
