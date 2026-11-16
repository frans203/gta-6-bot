# JASON · frontend

Vite + React 19 + TypeScript + Tailwind v4 + shadcn/ui (radix) + TanStack Query + React Router.

```powershell
npm install
npm run dev          # http://localhost:5173 (proxy /api -> http://127.0.0.1:8765; rode `python jason.py web` junto)
npm run build        # gera dist/, servido pelo FastAPI em `python jason.py web`
npm run lint         # oxlint
npm run typecheck    # tsc
npm run api:tipos    # regenera src/api/schema.d.ts a partir de openapi.json
npm run api:tipos:vivo  # idem, direto do backend rodando (http://127.0.0.1:8765/openapi.json)
```

Atualizar o `openapi.json` depois de mudar a API:
`cd backend; python -c "import json; from app.api.main import app; open('../frontend/openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=1))"`

## Estrutura

```
src/
  api/        cliente.ts (openapi-fetch tipado), schema.d.ts (gerado), tipos.ts (aliases), chaves.ts (query keys),
              eventos.ts (SSE /api/eventos -> cache + toasts + log ao vivo), hooks/*.ts (um arquivo por recurso)
  components/ ui/ (shadcn, gerado: `npx shadcn@latest add <nome>`), layout, status-chip, job-progresso,
              players (9:16 e embed da fonte), webcam-editor, form-streamer, dialogo-postar, confirmar...
  lib/        formatos (datas/tempos pt-BR), status (cores/rótulos), conta (conta global), embed (URLs de player)
  pages/      painel, fila, agenda, cortador, streamer, cortes, jobs, logs, contas
  rotas.tsx   rotas (lazy por página)
```

Página nova: arquivo em `src/pages/`, uma linha em `src/rotas.tsx` e um item no `MENU` de `components/layout.tsx`.
Tipo novo de job: acrescente o que invalidar em `INVALIDAR_POR_TIPO` (`src/api/eventos.ts`).
