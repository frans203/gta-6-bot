import { useEffect, useRef, useState } from 'react'

import type { Regiao } from '@/api/tipos'
import { type Cena, desenhar } from '@/lib/editor/desenho'
import type { Caixa, Edicao, Palavra } from '@/lib/editor/modelo'
import type { Reproducao } from '@/lib/editor/reproducao'
import { cn } from '@/lib/utils'

export type Elemento = 'jogo' | 'webcam' | 'legenda' | 'gancho'

type Arraste =
  | { tipo: 'caixa'; alvo: 'jogo' | 'webcam'; modo: 'mover' | 'nw' | 'ne' | 'sw' | 'se'; px: number; py: number; inicial: Caixa }
  | { tipo: 'linha'; alvo: 'legenda' | 'gancho'; py: number; inicial: number }

const IMA = 0.012
/** Encaixa nas bordas e no centro do vídeo (como os guias de um editor). */
function imantar(v: number, tamanho: number) {
  for (const alvo of [0, 0.5 - tamanho / 2, 1 - tamanho]) if (Math.abs(v - alvo) < IMA) return alvo
  return v
}

interface Props {
  ed: Edicao
  sw: number
  sh: number
  rep: Reproducao
  fonteVideo: string
  fundoImg: string | null
  corteJogo?: Regiao | null
  corteWebcam?: Regiao | null
  grupos: Palavra[][]
  gancho: string | null
  credito: string
  barra: boolean
  selecionado: Elemento | null
  onSelecionar: (e: Elemento | null) => void
  onChange: (ed: Edicao, grupo: string) => void
  /** aumenta quando algo externo pede para redesenhar (ex.: uma fonte terminou de carregar) */
  versao: number
}

/**
 * Prévia ao vivo do vídeo editado: um canvas 9:16 desenhado a cada quadro a partir do trecho baixado
 * (o mesmo vídeo para jogo e streamer: não tem como dessincronizar) + caixas arrastáveis por cima.
 */
