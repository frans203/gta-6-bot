import { motion } from 'motion/react'
import type { ReactNode } from 'react'

import { GradientHeading } from '@/components/ui/gradient-heading'

/** Título de página + descrição + ações à direita. */
export function Cabecalho({ titulo, descricao, children }: { titulo: ReactNode; descricao?: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {typeof titulo === 'string' ? (
          <GradientHeading variant="jason" size="sm" weight="black" className="font-heading">
            {titulo}
          </GradientHeading>
        ) : (
          // título com ícone/elementos: o texto em gradiente (background-clip) some dentro de filhos com display próprio
          <h1 className="font-heading text-xl font-black tracking-tight text-[#efe9ff] sm:text-2xl lg:text-3xl">{titulo}</h1>
        )}
        {descricao && (
          <motion.p
            className="mt-1.5 max-w-2xl text-sm text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.12, duration: 0.4 }}
          >
            {descricao}
          </motion.p>
        )}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}

/** Estado vazio de listas. */
export function Vazio({ icone, titulo, children }: { icone?: ReactNode; titulo: string; children?: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-white/10 bg-white/[0.015] p-12 text-center"
    >
      {icone && (
        <div className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-roxo/25 to-rosa/15 text-ciano ring-1 ring-white/10 [&_svg]:size-7">
          {icone}
        </div>
      )}
      <p className="font-heading text-base font-semibold">{titulo}</p>
      {children && <div className="max-w-md text-sm text-muted-foreground">{children}</div>}
    </motion.div>
  )
}
