# Music-Assist Frontend

React + TypeScript frontend for the Music-Assist RAG chatbot, backed by the
FastAPI service in `../backend`.

## Run locally

**Prerequisites:** Node (see `.node-version`)

```bash
npm install
cp .env.example .env.development   # fill in Firebase web config (see firebase.ts)
npm run dev
```

Make sure the FastAPI backend is running on `http://127.0.0.1:8080` (see
`../backend/README.md`) - `VITE_API_BASE_URL` in `.env.development` points at
it. The app is served at `http://localhost:3000` (or another port if 3000 is
in use).

## Testing & checks

```bash
npm run typecheck   # tsc --noEmit
npm run test         # vitest
npm run build        # production build (vite build)
```

## Architecture

- React 19 + TypeScript, Vite, Tailwind CSS.
- `App.tsx` composes `hooks/` (`useAuth`, `useChat`, `useConversationHistory`)
  with presentational components (`Sidebar`, `ChatHeader`, `EmptyState`,
  `ChatMessage`, `AudioPlayer`); `ErrorBoundary` wraps the tree in `index.tsx`.
- `services/apiService.ts` talks to the FastAPI backend (`chat`/`chat/stream`,
  `conversations/*`) - see `constants.ts` for how `API_BASE_URL` resolves.
- `firebase.ts` configures Firebase Auth (Google sign-in) for `useAuth`.
- Deployed as a static site via Firebase Hosting (`../firebase.json`) - the
  backend is deployed separately (Render).
