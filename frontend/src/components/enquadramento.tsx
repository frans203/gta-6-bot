import { AlertTriangle, Check, ScanFace } from 'lucide-react'

import { urls } from '@/api/cliente'
import { useEditarCorte, useEnquadrar, useModelos, usePlugins } from '@/api/hooks/cortador'
import type { Corte, Job, Regiao } from '@/api/tipos'
import { EditorRegioes, type RegiaoEditavel } from '@/components/editor-regioes'
import { ProgressoJob } from '@/components/job-progresso'
import { Previa } from '@/components/previa'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  CORES_REGIAO,
  jogoPadrao,
  modeloEfetivo,
  type RascunhoEnquadramento,
  soRegiao,
  WEBCAM_EXEMPLO,
} from '@/lib/enquadramento'

interface Props {
  corte: Corte
  /** rascunho do cartão (modelo, estilo, gancho, webcam, jogo ainda não salvos) */
  modeloId: number | null | undefined
  estilo: string | null | undefined
  gancho: string | null | undefined
  rascunho: RascunhoEnquadramento
  onChange: (r: RascunhoEnquadramento) => void
  job?: Job
  editavel: boolean
}

/**
 * Enquadramento de um corte: onde está o streamer (webcam) e, opcionalmente, que parte do quadro é o jogo.
 * Sem câmera no vídeo, o corte segue sem a parte do streamer. Só quando há uma câmera fixa mas a posição é
 * incerta o corte fica "marcar webcam" e é aqui que você recorta.
 */
