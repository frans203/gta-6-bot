import { AlertTriangle, Check, Copy, Hash, Loader2, Save, Tags } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { type TextosVideo, useHashtagsLote, useSalvarTextos, useTextos } from '@/api/hooks/postagem'
import type { components } from '@/api/schema'
import type { Conta } from '@/api/tipos'
import { AbasAnimadas } from '@/components/abas-animadas'
import { CampoHashtags } from '@/components/campo-hashtags'
import { Plataforma } from '@/components/plataforma'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { contarHashtags, LIMITES, type Rede, textosFinais } from '@/lib/textos'
import { cn } from '@/lib/utils'

function Contador({ n, max, alerta }: { n: number; max: number; alerta?: boolean }) {
  return (
    <span className={cn('font-mono text-[10px] tabular-nums', n > max || alerta ? 'text-amarelo' : 'text-muted-foreground')}>
      {n}/{max}
    </span>
  )
}

function Copiar({ texto }: { texto: string }) {
  return (
    <Button
      size="icon-xs"
      variant="ghost"
      title="Copiar"
      onClick={() => void navigator.clipboard.writeText(texto).then(() => toast.success('Copiado'))}
    >
      <Copy />
    </Button>
  )
}

/** Título, descrição e hashtags do vídeo, com texto próprio opcional para cada rede e prévia do que vai sair. */
export function EditorTextos({ conta, nome }: { conta: Conta; nome: string }) {
  const { data, isLoading } = useTextos(conta.id, nome)
  if (isLoading || !data) return <Skeleton className="h-80" />
  return <FormTextos key={nome} conta={conta} nome={nome} inicial={data} />
}

