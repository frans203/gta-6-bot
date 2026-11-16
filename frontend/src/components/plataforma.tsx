import { Globe, Music2, Tv } from 'lucide-react'
import type { ComponentType, SVGProps } from 'react'

import { IconeInstagram, IconeTwitch, IconeYoutube } from '@/components/icones-marca'
import { cn } from '@/lib/utils'

const INFO: Record<string, { nome: string; Icone: ComponentType<SVGProps<SVGSVGElement>>; cor: string }> = {
  tiktok: { nome: 'TikTok', Icone: Music2, cor: 'text-ciano' },
  youtube: { nome: 'YouTube', Icone: IconeYoutube, cor: 'text-[#ff4e45]' },
  instagram: { nome: 'Instagram', Icone: IconeInstagram, cor: 'text-rosa' },
  twitch: { nome: 'Twitch', Icone: IconeTwitch, cor: 'text-[#a970ff]' },
  kick: { nome: 'Kick', Icone: Tv, cor: 'text-[#53fc18]' },
  outro: { nome: 'Outro site', Icone: Globe, cor: 'text-muted-foreground' },
}

/** Ícone + nome de uma rede (tiktok, youtube, instagram, twitch). */
export function Plataforma({ p, soIcone, className }: { p: string; soIcone?: boolean; className?: string }) {
  const i = INFO[p]
  if (!i) return <span className={className}>{p}</span>
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)} title={i.nome}>
      <i.Icone className={cn('size-4', i.cor)} />
      {!soIcone && <span>{i.nome}</span>}
    </span>
  )
}
