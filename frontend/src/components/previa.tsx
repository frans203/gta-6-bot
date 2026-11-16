import { Loader2 } from 'lucide-react'

import { useModelos, usePrevia } from '@/api/hooks/cortador'
import type { PreviaIn } from '@/api/tipos'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

/** Prévia 9:16 de um quadro, renderizada pelo backend (mesmo ffmpeg e mesma legenda do corte final). */
export function Previa({ pedido, className }: { pedido: PreviaIn | null; className?: string }) {
  const { url, carregando, erro } = usePrevia(pedido)
  return (
    <div className={cn('relative mx-auto aspect-[9/16] w-full max-w-[300px] overflow-hidden rounded-xl border bg-black', className)}>
      {url && <img src={url} alt="Prévia do corte" className="size-full object-contain" />}
      {carregando && (
        <div className="absolute top-2 right-2 rounded-full bg-black/70 p-1.5">
          <Loader2 className="size-4 animate-spin text-white" />
        </div>
      )}
      {erro && !url && <p className="absolute inset-0 flex items-center p-4 text-center text-xs text-destructive">{erro.message}</p>}
    </div>
  )
}

const PADRAO = '__padrao__'

/** Escolha de um modelo de corte. Com `rotuloPadrao`, oferece "usar o padrão" (valor null). */
export function SelectModelo({
  valor,
  onChange,
  rotuloPadrao,
  id,
}: {
  valor: number | null | undefined
  onChange: (v: number | null) => void
  rotuloPadrao?: string
  id?: string
}) {
  const { data: modelos = [] } = useModelos()
  return (
    <Select value={valor ? String(valor) : PADRAO} onValueChange={(v) => onChange(v === PADRAO ? null : Number(v))}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue placeholder="Escolha..." />
      </SelectTrigger>
      <SelectContent>
        {rotuloPadrao && <SelectItem value={PADRAO}>{rotuloPadrao}</SelectItem>}
        {modelos.map((m) => (
          <SelectItem key={m.id} value={String(m.id)}>
            {m.nome}
            {m.padrao ? ' (padrão)' : ''}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
