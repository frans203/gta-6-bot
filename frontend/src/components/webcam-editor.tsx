import { useState } from 'react'

import type { Regiao, Webcam } from '@/api/tipos'
import { EditorRegioes } from '@/components/editor-regioes'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { CORES_REGIAO, WEBCAM_EXEMPLO, normalizarRegiao } from '@/lib/enquadramento'

interface Props {
  quadro: string | null
  valor: Webcam | null | undefined
  salvando?: boolean
  onSalvar: (w: Regiao) => void
}

/** Webcam padrão do streamer (sugestão inicial no enquadramento de cada corte). */
export function WebcamEditor({ quadro, valor, salvando, onSalvar }: Props) {
  const [rascunho, setRascunho] = useState<Regiao | null>(null)
  const atual = rascunho ?? (valor ? { x: valor.x, y: valor.y, w: valor.w, h: valor.h } : WEBCAM_EXEMPLO)
  const alterado = rascunho !== null

  const slider = (campo: keyof Regiao, rotulo: string) => (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <Label>{rotulo}</Label>
        <span className="text-muted-foreground tabular-nums">{Math.round(atual[campo] * 100)}%</span>
      </div>
      <Slider
        min={0}
        max={100}
        step={0.5}
        value={[atual[campo] * 100]}
        onValueChange={([v]) => setRascunho(normalizarRegiao({ ...atual, [campo]: v / 100 }))}
      />
    </div>
  )

  return (
    <div className="space-y-4">
      <EditorRegioes
        quadro={quadro}
        regioes={[{ id: 'webcam', rotulo: 'WEBCAM', cor: CORES_REGIAO.webcam, valor: atual }]}
        onChange={(_, r) => setRascunho(r)}
        semQuadro="Sem quadro de referência ainda. Rode “Detectar webcam” (ou renderize um corte) para ver a imagem aqui."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {slider('x', 'Esquerda (x)')}
        {slider('y', 'Topo (y)')}
        {slider('w', 'Largura')}
        {slider('h', 'Altura')}
      </div>
      <div className="flex justify-end gap-2">
        {alterado && (
          <Button variant="ghost" onClick={() => setRascunho(null)}>
            Desfazer
          </Button>
        )}
        <Button
          disabled={(!alterado && !!valor) || salvando}
          onClick={() => {
            onSalvar(atual)
            setRascunho(null)
          }}
        >
          Salvar posição da webcam
        </Button>
      </div>
    </div>
  )
}
