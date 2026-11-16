import { useEffect, useState } from 'react'

/** O valor, mas só depois de `ms` sem mudar (para não chamar a API a cada movimento de slider). */
export function useAtrasado<T>(valor: T, ms = 300): T {
  const [atual, setAtual] = useState(valor)
  useEffect(() => {
    const t = setTimeout(() => setAtual(valor), ms)
    return () => clearTimeout(t)
  }, [valor, ms])
  return atual
}
