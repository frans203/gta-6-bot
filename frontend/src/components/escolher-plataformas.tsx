import { PLATAFORMAS, type Plataforma as P } from '@/api/tipos'
import { Plataforma } from '@/components/plataforma'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

/** Caixinhas de tiktok/youtube/instagram. `disponiveis` limita às plataformas da conta. */
export function EscolherPlataformas({
  valor,
  onChange,
  disponiveis = PLATAFORMAS,
}: {
  valor: string[]
  onChange: (v: P[]) => void
  disponiveis?: string[]
}) {
  return (
    <div className="flex flex-wrap gap-4">
      {PLATAFORMAS.filter((p) => disponiveis.includes(p)).map((p) => (
        <Label key={p} className="flex cursor-pointer items-center gap-2 font-normal">
          <Checkbox
            checked={valor.includes(p)}
            onCheckedChange={(c) =>
              onChange(PLATAFORMAS.filter((x) => (x === p ? c === true : valor.includes(x))))
            }
          />
          <Plataforma p={p} />
        </Label>
      ))}
    </div>
  )
}