export function PreviaCanvas(p: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const camada = useRef<HTMLDivElement>(null)
  const fundo = useRef<HTMLImageElement | null>(null)
  const cena = useRef<Omit<Cena, 't' | 'video' | 'videoCam' | 'fundoImg'> | null>(null)
  const sujo = useRef(true)
  const arraste = useRef<Arraste | null>(null)
  const [guias, setGuias] = useState<{ x: boolean; y: boolean }>({ x: false, y: false })
  const usarCam = !p.ed.sincronizado && Math.abs(p.ed.atraso_streamer) > 0.01

  useEffect(() => {
    cena.current = {
      ed: p.ed,
      sw: p.sw,
      sh: p.sh,
      corteJogo: p.corteJogo,
      corteWebcam: p.corteWebcam,
      grupos: p.grupos,
      duracao: p.rep.total,
      gancho: p.gancho,
      credito: p.credito,
      barra: p.barra,
    }
    sujo.current = true
  })

  useEffect(() => {
    if (!p.fundoImg) {
      fundo.current = null
      return
    }
    const img = new Image()
    img.onload = () => (sujo.current = true)
    img.src = p.fundoImg
    fundo.current = img
  }, [p.fundoImg])

  useEffect(() => {
    sujo.current = true
  }, [p.versao])

  // laço de desenho: todo quadro enquanto toca; parado, só quando algo mudou
  const { video, cam, tRef, tocando } = p.rep
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d')
    if (!ctx) return
    const marcar = () => (sujo.current = true)
    const v = video.current
    const c = cam.current
    v?.addEventListener('seeked', marcar)
    v?.addEventListener('loadeddata', marcar)
    c?.addEventListener('seeked', marcar)
    let quadro = 0
    let prontoAntes = false
    const passo = () => {
      // o vídeo acabou de ficar pronto (o 1º quadro chega depois do 'loadeddata' às vezes): redesenha
      const pronto = !!v && v.readyState >= 2 && (!usarCam || !c || c.readyState >= 2)
      if (pronto !== prontoAntes) {
        prontoAntes = pronto
        sujo.current = true
      }
      if ((tocando || sujo.current) && cena.current && v) {
        sujo.current = false
        ctx.setTransform(canvas.current!.width / 1080, 0, 0, canvas.current!.height / 1920, 0, 0)
        desenhar(ctx, { ...cena.current, t: tRef.current, video: v, videoCam: usarCam && c ? c : v, fundoImg: fundo.current })
      }
      quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => {
      cancelAnimationFrame(quadro)
      v?.removeEventListener('seeked', marcar)
      v?.removeEventListener('loadeddata', marcar)
      c?.removeEventListener('seeked', marcar)
    }
  }, [video, cam, tRef, tocando, usarCam])

  // ------------------------------------------------------------------ arrastar caixas e linhas

  const fracao = () => {
    const r = camada.current!.getBoundingClientRect()
    return { fx: 1 / r.width, fy: 1 / r.height }
  }

  const iniciarCaixa = (alvo: 'jogo' | 'webcam', modo: Extract<Arraste, { tipo: 'caixa' }>['modo']) => (e: React.PointerEvent) => {
    e.preventDefault()
    e.stopPropagation()
    p.onSelecionar(alvo)
    const zona = alvo === 'jogo' ? p.ed.layout.jogo : p.ed.layout.webcam
    if (!zona) return
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    arraste.current = { tipo: 'caixa', alvo, modo, px: e.clientX, py: e.clientY, inicial: zona.saida }
  }

  const iniciarLinha = (alvo: 'legenda' | 'gancho') => (e: React.PointerEvent) => {
    e.preventDefault()
    e.stopPropagation()
    p.onSelecionar(alvo)
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    arraste.current = { tipo: 'linha', alvo, py: e.clientY, inicial: alvo === 'legenda' ? p.ed.legenda.y : p.ed.gancho.y }
  }

  const mover = (e: React.PointerEvent) => {
    const a = arraste.current
    if (!a) return
    const { fx, fy } = fracao()
    if (a.tipo === 'linha') {
      const y = Math.round((a.inicial + (e.clientY - a.py) * fy) * 1000) / 1000
      if (a.alvo === 'legenda') p.onChange({ ...p.ed, legenda: { ...p.ed.legenda, y: Math.min(0.97, Math.max(0.03, y)) } }, 'arrastar-legenda')
      else p.onChange({ ...p.ed, gancho: { ...p.ed.gancho, y: Math.min(0.9, Math.max(0, y)) } }, 'arrastar-gancho')
      return
    }
    const dx = (e.clientX - a.px) * fx
    const dy = (e.clientY - a.py) * fy
    const c = { ...a.inicial }
    const livre = e.altKey // Alt: sem ímã
    if (a.modo === 'mover') {
      c.x = a.inicial.x + dx
      c.y = a.inicial.y + dy
      if (!livre) {
        c.x = imantar(c.x, c.w)
        c.y = imantar(c.y, c.h)
      }
    } else {
      const prop = a.inicial.w / a.inicial.h
      if (a.modo.includes('e')) c.w = a.inicial.w + dx
      if (a.modo.includes('w')) {
        c.w = a.inicial.w - dx
        c.x = a.inicial.x + dx
      }
      if (a.modo.includes('s')) c.h = a.inicial.h + dy
      if (a.modo.includes('n')) {
        c.h = a.inicial.h - dy
        c.y = a.inicial.y + dy
      }
      if (e.shiftKey) {
        // Shift: mantém a proporção
        const h = c.w / prop
        if (a.modo.includes('n')) c.y = a.inicial.y + a.inicial.h - h
        c.h = h
      }
      c.w = Math.max(0.05, c.w)
      c.h = Math.max(0.03, c.h)
    }
    const r = (n: number) => Math.round(n * 10000) / 10000
    const caixa = { x: r(c.x), y: r(c.y), w: r(c.w), h: r(c.h) }
    setGuias({ x: Math.abs(caixa.x + caixa.w / 2 - 0.5) < 0.001, y: Math.abs(caixa.y + caixa.h / 2 - 0.5) < 0.001 })
    const lay = p.ed.layout
    p.onChange(
      {
        ...p.ed,
        layout:
          a.alvo === 'jogo'
            ? { ...lay, jogo: { ...lay.jogo, saida: caixa } }
            : { ...lay, webcam: lay.webcam ? { ...lay.webcam, saida: caixa } : lay.webcam },
      },
      `arrastar-${a.alvo}`,
    )
  }

  const soltar = () => {
    arraste.current = null
    setGuias({ x: false, y: false })
  }

  const caixaEstilo = (c: Caixa) => ({ left: `${c.x * 100}%`, top: `${c.y * 100}%`, width: `${c.w * 100}%`, height: `${c.h * 100}%` })
  const ALCAS = ['nw', 'ne', 'sw', 'se'] as const
  const posAlca = { nw: '-top-1.5 -left-1.5 cursor-nwse-resize', ne: '-top-1.5 -right-1.5 cursor-nesw-resize', sw: '-bottom-1.5 -left-1.5 cursor-nesw-resize', se: '-right-1.5 -bottom-1.5 cursor-nwse-resize' }

  const zonas: { id: 'jogo' | 'webcam'; rotulo: string; caixa: Caixa; cor: string }[] = [
    { id: 'jogo', rotulo: 'JOGO', caixa: p.ed.layout.jogo.saida, cor: 'border-amarelo' },
  ]
  if (p.ed.layout.webcam) zonas.push({ id: 'webcam', rotulo: 'STREAMER', caixa: p.ed.layout.webcam.saida, cor: 'border-ciano' })
  if (!p.ed.layout.webcam_na_frente) zonas.reverse()

  return (
    <div className="relative mx-auto aspect-[9/16] h-full max-h-full overflow-hidden rounded-2xl bg-black shadow-[0_0_60px_-20px] shadow-roxo/70 ring-1 ring-white/10">
      <video ref={video} src={p.fonteVideo} preload="auto" playsInline className="hidden" />
      <video ref={cam} src={usarCam ? p.fonteVideo : undefined} preload="auto" playsInline muted className="hidden" />
      <canvas ref={canvas} width={540} height={960} className="absolute inset-0 size-full" />
      <div
        ref={camada}
        className="absolute inset-0 touch-none select-none"
        onPointerMove={mover}
        onPointerUp={soltar}
        onPointerCancel={soltar}
        onPointerDown={() => p.onSelecionar(null)}
      >
        {guias.x && <div className="pointer-events-none absolute inset-y-0 left-1/2 w-px bg-rosa/80" />}
        {guias.y && <div className="pointer-events-none absolute inset-x-0 top-1/2 h-px bg-rosa/80" />}
        {zonas.map((z) => {
          const sel = p.selecionado === z.id
          return (
            <div
              key={z.id}
              style={caixaEstilo(z.caixa)}
              onPointerDown={iniciarCaixa(z.id, 'mover')}
              className={cn(
                'group absolute cursor-move border-2 transition-colors',
                sel ? `${z.cor} bg-white/5` : 'border-transparent hover:border-white/40',
              )}
            >
              <span
                className={cn(
                  'absolute top-1 left-1 rounded px-1 text-[9px] font-bold text-black opacity-0 transition-opacity group-hover:opacity-100',
                  z.id === 'jogo' ? 'bg-amarelo' : 'bg-ciano',
                  sel && 'opacity-100',
                )}
              >
                {z.rotulo}
              </span>
              {sel &&
                ALCAS.map((a) => (
                  <span
                    key={a}
                    onPointerDown={iniciarCaixa(z.id, a)}
                    className={cn('absolute size-3 rounded-full border-2 border-black bg-white', posAlca[a])}
                  />
                ))}
            </div>
          )
        })}
        {p.ed.legenda.mostrar && (
          <LinhaArrastavel
            y={p.ed.legenda.y}
            rotulo="LEGENDA"
            selecionada={p.selecionado === 'legenda'}
            onPointerDown={iniciarLinha('legenda')}
            centro
          />
        )}
        {p.gancho && (
          <LinhaArrastavel y={p.ed.gancho.y} rotulo="GANCHO" selecionada={p.selecionado === 'gancho'} onPointerDown={iniciarLinha('gancho')} />
        )}
      </div>
    </div>
  )
}

function LinhaArrastavel({ y, rotulo, selecionada, onPointerDown, centro }: {
  y: number
  rotulo: string
  selecionada: boolean
  onPointerDown: (e: React.PointerEvent) => void
  centro?: boolean
}) {
  return (
    <div
      onPointerDown={onPointerDown}
      style={{ top: `${y * 100}%` }}
      className={cn('group absolute inset-x-[6%] z-10 h-6 cursor-ns-resize', centro && '-translate-y-1/2')}
    >
      <div
        className={cn(
          'absolute inset-x-0 top-1/2 border-t-2 border-dashed transition-colors',
          selecionada ? 'border-rosa' : 'border-transparent group-hover:border-white/50',
        )}
      />
      <span
        className={cn(
          'absolute top-1/2 -right-1 -translate-y-1/2 rounded bg-rosa px-1 text-[9px] font-bold text-white opacity-0 transition-opacity group-hover:opacity-100',
          selecionada && 'opacity-100',
        )}
      >
        {rotulo}
      </span>
    </div>
  )
}
