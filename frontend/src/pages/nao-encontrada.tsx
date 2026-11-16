import { Link } from 'react-router'

import { Vazio } from '@/components/cabecalho'

export function NaoEncontrada() {
  return (
    <Vazio titulo="Página não encontrada">
      <Link to="/" className="text-ciano hover:underline">
        Voltar ao painel
      </Link>
    </Vazio>
  )
}
