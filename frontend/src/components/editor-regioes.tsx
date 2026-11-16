import { useRef, useState } from 'react'

import type { Regiao } from '@/api/tipos'
import { normalizarRegiao } from '@/lib/enquadramento'
import { cn } from '@/lib/utils'

export interface RegiaoEditavel {
  id: string
  rotulo: string
  /** classes de cor da borda/fundo/etiqueta (ex.: 'border-ciano bg-ciano/15', 'bg-ciano') */
  cor: { caixa: string; etiqueta: string }
  valor: Regiao
}

type Arraste = { id: string; modo: 'mover' | 'redim'; px: number; py: number; inicial: Regiao }

interface Props {
  quadro: string | null
  regioes: RegiaoEditavel[]
  onChange: (id: string, r: Regiao) => void
  /** texto quando não há quadro */
  semQuadro?: React.ReactNode
  className?: string
}

/**
 * Quadro do vídeo original com retângulos editáveis: arraste para mover, puxe o canto para redimensionar.
 * Controlado: quem usa guarda os valores (frações 0..1 do quadro).
 */
export function EditorRegioes({ quadro, regioes, onChange, semQuadro, className }: Props) {
  const [semImagem, setSemImagem] = useState(false)
  const [ativa, setAtiva] = useState<string | null>(null)
  const caixa = useRef<HTMLDivElement>(null)
  const arraste = useRef<Arraste | null>(null)

  const iniciar = (r: RegiaoEditavel, modo: Arraste['modo']) => (e: React.PointerEvent) => {
    e.preventDefault()
    e.stopPropagation()
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    arraste.current = { id: r.id, modo, px: e.clientX, py: e.clientY, inicial: r.valor }
    setAtiva(r.id)
  }

  const mover = (e: React.PointerEvent) => {
    const a = arraste.current
    const b = caixa.current?.getBoundingClientRect()
    if (!a || !b) return
    const dx = (e.clientX - a.px) / b.width
    const dy = (e.clientY - a.py) / b.height
    const i = a.inicial
    onChange(a.id, normalizarRegiao(a.modo === 'mover' ? { ...i, x: i.x + dx, y: i.y + dy } : { ...i, w: i.w + dx, h: i.h + dy }))
  }

  const soltar = () => {
    arraste.current = null
  }

  return (
    <div
      ref={caixa}
      className={cn('relative aspect-video w-full touch-none overflow-hidden rounded-lg border bg-black/60 select-none', className)}
      onPointerMove={mover}
      onPointerUp={soltar}
      onPointerCancel={soltar}
    >
      {quadro && !semImagem ? (
        <img src={quadro} alt="Quadro do vídeo" className="size-full object-cover" onError={() => setSemImagem(true)} draggable={false} />
      ) : (
        <div className="flex size-full items-center justify-center p-4 text-center text-sm text-muted-foreground">
          {semQuadro ?? 'Sem quadro de referência ainda.'}
        </div>
      )}
      {regioes.map((r) => (
        <div
          key={r.id}
          className={cn('absolute cursor-move border-2', r.cor.caixa, ativa === r.id ? 'z-20' : 'z-10')}
          style={{ left: `${r.valor.x * 100}%`, top: `${r.valor.y * 100}%`, width: `${r.valor.w * 100}%`, height: `${r.valor.h * 100}%` }}
          onPointerDown={iniciar(r, 'mover')}
        >
          <span className={cn('absolute top-0 left-0 px-1 text-[10px] font-bold text-black', r.cor.etiqueta)}>{r.rotulo}</span>
          <span
            className={cn('absolute -right-1.5 -bottom-1.5 size-3.5 cursor-nwse-resize rounded-sm border-2 border-black', r.cor.etiqueta)}
            onPointerDown={iniciar(r, 'redim')}
          />
        </div>
      ))}
    </div>
  )
}
