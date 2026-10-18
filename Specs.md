# Architecture

```mermaid
flowchart LR
  A[School Config] --> B[Platform Adapter] --> DB[(School Info DB)]
  E[Enrichers] --> G[Deterministic Enricher: Grade dist, RMP raw ratings]
  E ---> NLE[Natural language Enricher: RMP comments, Reddit posts, etc...]
  G --> DB
  NLE --> F[LLM Feature Extraction] --> DB
  P[Audit + NL Prefs] --> L[LLM Parsing] --> U[User Confirms] --> R[Requirements/Preferences]
  DB --> S[Solver CP-SAT]
  R --> S --> K[LLM Rerank] --> O[Schedules + CRNs]
```

