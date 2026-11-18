import { Clock, Eye, Hourglass, Loader2, Radar, RefreshCw, Scissors, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { registros, useConfigurarVigia, useVigia, useVigiarAgora, type VigiaConfig } from '@/api/hooks/vigia'
import type { Streamer } from '@/api/tipos'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { fmtRelativo } from '@/lib/formatos'
import { cn } from '@/lib/utils'

function Numero({ rotulo, valor, onChange, min, max, sufixo }: {
  rotulo: string
  valor: number
  onChange: (n: number) => void
  min: number
  max: number
  sufixo?: string
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{rotulo}</Label>
      <div className="flex items-center gap-1.5">
        <Input type="number" min={min} max={max} value={valor} onChange={(e) => onChange(Number(e.target.value))} className="w-24" />
        {sufixo && <span className="text-xs text-muted-foreground">{sufixo}</span>}
      </div>
    </div>
  )
}

const ICONE = { corte: Scissors, ignorado: X, aguardando: Hourglass } as const

/** Vigia de clipes da Twitch: acha clipes novos e cria cortes (com contexto da live) para você revisar. */
export function VigiaClipes({ streamer }: { streamer: Streamer }) {
  const { data, isLoading } = useVigia(streamer.id)
  if (isLoading || !data) return <Skeleton className="h-64" />
  return <FormVigia key={JSON.stringify(data.config)} streamer={streamer} inicial={data.config} dados={data} />
}

function FormVigia({ streamer, inicial, dados }: {
  streamer: Streamer
  inicial: VigiaConfig
  dados: NonNullable<ReturnType<typeof useVigia>['data']>
}) {
  const [cfg, setCfg] = useState<VigiaConfig>(inicial)
  const salvar = useConfigurarVigia(streamer.id)
  const agora = useVigiarAgora(streamer.id)
  const set = (c: Partial<VigiaConfig>) => setCfg((x) => ({ ...x, ...c }))
  const alterado = JSON.stringify(cfg) !== JSON.stringify(inicial)
  const recentes = [...registros(dados.recentes)].reverse()

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Radar className={cn('size-4', inicial.ativo ? 'animate-pulse text-verde' : 'text-muted-foreground')} /> Vigia de clipes
            </CardTitle>
            <CardDescription>
              Olha os clipes que o público faz na Twitch. Quando um passa do mínimo de views, cria um corte com contexto da live e deixa
              pronto para você revisar na Biblioteca. Não renderiza nem posta sozinho.
            </CardDescription>
          </div>
          <Switch checked={cfg.ativo} onCheckedChange={(v) => set({ ativo: v })} />
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Numero rotulo="Olhar a cada" valor={cfg.intervalo_min} onChange={(n) => set({ intervalo_min: n })} min={2} max={120} sufixo="min" />
            <Numero rotulo="Mínimo de views" valor={cfg.min_views} onChange={(n) => set({ min_views: n })} min={0} max={100000} />
            <Numero rotulo="Máximo por dia" valor={cfg.max_por_dia} onChange={(n) => set({ max_por_dia: n })} min={1} max={100} sufixo="cortes" />
            <Numero rotulo="Contexto antes" valor={cfg.antes} onChange={(n) => set({ antes: n })} min={0} max={300} sufixo="s" />
            <Numero rotulo="Contexto depois" valor={cfg.depois} onChange={(n) => set({ depois: n })} min={0} max={300} sufixo="s" />
            <Numero rotulo="Clipe entre" valor={cfg.dur_min} onChange={(n) => set({ dur_min: n })} min={1} max={60} sufixo={`e ${cfg.dur_max} s`} />
          </div>
          <div className="flex items-center justify-between text-xs">
            <Label htmlFor="auto-preparar" className="text-xs">
              Já baixar o trecho e achar a webcam (sem renderizar)
            </Label>
            <Switch id="auto-preparar" checked={cfg.auto_preparar} onCheckedChange={(v) => set({ auto_preparar: v })} />
          </div>
          <p className="text-[11px] text-muted-foreground">
            O contexto “depois” só existe quando a live chega lá: enquanto o streamer ainda está transmitindo, o corte espera o VOD
            gravar esses segundos. Sem VOD (arquivo da live desligado), o corte usa o próprio clipe.
          </p>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4">
            <div className="text-xs text-muted-foreground">
              {inicial.ativo ? (
                <>
                  <Clock className="mr-1 inline size-3.5" />
                  {dados.ultima ? `última olhada ${fmtRelativo(dados.ultima)}` : 'ainda não olhou'} · {dados.hoje} corte(s) hoje
                </>
              ) : (
                'desligado'
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={agora.isPending} onClick={() => agora.mutate()}>
                {agora.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />} Olhar agora
              </Button>
              <Button size="sm" disabled={!alterado || salvar.isPending} onClick={() => salvar.mutate(cfg)}>
                Salvar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Clipes vistos</CardTitle>
          <CardDescription>Os mais recentes primeiro. Os que estão esperando a live andar aparecem em cima.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {!dados.aguardando.length && !recentes.length && <p className="text-sm text-muted-foreground">Nenhum clipe ainda.</p>}
          {[...registros(dados.aguardando), ...recentes].slice(0, 25).map((x, i) => {
            const Icone = ICONE[x.situacao as keyof typeof ICONE] ?? Eye
            return (
              <div key={`${x.id}-${i}`} className="flex items-start gap-3 rounded-lg border bg-white/[0.02] p-2.5 text-sm">
                <Icone
                  className={cn(
                    'mt-0.5 size-4 shrink-0',
                    x.situacao === 'corte' ? 'text-verde' : x.situacao === 'aguardando' ? 'text-amarelo' : 'text-muted-foreground',
                  )}
                />
                <div className="min-w-0 flex-1">
                  <a href={x.url} target="_blank" rel="noreferrer" className="block truncate font-medium hover:text-rosa">
                    {x.titulo || 'clipe sem título'}
                  </a>
                  <p className="text-xs text-muted-foreground">
                    {x.views} views · {x.motivo}
                  </p>
                </div>
                {x.corte_id && (
                  <Button size="xs" variant="ghost" asChild>
                    <Link to={`/biblioteca?corte=${x.corte_id}`}>abrir</Link>
                  </Button>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}
