import { Check, CheckCircle2, ImagePlus, Loader2, ScanFace, Upload, X } from 'lucide-react'
import { useRef } from 'react'

import { urls } from '@/api/cliente'
import { useAplicarCortes, useEnviarFundo, useFundos, useModelos, usePlugins } from '@/api/hooks/cortador'
import type { Corte } from '@/api/tipos'
import { Button } from '@/components/ui/button'
import { modeloEfetivo } from '@/lib/enquadramento'
import { cn } from '@/lib/utils'

/* Ajustes que valem para todos os cortes de um vídeo original (modal do vídeo na Biblioteca). */

const NOME_IDIOMA: Record<string, string> = { pt: 'Português', en: 'Inglês', es: 'Espanhol' }
export const nomeIdioma = (c?: string | null) => (c ? (NOME_IDIOMA[c] ?? c.toUpperCase()) : '?')
const IDIOMAS_LEGENDA = ['pt', 'en', 'es']
const PRETO_MINIMO = 0.15

export function PerguntaIdioma({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const aplicar = useAplicarCortes(fonteId)
  const falado = cortes.find((c) => c.fonte_idioma)?.fonte_idioma ?? cortes.find((c) => c.extra.idioma)?.extra.idioma as string | undefined
  if (!falado) return <p className="text-sm text-muted-foreground">Ainda descobrindo o idioma falado...</p>
  const atual = cortes[0]?.idioma_legenda ?? falado
  const opcoes = Array.from(new Set([falado, 'pt', 'en'].filter((x) => IDIOMAS_LEGENDA.includes(x))))
  return (
    <div className="space-y-2">
      <p className="text-sm">
        O vídeo está em <b>{nomeIdioma(falado)}</b>. Legenda em:
      </p>
      <div className="flex flex-wrap gap-2">
        {opcoes.map((x) => (
          <Button
            key={x}
            variant={atual === x ? 'default' : 'outline'}
            disabled={aplicar.isPending}
            onClick={() => aplicar.mutate({ idioma_legenda: x === falado ? null : (x as 'pt' | 'en' | 'es') })}
          >
            {atual === x && <Check />} {nomeIdioma(x)} {x === falado ? '(original)' : '(traduzida)'}
          </Button>
        ))}
      </div>
      {atual !== falado && (
        <p className="text-xs text-muted-foreground">
          A tradução roda no seu PC (modelo gratuito, sem IA paga). Na 1ª vez baixa ~80 MB. Gírias podem sair literais: confira no
          vídeo pronto.
        </p>
      )}
    </div>
  )
}

export function ImagemDeFundo({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const { data: fundos = [] } = useFundos()
  const { data: modelos = [] } = useModelos()
  const enviar = useEnviarFundo()
  const aplicar = useAplicarCortes(fonteId)
  const arquivo = useRef<HTMLInputElement>(null)
  const preto = Math.max(0, ...cortes.map((c) => (c.extra.espaco_preto as number | undefined) ?? 0))
  const atual = cortes.find((c) => c.fundo)?.fundo ?? null
  const modeloFundo = modelos.find((m) => m.layout === 'fundo_imagem')

  const usar = (nome: string) => aplicar.mutate({ fundo: nome, modelo_id: modeloFundo?.id ?? null })
  const enviarArquivo = (f?: File) => f && enviar.mutate(f, { onSuccess: (r) => usar(r.nome) })

  return (
    <div className="space-y-3">
      {preto >= PRETO_MINIMO ? (
        <p className="text-sm">
          Este vídeo tem <b className="text-amarelo">{Math.round(preto * 100)}% de espaço preto</b> (barras). Escolha uma imagem de fundo:
          o corte fica com a <b>imagem atrás</b>, o <b>vídeo em cima</b>, a <b>legenda</b> e o <b>streamer embaixo</b>.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Sem barras pretas relevantes{preto > 0 ? ` (${Math.round(preto * 100)}%)` : ''}. Se quiser, use mesmo assim uma imagem de
          fundo.
        </p>
      )}
      <div
        className="flex flex-wrap gap-2"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          enviarArquivo(e.dataTransfer.files[0])
        }}
      >
        {fundos.map((f) => (
          <button
            key={f.nome}
            type="button"
            onClick={() => usar(f.nome)}
            className={cn(
              'relative h-28 w-16 overflow-hidden rounded-md border-2',
              atual === f.nome ? 'border-primary' : 'border-transparent opacity-80 hover:opacity-100',
            )}
            title={f.nome}
          >
            <img src={urls.fundo(f.nome)} alt="" className="size-full object-cover" />
            {atual === f.nome && <CheckCircle2 className="absolute top-1 right-1 size-4 text-primary" />}
          </button>
        ))}
        <button
          type="button"
          onClick={() => arquivo.current?.click()}
          className="flex h-28 w-16 flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed text-[10px] text-muted-foreground hover:bg-muted/50"
        >
          {enviar.isPending ? <Loader2 className="size-5 animate-spin" /> : <ImagePlus className="size-5" />}
          enviar
        </button>
        <input
          ref={arquivo}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => enviarArquivo(e.target.files?.[0])}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Upload className="size-3.5" /> Arraste uma imagem aqui ou clique em “enviar” (JPG/PNG/WEBP, de preferência vertical 1080x1920).
        {atual && (
          <Button size="sm" variant="ghost" onClick={() => aplicar.mutate({ fundo: null, modelo_id: null })}>
            <X /> Não usar fundo
          </Button>
        )}
      </div>
    </div>
  )
}

export function SugerirModeloComStreamer({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const { data: modelos = [] } = useModelos()
  const { data: plugins } = usePlugins()
  const aplicar = useAplicarCortes(fonteId)
  const usaCam = (c: Corte) =>
    !!plugins?.layouts.find((l) => l.id === modeloEfetivo(modelos, c.modelo_id, c)?.layout)?.opcoes.precisa_webcam
  const achados = cortes.filter((c) => c.webcam && ['auto', 'manual'].includes(c.webcam.origem ?? '') && !usaCam(c))
  const alvo = modelos.find((m) => m.layout === 'jogo_em_cima' && m.padrao) ?? modelos.find((m) => m.layout === 'jogo_em_cima')
  if (!achados.length || !alvo || !plugins) return null
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-ciano/40 bg-ciano/10 p-3 text-sm">
      <ScanFace className="size-5 shrink-0 text-ciano" />
      <p className="min-w-0 flex-1">
        Achei a câmera do streamer em {achados.length} corte(s), mas o modelo atual não mostra a webcam.
      </p>
      <Button size="sm" disabled={aplicar.isPending} onClick={() => aplicar.mutate({ modelo_id: alvo.id })}>
        Usar “{alvo.nome}”
      </Button>
    </div>
  )
}
