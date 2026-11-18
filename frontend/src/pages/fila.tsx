import { Ban, Download, ExternalLink, MoreHorizontal, Send, Undo2, CheckCircle2, ListVideo } from 'lucide-react'
import { useMemo, useState } from 'react'

import { urls } from '@/api/cliente'
import { useApagarPost, useBaixarPack, useCorrigirPost, useEstadoRede, usePosts, useVideos } from '@/api/hooks/postagem'
import type { Conta, Post, Video } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { DialogoPostar } from '@/components/dialogo-postar'
import { EditorTextos, HashtagsEmLote } from '@/components/editor-textos'
import { Plataforma } from '@/components/plataforma'
import { Player9x16 } from '@/components/players'
import { StatusChip } from '@/components/status-chip'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useConta } from '@/lib/conta'
import { fmtDataHora } from '@/lib/formatos'

/** Menu de correção manual do estado de um vídeo numa plataforma. */
function MenuPost({ conta, video, plataforma, status, post, link }: {
  conta: Conta
  video: string
  plataforma: string
  status: string
  post: Post | undefined
  link: string | null | undefined
}) {
  const corrigir = useCorrigirPost()
  const apagar = useApagarPost()
  const estado = useEstadoRede(conta.id)
  const podeRemover = !['publicado', 'agendado', 'removido'].includes(status)
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="icon-xs" variant="ghost" aria-label="Mais ações">
          <MoreHorizontal />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Correção manual</DropdownMenuLabel>
        {link && (
          <DropdownMenuItem asChild>
            <a href={link} target="_blank" rel="noreferrer">
              <ExternalLink /> Abrir o post
            </a>
          </DropdownMenuItem>
        )}
        {post && post.status !== 'publicado' && (
          <DropdownMenuItem onClick={() => corrigir.mutate({ id: post.id, body: { status: 'publicado' } })}>
            <CheckCircle2 /> Marcar como publicado
          </DropdownMenuItem>
        )}
        {podeRemover && (
          <DropdownMenuItem onClick={() => estado.mutate({ nome: video, plataforma, status: 'removido' })}>
            <Ban /> Não postar nesta rede
          </DropdownMenuItem>
        )}
        {post && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={() => apagar.mutate(post.id)}>
              <Undo2 /> Voltar para pendente
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/** Gaveta com preview do vídeo e edição de título/tags (.txt ao lado do mp4). */
function DetalheVideo({ conta, video, onFechar }: { conta: Conta; video: Video | null; onFechar: () => void }) {
  return (
    <Sheet open={!!video} onOpenChange={(a) => !a && onFechar()}>
      <SheetContent className="w-full overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-3xl">
        {video && <FormVideo key={video.video} conta={conta} video={video} />}
      </SheetContent>
    </Sheet>
  )
}

function FormVideo({ conta, video }: { conta: Conta; video: Video }) {
  return (
    <>
      <SheetHeader>
        <SheetTitle>{video.video}</SheetTitle>
        <SheetDescription>{video.mb} MB · título, descrição e hashtags do post</SheetDescription>
      </SheetHeader>
      <div className="grid gap-6 px-4 pb-6 md:grid-cols-[220px_minmax(0,1fr)]">
        <div className="space-y-3">
          <Player9x16 src={urls.video(conta.id, video.video)} />
          <DialogoPostar conta={conta} video={video.video}>
            <Button variant="outline" className="w-full">
              <Send /> Postar agora
            </Button>
          </DialogoPostar>
        </div>
        <EditorTextos conta={conta} nome={video.video} />
      </div>
    </>
  )
}

function BaixarPack() {
  const [qtd, setQtd] = useState(5)
  const baixar = useBaixarPack()
  return (
    <div className="flex items-center gap-2">
      <Input type="number" min={1} max={100} value={qtd} onChange={(e) => setQtd(Number(e.target.value))} className="w-20" aria-label="Quantidade" />
      <Button variant="outline" disabled={baixar.isPending || qtd < 1} onClick={() => baixar.mutate(qtd)}>
        <Download /> Baixar do pack
      </Button>
    </div>
  )
}

export function PaginaFila() {
  const { conta } = useConta()
  const { data: videos = [], isLoading } = useVideos(conta?.id)
  const { data: posts = [] } = usePosts({ conta_id: conta?.id, limite: 5000 }, !!conta)
  const [aberto, setAberto] = useState<Video | null>(null)

  const postPor = useMemo(() => new Map(posts.map((p) => [`${p.video}|${p.plataforma}`, p])), [posts])

  if (!conta) return <Skeleton className="h-64" />
  const plats = conta.plataformas

  return (
    <>
      <Cabecalho titulo="Fila de vídeos" descricao={`${videos.length} vídeo(s) na pasta da conta ${conta.nome}. Clique num vídeo para editar título, descrição e hashtags.`}>
        {conta.padrao && <BaixarPack />}
        <HashtagsEmLote conta={conta} />
        <DialogoPostar conta={conta}>
          <Button>
            <Send /> Postar próximo agora
          </Button>
        </DialogoPostar>
      </Cabecalho>

      {isLoading ? (
        <Skeleton className="h-96" />
      ) : !videos.length ? (
        <Vazio icone={<ListVideo />} titulo="Nenhum vídeo na fila desta conta">
          Renderize cortes no Cortador e mande para a fila, ou baixe vídeos do pack.
        </Vazio>
      ) : (
        <div className="rounded-xl border bg-card/60">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vídeo</TableHead>
                <TableHead className="text-right">MB</TableHead>
                {plats.map((p) => (
                  <TableHead key={p}>
                    <Plataforma p={p} />
                  </TableHead>
                ))}
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {videos.map((v) => (
                <TableRow key={v.video}>
                  <TableCell className="max-w-72">
                    <button type="button" className="text-left hover:underline" onClick={() => setAberto(v)}>
                      <div className="font-medium">{v.video}</div>
                      <div className="truncate text-xs text-muted-foreground">{v.titulo ?? 'sem título'}</div>
                    </button>
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground tabular-nums">{v.mb}</TableCell>
                  {plats.map((p) => {
                    const e = v.plataformas[p] ?? { status: 'pendente' }
                    return (
                      <TableCell key={p}>
                        <div className="flex items-center gap-1">
                          <div>
                            <StatusChip status={e.status} />
                            {e.para && e.status !== 'publicado' && (
                              <div className="mt-0.5 text-[11px] text-muted-foreground tabular-nums">{fmtDataHora(e.para)}</div>
                            )}
                          </div>
                          <MenuPost
                            conta={conta}
                            video={v.video}
                            plataforma={p}
                            status={e.status}
                            post={postPor.get(`${v.video}|${p}`)}
                            link={e.link}
                          />
                        </div>
                      </TableCell>
                    )
                  })}
                  <TableCell>
                    <DialogoPostar conta={conta} video={v.video}>
                      <Button size="icon-sm" variant="ghost" title="Postar este vídeo agora">
                        <Send />
                      </Button>
                    </DialogoPostar>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <DetalheVideo conta={conta} video={aberto} onFechar={() => setAberto(null)} />
    </>
  )
}
