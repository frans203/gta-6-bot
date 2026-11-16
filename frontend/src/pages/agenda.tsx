import { CalendarCheck, Eye } from 'lucide-react'
import { useState } from 'react'

import { type FiltrosPlano, useAgendar, useHorarios, usePlano, usePosts, useSalvarHorarios, useTarefasWindows } from '@/api/hooks/postagem'
import type { Conta, Grade, Plataforma as P } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { Confirmar } from '@/components/confirmar'
import { EscolherPlataformas } from '@/components/escolher-plataformas'
import { Plataforma } from '@/components/plataforma'
import { StatusChip } from '@/components/status-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useConta } from '@/lib/conta'
import { agruparPorDia, fmtDataHora, fmtDia, fmtHora } from '@/lib/formatos'

function MontarLote({ conta }: { conta: Conta }) {
  const [plats, setPlats] = useState<P[]>(conta.plataformas as P[])
  const [porHora, setPorHora] = useState('')
  const [ate, setAte] = useState('')
  const [filtros, setFiltros] = useState<FiltrosPlano | null>(null)
  const { data: plano = [], isFetching } = usePlano(conta.id, filtros ?? {}, !!filtros)
  const agendar = useAgendar(conta.id)

  const montar = () =>
    setFiltros({ plataformas: plats, por_hora: porHora ? Number(porHora) : null, ate: porHora || ate ? ate || '00:00' : null })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Montar lote</CardTitle>
          <CardDescription>
            Sem “por hora”, usa a grade de melhores horários (até ~5/dia por plataforma). Com “por hora”, espalha N posts em cada
            hora até o limite (minutos múltiplos de 5, exigência do TikTok). O que não couber continua pendente.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <EscolherPlataformas valor={plats} onChange={setPlats} disponiveis={conta.plataformas} />
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="por-hora">Posts por hora (opcional)</Label>
              <Input id="por-hora" type="number" min={1} max={12} placeholder="grade" value={porHora} onChange={(e) => setPorHora(e.target.value)} className="w-32" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ate">Até (HH:MM)</Label>
              <Input id="ate" type="time" value={ate} onChange={(e) => setAte(e.target.value)} className="w-32" />
            </div>
            <Button variant="outline" onClick={montar} disabled={!plats.length}>
              <Eye /> Ver plano
            </Button>
          </div>
        </CardContent>
      </Card>

      {filtros && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle>Prévia: {plano.length} post(s)</CardTitle>
              <CardDescription>Nada é enviado até você confirmar.</CardDescription>
            </div>
            <Confirmar
              titulo={`Agendar ${plano.length} post(s)?`}
              descricao={
                <>
                  O lote abre o Chrome do script e agenda de verdade na conta <b>{conta.nome}</b>. Instagram vai para o Agendador do
                  Windows (o PC precisa estar ligado no horário). Demora: acompanhe em Jobs.
                </>
              }
              confirmar="Agendar"
              onConfirmar={() => agendar.mutate({ plataformas: filtros.plataformas as P[], por_hora: filtros.por_hora, ate: filtros.ate })}
            >
              <Button disabled={!plano.length || agendar.isPending}>
                <CalendarCheck /> Agendar
              </Button>
            </Confirmar>
          </CardHeader>
          <CardContent>
            {isFetching ? (
              <Skeleton className="h-40" />
            ) : !plano.length ? (
              <p className="text-sm text-muted-foreground">Nada pendente: tudo postado ou agendado.</p>
            ) : (
              <div className="space-y-5">
                {agruparPorDia(plano, (x) => x.quando).map(([dia, itens]) => (
                  <div key={dia}>
                    <h3 className="mb-2 text-sm font-semibold capitalize text-laranja">{fmtDia(itens[0].quando)}</h3>
                    <div className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
                      {itens.map((x) => (
                        <div key={`${x.plataforma}${x.video}${x.quando}`} className="flex items-center gap-2 rounded-md border bg-background/40 px-2.5 py-1.5 text-sm">
                          <span className="font-semibold tabular-nums">{fmtHora(x.quando)}</span>
                          <Plataforma p={x.plataforma} soIcone />
                          <span className="min-w-0 flex-1 truncate">{x.video}</span>
                          {x.como === 'windows' && <Badge variant="outline" className="text-laranja">PC</Badge>}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function Agendados({ conta }: { conta: Conta }) {
  const [hoje] = useState(() => new Date().toISOString().slice(0, 10))
  const { data: posts = [], isLoading } = usePosts({ conta_id: conta.id, status: 'agendado,agendado_pc', de: hoje, limite: 2000 })
  const ordenados = [...posts].filter((p) => p.para).sort((a, b) => a.para!.localeCompare(b.para!))
  if (isLoading) return <Skeleton className="h-64" />
  if (!ordenados.length) return <Vazio icone={<CalendarCheck />} titulo="Nada agendado de hoje em diante" />
  return (
    <div className="space-y-5">
      {agruparPorDia(ordenados, (p) => p.para!).map(([dia, itens]) => (
        <Card key={dia} size="sm">
          <CardHeader>
            <CardTitle className="capitalize">
              {fmtDia(itens[0].para!)} <span className="text-muted-foreground">· {itens.length}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {itens.map((p) => (
              <div key={p.id} className="flex items-center gap-3 text-sm">
                <span className="w-12 font-semibold tabular-nums">{fmtHora(p.para)}</span>
                <Plataforma p={p.plataforma} />
                <span className="min-w-0 flex-1 truncate">{p.video}</span>
                <StatusChip status={p.status} />
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function TarefasWindows() {
  const { data = [], isLoading } = useTarefasWindows()
  if (isLoading) return <Skeleton className="h-40" />
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agendador do Windows (\JASON_GTAVI\)</CardTitle>
        <CardDescription>Posts do Instagram agendados no PC. Rodam sozinhos se o PC estiver ligado no horário.</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tarefa</TableHead>
              <TableHead>Próxima execução</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((t) => (
              <TableRow key={t.nome}>
                <TableCell className="font-medium">{t.nome}</TableCell>
                <TableCell className="tabular-nums">{t.proxima ? fmtDataHora(t.proxima) : '—'}</TableCell>
                <TableCell>{t.estado}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

const lerHorarios = (t: string) =>
  t
    .split(/[,\s]+/)
    .map((x) => x.trim())
    .filter((x) => /^\d{1,2}:\d{2}$/.test(x))
    .map((x) => x.padStart(5, '0'))

function EditorGrade() {
  const { data, isLoading } = useHorarios()
  if (isLoading || !data) return <Skeleton className="h-40" />
  return <FormGrade inicial={data} />
}

function FormGrade({ inicial }: { inicial: Record<string, Grade> }) {
  const [texto, setTexto] = useState(() =>
    Object.fromEntries(Object.entries(inicial).map(([p, g]) => [p, { semana: g.semana.join(', '), fimdesemana: g.fimdesemana.join(', ') }])),
  )
  const salvar = useSalvarHorarios()
  return (
    <Card>
      <CardHeader>
        <CardTitle>Grade de melhores horários</CardTitle>
        <CardDescription>Horários (HH:MM) separados por vírgula. Usada quando o lote não tem “por hora”.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(texto).map(([p, g]) => (
          <div key={p} className="grid gap-3 sm:grid-cols-[140px_1fr_1fr] sm:items-center">
            <Plataforma p={p} />
            <Input value={g.semana} aria-label={`${p} dias úteis`} onChange={(e) => setTexto({ ...texto, [p]: { ...g, semana: e.target.value } })} />
            <Input value={g.fimdesemana} aria-label={`${p} fim de semana`} onChange={(e) => setTexto({ ...texto, [p]: { ...g, fimdesemana: e.target.value } })} />
          </div>
        ))}
        <div className="hidden text-xs text-muted-foreground sm:grid sm:grid-cols-[140px_1fr_1fr]">
          <span />
          <span>dias úteis</span>
          <span>fim de semana</span>
        </div>
        <div className="flex justify-end">
          <Button
            disabled={salvar.isPending}
            onClick={() =>
              salvar.mutate(
                Object.fromEntries(Object.entries(texto).map(([p, g]) => [p, { semana: lerHorarios(g.semana), fimdesemana: lerHorarios(g.fimdesemana) }])),
              )
            }
          >
            Salvar grade
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function PaginaAgenda() {
  const { conta } = useConta()
  if (!conta) return <Skeleton className="h-64" />
  return (
    <>
      <Cabecalho titulo="Agenda" descricao={`Agendamentos da conta ${conta.nome}.`} />
      <Tabs defaultValue="lote">
        <TabsList className="mb-4 flex-wrap">
          <TabsTrigger value="lote">Montar lote</TabsTrigger>
          <TabsTrigger value="agendados">Agendados</TabsTrigger>
          <TabsTrigger value="grade">Grade de horários</TabsTrigger>
          <TabsTrigger value="windows">Tarefas do Windows</TabsTrigger>
        </TabsList>
        <TabsContent value="lote">
          <MontarLote key={conta.id} conta={conta} />
        </TabsContent>
        <TabsContent value="agendados">
          <Agendados conta={conta} />
        </TabsContent>
        <TabsContent value="grade">
          <EditorGrade />
        </TabsContent>
        <TabsContent value="windows">
          <TarefasWindows />
        </TabsContent>
      </Tabs>
    </>
  )
}
