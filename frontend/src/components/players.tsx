import { urlEmbed } from '@/lib/embed'
import { cn } from '@/lib/utils'

/** Player de mp4 vertical (9:16) servido pela API. */
export function Player9x16({ src, className }: { src: string; className?: string }) {
  return (
    <div className={cn('mx-auto aspect-[9/16] w-full max-w-[320px] overflow-hidden rounded-xl bg-black', className)}>
      <video key={src} src={src} controls preload="metadata" className="size-full object-contain" />
    </div>
  )
}

/** Player da fonte original no trecho do corte (para revisar antes de renderizar). */
export function PlayerFonte({ url, inicio, fim, className }: { url: string; inicio: number; fim: number; className?: string }) {
  const src = urlEmbed(url, inicio, fim)
  if (!src) {
    return (
      <a href={url} target="_blank" rel="noreferrer" className="text-sm text-ciano underline">
        Abrir a fonte em outra aba
      </a>
    )
  }
  return (
    <div className={cn('aspect-video w-full overflow-hidden rounded-lg bg-black', className)}>
      <iframe
        key={src}
        src={src}
        title="Fonte do corte"
        className="size-full"
        allow="autoplay; encrypted-media; picture-in-picture"
        allowFullScreen
      />
    </div>
  )
}
