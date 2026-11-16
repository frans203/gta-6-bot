import { useState } from 'react'

import { usePlugins } from '@/api/hooks/cortador'
import type { StreamerIn } from '@/api/tipos'
import { SelectModelo } from '@/components/previa'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useConta } from '@/lib/conta'

export type DadosStreamer = StreamerIn

const SEM_CONTA = '__nenhuma__'
const PADRAO = '__padrao__'

function Campo({ id, rotulo, children, dica }: { id?: string; rotulo: string; children: React.ReactNode; dica?: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{rotulo}</Label>
      {children}
      {dica && <p className="text-xs text-muted-foreground">{dica}</p>}
    </div>
  )
}

/** Escolha de um plugin (layout/estilo) vindo de /api/plugins, com a descrição embaixo. */
export function SelectPlugin({
  tipo,
  valor,
  onChange,
  id,
  rotuloPadrao,
}: {
  tipo: 'layouts' | 'estilos'
  valor: string | null
  onChange: (v: string | null) => void
  id?: string
  /** Se informado, oferece a opção "usar o padrão" (valor null). */
  rotuloPadrao?: string
}) {
  const { data } = usePlugins()
  const itens = data?.[tipo] ?? []
  const atual = itens.find((p) => p.id === valor)
  return (
    <div className="space-y-1">
      <Select value={valor ?? PADRAO} onValueChange={(v) => onChange(v === PADRAO ? null : v)}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder="Escolha..." />
        </SelectTrigger>
        <SelectContent>
          {rotuloPadrao && <SelectItem value={PADRAO}>{rotuloPadrao}</SelectItem>}
          {itens.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.nome}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {atual && <p className="text-xs text-muted-foreground">{atual.descricao}</p>}
    </div>
  )
}

/** Formulário de streamer, usado para criar e editar. `bloquearPlataforma` na edição (o canal é da plataforma). */
export function FormStreamer({
  inicial,
  bloquearPlataforma,
  enviando,
  rotuloEnviar,
  onEnviar,
}: {
  inicial?: Partial<DadosStreamer>
  bloquearPlataforma?: boolean
  enviando?: boolean
  rotuloEnviar: string
  onEnviar: (d: DadosStreamer) => void
}) {
  const { contas } = useConta()
  const [d, setD] = useState<DadosStreamer>({
    nome: '',
    plataforma: 'twitch',
    canal: '',
    idioma: 'pt',
    conta_id: null,
    modelo_id: null,
    campanha_url: null,
    notas: null,
    ...inicial,
  })
  const set = <K extends keyof DadosStreamer>(k: K, v: DadosStreamer[K]) => setD((x) => ({ ...x, [k]: v }))

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        onEnviar(d)
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="nome" rotulo="Nome">
          <Input id="nome" required value={d.nome} onChange={(e) => set('nome', e.target.value)} placeholder="alanzoka" />
        </Campo>
        <Campo rotulo="Plataforma">
          <Select value={d.plataforma} onValueChange={(v) => set('plataforma', v as DadosStreamer['plataforma'])} disabled={bloquearPlataforma}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="twitch">Twitch</SelectItem>
              <SelectItem value="youtube">YouTube</SelectItem>
            </SelectContent>
          </Select>
        </Campo>
        <Campo id="canal" rotulo="Canal ou URL" dica={d.plataforma === 'twitch' ? 'ex.: alanzoka ou twitch.tv/alanzoka' : 'ex.: @IShowSpeed ou a URL do canal'}>
          <Input id="canal" required value={d.canal} onChange={(e) => set('canal', e.target.value)} />
        </Campo>
        <Campo rotulo="Idioma da live" dica="Usado na transcrição (legendas).">
          <Select value={d.idioma ?? 'pt'} onValueChange={(v) => set('idioma', v as DadosStreamer['idioma'])}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pt">Português</SelectItem>
              <SelectItem value="en">Inglês</SelectItem>
              <SelectItem value="es">Espanhol</SelectItem>
            </SelectContent>
          </Select>
        </Campo>
        <Campo rotulo="Conta de destino" dica="Para qual fila os cortes vão.">
          <Select value={d.conta_id ?? SEM_CONTA} onValueChange={(v) => set('conta_id', v === SEM_CONTA ? null : v)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={SEM_CONTA}>(escolher depois)</SelectItem>
              {contas.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>
        <Campo id="campanha" rotulo="URL da campanha de clipping (opcional)">
          <Input id="campanha" value={d.campanha_url ?? ''} onChange={(e) => set('campanha_url', e.target.value || null)} placeholder="https://whop.com/..." />
        </Campo>
        <Campo id="modelo" rotulo="Modelo de corte" dica="Como os cortes deste streamer são montados (página Modelos).">
          <SelectModelo id="modelo" valor={d.modelo_id} rotuloPadrao="O modelo padrão" onChange={(v) => set('modelo_id', v)} />
        </Campo>
      </div>
      <Campo id="notas" rotulo="Notas">
        <Textarea id="notas" rows={2} value={d.notas ?? ''} onChange={(e) => set('notas', e.target.value || null)} placeholder="ex.: libera cortes, pede crédito no título" />
      </Campo>
      <div className="flex justify-end">
        <Button type="submit" disabled={enviando || !d.nome.trim() || !d.canal.trim()}>
          {rotuloEnviar}
        </Button>
      </div>
    </form>
  )
}
