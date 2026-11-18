import { Columns2, Eye, EyeOff, ImagePlus, Layers, Link2, Loader2, PictureInPicture2, RectangleVertical, RotateCcw, Rows2, Unlink2, Upload } from 'lucide-react'
import { useRef } from 'react'

import { urls } from '@/api/cliente'
import { useEnviarFonteTexto } from '@/api/hooks/editor'
import type { Corte } from '@/api/tipos'
import { EditorRegioes, type RegiaoEditavel } from '@/components/editor-regioes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { CORES_REGIAO, WEBCAM_EXEMPLO } from '@/lib/enquadramento'
import {
  aplicarPredefinicao,
  cssParaHex,
  type Edicao,
  type EditorInfo,
  fmtSeg,
  fontesDasZonas,
  hexParaCss,
  type Predefinicao,
  QUADRO,
} from '@/lib/editor/modelo'
import { cn } from '@/lib/utils'

type Mudar = (ed: Edicao, grupo?: string) => void

function Campo({ rotulo, valor, children }: { rotulo: string; valor?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <Label className="text-xs">{rotulo}</Label>
        {valor != null && <span className="font-mono text-muted-foreground tabular-nums">{valor}</span>}
      </div>
      {children}
    </div>
  )
}

function Secao({ titulo, children, acao }: { titulo: string; children: React.ReactNode; acao?: React.ReactNode }) {
  return (
    <section className="space-y-4 rounded-xl border bg-white/[0.02] p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-heading text-sm font-bold">{titulo}</h3>
        {acao}
      </div>
      {children}
    </section>
  )
}

function Cor({ rotulo, valor, onChange }: { rotulo: string; valor: string; onChange: (hex: string) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-lg border bg-white/[0.03] px-2 py-1.5 text-xs transition-colors hover:border-roxo/50">
      <span className="relative size-6 overflow-hidden rounded-md ring-1 ring-white/20" style={{ background: hexParaCss(valor) }}>
        <input type="color" value={hexParaCss(valor)} onChange={(e) => onChange(cssParaHex(e.target.value))} className="absolute inset-0 cursor-pointer opacity-0" />
      </span>
      <span className="text-muted-foreground">{rotulo}</span>
      <span className="ml-auto font-mono text-[10px] uppercase">#{valor}</span>
    </label>
  )
}

