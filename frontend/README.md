# CASSANDRA - Frontend

React + TypeScript + Vite SPA. See the root README for full project documentation.

## Dev

```bash
npm install
npm run dev
```

Requires `frontend/.env.local`:

```
VITE_CASSANDRA_ADDRESS=0xaa7F8f52228B6001DbC276397B4519F3EA05FFB0
VITE_GENLAYER_RPC=https://studio.genlayer.com/api
VITE_GENLAYER_CHAIN_ID=61999
```

## Build

```bash
npm run build
```

Output goes to `dist/`. Deployed automatically to Vercel on push to `main`.
