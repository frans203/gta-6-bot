import { Ban, CalendarClock, Download, ExternalLink, MoreHorizontal, PenLine, Send, Undo2, CheckCircle2, ListVideo } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'

import { urls } from '@/api/cliente'
import { useApagarPost, useBaixarPack, useCorrigirPost, useEstadoRede, usePosts, useVideos } from '@/api/hooks/postagem'
import type { Conta, Post, Video } from '@/api/tipos'
import { AbasAnimadas } from '@/components/abas-animadas'
import { AgendarVideo } from '@/components/agendar-video'
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
type AbaVideo = 'textos' | 'agendar'

interface PropsDetalhe {
  conta: Conta
  video: Video | null
  aba: AbaVideo
  onAba: (a: AbaVideo) => void
  onFechar: () => void
  postDe: (video: string, rede: string) => Post | undefined
}

function DetalheVideo({ video, onFechar, ...resto }: PropsDetalhe) {
  return (
    <Sheet open={!!video} onOpenChange={(a) => !a && onFechar()}>
      <SheetContent className="w-full overflow-y-auto data-[side=right]:w-[min(1180px,94vw)] data-[side=right]:max-w-none data-[side=right]:sm:max-w-none">
        {video && <FormVideo key={video.video} video={video} {...resto} />}
      </SheetContent>
    </Sheet>
  )
}

function FormVideo({ conta, video, aba, onAba, postDe }: Omit<PropsDetalhe, 'video' | 'onFechar'> & { video: Video }) {
  return (
    <>
      <SheetHeader>
        <SheetTitle>{video.video}</SheetTitle>
        <SheetDescription>{video.mb} MB · textos do post e agendamento por rede</SheetDescription>
      </SheetHeader>
      <div className="grid gap-8 px-6 pb-8 md:grid-cols-[minmax(260px,340px)_minmax(0,1fr)]">
        <div className="space-y-3 md:sticky md:top-0 md:self-start">
          <Player9x16 src={urls.video(conta.id, video.video)} className="max-w-none" />
          <div className="grid grid-cols-3 gap-1.5 text-center text-[11px]">
            {conta.plataformas.map((p) => (
              <div key={p} className="space-y-1 rounded-lg border bg-white/[0.02] p-1.5">
                <Plataforma p={p} soIcone className="justify-center" />
                <StatusChip status={video.plataformas[p]?.status ?? 'pendente'} />
              </div>
            ))}
          </div>
          <DialogoPostar conta={conta} video={video.video}>
            <Button size="lg" className="botao-brilho w-full">
              <Send /> Postar este vídeo agora
            </Button>
          </DialogoPostar>
          {aba !== 'agendar' && (
            <Button size="lg" variant="outline" className="w-full" onClick={() => onAba('agendar')}>
              <CalendarClock /> Agendar
            </Button>
          )}
        </div>
        <AbasAnimadas<AbaVideo>
          abas={[
            { id: 'textos', rotulo: 'Textos', Icone: PenLine },
            { id: 'agendar', rotulo: 'Agendar', Icone: CalendarClock },
          ]}
          valor={aba}
          onChange={onAba}
        >
          {aba === 'textos' ? (
            <EditorTextos conta={conta} nome={video.video} />
          ) : (
            <AgendarVideo conta={conta} video={video} postDe={(r) => postDe(video.video, r)} />
          )}
        </AbasAnimadas>
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
  const { conta, setContaId } = useConta()
  const { data: videos = [], isLoading } = useVideos(conta?.id)
  const { data: posts = [] } = usePosts({ conta_id: conta?.id, limite: 5000 }, !!conta)
  // gaveta aberta na URL: ?video=X&aba=agendar (a Biblioteca abre direto aqui; ?conta= troca a conta)
  const [busca, setBusca] = useSearchParams()
  const nomeAberto = busca.get('video')
  const aba: AbaVideo = busca.get('aba') === 'agendar' ? 'agendar' : 'textos'
  const aberto = videos.find((v) => v.video === nomeAberto) ?? null
  const abrir = (v: Video | null, a: AbaVideo = 'textos') =>
    setBusca(v ? { video: v.video, ...(a === 'agendar' ? { aba: a } : {}) } : {}, { replace: !!nomeAberto })
  const contaUrl = busca.get('conta')
  useEffect(() => {
    if (contaUrl && contaUrl !== conta?.id) setContaId(contaUrl)
  }, [contaUrl, conta?.id, setContaId])

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
                    <button type="button" className="text-left hover:underline" onClick={() => abrir(v)}>
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
                    <div className="flex">
                      <Button size="icon-sm" variant="ghost" title="Agendar este vídeo" onClick={() => abrir(v, 'agendar')}>
                        <CalendarClock />
                      </Button>
                      <DialogoPostar conta={conta} video={v.video}>
                        <Button size="icon-sm" variant="ghost" title="Postar este vídeo agora">
                          <Send />
                        </Button>
                      </DialogoPostar>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <DetalheVideo
        conta={conta}
        video={aberto}
        aba={aba}
        onAba={(a) => aberto && abrir(aberto, a)}
        onFechar={() => abrir(null)}
        postDe={(video, rede) => postPor.get(`${video}|${rede}`)}
      />
    </>
  )
}
