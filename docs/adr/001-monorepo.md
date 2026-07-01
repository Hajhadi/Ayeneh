# Use pnpm Workspaces Monorepo

## Status

Accepted

## Context

Ayeneh consists of multiple applications (API, web frontend, background worker) and shared libraries (agents, memory, RAG, patterns, models, etc.). Without a monorepo structure, each component would require independent versioning, publishing, and dependency management, leading to coordination overhead and drift between compatible versions. The project needs a single-source-of-truth repository that allows atomic cross-component changes and consistent builds.

## Decision

Use pnpm workspaces to organize the codebase as a monorepo. All applications live under `apps/` and all shared libraries under `packages/`. The root `package.json` is private and serves only orchestration scripts. Each package and app declares its own dependencies and is built independently through pnpm's dependency isolation.

## Consequences

### Positive
- Atomic commits across applications and packages.
- Single version of truth for shared dependencies via the lockfile.
- pnpm's strict dependency isolation prevents accidental use of undeclared dependencies.
- Fast installs with pnpm's content-addressable store.

### Negative
- Increased root-level complexity in CI and tooling configuration.
- All consumers must use pnpm (not npm or yarn).
- Build orchestration requires additional tooling for dependency graph awareness.

## Alternatives Considered

- **npm workspaces**: Rejected due to looser dependency isolation and slower install times.
- **Yarn workspaces**: Rejected — comparable to pnpm but with less strict isolation and larger lockfiles.
- **Multi-repo**: Rejected — would introduce versioning friction, duplicated CI, and cross-repo coordination overhead for a project with many interdependencies.
- **Turborepo without pnpm workspaces**: Rejected — Turborepo is a build orchestrator, not a package manager; it complements pnpm workspaces rather than replacing them.
