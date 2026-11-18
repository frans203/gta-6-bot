import { ArrowLeft, Clapperboard, Film, Link2, ScanFace, Search, Trash2, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { urls } from '@/api/cliente'
import {
  useAdicionarFonte,
  useAnalisar,
  useAtualizarStreamer,
  useBuscarFontes,
  useDetectarWebcam,
  useFontes,
  useRemoverStreamer,
  useStreamer,
} from '@/api/hooks/cortador'
import { useJobs } from '@/api/hooks/jobs'
import type { Fonte, Streamer } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { Confirmar } from '@/components/confirmar'
import { type DadosStreamer, FormStreamer } from '@/components/form-streamer'
import { JobProgresso } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { StatusChip } from '@/components/status-chip'
import { WebcamEditor } from '@/components/webcam-editor'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { fmtDuracao, fmtNumero } from '@/lib/formatos'

function NumeroCampo({ id, rotulo, valor, onChange, min, max, dica }: {
  id: string
  rotulo: string
  valor: number
  onChange: (n: number) => void
  min: number
  max: number
  dica?: string
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{rotulo}</Label>
      <Input id={id} type="number" min={min} max={max} value={valor} onChange={(e) => onChange(Number(e.target.value))} />
      {dica && <p className="text-xs text-muted-foreground">{dica}</p>}
    </div>
  )
}

function DialogoBuscar({ streamer, tipo }: { streamer: Streamer; tipo: 'vod' | 'clipe' }) {
  const [aberto, setAberto] = useState(false)
  const [limite, setLimite] = useState(tipo === 'vod' ? 5 : 20)
  const [dias, setDias] = useState(7)
  const buscar = useBuscarFontes(streamer.id)
  const nome = tipo === 'vod' ? 'VODs' : 'clipes'
  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <Button variant={tipo === 'vod' ? 'default' : 'outline'}>
          {tipo === 'vod' ? <Search /> : <Film />} Buscar {nome}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Buscar {nome} de {streamer.nome}</DialogTitle>
          <DialogDescription>
            {tipo === 'vod'
              ? 'Lista as lives gravadas mais recentes do canal (nada é baixado ainda).'
              : 'Clipes mais vistos do período: cada clipe vira um corte candidato (curadoria dos próprios espectadores).'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <NumeroCampo id="limite" rotulo="Quantos" valor={limite} onChange={setLimite} min={1} max={50} />
          {tipo === 'clipe' && <NumeroCampo id="dias" rotulo="Dos últimos N dias" valor={dias} onChange={setDias} min={1} max={365} />}
        </div>
        <DialogFooter>
          <Button
            disabled={buscar.isPending}
            onClick={() => buscar.mutate({ tipo, limite, periodo_dias: dias }, { onSuccess: () => setAberto(false) })}
          >
            Buscar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DialogoAnalisar({ fonte }: { fonte: Fonte }) {
  const [aberto, setAberto] = useState(false)
  const [max, setMax] = useState(8)
  const [duracao, setDuracao] = useState(45)
  const analisar = useAnalisar()
  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <Button size="sm" variant={fonte.status === 'analisada' ? 'outline' : 'default'} disabled={fonte.status === 'analisando'}>
          <Wand2 /> {fonte.status === 'analisada' ? 'Reanalisar' : 'Analisar'}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Achar os melhores trechos</DialogTitle>
          <DialogDescription className="line-clamp-2">{fonte.titulo}</DialogDescription>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          {fonte.tipo === 'clipe'
            ? 'Clipe: vira um corte candidato inteiro (dá para aparar na revisão).'
            : 'Baixa só o áudio (qualidade mínima) e procura picos: gritos, risadas, partes mais repetidas, clipes. Candidatos ainda não revisados desta fonte são substituídos.'}
        </p>
        {fonte.tipo === 'vod' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <NumeroCampo id="max" rotulo="Máximo de cortes" valor={max} onChange={setMax} min={1} max={40} />
            <NumeroCampo id="dur" rotulo="Duração alvo (s)" valor={duracao} onChange={setDuracao} min={15} max={180} dica="> 60 s conta no TikTok Rewards" />
          </div>
        )}
        <DialogFooter>
          <Button
            disabled={analisar.isPending}
            onClick={() =>
              analisar.mutate({ id: fonte.id, body: { max_cortes: max, duracao } }, { onSuccess: () => setAberto(false) })
            }
          >
            Analisar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CartaoFonte({ fonte }: { fonte: Fonte }) {
  return (
    <Card size="sm" className="flex-row gap-3 px-3">
      {fonte.miniatura ? (
        <img src={fonte.miniatura} alt="" className="aspect-video w-36 shrink-0 rounded-md object-cover" loading="lazy" />
      ) : (
        <div className="flex aspect-video w-36 shrink-0 items-center justify-center rounded-md bg-muted">
          <Film className="size-6 text-muted-foreground" />
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <a href={fonte.url} target="_blank" rel="noreferrer" className="line-clamp-2 text-sm font-medium hover:underline">
          {fonte.titulo || fonte.url}
        </a>
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <Badge variant="secondary">{fonte.tipo}</Badge>
          <span>{fmtDuracao(fonte.duracao)}</span>
          <span>· {fmtNumero(fonte.views)} views</span>
          {fonte.publicado_em && <span>· {fonte.publicado_em.slice(0, 10)}</span>}
          <StatusChip status={fonte.status} />
        </div>
        <div className="mt-auto flex flex-wrap gap-2">
          <DialogoAnalisar fonte={fonte} />
          {fonte.total_cortes > 0 && (
            <Button size="sm" variant="ghost" asChild>
              <Link to={`/biblioteca?fonte=${fonte.id}`}>
                <Clapperboard /> {fonte.total_cortes} corte(s)
              </Link>
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

function AbaFontes({ streamer }: { streamer: Streamer }) {
  const { data: fontes = [], isLoading } = useFontes(streamer.id)
  const [url, setUrl] = useState('')
  const adicionar = useAdicionarFonte()
  return (
    <div className="space-y-4">
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          adicionar.mutate({ streamer_id: streamer.id, url: url.trim() }, { onSuccess: () => setUrl('') })
        }}
      >
        <Input
          className="min-w-64 flex-1"
          placeholder="Colar URL de um VOD ou clipe (Twitch ou YouTube)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Button type="submit" variant="outline" disabled={!url.trim() || adicionar.isPending}>
          <Link2 /> Adicionar
        </Button>
      </form>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : !fontes.length ? (
        <Vazio icone={<Film />} titulo="Nenhum VOD ou clipe ainda">
          Use “Buscar VODs” / “Buscar clipes” ou cole uma URL acima.
        </Vazio>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {fontes.map((f) => (
            <CartaoFonte key={f.id} fonte={f} />
          ))}
        </div>
      )}
    </div>
  )
}

function AbaWebcam({ streamer, versao }: { streamer: Streamer; versao: number }) {
  const detectar = useDetectarWebcam(streamer.id)
  const atualizar = useAtualizarStreamer(streamer.id)
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle>Posição da webcam</CardTitle>
          <CardDescription>
            Ponto de partida do enquadramento de cada corte (cada corte confere a webcam no próprio trecho). A detecção acha o rosto fixo num trecho de um VOD; ajuste à mão se precisar.
          </CardDescription>
        </div>
        <Button variant="outline" disabled={detectar.isPending} onClick={() => detectar.mutate(undefined)}>
          <ScanFace /> Detectar webcam
        </Button>
      </CardHeader>
      <CardContent>
        <WebcamEditor
          key={`${versao}-${JSON.stringify(streamer.webcam)}`}
          quadro={urls.quadro(streamer.id, versao)}
          valor={streamer.webcam}
          salvando={atualizar.isPending}
          onSalvar={(w) => atualizar.mutate({ webcam: w })}
        />
      </CardContent>
    </Card>
  )
}

function JobsDoStreamer({ streamer, fontes }: { streamer: Streamer; fontes: number[] }) {
  const { data: jobs = [] } = useJobs({ status: 'fila,rodando,cancelando' })
  const meus = jobs.filter((j) => j.params.streamer_id === streamer.id || fontes.includes(j.params.fonte_id as number))
  if (!meus.length) return null
  return (
    <div className="mb-6 grid gap-2 md:grid-cols-2">
      {meus.map((j) => (
        <JobProgresso key={j.id} job={j} />
      ))}
    </div>
  )
}

export function PaginaStreamer() {
  const id = Number(useParams().id)
  const { data: s, isLoading, dataUpdatedAt } = useStreamer(id)
  const { data: fontes = [] } = useFontes(id)
  const atualizar = useAtualizarStreamer(id)
  const remover = useRemoverStreamer()
  const navegar = useNavigate()

  if (isLoading) return <Skeleton className="h-64" />
  if (!s) return <Vazio titulo="Streamer não encontrado" />

  return (
    <>
      <Link to="/biblioteca" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Biblioteca
      </Link>
      <Cabecalho
        titulo={
          <span className="flex items-center gap-2">
            <Plataforma p={s.plataforma} soIcone className="[&_svg]:size-6" /> {s.nome}
          </span>
        }
        descricao={
          <>
            {s.canal} · {s.idioma.toUpperCase()}
            {s.campanha_url && (
              <>
                {' · '}
                <a href={s.campanha_url} target="_blank" rel="noreferrer" className="text-ciano hover:underline">
                  campanha
                </a>
              </>
            )}
          </>
        }
      >
        {(s.plataforma === 'twitch' || s.plataforma === 'youtube') && <DialogoBuscar streamer={s} tipo="vod" />}
        {s.plataforma === 'twitch' && <DialogoBuscar streamer={s} tipo="clipe" />}
        <Button variant="outline" asChild>
          <Link to={`/biblioteca?streamer=${s.id}`}>
            <Clapperboard /> Cortes
          </Link>
        </Button>
      </Cabecalho>

      <JobsDoStreamer streamer={s} fontes={fontes.map((f) => f.id)} />

      <Tabs defaultValue="fontes">
        <TabsList className="mb-4">
          <TabsTrigger value="fontes">VODs e clipes</TabsTrigger>
          <TabsTrigger value="webcam">Webcam</TabsTrigger>
          <TabsTrigger value="config">Configurações</TabsTrigger>
        </TabsList>
        <TabsContent value="fontes">
          <AbaFontes streamer={s} />
        </TabsContent>
        <TabsContent value="webcam">
          <AbaWebcam streamer={s} versao={dataUpdatedAt} />
        </TabsContent>
        <TabsContent value="config">
          <Card>
            <CardContent className="space-y-6">
              <FormStreamer
                key={dataUpdatedAt}
                inicial={{
                  nome: s.nome,
                  plataforma: s.plataforma as DadosStreamer['plataforma'],
                  canal: s.canal,
                  idioma: s.idioma as DadosStreamer['idioma'],
                  conta_id: s.conta_id,
                  modelo_id: s.modelo_id,
                  campanha_url: s.campanha_url,
                  notas: s.notas,
                }}
                bloquearPlataforma
                rotuloEnviar="Salvar"
                enviando={atualizar.isPending}
                onEnviar={({ plataforma: _p, ...resto }) => atualizar.mutate(resto)}
              />
              <div className="flex items-center justify-between gap-2 border-t pt-4">
                <p className="text-sm text-muted-foreground">Remover apaga o streamer, as fontes e os cortes dele (os vídeos já na fila ficam).</p>
                <Confirmar
                  titulo={`Remover ${s.nome}?`}
                  descricao="Apaga o streamer, as fontes e os cortes candidatos do banco."
                  confirmar="Remover"
                  perigoso
                  onConfirmar={() => remover.mutate(s.id, { onSuccess: () => void navegar('/biblioteca') })}
                >
                  <Button variant="destructive">
                    <Trash2 /> Remover
                  </Button>
                </Confirmar>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  )
}
