import { Camera, CameraOff, Clapperboard, Link2, Plus, Scissors } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { useCriarStreamer, useStreamers } from '@/api/hooks/cortador'
import { useSistema } from '@/api/hooks/contas'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { FormStreamer } from '@/components/form-streamer'
import { Plataforma } from '@/components/plataforma'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { useConta } from '@/lib/conta'

function NovoStreamer() {
  const [aberto, setAberto] = useState(false)
  const criar = useCriarStreamer()
  const navegar = useNavigate()
  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Novo streamer
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Novo streamer</DialogTitle>
          <DialogDescription>De quem vamos tirar os cortes. Dá para mudar tudo depois.</DialogDescription>
        </DialogHeader>
        <FormStreamer
          rotuloEnviar="Adicionar"
          enviando={criar.isPending}
          onEnviar={(d) =>
            criar.mutate(d, {
              onSuccess: (s) => {
                setAberto(false)
                void navegar(`/cortador/streamers/${s.id}`)
              },
            })
          }
        />
      </DialogContent>
    </Dialog>
  )
}

export function PaginaCortador() {
  const { data: streamers = [], isLoading } = useStreamers()
  const { data: sis } = useSistema()
  const { contas } = useConta()
  const nomeConta = (id?: string | null) => contas.find((c) => c.id === id)?.nome

  return (
    <>
      <Cabecalho
        titulo="Cortador"
        descricao="Streamers → VODs/clipes → trechos detectados (sem IA: picos de áudio, mais assistidos, clipes) → revisão → vertical com legenda → fila."
      >
        <Button asChild>
          <Link to="/cortador/novo">
            <Link2 /> Cortar vídeo (colar link)
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/cortador/cortes">
            <Clapperboard /> Revisar cortes
          </Link>
        </Button>
        <NovoStreamer />
      </Cabecalho>

      {sis && !sis.twitch_api && (
        <p className="mb-4 rounded-lg border border-laranja/40 bg-laranja/10 p-3 text-sm">
          A API da Twitch não está configurada: VODs funcionam (picos de áudio), mas “Buscar clipes” e o detector de clipes
          precisam de <code>JASON_TWITCH_CLIENT_ID</code> e <code>JASON_TWITCH_CLIENT_SECRET</code> no <code>.env</code>{' '}
          (grátis em dev.twitch.tv/console/apps).
        </p>
      )}

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !streamers.length ? (
        <Vazio icone={<Scissors />} titulo="Nenhum streamer ainda">
          Adicione alanzoka, Flow Games, Kai Cenat, Speed... e comece buscando os VODs deles.
        </Vazio>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {streamers.map((s) => (
            <Link key={s.id} to={`/cortador/streamers/${s.id}`} className="group">
              <Card className="h-full transition-colors group-hover:ring-rosa/60">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Plataforma p={s.plataforma} soIcone />
                    {s.nome}
                    {!s.ativo && <Badge variant="outline">inativo</Badge>}
                  </CardTitle>
                  <CardDescription>
                    {s.canal} · {s.idioma.toUpperCase()}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">{s.total_fontes} fonte(s)</Badge>
                    <Badge variant="secondary">{s.total_cortes} corte(s)</Badge>
                    {s.webcam ? (
                      <Badge variant="outline" className="border-verde/40 text-verde">
                        <Camera /> webcam ok
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground">
                        <CameraOff /> sem webcam
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Destino: {nomeConta(s.conta_id) ?? <span className="text-laranja">nenhuma conta</span>}
                    {s.campanha_url && ' · com campanha'}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
