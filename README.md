# Ayeneh

> A production-grade monorepo.

## Structure

```
Ayeneh/
├── apps/
│   ├── api/          # API server
│   ├── web/          # Web application
│   └── worker/       # Background worker
├── packages/
│   ├── agents/       # Agent orchestration
│   ├── memory/       # Memory storage
│   ├── rag/          # Retrieval-augmented generation
│   ├── patterns/     # Pattern detection
│   ├── reflections/  # Reflection logic
│   ├── prompts/      # Prompt management
│   ├── models/       # Shared data models
│   └── common/       # Shared utilities
├── docs/             # Documentation
├── infra/            # Infrastructure configs
├── docker/           # Docker files
└── data/             # Runtime data
```

## Prerequisites

- **Node.js** >= 20
- **pnpm** >= 9

## Getting started

```bash
pnpm install
pnpm dev
```

## Scripts

| Command          | Description              |
| ---------------- | ------------------------ |
| `pnpm build`     | Build all packages       |
| `pnpm dev`       | Run all in dev mode      |
| `pnpm lint`      | Lint all packages        |
| `pnpm clean`     | Clean build artifacts    |
| `pnpm format`    | Check code formatting    |