function SelectFonte({ valor, fontes, onChange }: { valor: string; fontes: EditorInfo['fontes']; onChange: (f: string) => void }) {
  const lista = fontes.some((f) => f.nome === valor) ? fontes : [{ nome: valor, arquivo: null }, ...fontes]
  return (
    <Select value={valor} onValueChange={onChange}>
      <SelectTrigger className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {lista.map((f) => (
          <SelectItem key={f.nome} value={f.nome}>
            <span style={{ fontFamily: `"${f.nome}"` }} className="text-base">
              {f.nome}
            </span>
            {f.arquivo && <span className="ml-2 text-[10px] text-muted-foreground">sua</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function EnviarFonte() {
  const enviar = useEnviarFonteTexto()
  const arquivo = useRef<HTMLInputElement>(null)
  return (
    <>
      <Button size="xs" variant="ghost" onClick={() => arquivo.current?.click()} disabled={enviar.isPending} title="Enviar uma fonte .ttf/.otf">
        {enviar.isPending ? <Loader2 className="animate-spin" /> : <Upload />} fonte
      </Button>
      <input ref={arquivo} type="file" accept=".ttf,.otf" className="hidden" onChange={(e) => e.target.files?.[0] && enviar.mutate(e.target.files[0])} />
    </>
  )
}

// ------------------------------------------------------------------ Texto

export function PainelTexto({ ed, info, gancho, onGancho, onChange }: {
  ed: Edicao
  info: EditorInfo
  gancho: string
  onGancho: (t: string) => void
  onChange: Mudar
}) {
  const leg = ed.legenda
  const g = ed.gancho
  const setLeg = (campos: Partial<Edicao['legenda']>, grupo?: string) => onChange({ ...ed, legenda: { ...leg, ...campos } }, grupo)
  const setGan = (campos: Partial<Edicao['gancho']>, grupo?: string) => onChange({ ...ed, gancho: { ...g, ...campos } }, grupo)
  return (
    <div className="space-y-4">
      <Secao
        titulo="Legenda"
        acao={
          <div className="flex items-center gap-2">
            <EnviarFonte />
            <Switch checked={leg.mostrar} onCheckedChange={(v) => setLeg({ mostrar: v })} title="Mostrar a legenda" />
          </div>
        }
      >
        <div className={cn('space-y-4', !leg.mostrar && 'pointer-events-none opacity-40')}>
          <Campo rotulo="Fonte">
            <SelectFonte valor={leg.fonte} fontes={info.fontes} onChange={(f) => setLeg({ fonte: f })} />
          </Campo>
          <div className="grid grid-cols-2 gap-2">
            <Cor rotulo="Texto" valor={leg.cor} onChange={(c) => setLeg({ cor: c }, 'leg-cor')} />
            <Cor rotulo="Palavra falada" valor={leg.destaque} onChange={(c) => setLeg({ destaque: c }, 'leg-destaque')} />
          </div>
          <Campo rotulo="Tamanho" valor={`${leg.tamanho}px`}>
            <Slider min={20} max={220} step={1} value={[leg.tamanho]} onValueChange={([v]) => setLeg({ tamanho: v }, 'leg-tam')} />
          </Campo>
          <Campo rotulo="Contorno" valor={leg.contorno}>
            <Slider min={0} max={24} step={1} value={[leg.contorno]} onValueChange={([v]) => setLeg({ contorno: v }, 'leg-cont')} />
          </Campo>
          <Campo rotulo="Palavras na tela por vez" valor={leg.por_bloco}>
            <Slider min={1} max={8} step={1} value={[leg.por_bloco]} onValueChange={([v]) => setLeg({ por_bloco: v }, 'leg-bloco')} />
          </Campo>
          <Campo rotulo="Altura na tela" valor={`${Math.round(leg.y * 100)}%`}>
            <Slider min={3} max={97} step={0.5} value={[leg.y * 100]} onValueChange={([v]) => setLeg({ y: v / 100 }, 'leg-y')} />
          </Campo>
          <div className="flex items-center justify-between text-xs">
            <Label htmlFor="maiusculas" className="text-xs">
              CAIXA ALTA
            </Label>
            <Switch id="maiusculas" checked={leg.maiusculas} onCheckedChange={(v) => setLeg({ maiusculas: v })} />
          </div>
        </div>
      </Secao>

      <Secao titulo="Gancho (primeiros 3,5 s)">
        <Input value={gancho} maxLength={120} placeholder="ex.: ELE NÃO ESPERAVA ISSO 😳" onChange={(e) => onGancho(e.target.value)} />
        <div className={cn('space-y-4', !gancho && 'pointer-events-none opacity-40')}>
          <Campo rotulo="Fonte">
            <SelectFonte valor={g.fonte} fontes={info.fontes} onChange={(f) => setGan({ fonte: f })} />
          </Campo>
          <div className="grid grid-cols-2 gap-2">
            <Cor rotulo="Texto" valor={g.cor} onChange={(c) => setGan({ cor: c }, 'gan-cor')} />
            <Cor rotulo="Caixa" valor={g.fundo} onChange={(c) => setGan({ fundo: c }, 'gan-fundo')} />
          </div>
          <Campo rotulo="Tamanho" valor={`${g.tamanho}px`}>
            <Slider min={20} max={200} step={1} value={[g.tamanho]} onValueChange={([v]) => setGan({ tamanho: v }, 'gan-tam')} />
          </Campo>
          <Campo rotulo="Altura na tela" valor={`${Math.round(g.y * 100)}%`}>
            <Slider min={0} max={90} step={0.5} value={[g.y * 100]} onValueChange={([v]) => setGan({ y: v / 100 }, 'gan-y')} />
          </Campo>
        </div>
      </Secao>
    </div>
  )
}

// ------------------------------------------------------------------ Layout

const PREDEFINICOES: { id: Predefinicao; rotulo: string; Icone: typeof Rows2; precisaCam?: boolean }[] = [
  { id: 'jogo_em_cima', rotulo: 'Jogo em cima', Icone: Rows2, precisaCam: true },
  { id: 'streamer_em_cima', rotulo: 'Streamer em cima', Icone: Columns2, precisaCam: true },
  { id: 'canto', rotulo: 'Streamer no canto', Icone: PictureInPicture2, precisaCam: true },
  { id: 'so_jogo', rotulo: 'Só o jogo', Icone: RectangleVertical },
]

export function PainelLayout({ ed, info, corte, onChange, onRestaurar }: {
  ed: Edicao
  info: EditorInfo
  corte: Corte
  onChange: Mudar
  onRestaurar: () => void
}) {
  const lay = ed.layout
  const fontes = fontesDasZonas(ed, corte.jogo, corte.webcam)
  const camConfirmada = !!lay.webcam?.fonte || ['auto', 'manual'].includes(corte.webcam?.origem ?? '')
  const camPadrao = corte.webcam ?? WEBCAM_EXEMPLO

  const mostrarStreamer = (v: boolean) =>
    onChange({
      ...ed,
      // sem fonte própria: usa a webcam do corte; a posição só vale para o render depois de confirmada
      layout: { ...lay, webcam: v ? { saida: { x: 0.56, y: 0.06, w: 0.4, h: 0.13 }, fonte: null } : null },
    })

  const regioes: RegiaoEditavel[] = [{ id: 'jogo', rotulo: 'JOGO', cor: CORES_REGIAO.jogo, valor: fontes.jogo ?? QUADRO }]
  if (lay.webcam) regioes.push({ id: 'webcam', rotulo: 'STREAMER', cor: CORES_REGIAO.webcam, valor: fontes.webcam ?? camPadrao })

  return (
    <div className="space-y-4">
      <Secao
        titulo="Arrumação"
        acao={
          <Button size="xs" variant="ghost" onClick={onRestaurar} title="Volta para o layout do modelo de corte">
            <RotateCcw /> do modelo
          </Button>
        }
      >
        <div className="grid grid-cols-2 gap-2">
          {PREDEFINICOES.map((p) => (
            <button
              key={p.id}
              type="button"
              disabled={p.precisaCam && !lay.webcam && !corte.webcam}
              onClick={() => onChange({ ...ed, layout: aplicarPredefinicao(lay, p.id, !!(lay.webcam || corte.webcam)) })}
              className="group flex items-center gap-2 rounded-lg border bg-white/[0.03] px-3 py-2 text-left text-xs font-medium transition-all hover:-translate-y-0.5 hover:border-roxo/60 hover:bg-roxo/10 disabled:opacity-40"
            >
              <p.Icone className="size-4 text-ciano transition-transform group-hover:scale-110" /> {p.rotulo}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-muted-foreground">
          Arraste as caixas na prévia para mover; puxe os cantos para o tamanho (<kbd>Shift</kbd> mantém a proporção, <kbd>Alt</kbd>{' '}
          desliga o ímã).
        </p>
        <div className="space-y-3 border-t pt-3">
          <div className="flex items-center justify-between text-xs">
            <Label className="flex items-center gap-2 text-xs">{lay.webcam ? <Eye className="size-3.5" /> : <EyeOff className="size-3.5" />} Mostrar o streamer</Label>
            <Switch checked={!!lay.webcam} onCheckedChange={mostrarStreamer} />
          </div>
          {lay.webcam && (
            <div className="flex items-center justify-between text-xs">
              <Label className="flex items-center gap-2 text-xs">
                <Layers className="size-3.5" /> Streamer na frente do jogo
              </Label>
              <Switch checked={lay.webcam_na_frente} onCheckedChange={(v) => onChange({ ...ed, layout: { ...lay, webcam_na_frente: v } })} />
            </div>
          )}
          <Campo rotulo="Fundo">
            <Select value={lay.fundo} onValueChange={(v) => onChange({ ...ed, layout: { ...lay, fundo: v as typeof lay.fundo } })}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desfocado">O próprio vídeo desfocado</SelectItem>
                <SelectItem value="preto">Preto</SelectItem>
                <SelectItem value="imagem" disabled={!info.fundo_imagem}>
                  <ImagePlus className="size-3.5" /> Imagem de fundo {info.fundo_imagem ? '' : '(escolha uma no modal do vídeo)'}
                </SelectItem>
              </SelectContent>
            </Select>
          </Campo>
        </div>
      </Secao>

      <Secao titulo="O que recortar do vídeo original">
        <EditorRegioes
          quadro={corte.tem_quadro ? urls.quadroCorte(corte.id, corte.atualizado_em) : null}
          regioes={regioes}
          onChange={(id, r) =>
            onChange(
              {
                ...ed,
                layout:
                  id === 'jogo'
                    ? { ...lay, jogo: { ...lay.jogo, fonte: r } }
                    : { ...lay, webcam: lay.webcam ? { ...lay.webcam, fonte: r } : lay.webcam },
              },
              `recorte-${id}`,
            )
          }
          semQuadro={<p>Sem quadro do vídeo ainda.</p>}
        />
        {lay.webcam && !camConfirmada && (
          <div className="space-y-2 rounded-lg border border-amarelo/40 bg-amarelo/10 p-2 text-[11px]">
            <p>
              A posição do streamer não foi confirmada. Arraste o retângulo <b className="text-ciano">STREAMER</b> até a webcam (ou confirme):
              só assim o vídeo pode ser gerado. Nunca sai com a webcam errada.
            </p>
            <Button
              size="xs"
              variant="outline"
              onClick={() => onChange({ ...ed, layout: { ...lay, webcam: lay.webcam ? { ...lay.webcam, fonte: fontes.webcam ?? camPadrao } : null } })}
            >
              A posição está certa
            </Button>
          </div>
        )}
      </Secao>
    </div>
  )
}

// ------------------------------------------------------------------ Tempo

export function PainelTempo({ ed, base, selecionado, onSelecionar, onChange }: {
  ed: Edicao
  base: number
  selecionado: number | null
  onSelecionar: (k: number) => void
  onChange: Mudar
}) {
  return (
    <div className="space-y-4">
      <Secao titulo="Streamer e jogo">
        <div className="flex items-start justify-between gap-3 text-xs">
          <div>
            <Label className="flex items-center gap-2 text-xs">
              {ed.sincronizado ? <Link2 className="size-3.5 text-verde" /> : <Unlink2 className="size-3.5 text-amarelo" />} Manter sincronizados
            </Label>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Os dois vêm do mesmo vídeo: todo corte vale para os dois, então ficam sempre juntos. Desligue só se a câmera da live vier
              adiantada ou atrasada em relação ao jogo.
            </p>
          </div>
          <Switch checked={ed.sincronizado} onCheckedChange={(v) => onChange({ ...ed, sincronizado: v, atraso_streamer: v ? 0 : ed.atraso_streamer })} />
        </div>
        {!ed.sincronizado && (
          <Campo rotulo="Atraso do streamer" valor={`${ed.atraso_streamer > 0 ? '+' : ''}${ed.atraso_streamer.toFixed(2)} s`}>
            <Slider
              min={-3}
              max={3}
              step={0.05}
              value={[ed.atraso_streamer]}
              onValueChange={([v]) => onChange({ ...ed, atraso_streamer: Math.round(v * 100) / 100 }, 'atraso')}
            />
            <p className="text-[11px] text-muted-foreground">+ = o streamer aparece depois; − = antes.</p>
          </Campo>
        )}
      </Secao>

      <Secao titulo={`Trechos (${ed.segmentos.length})`}>
        <ol className="space-y-1.5">
          {ed.segmentos.map((s, k) => (
            <li key={k}>
              <button
                type="button"
                onClick={() => onSelecionar(k)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left font-mono text-xs transition-colors hover:border-roxo/50',
                  selecionado === k && 'border-rosa/60 bg-rosa/10',
                )}
              >
                <span className="font-bold text-rosa">{k + 1}</span>
                <span className="tabular-nums">
                  {fmtSeg(s.i)} → {fmtSeg(s.f)}
                </span>
                <span className="ml-auto text-muted-foreground tabular-nums">{fmtSeg(s.f - s.i)}</span>
              </button>
            </li>
          ))}
        </ol>
        <p className="text-[11px] text-muted-foreground">
          Tempos da live original. O vídeo baixado começa em {fmtSeg(base)}: puxe as pontas dos trechos na linha do tempo para aproveitar a
          folga.
        </p>
      </Secao>
    </div>
  )
}
