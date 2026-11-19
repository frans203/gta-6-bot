import { DndContext, type DragEndEvent, PointerSensor, closestCenter, useSensor, useSensors } from '@dnd-kit/core'
import { horizontalListSortingStrategy, SortableContext, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { ClipboardPaste, Copy, CopyPlus, GripVertical, Pause, Play, Scissors, ScissorsLineDashed, SkipBack, Star, Trash2, Zap } from 'lucide-react'
import { useRef, useState } from 'react'
import useMeasure from 'react-use-measure'

import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { aparar, type Edicao, fmtSeg, localizar, moverTrecho, type SegArq } from '@/lib/editor/modelo'
import type { Reproducao } from '@/lib/editor/reproducao'
import { cn } from '@/lib/utils'

const CORES = ['from-roxo/70 to-roxo/40', 'from-rosa/70 to-rosa/40', 'from-laranja/60 to-laranja/30', 'from-ciano/60 to-ciano/30']

interface Props {
  ed: Edicao
  segs: SegArq[]
  base: number
  duracaoArquivo: number
  /** onde o corte original começa/termina dentro do arquivo (o resto é a folga) */
  janela: { a: number; b: number }
  rep: Reproducao
  selecionado: number | null
  onSelecionar: (k: number | null) => void
  onChange: (ed: Edicao, grupo?: string) => void
  onCortar: () => void
  onApagar: () => void
  onCopiar: () => void
  onRecortar: () => void
  onColar: () => void
  onDuplicar: () => void
  temCopia: boolean
  /** momento mais forte do corte, em segundos do ARQUIVO (análise: sinais.pico); null = não se sabe */
  pico?: number | null
  onGanchoInicio?: () => void
}

function Dica({ texto, atalho, children }: { texto: string; atalho?: string; children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent>
        {texto}
        {atalho && <kbd className="ml-2 rounded bg-white/15 px-1 font-mono text-[10px]">{atalho}</kbd>}
      </TooltipContent>
    </Tooltip>
  )
}

/** Um trecho na trilha: arrasta pelo corpo para reordenar, pelas pontas para aparar. */
function Bloco({ id, k, seg, largura, selecionado, onSelecionar, onAparar }: {
  id: string
  k: number
  seg: SegArq
  largura: string
  selecionado: boolean
  onSelecionar: (clientX: number) => void
  onAparar: (lado: 'i' | 'f') => (e: React.PointerEvent) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  return (
    <div
      ref={setNodeRef}
      style={{ width: largura, transform: CSS.Translate.toString(transform), transition }}
      className={cn('relative h-full shrink-0 px-px', isDragging && 'z-20 opacity-80')}
    >
      <div
        {...attributes}
        {...listeners}
        onClick={(e) => onSelecionar(e.clientX)}
        className={cn(
          'group relative flex h-full cursor-grab items-center overflow-hidden rounded-lg bg-gradient-to-b ring-1 ring-white/10 transition-shadow active:cursor-grabbing',
          CORES[k % CORES.length],
          selecionado && 'ring-2 ring-white shadow-[0_0_18px_-4px] shadow-rosa',
        )}
      >
        <span className="pointer-events-none flex min-w-0 items-center gap-1 px-3 text-[11px] font-semibold text-white drop-shadow">
          <GripVertical className="size-3 shrink-0 opacity-60" />
          <span className="truncate">
            {k + 1} · {fmtSeg(seg.b - seg.a)}
          </span>
        </span>
        {(['i', 'f'] as const).map((lado) => (
          <span
            key={lado}
            onPointerDown={onAparar(lado)}
            className={cn(
              'absolute inset-y-0 z-10 flex w-2.5 cursor-ew-resize items-center justify-center bg-white/25 opacity-0 transition-opacity group-hover:opacity-100',
              lado === 'i' ? 'left-0 rounded-l-lg' : 'right-0 rounded-r-lg',
              selecionado && 'opacity-100',
            )}
          >
            <span className="h-4 w-0.5 rounded bg-white" />
          </span>
        ))}
      </div>
    </div>
  )
}

/**
 * Linha do tempo do vídeo editado (trechos na ordem; arraste um trecho para movê-lo; copiar/recortar/colar no cursor) + barra do vídeo original embaixo, com a folga baixada
 * e onde cada trecho foi tirado.
 */
export function Timeline({ ed, segs, base, duracaoArquivo, janela, rep, selecionado, onSelecionar, onChange, onCortar, onApagar, onCopiar, onRecortar, onColar, onDuplicar, temCopia, pico, onGanchoInicio }: Props) {
  const trilha = useRef<HTMLDivElement>(null)
  const sensores = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))
  // enquanto apara, a escala (px por segundo) fica parada: senão os blocos "fogem" do mouse
  const [escalaFixa, setEscalaFixa] = useState<number | null>(null)
  const aparando = useRef<{ k: number; lado: 'i' | 'f'; x: number; inicial: number; pxPorSeg: number } | null>(null)
  const total = rep.total
  const [medir, medidas] = useMeasure()
  const larguraTrilha = () => trilha.current?.getBoundingClientRect().width ?? medidas.width
  const pxPorSeg = escalaFixa ?? Math.max(1, medidas.width) / Math.max(total, 0.1)

  const ids = segs.map((s) => `seg-${s.k}`)
  const aoSoltar = (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id) return
    const de = ids.indexOf(String(e.active.id))
    const para = ids.indexOf(String(e.over.id))
    onChange(moverTrecho(ed, segs[de].k, segs[para].k))
    onSelecionar(segs[para].k)
  }

  const iniciarAparar = (k: number) => (lado: 'i' | 'f') => (e: React.PointerEvent) => {
    e.stopPropagation()
    e.preventDefault()
    rep.pausar()
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    const px = larguraTrilha() / Math.max(total, 0.1)
    aparando.current = { k, lado, x: e.clientX, inicial: ed.segmentos[k][lado], pxPorSeg: px }
    setEscalaFixa(px)
    onSelecionar(k)
    const mover = (ev: PointerEvent) => {
      const a = aparando.current
      if (!a) return
      const valor = a.inicial + (ev.clientX - a.x) / a.pxPorSeg
      onChange(aparar(ed, a.k, a.lado, valor, base, duracaoArquivo), `aparar-${a.k}-${a.lado}`)
    }
    const fim = () => {
      aparando.current = null
      setEscalaFixa(null)
      window.removeEventListener('pointermove', mover)
      window.removeEventListener('pointerup', fim)
    }
    window.addEventListener('pointermove', mover)
    window.addEventListener('pointerup', fim)
  }

  const irPara = (clientX: number) => {
    const r = trilha.current!.getBoundingClientRect()
    rep.ir(((clientX - r.left) / pxPorSeg))
  }
  const arrastarCursor = (e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest('[data-bloco]')) return
    irPara(e.clientX)
    const mover = (ev: PointerEvent) => irPara(ev.clientX)
    const fim = () => {
      window.removeEventListener('pointermove', mover)
      window.removeEventListener('pointerup', fim)
    }
    window.addEventListener('pointermove', mover)
    window.addEventListener('pointerup', fim)
  }

  const posArquivo = localizar(segs, rep.t)?.arquivo ?? 0
  const marcas = Array.from({ length: Math.floor(total / 5) + 1 }, (_, i) => i * 5)

  return (
    <div className="space-y-3 rounded-2xl border bg-card/70 p-3 backdrop-blur">
      {/* controles */}
      <div className="flex flex-wrap items-center gap-2">
        <Dica texto="Voltar ao início" atalho="Home">
          <Button size="icon-sm" variant="ghost" onClick={() => rep.ir(0)}>
            <SkipBack />
          </Button>
        </Dica>
        <Dica texto={rep.tocando ? 'Pausar' : 'Tocar'} atalho="Espaço">
          <Button size="icon" onClick={rep.alternar} className="rounded-full">
            {rep.tocando ? <Pause /> : <Play />}
          </Button>
        </Dica>
        <span className="font-mono text-sm tabular-nums">
          <span className="text-rosa">{fmtSeg(rep.t)}</span>
          <span className="text-muted-foreground"> / {fmtSeg(total)}</span>
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <Dica texto="Cortar o trecho no cursor" atalho="S">
            <Button size="sm" variant="outline" onClick={onCortar}>
              <Scissors /> Cortar aqui
            </Button>
          </Dica>
          <span className="mx-1 h-5 w-px bg-white/10" />
          <Dica texto="Copiar o trecho selecionado" atalho="Ctrl+C">
            <Button size="icon-sm" variant="outline" disabled={selecionado == null} onClick={onCopiar} aria-label="Copiar trecho">
              <Copy />
            </Button>
          </Dica>
          <Dica texto="Recortar o trecho selecionado (tira daqui para colar em outro lugar)" atalho="Ctrl+X">
            <Button size="icon-sm" variant="outline" disabled={selecionado == null || ed.segmentos.length <= 1} onClick={onRecortar} aria-label="Recortar trecho">
              <ScissorsLineDashed />
            </Button>
          </Dica>
          <Dica texto="Colar no cursor (no meio de um trecho, ele é dividido)" atalho="Ctrl+V">
            <Button size="sm" variant={temCopia ? 'default' : 'outline'} disabled={!temCopia} onClick={onColar}>
              <ClipboardPaste /> Colar
            </Button>
          </Dica>
          <Dica texto="Duplicar o trecho selecionado" atalho="Ctrl+D">
            <Button size="icon-sm" variant="outline" disabled={selecionado == null} onClick={onDuplicar} aria-label="Duplicar trecho">
              <CopyPlus />
            </Button>
          </Dica>
          {onGanchoInicio && (
            <Dica texto="Gancho no início: copia ~3 s em volta do ★ (momento mais forte) para o começo do vídeo">
              <Button size="sm" variant="outline" disabled={pico == null} onClick={onGanchoInicio}>
                <Zap /> Gancho no início
              </Button>
            </Dica>
          )}
          <Dica texto="Apagar o trecho selecionado" atalho="Delete">
            <Button size="sm" variant="outline" disabled={selecionado == null || ed.segmentos.length <= 1} onClick={onApagar}>
              <Trash2 /> Apagar trecho
            </Button>
          </Dica>
        </div>
      </div>

      {/* trilha do vídeo editado */}
      <div ref={medir} className="relative select-none" onPointerDown={arrastarCursor}>
        <div className="relative mb-1 h-4 text-[10px] text-muted-foreground">
          {marcas.map((m) => (
            <span key={m} className="absolute -translate-x-1/2 font-mono" style={{ left: m * pxPorSeg }}>
              {fmtSeg(m).replace(/\.\d$/, '')}
            </span>
          ))}
        </div>
        <div ref={trilha} className="relative h-14 overflow-visible">
          <DndContext sensors={sensores} collisionDetection={closestCenter} onDragEnd={aoSoltar} onDragStart={() => rep.pausar()}>
            <SortableContext items={ids} strategy={horizontalListSortingStrategy}>
              <div className="flex h-full" data-bloco>
                {segs.map((s, i) => (
                  <Bloco
                    key={ids[i]}
                    id={ids[i]}
                    k={s.k}
                    seg={s}
                    largura={`${(s.b - s.a) * pxPorSeg}px`}
                    selecionado={selecionado === s.k}
                    onSelecionar={(x) => (onSelecionar(s.k), irPara(x))}
                    onAparar={iniciarAparar(s.k)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          {/* ★ momento mais forte (em cada trecho que o contém) */}
          {pico != null &&
            segs
              .filter((s) => pico >= s.a && pico < s.b)
              .map((s) => (
                <Star
                  key={`pico-${s.ini}`}
                  className="pointer-events-none absolute -top-2 z-20 size-3.5 -translate-x-1/2 fill-amarelo text-amarelo drop-shadow"
                  style={{ left: (s.ini + pico - s.a) * pxPorSeg }}
                />
              ))}
          {/* cursor */}
          <div className="pointer-events-none absolute -top-5 bottom-0 z-30 w-0.5 bg-rosa shadow-[0_0_8px] shadow-rosa" style={{ left: rep.t * pxPorSeg }}>
            <span className="absolute -top-1 -left-1.5 size-3.5 rotate-45 rounded-sm bg-rosa" />
          </div>
        </div>
      </div>

      {/* vídeo original (com a folga) */}
      <div>
        <div className="mb-1 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>Vídeo original baixado (a parte clara é o corte; dá para puxar os trechos para a folga)</span>
          <span className="font-mono">
            {fmtSeg(base)} – {fmtSeg(base + duracaoArquivo)}
          </span>
        </div>
        <div className="relative h-5 overflow-hidden rounded-md bg-white/[0.04] ring-1 ring-white/5">
          <div
            className="absolute inset-y-0 border-x border-dashed border-white/30 bg-white/[0.06]"
            style={{ left: `${(janela.a / duracaoArquivo) * 100}%`, width: `${((janela.b - janela.a) / duracaoArquivo) * 100}%` }}
          />
          {segs.map((s) => (
            <div
              key={s.k}
              className={cn('absolute inset-y-1 rounded-sm bg-gradient-to-b text-center text-[9px] leading-3 font-bold text-white', CORES[s.k % CORES.length])}
              style={{ left: `${(s.a / duracaoArquivo) * 100}%`, width: `${((s.b - s.a) / duracaoArquivo) * 100}%` }}
            >
              {s.k + 1}
            </div>
          ))}
          {pico != null && (
            <Star
              className="pointer-events-none absolute top-0.5 z-10 size-3.5 -translate-x-1/2 fill-amarelo text-amarelo"
              style={{ left: `${(pico / duracaoArquivo) * 100}%` }}
            />
          )}
          <div className="absolute inset-y-0 w-px bg-rosa" style={{ left: `${(posArquivo / duracaoArquivo) * 100}%` }} />
        </div>
      </div>
    </div>
  )
}
