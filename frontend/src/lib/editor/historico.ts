import { useCallback, useRef, useState } from 'react'

/**
 * Estado com desfazer/refazer. `definir(v, grupo)`: mudanças seguidas do mesmo grupo (ex.: arrastar um slider)
 * em menos de 700 ms viram um passo só.
 */
export function useHistorico<T>(inicial: T) {
  const [estado, setEstado] = useState({ passado: [] as T[], atual: inicial, futuro: [] as T[] })
  const ultimo = useRef<{ grupo?: string; em: number }>({ em: 0 })

  const definir = useCallback((v: T | ((x: T) => T), grupo?: string) => {
    setEstado((s) => {
      const novo = typeof v === 'function' ? (v as (x: T) => T)(s.atual) : v
      if (novo === s.atual) return s
      const agora = Date.now()
      const junta = grupo != null && ultimo.current.grupo === grupo && agora - ultimo.current.em < 700
      ultimo.current = { grupo, em: agora }
      return { passado: junta ? s.passado : [...s.passado.slice(-99), s.atual], atual: novo, futuro: [] }
    })
  }, [])

  const desfazer = useCallback(() => {
    ultimo.current = { em: 0 }
    setEstado((s) => (s.passado.length ? { passado: s.passado.slice(0, -1), atual: s.passado[s.passado.length - 1], futuro: [s.atual, ...s.futuro] } : s))
  }, [])

  const refazer = useCallback(() => {
    ultimo.current = { em: 0 }
    setEstado((s) => (s.futuro.length ? { passado: [...s.passado, s.atual], atual: s.futuro[0], futuro: s.futuro.slice(1) } : s))
  }, [])

  /** troca o valor sem histórico (ex.: carregar do servidor) */
  const reiniciar = useCallback((v: T) => setEstado({ passado: [], atual: v, futuro: [] }), [])

  return {
    valor: estado.atual,
    definir,
    desfazer,
    refazer,
    reiniciar,
    podeDesfazer: estado.passado.length > 0,
    podeRefazer: estado.futuro.length > 0,
  }
}
