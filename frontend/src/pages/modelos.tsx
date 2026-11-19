import { Copy, LayoutTemplate, Save, Star, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { useAtualizarModelo, useCriarModelo, useModelos, usePlugins, useRemoverModelo, useStreamers } from '@/api/hooks/cortador'
import type { Modelo, ModeloIn, ModeloParams } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { Confirmar } from '@/components/confirmar'
import { SelectPlugin } from '@/components/form-streamer'
import { Previa } from '@/components/previa'
import { CardAprendizado } from '@/components/sinais'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'

const QUALQUER = '__qualquer__'

/** Slider de posição (fração 0..1 da altura do vídeo final), mostrando em %. */
function SliderPosicao({ rotulo, valor, onChange, min = 0, max = 1, dica }: {
  rotulo: string
  valor: number
  onChange: (v: number) => void
  min?: number
  max?: number
  dica?: string
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <Label>{rotulo}</Label>
        <span className="text-muted-foreground tabular-nums">{Math.round(valor * 100)}%</span>
      </div>
      <Slider min={min * 100} max={max * 100} step={0.5} value={[valor * 100]} onValueChange={([v]) => onChange(v / 100)} />
      {dica && <p className="text-xs text-muted-foreground">{dica}</p>}
    </div>
  )
}

function EditorModelo({ modelo, total }: { modelo: Modelo; total: number }) {
  const [d, setD] = useState<ModeloIn>({
    nome: modelo.nome,
    layout: modelo.layout,
    estilo_legenda: modelo.estilo_legenda,
    params: modelo.params,
    padrao: modelo.padrao,
  })
  const [fundo, setFundo] = useState<number | null>(null)
  const { data: plugins } = usePlugins()
  const { data: streamers = [] } = useStreamers()
  const atualizar = useAtualizarModelo()
  const remover = useRemoverModelo()
  const criar = useCriarModelo()

  const p: ModeloParams = d.params ?? { barra: true, credito: true }
  const setP = (x: Partial<ModeloParams>) => setD((v) => ({ ...v, params: { ...p, ...x } }))
  const opcoes = plugins?.layouts.find((l) => l.id === d.layout)?.opcoes ?? {}
  const divide = !!opcoes.usa_divisao
  const divisao = p.divisao ?? (d.layout === 'webcam_em_cima' ? 0.36 : 0.55)
  const legendaY = p.legenda_y ?? (divide ? divisao : 0.7)
  const alterado = JSON.stringify(d) !== JSON.stringify({ nome: modelo.nome, layout: modelo.layout, estilo_legenda: modelo.estilo_legenda, params: modelo.params, padrao: modelo.padrao })

  const posicoes = [
    { rotulo: 'Em cima', valor: 0.15 },
    { rotulo: divide ? 'No meio (na divisa)' : 'No meio', valor: divide ? divisao : 0.5 },
    { rotulo: 'Embaixo', valor: 0.85 },
  ]

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="nome-modelo">Nome</Label>
            <Input id="nome-modelo" value={d.nome} maxLength={100} onChange={(e) => setD({ ...d, nome: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label>Layout</Label>
            <SelectPlugin tipo="layouts" valor={d.layout} onChange={(v) => v && setD({ ...d, layout: v })} />
          </div>
          <div className="space-y-1.5">
            <Label>Estilo da legenda</Label>
            <SelectPlugin tipo="estilos" valor={d.estilo_legenda ?? 'destaque'} onChange={(v) => v && setD({ ...d, estilo_legenda: v })} />
          </div>
        </div>

        {divide && (
          <SliderPosicao
            rotulo={d.layout === 'webcam_em_cima' ? 'Altura da webcam (parte de cima)' : 'Altura do jogo (parte de cima)'}
            valor={divisao}
            min={0.2}
            max={0.8}
            onChange={(v) => setP({ divisao: v, ...(p.legenda_y === divisao && { legenda_y: v }) })}
            dica="O resto da altura fica com a outra parte. A legenda “no meio” acompanha a divisa."
          />
        )}

        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Label className="mr-2">Legenda</Label>
            {posicoes.map((x) => (
              <Button
                key={x.rotulo}
                type="button"
                size="sm"
                variant={Math.abs(legendaY - x.valor) < 0.005 ? 'default' : 'outline'}
                onClick={() => setP({ legenda_y: x.valor })}
              >
                {x.rotulo}
              </Button>
            ))}
          </div>
          <SliderPosicao rotulo="Posição da legenda (centro)" valor={legendaY} min={0.03} max={0.97} onChange={(v) => setP({ legenda_y: v })} />
        </div>

        <SliderPosicao
          rotulo="Posição do gancho (texto dos primeiros segundos)"
          valor={p.gancho_y ?? 0.05}
          max={0.9}
          onChange={(v) => setP({ gancho_y: v })}
        />

        <div className="flex flex-wrap gap-x-6 gap-y-3">
          {(
            [
              ['barra', 'Barra de progresso embaixo'],
              ['credito', 'Crédito do streamer (twitch.tv/...)'],
            ] as const
          ).map(([k, rotulo]) => (
            <div key={k} className="flex items-center gap-2">
              <Switch id={`m-${k}`} checked={p[k] ?? true} onCheckedChange={(v) => setP({ [k]: v })} />
              <Label htmlFor={`m-${k}`}>{rotulo}</Label>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <Switch id="m-padrao" checked={!!d.padrao} disabled={modelo.padrao} onCheckedChange={(v) => setD({ ...d, padrao: v })} />
            <Label htmlFor="m-padrao">Modelo padrão (streamers sem modelo usam este)</Label>
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-2 border-t pt-4">
          {!modelo.padrao && total > 1 && (
            <Confirmar
              titulo={`Remover “${modelo.nome}”?`}
              descricao="Streamers e cortes que usam este modelo voltam para o modelo padrão."
              confirmar="Remover"
              perigoso
              onConfirmar={() => remover.mutate(modelo.id)}
            >
              <Button variant="ghost">
                <Trash2 /> Remover
              </Button>
            </Confirmar>
          )}
          <Button variant="outline" disabled={criar.isPending} onClick={() => criar.mutate({ ...d, nome: `${d.nome} (cópia)`, padrao: false })}>
            <Copy /> Duplicar
          </Button>
          {alterado && (
            <Button variant="ghost" onClick={() => setD({ nome: modelo.nome, layout: modelo.layout, estilo_legenda: modelo.estilo_legenda, params: modelo.params, padrao: modelo.padrao })}>
              Desfazer
            </Button>
          )}
          <Button disabled={!alterado || !d.nome.trim() || atualizar.isPending} onClick={() => atualizar.mutate({ id: modelo.id, body: d })}>
            <Save /> Salvar
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <Previa
          pedido={{
            layout: d.layout,
            estilo_legenda: d.estilo_legenda,
            params: { ...p, divisao, legenda_y: legendaY },
            streamer_id: fundo,
            gancho: 'ELE NÃO ESPERAVA ISSO',
          }}
        />
        <Select value={fundo ? String(fundo) : QUALQUER} onValueChange={(v) => setFundo(v === QUALQUER ? null : Number(v))}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={QUALQUER}>Fundo: último quadro salvo</SelectItem>
            {streamers.map((s) => (
              <SelectItem key={s.id} value={String(s.id)}>
                Fundo: {s.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Prévia real (mesmo ffmpeg do corte). A posição da webcam vem do streamer escolhido; em cada corte você confere no
          enquadramento.
        </p>
      </div>
    </div>
  )
}

export function PaginaModelos() {
  const { data: modelos = [], isLoading } = useModelos()
  const [escolhido, setEscolhido] = useState<number | null>(null)
  const atual = modelos.find((m) => m.id === escolhido) ?? modelos.find((m) => m.padrao) ?? modelos[0]

  return (
    <>
      <Cabecalho
        titulo="Modelos de corte"
        descricao="Como o vertical é montado: onde fica o jogo, o streamer, a legenda e o gancho. Cada streamer usa um modelo (e cada corte pode trocar)."
      />
      {isLoading ? (
        <Skeleton className="h-96" />
      ) : !atual ? (
        <Vazio icone={<LayoutTemplate />} titulo="Nenhum modelo" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
          <div className="space-y-2">
            {modelos.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setEscolhido(m.id)}
                className={cn(
                  'w-full rounded-lg border p-3 text-left text-sm transition-colors hover:bg-muted/50',
                  m.id === atual.id && 'border-primary bg-muted/60',
                )}
              >
                <div className="flex items-center justify-between gap-2 font-medium">
                  <span className="truncate">{m.nome}</span>
                  {m.padrao && (
                    <Badge variant="secondary" className="shrink-0">
                      <Star className="size-3" /> padrão
                    </Badge>
                  )}
                </div>
              </button>
            ))}
          </div>
          <Card>
            <CardContent>
              <EditorModelo key={`${atual.id}-${JSON.stringify(atual)}`} modelo={atual} total={modelos.length} />
            </CardContent>
          </Card>
        </div>
      )}
      <div className="mt-4">
        <CardAprendizado />
      </div>
    </>
  )
}
