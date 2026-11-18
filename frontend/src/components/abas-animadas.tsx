import type { LucideIcon } from 'lucide-react'
import { AnimatePresence, motion, MotionConfig } from 'motion/react'
import { type ReactNode, useId, useState } from 'react'
import useMeasure from 'react-use-measure'

import { cn } from '@/lib/utils'

export interface Aba<T extends string> {
  id: T
  rotulo: ReactNode
  Icone?: LucideIcon
  /** bolinha pulsando ao lado do rótulo (algo pede atenção nesta aba) */
  alerta?: boolean
  contagem?: number
}

/**
 * Abas com a "bolha" que desliza até a aba ativa e o conteúdo entrando pelo lado certo (adaptado do
 * Direction Aware Tabs do cult-ui, mas controlado: o valor vem de fora, ex. da URL).
 * Sem `children`, mostra só a barra de abas.
 */
export function AbasAnimadas<T extends string>({ abas, valor, onChange, children, className }: {
  abas: Aba<NoInfer<T>>[]
  valor: T
  onChange: (v: T) => void
  children?: ReactNode
  className?: string
}) {
  const id = useId()
  const indice = abas.findIndex((a) => a.id === valor)
  // direção da animação: para a direita quando a nova aba fica depois da anterior
  const [anterior, setAnterior] = useState(indice)
  const [direcao, setDirecao] = useState(1)
  if (anterior !== indice) {
    setDirecao(indice > anterior ? 1 : -1)
    setAnterior(indice)
  }
  const [ref, medidas] = useMeasure()

  return (
    <div className={cn('w-full', className)}>
      <div className="inline-flex max-w-full flex-wrap gap-1 rounded-full border border-white/5 bg-black/40 p-1 shadow-[inset_0_1px_2px_rgba(0,0,0,0.6)]">
        {abas.map((a) => {
          const ativa = a.id === valor
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => onChange(a.id)}
              className={cn(
                'relative flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring',
                ativa ? 'text-white' : 'text-muted-foreground hover:text-foreground',
              )}
              style={{ WebkitTapHighlightColor: 'transparent' }}
            >
              {ativa && (
                <motion.span
                  layoutId={`bolha-${id}`}
                  className="absolute inset-0 rounded-full border border-white/10 bg-gradient-to-b from-roxo/60 to-rosa/40 shadow-[0_0_20px_-4px] shadow-rosa/60"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.45 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-2">
                {a.Icone && <a.Icone className="size-4" />}
                {a.rotulo}
                {a.contagem != null && (
                  <span className={cn('rounded-full px-1.5 font-mono text-[10px] tabular-nums', ativa ? 'bg-white/20' : 'bg-muted')}>
                    {a.contagem}
                  </span>
                )}
                {a.alerta && (
                  <span className="relative flex size-2">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-amarelo opacity-75" />
                    <span className="relative inline-flex size-2 rounded-full bg-amarelo" />
                  </span>
                )}
              </span>
            </button>
          )
        })}
      </div>
      {children != null && (
        <MotionConfig transition={{ duration: 0.35, type: 'spring', bounce: 0.15 }}>
          <motion.div className="relative mt-4 overflow-hidden" initial={false} animate={{ height: medidas.height || 'auto' }}>
            <div ref={ref} className="p-0.5">
              <AnimatePresence custom={direcao} mode="popLayout" initial={false}>
                <motion.div
                  key={valor}
                  custom={direcao}
                  variants={{
                    entra: (d: number) => ({ x: 60 * d, opacity: 0, filter: 'blur(4px)' }),
                    ativa: { x: 0, opacity: 1, filter: 'blur(0px)' },
                    sai: (d: number) => ({ x: -60 * d, opacity: 0, filter: 'blur(4px)' }),
                  }}
                  initial="entra"
                  animate="ativa"
                  exit="sai"
                >
                  {children}
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.div>
        </MotionConfig>
      )}
    </div>
  )
}