function FormTextos({ conta, nome, inicial }: { conta: Conta; nome: string; inicial: components['schemas']['TextosOut'] }) {
  const [t, setT] = useState<TextosVideo>({
    titulo: inicial.titulo,
    descricao: inicial.descricao ?? '',
    tags: inicial.tags || conta.tags,
    redes: {
      youtube: { titulo: inicial.redes?.youtube?.titulo ?? null, descricao: inicial.redes?.youtube?.descricao ?? null },
      tiktok: { legenda: inicial.redes?.tiktok?.legenda ?? null },
      instagram: { legenda: inicial.redes?.instagram?.legenda ?? null },
    },
  })
  const [salvo, setSalvo] = useState(JSON.stringify(t))
  const [rede, setRede] = useState<Rede>('tiktok')
  const salvar = useSalvarTextos(conta.id, nome)
  const finais = textosFinais(t)
  const alterado = JSON.stringify(t) !== salvo
  const nTags = contarHashtags(t.tags)
  const set = (campos: Partial<TextosVideo>) => setT((x) => ({ ...x, ...campos }))
  const redes = t.redes!
  const proprio = {
    youtube: redes.youtube?.titulo != null || redes.youtube?.descricao != null,
    tiktok: redes.tiktok?.legenda != null,
    instagram: redes.instagram?.legenda != null,
  }
  const alternarProprio = (r: Rede, v: boolean) =>
    set({
      redes: {
        ...redes,
        [r]: r === 'youtube'
          ? v ? { ...finais.youtube } : { titulo: null, descricao: null }
          : { legenda: v ? finais[r].legenda : null },
      },
    })

  const legendaIg = finais.instagram.legenda
  const avisos: Record<Rede, string | null> = {
    instagram: contarHashtags(legendaIg) > LIMITES.instagramHashtags ? `O Instagram aceita até ${LIMITES.instagramHashtags} hashtags.` : null,
    youtube: contarHashtags(finais.youtube.descricao) > 15 ? 'O YouTube mostra só 3 hashtags acima do título e ignora todas se passar de 60.' : null,
    tiktok: null,
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="titulo">Título</Label>
          <Contador n={t.titulo.length} max={100} />
        </div>
        <Input id="titulo" value={t.titulo} maxLength={100} placeholder="O gancho do vídeo em uma frase" onChange={(e) => set({ titulo: e.target.value })} />
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="descricao">Descrição</Label>
          <Contador n={t.descricao?.length ?? 0} max={2000} />
        </div>
        <Textarea
          id="descricao"
          rows={3}
          maxLength={2000}
          value={t.descricao ?? ''}
          placeholder="Opcional: contexto, chamada para seguir, crédito…"
          onChange={(e) => set({ descricao: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="hashtags" className="flex items-center gap-1.5">
            <Hash className="size-3.5" /> Hashtags
          </Label>
          <Contador n={nTags} max={LIMITES.instagramHashtags} />
        </div>
        <CampoHashtags id="hashtags" valor={t.tags} onChange={(tags) => set({ tags })} aviso={nTags > LIMITES.instagramHashtags ? 'muitas' : null} />
      </div>

      {/* por rede */}
      <div className="space-y-3 rounded-2xl border bg-white/[0.02] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-heading text-sm font-bold">Como sai em cada rede</h3>
          <AbasAnimadas<Rede>
            className="w-auto"
            valor={rede}
            onChange={setRede}
            abas={(['tiktok', 'youtube', 'instagram'] as Rede[]).map((r) => ({
              id: r,
              rotulo: <Plataforma p={r} />,
              alerta: !!avisos[r],
            }))}
          />
        </div>
        <div className="flex items-center justify-between text-xs">
          <Label htmlFor={`proprio-${rede}`} className="text-xs">
            Texto próprio nesta rede
          </Label>
          <Switch id={`proprio-${rede}`} checked={proprio[rede]} onCheckedChange={(v) => alternarProprio(rede, v)} />
        </div>

        {rede === 'youtube' ? (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Título no YouTube</span>
                <span className="flex items-center gap-1">
                  <Contador n={finais.youtube.titulo.length} max={LIMITES.youtubeTitulo} />
                  <Copiar texto={finais.youtube.titulo} />
                </span>
              </div>
              {proprio.youtube ? (
                <Input
                  value={redes.youtube?.titulo ?? ''}
                  maxLength={100}
                  onChange={(e) => set({ redes: { ...redes, youtube: { ...redes.youtube, titulo: e.target.value } } })}
                />
              ) : (
                <p className="rounded-lg bg-black/30 p-2.5 text-sm">{finais.youtube.titulo}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Descrição no YouTube</span>
                <span className="flex items-center gap-1">
                  <Contador n={finais.youtube.descricao.length} max={LIMITES.youtubeDescricao} />
                  <Copiar texto={finais.youtube.descricao} />
                </span>
              </div>
              {proprio.youtube ? (
                <Textarea
                  rows={4}
                  value={redes.youtube?.descricao ?? ''}
                  maxLength={5000}
                  onChange={(e) => set({ redes: { ...redes, youtube: { ...redes.youtube, descricao: e.target.value } } })}
                />
              ) : (
                <p className="rounded-lg bg-black/30 p-2.5 text-sm whitespace-pre-wrap">{finais.youtube.descricao}</p>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Legenda</span>
              <span className="flex items-center gap-1">
                <Contador n={finais[rede].legenda.length} max={LIMITES[rede]} />
                <Copiar texto={finais[rede].legenda} />
              </span>
            </div>
            {proprio[rede] ? (
              <Textarea
                rows={5}
                maxLength={2200}
                value={redes[rede]?.legenda ?? ''}
                onChange={(e) => set({ redes: { ...redes, [rede]: { legenda: e.target.value } } })}
              />
            ) : (
              <p className="rounded-lg bg-black/30 p-2.5 text-sm">{finais[rede].legenda}</p>
            )}
          </div>
        )}
        {avisos[rede] && (
          <p className="flex items-center gap-1.5 text-[11px] text-amarelo">
            <AlertTriangle className="size-3.5" /> {avisos[rede]}
          </p>
        )}
        <p className="text-[11px] text-muted-foreground">
          Sem texto próprio, cada rede recebe <b>título + descrição + hashtags</b> (o YouTube usa o título no campo de título). Quebras de
          linha viram espaço: o robô digita tudo numa linha.
        </p>
      </div>

      <div className="flex items-center justify-end gap-2">
        {!alterado && <span className="flex items-center gap-1 text-xs text-muted-foreground"><Check className="size-3.5" /> salvo</span>}
        <Button
          disabled={!alterado || !t.titulo.trim() || salvar.isPending}
          onClick={() => salvar.mutate(t, { onSuccess: () => setSalvo(JSON.stringify(t)) })}
        >
          {salvar.isPending ? <Loader2 className="animate-spin" /> : <Save />} Salvar textos
        </Button>
      </div>
    </div>
  )
}

/** Troca ou acrescenta hashtags em vários vídeos de uma vez. */
export function HashtagsEmLote({ conta }: { conta: Conta }) {
  const [aberto, setAberto] = useState(false)
  const [tags, setTags] = useState(conta.tags)
  const [modo, setModo] = useState<'substituir' | 'adicionar'>('adicionar')
  const aplicar = useHashtagsLote(conta.id)
  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Tags /> Hashtags em lote
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogTitle>Hashtags em lote</DialogTitle>
        <DialogDescription>Vale para todos os vídeos desta conta que ainda não foram postados em nenhuma rede.</DialogDescription>
        <CampoHashtags id="hashtags-lote" valor={tags} onChange={setTags} />
        <div className="grid grid-cols-2 gap-2">
          {(['adicionar', 'substituir'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setModo(m)}
              className={cn(
                'rounded-lg border px-3 py-2 text-left text-xs transition-colors hover:border-roxo/60',
                modo === m && 'border-rosa/60 bg-rosa/10',
              )}
            >
              <b className="block text-sm">{m === 'adicionar' ? 'Acrescentar' : 'Substituir'}</b>
              {m === 'adicionar' ? 'Mantém as que já têm e põe estas no fim' : 'Troca todas as hashtags por estas'}
            </button>
          ))}
        </div>
        <div className="flex justify-end">
          <Button
            disabled={!tags.trim() || aplicar.isPending}
            onClick={() => aplicar.mutate({ tags, modo, videos: null }, { onSuccess: () => setAberto(false) })}
          >
            {aplicar.isPending ? <Loader2 className="animate-spin" /> : <Tags />} Aplicar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
