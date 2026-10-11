# Voyara — Frontend (micro-frontends)

Workspace npm : deux applications indépendantes + packages partagés.

```text
apps/
├── client/   → http://localhost:5173        site touriste NEXT.JS (SSR/SEO)
└── admin/    → http://localhost:5174/admin  espace administrateur
packages/
├── ui/       @voyara/ui     design system (thème, composants)
├── api/      @voyara/api    axios, endpoints, query-client
├── auth/     @voyara/auth   store, AuthProvider, guards
└── i18n/     @voyara/i18n   fr / en / ar (+ RTL)
```

## Commandes

```powershell
npm install            # une seule fois, à la racine de frontend/
npm run dev            # démarre client + admin ensemble
npm run dev:client     # seulement le client (5173)
npm run dev:admin      # seulement l'admin (5174)
npm run build          # build des deux apps
npm run typecheck      # tsc strict sur les deux apps (+ packages)
npm run test           # vitest (app client)
```

Le backend doit tourner sur `http://localhost:8000` (gateway) — voir le README racine.

## Production

Deux images : `Dockerfile.client` (Next standalone, SSR) et `Dockerfile`
(admin statique + nginx). nginx expose **une seule origine** (port 8080) :
`/` → client Next, `/admin/` → admin, `/api` → gateway.

SEO : rendu serveur du catalogue, `generateMetadata`, sitemap/robots générés,
JSON-LD par activité, pages détail pré-générées (ISR 60 s).
