import { Clapperboard, Minus, Plus, RotateCcw, Send, Trash2, Wand2, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { urls } from '@/api/cliente'
import { useCortes, useEditarCorte, useModelos, usePlugins, usePublicarCorte, useRenderizar, useStreamers } from '@/api/hooks/cortador'
import { useJobs } from '@/api/hooks/jobs'
import type { Corte, CortePatch, Job } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { SelectPlugin } from '@/components/form-streamer'
import { Enquadramento } from '@/components/enquadramento'
import { BarraJob } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { Player9x16, PlayerFonte } from '@/components/players'
import { SelectModelo } from '@/components/previa'
import { StatusChip } from '@/components/status-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useConta } from '@/lib/conta'
import { modeloEfetivo, podeRenderizar } from '@/lib/enquadramento'
import { fmtTempo, lerTempo } from '@/lib/formatos'

const ABAS = {
  revisar: { rotulo: 'Para revisar', status: ['enquadrar', 'candidato', 'aprovado', 'renderizando', 'erro'] },
  prontos: { rotulo: 'Prontos', status: ['pronto'] },
  fila: { rotulo: 'Na fila de postagem', status: ['na_fila'] },
  descartados: { rotulo: 'Descartados', status: ['descartado'] },
} as const
type Aba = keyof typeof ABAS

const COR_SINAL: Record<string, string> = {
  audio: 'bg-rosa',
  mais_assistidos: 'bg-ciano',
  clipes_twitch: 'bg-roxo',
  views: 'bg-laranja',
}

/** Barrinhas com a força de cada detector no pico do corte. */
function Sinais({ corte }: { corte: Corte }) {
  const sinais = Object.entries(corte.sinais).filter(([k, v]) => k !== 'pico' && typeof v === 'number' && k !== 'views')
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Score</span>
        <span className="font-semibold text-amarelo tabular-nums">{corte.score.toFixed(2)}</span>
      </div>
      {sinais.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-[11px]">
          <span className="w-28 truncate text-muted-foreground">{k.replaceAll('_', ' ')}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div className={`h-full ${COR_SINAL[k] ?? 'bg-verde'}`} style={{ width: `${Math.min(1, v as number) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Campo de tempo (m:ss) com botões de ±5 s. */
function CampoTempo({ id, rotulo, valor, onChange }: { id: string; rotulo: string; valor: number; onChange: (s: number) => void }) {
  const [texto, setTexto] = useState(fmtTempo(valor))
  const [ultimo, setUltimo] = useState(valor)
  if (ultimo !== valor) {
    setUltimo(valor)
    setTexto(fmtTempo(valor))
  }
  const passo = (d: number) => onChange(Math.max(0, valor + d))
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{rotulo}</Label>
      <div className="flex items-center gap-1">
        <Button type="button" size="icon-sm" variant="outline" onClick={() => passo(-5)} title="-5 s">
          <Minus />
        </Button>
        <Input
          id={id}
          className="w-24 text-center tabular-nums"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onBlur={() => {
            const s = lerTempo(texto)
            if (s == null) setTexto(fmtTempo(valor))
            else onChange(s)
          }}
        />
        <Button type="button" size="icon-sm" variant="outline" onClick={() => passo(5)} title="+5 s">
          <Plus />
        </Button>
      </div>
    </div>
  )
}

function MandarParaFila({ corte }: { corte: Corte }) {
  const { contas } = useConta()
  const [conta, setConta] = useState(corte.conta_id ?? contas.find((c) => c.padrao)?.id ?? '')
  const publicar = usePublicarCorte()
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="min-w-40 flex-1 space-y-1.5">
        <Label>Conta</Label>
        <Select value={conta} onValueChange={setConta}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Escolha a conta" />
          </SelectTrigger>
          <SelectContent>
            {contas.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button disabled={!conta || publicar.isPending} onClick={() => publicar.mutate({ id: corte.id, conta })}>
        <Send /> Mandar para a fila
      </Button>
    </div>
  )
}

function CartaoCorte({ corte, jobs }: { corte: Corte; jobs: Job[] }) {
  const [rascunho, setRascunho] = useState<CortePatch>({})
  const editar = useEditarCorte()
  const renderizar = useRenderizar()
  const { data: modelos = [] } = useModelos()
  const { data: plugins } = usePlugins()
  const v = { ...corte, ...rascunho } as Corte
  const set = (campos: CortePatch) => setRascunho((r) => ({ ...r, ...campos }))
  const alterado = Object.keys(rascunho).length > 0
  const ocupado = ['aprovado', 'renderizando'].includes(corte.status)
  // o crop e os ajustes podem mudar a qualquer momento, menos enquanto o vídeo está sendo gerado
  const editavel = !ocupado
  const job = jobs.find((j) => j.tipo === 'renderizar_corte')
  const jobEnquadrar = jobs.find((j) => j.tipo === 'enquadrar_corte')
  const modelo = modeloEfetivo(modelos, v.modelo_id, corte)
  const precisaWebcam = !!plugins?.layouts.find((l) => l.id === modelo?.layout)?.opcoes.precisa_webcam
  const liberado = podeRenderizar(corte, precisaWebcam, rascunho)
  const rascunhoEnq = {
    ...('webcam' in rascunho && { webcam: rascunho.webcam }),
    ...('jogo' in rascunho && { jogo: rascunho.jogo }),
  }

  const salvar = (depois?: () => void) => {
    if (!alterado) return depois?.()
    editar.mutate({ id: corte.id, body: rascunho }, { onSuccess: () => (setRascunho({}), depois?.()) })
  }

  return (
    <Card>
      <CardContent className="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          {corte.status === 'pronto' || corte.status === 'na_fila' ? (
            <Player9x16 src={urls.corte(corte.id, corte.atualizado_em)} />
          ) : (
            <PlayerFonte url={corte.fonte_url} inicio={v.inicio} fim={v.fim} />
          )}
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Plataforma p={corte.plataforma} soIcone />
            <Link to={`/cortador/streamers/${corte.streamer_id}`} className="font-medium text-foreground hover:underline">
              {corte.streamer_nome}
            </Link>
            <span className="min-w-0 flex-1 truncate" title={corte.fonte_titulo}>
              · {corte.fonte_titulo}
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">#{corte.id}</span>
              <StatusChip status={corte.status} />
              <Badge variant="secondary" className="tabular-nums">
                {fmtTempo(v.fim - v.inicio)}
              </Badge>
            </div>
            {editavel && corte.status !== 'descartado' && corte.status !== 'na_fila' && (
              <Button size="sm" variant="ghost" onClick={() => editar.mutate({ id: corte.id, body: { status: 'descartado' } })}>
                <Trash2 /> Descartar
              </Button>
            )}
            {corte.status === 'descartado' && (
              <Button size="sm" variant="ghost" onClick={() => editar.mutate({ id: corte.id, body: { status: 'candidato' } })}>
                <RotateCcw /> Restaurar
              </Button>
            )}
          </div>

          {ocupado && job && (
            <div className="space-y-1">
              <BarraJob job={job} />
              <p className="text-xs text-muted-foreground">{job.mensagem}</p>
            </div>
          )}
          {corte.status === 'erro' && corte.erro && (
            <p className="line-clamp-4 rounded-md bg-destructive/10 p-2 text-xs text-destructive">{corte.erro}</p>
          )}

          <div className="flex flex-wrap gap-4">
            <CampoTempo id={`ini-${corte.id}`} rotulo="Início" valor={v.inicio} onChange={(s) => set({ inicio: s })} />
            <CampoTempo id={`fim-${corte.id}`} rotulo="Fim" valor={v.fim} onChange={(s) => set({ fim: s })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={`tit-${corte.id}`}>Título (legenda do post)</Label>
            <Input id={`tit-${corte.id}`} value={v.titulo} maxLength={300} onChange={(e) => set({ titulo: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={`gan-${corte.id}`}>Gancho (texto no topo nos primeiros segundos)</Label>
            <Input
              id={`gan-${corte.id}`}
              value={v.gancho ?? ''}
              maxLength={120}
              placeholder="ex.: ELE NÃO ESPERAVA ISSO 😳"
              onChange={(e) => set({ gancho: e.target.value || null })}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Modelo de corte</Label>
              <SelectModelo valor={v.modelo_id} rotuloPadrao="Do streamer" onChange={(x) => set({ modelo_id: x })} />
            </div>
            <div className="space-y-1.5">
              <Label>Legenda</Label>
              <SelectPlugin tipo="estilos" valor={v.estilo_legenda} rotuloPadrao="Do modelo" onChange={(x) => set({ estilo_legenda: x })} />
            </div>
          </div>
          <Sinais corte={corte} />

          <div className="flex flex-wrap justify-end gap-2 border-t pt-3">
            {alterado && (
              <>
                <Button variant="ghost" onClick={() => setRascunho({})}>
                  <X /> Desfazer
                </Button>
                <Button variant="outline" disabled={editar.isPending} onClick={() => salvar()}>
                  Salvar
                </Button>
              </>
            )}
            {editavel && corte.status !== 'descartado' && (
              <Button
                variant={['pronto', 'na_fila'].includes(corte.status) ? 'outline' : 'default'}
                disabled={renderizar.isPending || editar.isPending || !liberado}
                title={liberado ? undefined : 'Marque a posição do streamer no enquadramento primeiro'}
                onClick={() => salvar(() => renderizar.mutate(corte.id))}
              >
                <Wand2 /> {['pronto', 'na_fila'].includes(corte.status) ? 'Renderizar de novo' : 'Renderizar'}
              </Button>
            )}
          </div>
          {corte.status === 'pronto' && <MandarParaFila corte={corte} />}
          {corte.status === 'na_fila' && (
            <p className="text-xs text-muted-foreground">
              Já está na fila de postagem. Mudou o crop? Renderize de novo e mande para a fila outra vez (troca o vídeo, se ainda não
              foi postado).
            </p>
          )}
        </div>

        {corte.status !== 'descartado' && (
          <div className="space-y-2 border-t pt-4 lg:col-span-2">
            <h3 className="text-sm font-semibold">Enquadramento</h3>
            <Enquadramento
              corte={corte}
              modeloId={v.modelo_id}
              estilo={v.estilo_legenda}
              gancho={v.gancho}
              rascunho={rascunhoEnq}
              onChange={(r) => set(r)}
              job={jobEnquadrar}
              editavel={editavel}
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function PaginaCortes() {
  const [params, setParams] = useSearchParams()
  const aba = (params.get('aba') as Aba) in ABAS ? (params.get('aba') as Aba) : 'revisar'
  const fonteId = params.get('fonte') ? Number(params.get('fonte')) : undefined
  const streamerId = params.get('streamer') ? Number(params.get('streamer')) : undefined
  const { data: streamers = [] } = useStreamers()
  const { data: cortes = [], isLoading } = useCortes({ status: [...ABAS[aba].status], fonte_id: fonteId, streamer_id: streamerId })
  const { data: jobs = [] } = useJobs({ status: 'fila,rodando', tipo: 'renderizar_corte,enquadrar_corte' })
  const jobsDe = (id: number) => jobs.filter((j) => j.params.corte_id === id)
  // os que esperam você marcar o streamer vêm primeiro
  const lista =
    aba === 'revisar'
      ? [...cortes].sort((a, b) => Number(b.status === 'enquadrar') - Number(a.status === 'enquadrar') || b.score - a.score)
      : cortes

  const mudar = (chave: string, valor?: string) => {
    const p = new URLSearchParams(params)
    if (valor) p.set(chave, valor)
    else p.delete(chave)
    setParams(p, { replace: true })
  }

  return (
    <>
      <Cabecalho
        titulo="Revisar cortes"
        descricao="Confira o trecho, ajuste início/fim, título e gancho, confira o enquadramento (onde está o streamer) e renderize. Prontos podem ir para a fila de uma conta."
      >
        <Select value={streamerId ? String(streamerId) : 'todos'} onValueChange={(x) => mudar('streamer', x === 'todos' ? undefined : x)}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os streamers</SelectItem>
            {streamers.map((s) => (
              <SelectItem key={s.id} value={String(s.id)}>
                {s.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {fonteId && (
          <Button variant="outline" onClick={() => mudar('fonte')}>
            <X /> Fonte #{fonteId}
          </Button>
        )}
      </Cabecalho>

      <Tabs value={aba} onValueChange={(x) => mudar('aba', x === 'revisar' ? undefined : x)}>
        <TabsList className="mb-4 flex-wrap">
          {Object.entries(ABAS).map(([k, a]) => (
            <TabsTrigger key={k} value={k}>
              {a.rotulo}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <Skeleton className="h-96" />
      ) : !lista.length ? (
        <Vazio icone={<Clapperboard />} titulo="Nenhum corte aqui">
          Analise um VOD ou clipe na página do streamer para gerar candidatos.
        </Vazio>
      ) : (
        <div className="space-y-4">
          {lista.map((c) => (
            <CartaoCorte key={`${c.id}-${c.atualizado_em}`} corte={c} jobs={jobsDe(c.id)} />
          ))}
        </div>
      )}
    </>
  )
}
