import { Image } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { urls } from '@/api/cliente'
import { useLogAoVivo } from '@/api/eventos'
import { useLogs, usePrints } from '@/api/hooks/jobs'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

function corLinha(l: string) {
  if (/erro|error|falhou|timeout/i.test(l)) return 'text-destructive'
  if (/publicado|agendado|: ok|pronto/i.test(l)) return 'text-verde'
  if (/\[worker\]/.test(l)) return 'text-roxo'
  return 'text-foreground/85'
}

function LogAoVivo() {
  const { data: iniciais = [], isLoading } = useLogs(400)
  const aoVivo = useLogAoVivo()
  const [filtro, setFiltro] = useState('')
  const fim = useRef<HTMLDivElement>(null)
  const linhas = useMemo(() => {
    const todas = [...iniciais, ...aoVivo]
    return filtro ? todas.filter((l) => l.toLowerCase().includes(filtro.toLowerCase())) : todas
  }, [iniciais, aoVivo, filtro])

  useEffect(() => {
    fim.current?.scrollIntoView({ block: 'end' })
  }, [linhas.length])

  if (isLoading) return <Skeleton className="h-96" />
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>logs/postar.log</CardTitle>
        <Input placeholder="Filtrar..." value={filtro} onChange={(e) => setFiltro(e.target.value)} className="max-w-60" />
      </CardHeader>
      <CardContent>
        <div className="h-[65svh] overflow-y-auto rounded-md border bg-black/50 p-3 font-mono text-xs leading-relaxed">
          {linhas.map((l, i) => (
            <div key={i} className={cn('whitespace-pre-wrap', corLinha(l))}>
              {l}
            </div>
          ))}
          <div ref={fim} />
        </div>
      </CardContent>
    </Card>
  )
}

function Prints() {
  const { data: prints = [], isLoading } = usePrints()
  if (isLoading) return <Skeleton className="h-64" />
  if (!prints.length) return <Vazio icone={<Image />} titulo="Nenhum print ainda" />
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {prints.map((p) => (
        <a key={p} href={urls.print(p)} target="_blank" rel="noreferrer" className="group overflow-hidden rounded-lg border bg-card">
          <img src={urls.print(p)} alt={p} loading="lazy" className="aspect-video w-full object-cover object-top transition-transform group-hover:scale-105" />
          <div className={cn('truncate px-2 py-1.5 text-xs', p.startsWith('erro') ? 'text-destructive' : 'text-verde')}>{p}</div>
        </a>
      ))}
    </div>
  )
}

export function PaginaLogs() {
  return (
    <>
      <Cabecalho titulo="Logs" descricao="Log ao vivo da postagem e prints das telas (erros e sucessos)." />
      <Tabs defaultValue="log">
        <TabsList className="mb-4">
          <TabsTrigger value="log">Log ao vivo</TabsTrigger>
          <TabsTrigger value="prints">Prints</TabsTrigger>
        </TabsList>
        <TabsContent value="log">
          <LogAoVivo />
        </TabsContent>
        <TabsContent value="prints">
          <Prints />
        </TabsContent>
      </Tabs>
    </>
  )
}
