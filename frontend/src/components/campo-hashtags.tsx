import { Hash, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'

import { normalizarHashtags } from '@/lib/textos'
import { cn } from '@/lib/utils'

/**
 * Hashtags como "chips": digite e aperte Enter/espaço/vírgula (o # é opcional), cole várias de uma vez,
 * Backspace apaga a última, clique no × para tirar uma. Valor = string "#a #b #c".
 */
export function CampoHashtags({ valor, onChange, id, aviso }: {
  valor: string
  onChange: (v: string) => void
  id?: string
  aviso?: string | null
}) {
  const [texto, setTexto] = useState('')
  const tags = normalizarHashtags(valor)
  const definir = (lista: string[]) => onChange(lista.join(' '))
  const adicionar = (t: string) => {
    const novas = normalizarHashtags(`${tags.join(' ')} ${t}`)
    if (novas.length !== tags.length) definir(novas)
    setTexto('')
  }

  return (
    <div
      className={cn(
        'flex min-h-10 flex-wrap items-center gap-1.5 rounded-lg border bg-white/[0.03] p-1.5 transition-colors focus-within:border-roxo/60',
        aviso && 'border-amarelo/60',
      )}
      onClick={() => document.getElementById(id ?? 'hashtags')?.focus()}
    >
      <AnimatePresence initial={false}>
        {tags.map((t) => (
          <motion.span
            key={t.toLowerCase()}
            layout
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="group flex items-center gap-1 rounded-full bg-gradient-to-r from-roxo/30 to-rosa/20 py-0.5 pr-1 pl-2.5 text-xs font-medium ring-1 ring-white/10"
          >
            {t}
            <button
              type="button"
              aria-label={`Tirar ${t}`}
              onClick={(e) => {
                e.stopPropagation()
                definir(tags.filter((x) => x !== t))
              }}
              className="rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-white/15 hover:text-white"
            >
              <X className="size-3" />
            </button>
          </motion.span>
        ))}
      </AnimatePresence>
      <div className="flex min-w-32 flex-1 items-center gap-1 px-1">
        {!tags.length && <Hash className="size-3.5 text-muted-foreground" />}
        <input
          id={id ?? 'hashtags'}
          value={texto}
          placeholder={tags.length ? 'mais uma…' : 'gta6, fyp, viral…'}
          className="w-full bg-transparent py-1 text-sm outline-none placeholder:text-muted-foreground/60"
          onChange={(e) => {
            const v = e.target.value
            if (/[\s,;]$/.test(v)) adicionar(v)
            else setTexto(v)
          }}
          onPaste={(e) => {
            e.preventDefault()
            adicionar(e.clipboardData.getData('text'))
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              adicionar(texto)
            } else if (e.key === 'Backspace' && !texto && tags.length) {
              definir(tags.slice(0, -1))
            }
          }}
          onBlur={() => texto && adicionar(texto)}
        />
      </div>
    </div>
  )
}