export function Enquadramento({ corte, modeloId, estilo, gancho, rascunho, onChange, job, editavel }: Props) {
  const { data: modelos = [] } = useModelos()
  const { data: plugins } = usePlugins()
  const enquadrar = useEnquadrar()
  const editar = useEditarCorte()

  const modelo = modeloEfetivo(modelos, modeloId, corte)
  const opcoes = plugins?.layouts.find((l) => l.id === modelo?.layout)?.opcoes ?? {}
  const precisaWebcam = !!opcoes.precisa_webcam
  const usaJogo = !!opcoes.usa_jogo

  // o enquadramento concluiu que não há streamer neste trecho (e você ainda não marcou um à mão)
  const semStreamer = (corte.extra as { webcam?: string }).webcam === 'nenhuma' && !rascunho.webcam
  const webcam: Regiao | null =
    rascunho.webcam !== undefined
      ? rascunho.webcam
      : corte.webcam
        ? soRegiao(corte.webcam)
        : corte.streamer_webcam
          ? soRegiao(corte.streamer_webcam)
          : null
  const jogo: Regiao | null = rascunho.jogo !== undefined ? rascunho.jogo : corte.jogo ? soRegiao(corte.jogo) : null
  const webcamConfirmada = rascunho.webcam != null || corte.webcam?.origem === 'auto' || corte.webcam?.origem === 'manual'

  const regioes: RegiaoEditavel[] = []
  if (usaJogo && jogo) regioes.push({ id: 'jogo', rotulo: 'JOGO', cor: CORES_REGIAO.jogo, valor: jogo })
  if (precisaWebcam && !semStreamer) regioes.push({ id: 'webcam', rotulo: 'STREAMER', cor: CORES_REGIAO.webcam, valor: webcam ?? WEBCAM_EXEMPLO })

  const detectarDeNovo = () =>
    editar.mutate({ id: corte.id, body: { webcam: null } }, { onSuccess: () => enquadrar.mutate(corte.id) })

  return (
    <div className="space-y-3">
      {precisaWebcam && corte.status === 'enquadrar' && rascunho.webcam == null && (
        <div className="flex gap-2 rounded-md border border-amarelo/40 bg-amarelo/10 p-2.5 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amarelo" />
          <div>
            <p className="font-medium">Tem uma câmera do streamer, mas não tenho certeza da posição.</p>
            <p className="text-muted-foreground">
              Arraste o retângulo <b className="text-ciano">STREAMER</b> até a webcam (puxe o canto para o tamanho) e confira na
              prévia. Se não tiver streamer, clique em “Não tem streamer”.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              disabled={editar.isPending}
              onClick={() => editar.mutate({ id: corte.id, body: { sem_webcam: true } })}
            >
              Não tem streamer neste corte
            </Button>
          </div>
        </div>
      )}
      {precisaWebcam && semStreamer && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>Sem câmera do streamer neste trecho: o corte sai só com o jogo (fundo desfocado ou a sua imagem).</span>
          {editavel && corte.tem_quadro && (
            <Button size="sm" variant="ghost" onClick={() => onChange({ ...rascunho, webcam: corte.streamer_webcam ? soRegiao(corte.streamer_webcam) : WEBCAM_EXEMPLO })}>
              Tem streamer sim: marcar
            </Button>
          )}
        </div>
      )}
      {precisaWebcam && corte.webcam?.origem === 'auto' && rascunho.webcam === undefined && (
        <p className="flex items-center gap-1.5 text-xs text-verde">
          <Check className="size-3.5" /> Streamer identificado automaticamente
          {corte.webcam.confianca != null && ` (rosto em ${Math.round(corte.webcam.confianca * 100)}% das amostras)`}. Confira na prévia.
        </p>
      )}

      {job && (
        <div className="flex items-center gap-3 rounded-xl border border-roxo/40 bg-roxo/10 p-3">
          <ScanFace className="size-5 shrink-0 animate-pulse text-rosa" />
          <ProgressoJob job={job} className="flex-1" />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_180px]">
        <div className="space-y-3">
          <div className={job ? 'pointer-events-none opacity-50 transition-opacity' : 'transition-opacity'}>
          <EditorRegioes
            quadro={corte.tem_quadro ? urls.quadroCorte(corte.id, corte.atualizado_em) : null}
            regioes={editavel && corte.tem_quadro ? regioes : []}
            onChange={(id, r) => onChange({ ...rascunho, [id]: r })}
            semQuadro={
              <div className="space-y-2">
                <p>Ainda não baixei este trecho. “Enquadrar” baixa o trecho, procura o streamer e mostra o quadro aqui.</p>
                <Button size="sm" variant="outline" disabled={enquadrar.isPending || !!job} onClick={() => enquadrar.mutate(corte.id)}>
                  <ScanFace /> Enquadrar
                </Button>
              </div>
            }
          />
          </div>
          {editavel && corte.tem_quadro && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              {usaJogo && (
                <div className="flex items-center gap-2">
                  <Switch
                    id={`jogo-${corte.id}`}
                    checked={!!jogo}
                    onCheckedChange={(v) => onChange({ ...rascunho, jogo: v ? jogoPadrao(modelo) : null })}
                  />
                  <Label htmlFor={`jogo-${corte.id}`} className="text-xs">
                    Escolher a área do jogo (senão, recorte central)
                  </Label>
                </div>
              )}
              <div className="ml-auto flex gap-2">
                {precisaWebcam && !webcamConfirmada && !semStreamer && (
                  <Button size="sm" variant="outline" onClick={() => onChange({ ...rascunho, webcam: webcam ?? WEBCAM_EXEMPLO })}>
                    <Check /> A posição está certa
                  </Button>
                )}
                {precisaWebcam && !job && (
                  <Button size="sm" variant="outline" disabled={enquadrar.isPending || editar.isPending} onClick={detectarDeNovo}>
                    <ScanFace /> Detectar de novo
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
        <Previa
          className="max-w-[180px]"
          pedido={
            modelo && corte.tem_quadro
              ? {
                  corte_id: corte.id,
                  modelo_id: modelo.id,
                  estilo_legenda: estilo ?? null,
                  gancho: gancho ?? null,
                  webcam: precisaWebcam && !semStreamer ? (webcam ?? WEBCAM_EXEMPLO) : null,
                  jogo,
                }
              : null
          }
        />
      </div>
    </div>
  )
}
