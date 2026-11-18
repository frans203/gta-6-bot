import { ArrowRight, Check, Library, Link2, Loader2, Scissors } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { useCortarVideo, useCortes, useFonte, useIdentificar, useModelos, useStreamers } from '@/api/hooks/cortador'
import { useJob, useJobs } from '@/api/hooks/jobs'
import type { Identificado, Job } from '@/api/tipos'
import { nomeIdioma } from '@/components/ajustes-fonte'
import { Cabecalho } from '@/components/cabecalho'
import { BarraJob, JobProgresso } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { SelectModelo } from '@/components/previa'
import { StatusChip } from '@/components/status-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { fmtDuracao } from '@/lib/formatos'
import { cn } from '@/lib/utils'

const QTDS = [1, 3, 5, 8, 10]

function Passo({ n, titulo, feito, children, descricao }: {
  n: number
  titulo: string
  feito?: boolean
  descricao?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span
            className={cn(
              'flex size-6 items-center justify-center rounded-full text-xs font-bold',
              feito ? 'bg-verde text-black' : 'bg-primary text-primary-foreground',
            )}
          >
            {feito ? <Check className="size-3.5" /> : n}
          </span>
          {titulo}
        </CardTitle>
        {descricao && <CardDescription>{descricao}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

// ------------------------------------------------------------------ 1 e 2: link + quantidade

function ResumoLink({ i }: { i: Identificado }) {
  return (
    <div className="flex gap-3 rounded-lg border p-3">
      {i.miniatura && <img src={i.miniatura} alt="" className="aspect-video w-36 shrink-0 rounded object-cover" />}
      <div className="min-w-0 space-y-1 text-sm">
        <p className="line-clamp-2 font-medium">{i.titulo || i.url}</p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <Plataforma p={i.plataforma} />
          {i.plataforma === 'outro' && <span>({i.site})</span>}
          <span>{i.canal_nome}</span>
          <Badge variant="secondary">{i.tipo === 'clipe' ? 'clipe' : 'vídeo / VOD'}</Badge>
          {i.duracao != null && <span className="tabular-nums">{fmtDuracao(i.duracao)}</span>}
          {i.idioma && <span>idioma: {nomeIdioma(i.idioma)}</span>}
        </div>
        <p className="text-xs">
          {i.streamer_id ? (
            <span className="text-verde">
              {i.fonte_id ? 'Vídeo já cadastrado' : 'Streamer já cadastrado'}: <b>{i.streamer_nome}</b>.
            </span>
          ) : (
            <span className="text-ciano">Streamer novo: vou cadastrar “{i.canal_nome}” automaticamente.</span>
          )}
        </p>
      </div>
    </div>
  )
}

/** Jobs de "cortar vídeo" em andamento e os últimos feitos: dá para sair da página e voltar. */
function EmAndamento({ onAbrir }: { onAbrir: (fonte: number, job: number) => void }) {
  const { data: jobs = [] } = useJobs({ tipo: 'cortar_video', limite: 6 })
  if (!jobs.length) return null
  const ativos = jobs.filter((j) => ['fila', 'rodando', 'cancelando'].includes(j.status))
  const recentes = jobs.filter((j) => !ativos.includes(j)).slice(0, 4)
  const abrir = (j: Job) => onAbrir(j.params.fonte_id as number, j.id)
  return (
    <Card>
      <CardHeader>
        <CardTitle>{ativos.length ? 'Cortes em andamento' : 'Vídeos recentes'}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {ativos.map((j) => (
          <div key={j.id} className="space-y-2 rounded-lg border p-3">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium">{j.titulo.replace(/^Cortar · /, '')}</span>
              <Button size="sm" onClick={() => abrir(j)}>
                Abrir
              </Button>
            </div>
            <BarraJob job={j} />
            <p className="text-xs text-muted-foreground">{j.mensagem}</p>
          </div>
        ))}
        {recentes.map((j) => (
          <button
            key={j.id}
            type="button"
            onClick={() => abrir(j)}
            className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/50"
          >
            <span className="min-w-0 truncate">{j.titulo.replace(/^Cortar · /, '')}</span>
            <StatusChip status={j.status} />
          </button>
        ))}
      </CardContent>
    </Card>
  )
}

function PassosIniciais({ onComecar }: { onComecar: (fonte: number, job: number) => void }) {
  const [url, setUrl] = useState('')
  const [qtd, setQtd] = useState(3)
  const [duracao, setDuracao] = useState(45)
  const [modelo, setModelo] = useState<number | null>(null)
  const identificar = useIdentificar()
  const cortar = useCortarVideo()
  const { data: streamers = [] } = useStreamers()
  const i = identificar.data
  const { data: modelos = [] } = useModelos()
  const modeloStreamer = streamers.find((s) => s.id === i?.streamer_id)?.modelo_id ?? null
  const nomeModeloPadrao = (modelos.find((m) => m.id === modeloStreamer) ?? modelos.find((m) => m.padrao))?.nome
  const curto = i?.duracao != null && i.duracao <= duracao * 1.3

  return (
    <div className="space-y-4">
      <EmAndamento onAbrir={onComecar} />
      <Passo n={1} titulo="Link do vídeo" feito={!!i} descricao="Twitch, YouTube, Kick ou outro site: VOD, vídeo ou clipe.">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (url.trim()) identificar.mutate(url.trim())
          }}
        >
          <Input
            className="min-w-64 flex-1"
            placeholder="https://www.twitch.tv/videos/... ou https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => {
              setUrl(e.target.value)
              identificar.reset()
            }}
          />
          <Button type="submit" disabled={!url.trim() || identificar.isPending}>
            {identificar.isPending ? <Loader2 className="animate-spin" /> : <Link2 />} Ler link
          </Button>
        </form>
        {i && (
          <div className="mt-3 space-y-2">
            <ResumoLink i={i} />
            {i.fonte_id && (
              <p className="text-xs text-amarelo">
                Este vídeo já foi cortado antes.{' '}
                <Link className="underline" to={`/biblioteca?fonte=${i.fonte_id}`}>
                  Ver os cortes dele
                </Link>{' '}
                ou continue para gerar de novo (os já revisados ficam).
              </p>
            )}
          </div>
        )}
      </Passo>

      {i && (
        <Passo n={2} titulo="Quantos cortes?">
          <div className="space-y-5">
            {curto ? (
              <p className="text-sm text-muted-foreground">O vídeo é curto ({fmtDuracao(i.duracao)}): ele vira 1 corte inteiro.</p>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  {QTDS.map((n) => (
                    <Button key={n} type="button" size="sm" variant={qtd === n ? 'default' : 'outline'} onClick={() => setQtd(n)}>
                      {n}
                    </Button>
                  ))}
                  <span className="ml-2 text-sm text-muted-foreground tabular-nums">{qtd} corte(s)</span>
                </div>
                <Slider min={1} max={20} step={1} value={[qtd]} onValueChange={([v]) => setQtd(v)} className="max-w-sm" />
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Duração de cada corte</Label>
                <Select value={String(duracao)} onValueChange={(v) => setDuracao(Number(v))}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[30, 45, 60, 90].map((s) => (
                      <SelectItem key={s} value={String(s)}>
                        {s} segundos
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Modelo de corte</Label>
                <SelectModelo
                  valor={modelo}
                  rotuloPadrao={`${i.streamer_id ? 'Do streamer' : 'Padrão'}: ${nomeModeloPadrao ?? '...'}`}
                  onChange={setModelo}
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                disabled={cortar.isPending}
                onClick={() =>
                  cortar.mutate(
                    { url: i.url, quantidade: curto ? 1 : qtd, duracao, modelo_id: modelo },
                    { onSuccess: (r) => onComecar(r.fonte_id, r.job.id) },
                  )
                }
              >
                <Scissors /> Fazer os cortes
              </Button>
            </div>
          </div>
        </Passo>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ 3: análise -> Biblioteca

/** Acompanha o job "cortar vídeo". Quando termina, abre o vídeo na Biblioteca (onde se revisa e renderiza). */
function Analise({ fonteId, jobId }: { fonteId: number; jobId: number | null }) {
  const navegar = useNavigate()
  const { data: job } = useJob(jobId)
  const { data: fonte } = useFonte(fonteId)
  const { data: cortes = [] } = useCortes({ fonte_id: fonteId })
  const analisando = !!job && ['fila', 'rodando', 'cancelando'].includes(job.status)
  const ativos = cortes.filter((c) => c.status !== 'descartado')
  const pendentes = ativos.filter((c) => c.status === 'enquadrar').length
  const abrir = () => void navegar(`/biblioteca?fonte=${fonteId}`)
  // terminou com esta página aberta: segue direto para a revisão
  const [terminouAqui, setTerminouAqui] = useState(false)
  const [estavaRodando, setEstavaRodando] = useState(false)
  if (analisando && !estavaRodando) setEstavaRodando(true)
  if (estavaRodando && job?.status === 'ok' && !terminouAqui) setTerminouAqui(true)
  useEffect(() => {
    if (terminouAqui) void navegar(`/biblioteca?fonte=${fonteId}`, { replace: true })
  }, [terminouAqui, fonteId, navegar])

  return (
    <div className="space-y-4">
      {fonte && (
        <p className="text-sm text-muted-foreground">
          <b className="text-foreground">{fonte.titulo}</b> · {fmtDuracao(fonte.duracao)}
        </p>
      )}
      {job && (analisando || job.status === 'erro') && (
        <Passo n={3} titulo="Fazendo os cortes" descricao="Acha os melhores trechos e prepara cada um: streamer, barras pretas e idioma.">
          <JobProgresso job={job} />
        </Passo>
      )}
      {!analisando && ativos.length > 0 && (
        <Passo n={3} titulo={`${ativos.length} corte(s) encontrados`} feito>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {pendentes
                ? `${pendentes} precisam que você marque a câmera do streamer. O resto já pode ser renderizado.`
                : 'Tudo enquadrado: revise, escolha legenda e fundo e renderize.'}
            </p>
            <Button onClick={abrir}>
              <Library /> Revisar na Biblioteca <ArrowRight />
            </Button>
          </div>
        </Passo>
      )}
    </div>
  )
}

export function PaginaCortarVideo() {
  const [params, setParams] = useSearchParams()
  const fonte = params.get('fonte') ? Number(params.get('fonte')) : null
  const job = params.get('job') ? Number(params.get('job')) : null

  return (
    <>
      <Cabecalho
        titulo="Cortar vídeo"
        descricao="Cole o link e diga quantos cortes quer. Quando terminar, o vídeo aparece na Biblioteca para revisar e renderizar."
      >
        {fonte && (
          <Button variant="outline" onClick={() => setParams({})}>
            <Link2 /> Outro vídeo
          </Button>
        )}
      </Cabecalho>
      {fonte ? (
        <Analise fonteId={fonte} jobId={job} />
      ) : (
        <PassosIniciais onComecar={(f, j) => setParams({ fonte: String(f), job: String(j) })} />
      )}
    </>
  )
}
