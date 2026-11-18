import { useCallback, useEffect, useRef, useState } from 'react'

import { duracaoTotal, localizar, type SegArq } from './modelo'

/**
 * Toca a edição: um <video> com o trecho baixado pula de trecho em trecho na ordem da linha do tempo.
 * Sem sincronia, um 2º <video> (mudo) toca a mesma fonte deslocada pelo atraso, para a webcam.
 * `tRef` tem o tempo exato (o canvas lê a cada quadro); `t` (estado) atualiza ~15x/s para a interface.
 */
export function useReproducao(segs: SegArq[], atraso: number, usarCam: boolean) {
  const video = useRef<HTMLVideoElement>(null)
  const cam = useRef<HTMLVideoElement>(null)
  const tRef = useRef(0)
  const segAtual = useRef(0)
  const segsRef = useRef(segs)
  const camRef = useRef({ atraso, usarCam })
  const [t, setT] = useState(0)
  const [tocando, setTocando] = useState(false)
  const total = duracaoTotal(segs)

  useEffect(() => {
    segsRef.current = segs
    camRef.current = { atraso, usarCam }
  })

  const publicar = useCallback((v: number) => {
    tRef.current = v
    setT(v)
  }, [])

  const posicionar = useCallback(
    (tl: number) => {
      const v = video.current
      const pos = localizar(segsRef.current, tl)
      if (!v || !pos) return
      segAtual.current = segsRef.current.indexOf(pos.seg)
      v.currentTime = pos.arquivo
      const c = cam.current
      if (c && camRef.current.usarCam) c.currentTime = Math.max(0, pos.arquivo - camRef.current.atraso)
      publicar(tl)
    },
    [publicar],
  )

  const ir = useCallback((tl: number) => posicionar(Math.max(0, Math.min(duracaoTotal(segsRef.current), tl))), [posicionar])

  const pausar = useCallback(() => {
    video.current?.pause()
    cam.current?.pause()
    setTocando(false)
  }, [])

  const tocar = useCallback(() => {
    const v = video.current
    if (!v) return
    if (tRef.current >= duracaoTotal(segsRef.current) - 0.05) posicionar(0)
    void v.play().catch(() => setTocando(false))
    if (camRef.current.usarCam) void cam.current?.play().catch(() => undefined)
    setTocando(true)
  }, [posicionar])

  const alternar = useCallback(() => (tocando ? pausar() : tocar()), [tocando, pausar, tocar])

  // laço de reprodução: troca de trecho no fim de cada um e mantém a webcam junto
  useEffect(() => {
    if (!tocando) return
    let quadro = 0
    let ultimoPublicado = -1
    const passo = () => {
      const v = video.current
      const lista = segsRef.current
      let k = segAtual.current
      let s = lista[k]
      if (v && s) {
        if (v.currentTime >= s.b - 0.03 || v.ended) {
          if (k + 1 < lista.length) {
            k += 1
            segAtual.current = k
            s = lista[k]
            v.currentTime = s.a
          } else {
            pausar()
            publicar(duracaoTotal(lista))
            return
          }
        }
        const tl = s.ini + Math.max(0, Math.min(s.b - s.a, v.currentTime - s.a))
        tRef.current = tl
        if (Math.abs(tl - ultimoPublicado) > 0.066) {
          ultimoPublicado = tl
          setT(tl)
        }
        const c = cam.current
        const { atraso: d, usarCam: usar } = camRef.current
        if (c && usar) {
          const alvo = Math.max(0, v.currentTime - d)
          if (Math.abs(c.currentTime - alvo) > 0.2) c.currentTime = alvo
          if (c.paused) void c.play().catch(() => undefined)
        }
      }
      quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadro)
  }, [tocando, pausar, publicar])

  // a edição mudou com o vídeo parado: reposiciona no mesmo tempo (ou no fim, se encurtou)
  useEffect(() => {
    if (!tocando) posicionar(Math.min(tRef.current, Math.max(0, total - 0.01)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segs, atraso, usarCam])

  return { video, cam, t, tRef, tocando, total, tocar, pausar, alternar, ir }
}

export type Reproducao = ReturnType<typeof useReproducao>
