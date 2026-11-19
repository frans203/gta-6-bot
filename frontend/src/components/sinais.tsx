import { Brain, Sparkles } from 'lucide-react'

import { useAprendizado, useLigarAprendizado } from '@/api/hooks/cortador'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'

/** Nome de cada sinal que os detectores gravam em `corte.sinais` (backend: cortes/detectores.py). */
export const NOMES_SINAIS: Record<string, string> = {
  audio: 'Áudio alto',
  mais_assistidos: 'Mais assistido',
  clipes_twitch: 'Clipes da Twitch',
  fala: 'Fala',
  chat_youtube: 'Chat',
  fala_ritmo: 'Fala acelerada',
  fala_explosao: 'Grito depois de silêncio',
  fala_gatilho: 'Palavras de choque',
  fala_risada: 'Risada',
  chat_mensagens: 'Chat agitado',
  chat_reacoes: 'Risadas no chat',
}

// os específicos explicam melhor ("Risada" diz mais que "Fala")
const ORDEM = ['clipes_twitch', 'chat_reacoes', 'chat_mensagens', 'fala_risada', 'fala_explosao', 'fala_gatilho',
  'fala_ritmo', 'mais_assistidos', 'audio']

/** Por que este trecho foi escolhido: os sinais mais fortes no pico (até 3). */
export function Motivos({ sinais, className }: { sinais?: Record<string, unknown> | null; className?: string }) {
  if (!sinais) return null
  const num = (k: string) => (typeof sinais[k] === 'number' ? (sinais[k] as number) : 0)
  const fortes = ORDEM.filter((k) => num(k) >= 0.5).slice(0, 3)
  const aprendido = num('aprendido')
  if (!fortes.length && !aprendido) return null
  return (
    <div className={cn('flex flex-wrap items-center gap-1', className)}>
      <Sparkles className="size-3 text-muted-foreground" />
      {fortes.map((k) => (
        <Badge key={k} variant="secondary" className="text-[10px]" title={`${Math.round(num(k) * 100)}%`}>
          {NOMES_SINAIS[k]}
        </Badge>
      ))}
      {aprendido > 0 && (
        <Badge variant="outline" className="text-[10px]" title="chance de você aprovar, pelo que já aprovou/descartou">
          <Brain className="size-3" /> {Math.round(aprendido * 100)}%
        </Badge>
      )}
    </div>
  )
}

/** Tela Modelos: o que o cortador aprendeu com os cortes aprovados e descartados. */
export function CardAprendizado() {
  const { data: a } = useAprendizado()
  const ligar = useLigarAprendizado()
  if (!a) return null
  const falta = Math.max(0, a.minimo - a.exemplos, a.minimo_por_tipo - a.aprovados, a.minimo_por_tipo - a.descartados)
  const pesos = Object.entries(a.pesos).filter(([k]) => NOMES_SINAIS[k]).sort((x, y) => y[1] - x[1])
  const topo = Math.max(...pesos.map(([, v]) => Math.abs(v)), 0.001)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <Brain className="size-4" /> Como o cortador escolhe
          </span>
          {a.pronto && (
            <label className="flex items-center gap-2 text-sm font-normal">
              Usar o que aprendeu
              <Switch checked={a.ligado} disabled={ligar.isPending} onCheckedChange={(v) => ligar.mutate(v)} />
            </label>
          )}
        </CardTitle>
        <CardDescription>
          Aprende com o que você aprova e descarta na Biblioteca (sem IA paga). Só contam os descartes feitos na revisão:
          descartar um corte já pronto (webcam, repetido) não ensina nada sobre o momento.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          {a.exemplos} exemplo(s): <b className="text-verde">{a.aprovados} aprovados</b> e{' '}
          <b className="text-rosa">{a.descartados} descartados</b>.
        </p>
        {!a.pronto ? (
          <div className="space-y-1.5">
            <Progress value={(100 * a.exemplos) / Math.max(a.minimo, a.exemplos + falta)} />
            <p className="text-xs text-muted-foreground">
              Começa a usar com {a.minimo} exemplos (pelo menos {a.minimo_por_tipo} aprovados e {a.minimo_por_tipo} descartados).
              Até lá, valem os pesos fixos de cada detector.
            </p>
          </div>
        ) : (
          <div className={cn('space-y-1.5', !a.ligado && 'opacity-50')}>
            {pesos.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[160px_1fr_48px] items-center gap-2 text-xs">
                <span className="truncate">{NOMES_SINAIS[k]}</span>
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className={cn('h-2 rounded-full', v >= 0 ? 'bg-verde' : 'bg-rosa')}
                    style={{ width: `${(100 * Math.abs(v)) / topo}%` }}
                  />
                </div>
                <span className="text-right tabular-nums text-muted-foreground">{v >= 0 ? '+' : ''}{v.toFixed(1)}</span>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              Verde = você costuma aprovar quando esse sinal está forte; vermelho = costuma descartar.
              {!a.ligado && ' Desligado: a análise usa só os pesos fixos.'}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
