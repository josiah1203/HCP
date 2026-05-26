# HCP Web UI

React 18 + TypeScript 5 + Vite 5 + Tailwind. Four views: Dashboard, Project Tree, Object Detail, Search.

## Prerequisites

- API running at `http://localhost:8000`
- Node.js 18+

## Dev server

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/v1` and `/health` to the API.

Optional: set `VITE_API_URL=http://localhost:8000` if not using the proxy.

## Build

```bash
npm run build
npm run preview
```

Check bundle size:

```bash
gzip -c dist/assets/index-*.js | wc -c
```

Target: initial JS &lt; 500KB gzipped (D3 is code-split).

## Auth

JWT access token is held in memory only (not localStorage). Sign in with a user from your dev database.
