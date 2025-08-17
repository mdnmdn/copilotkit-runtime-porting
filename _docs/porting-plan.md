## CopilotRuntime Python Port – Phased Plan

### Overview
This plan delivers a Python port of CopilotRuntime that exposes a GraphQL endpoint via FastAPI and bridges to Python agent frameworks starting with LangGraph. It aligns with `_docs/agents.md` and CopilotKit architecture/agent development rules. Python package management uses `uv`.

### Rule Alignment
- Architecture: mirrors `CopilotKit/packages/runtime` GraphQL contract and semantics.
- Agent development: follows patterns from `sdk-python/` and examples.
- Suggestions system is out-of-scope for backend; ensure endpoint parity for frontend consumers.
- Package manager: use `uv` for Python env and dependencies.

---

## Phase 0 — Bootstrap and Alignment
Goal: Establish foundations and ensure contract parity.

Tasks
- Extract a frozen snapshot of the TS GraphQL schema and operations (queries/mutation, message/meta-event unions).
- Decide GraphQL library (prefer Strawberry) and streaming strategy (SSE/multipart first).
- Create Python runtime package layout under `sdk-python/copilotkit/runtime_py/` (see `_docs/agents.md`).
- Tooling setup with `uv`: ruff, black, mypy, pytest, uvicorn, httpx, strawberry-graphql, fastapi, sse-starlette.
- Document dev workflow in README and `_docs/agents.md` (confirm “Use uv”).

Deliverables
- Scaffolding for FastAPI app and GraphQL schema files.
- Dev environment working with `uv` and basic scripts.

Acceptance Criteria
- App starts: `uvicorn copilotkit.runtime_py.app.main:app --reload`.
- GraphQL playground loads at configured path.

---

## Phase 1 — GraphQL Schema and Endpoint (MVP, non-streaming)
Goal: Implement schema/types and resolvers returning static or stubbed data.

Tasks
- Define inputs/types: `GenerateCopilotResponseInput`, message unions, enums, `AgentsResponse`, `LoadAgentStateResponse`, meta-events.
- Implement resolvers: `hello`, `availableAgents` (static list), `loadAgentState` (in-memory), `generateCopilotResponse` (stubbed single-turn response).
- Implement request context (properties, headers, logger) and mount on FastAPI at `/api/copilotkit`.
- Add conversion helpers (GQL <-> internal models) with unit tests.

Deliverables
- Running GraphQL endpoint with full contract shape (non-streaming payloads).

Acceptance Criteria
- Frontend client (runtime-client-gql) can execute `hello`, `availableAgents`, `loadAgentState` without errors.
- `generateCopilotResponse` returns a valid response shape with at least one `TextMessage`.

---

## Phase 2 — Runtime Core and State Store
Goal: Implement `CopilotRuntime` orchestrator and state handling.

Tasks
- Implement `CopilotRuntime` class managing `threadId`, `runId`, orchestration lifecycle.
- In-memory `state_store` with interface for persistence (future: Redis/Postgres).
- Error normalization to CopilotKit status codes; abort handling stubs.
- Strengthen conversion utilities and add unit tests.

Deliverables
- Minimal orchestrator able to echo dialogs and persist/retrieve state per `{threadId, agentName}`.

Acceptance Criteria
- Unit tests cover conversion, runtime lifecycle, and state store.
- `loadAgentState` returns state written during previous `generateCopilotResponse`.

---

## Phase 3 — LangGraph Provider Integration
Goal: Bridge GraphQL mutation to a LangGraph agent and translate events.

Tasks
- Define provider interface in `providers/base.py` and implement `providers/langgraph/provider.py`.
- Implement agent discovery for `availableAgents` via LangGraph registry.
- Map LangGraph events to message/meta-event envelopes (AgentState, interrupts).
- Implement load/save state for LangGraph runs keyed by `{threadId, agentName}`.
- Create a minimal demo graph (toy agent) for integration tests.

Deliverables
- Working mutation path executing a LangGraph run and returning messages/meta-events (still non-streaming response bundling all events).

Acceptance Criteria
- Integration test starts a LangGraph run, returns at least one `AgentStateMessage` and a `TextMessage`.
- `loadAgentState` reflects updated graph state.

---

## Phase 4 — Streaming (SSE / Incremental Delivery)
Goal: Deliver messages/meta-events incrementally to clients.

Tasks
- Implement incremental response using SSE or multipart GraphQL over HTTP to stream messages and meta-events as they occur.
- Add abort support to stop in-flight runs (propagate to provider and close stream cleanly).
- Verify client compatibility with `@copilotkit/runtime-client-gql` (fallback to non-@defer support acceptable if events arrive incrementally).

Deliverables
- Streaming-capable `generateCopilotResponse` with async iterators.

Acceptance Criteria
- Messages appear incrementally in the UI during a run; abort stops both backend run and stream without retry loops.

---

## Phase 5 — Extensions, Guardrails, Forwarded Parameters
Goal: Reach feature parity for request metadata and cloud guardrails.

Tasks
- Support `extensions` field in responses and request metadata propagation.
- Implement forwarded parameters/headers from the context to providers.
- Implement input guardrails parity (topic allow/deny lists) where applicable.
- Add logging/telemetry hooks at resolver and provider boundaries.

Deliverables
- Extended resolver and provider logic with metadata and guardrails.

Acceptance Criteria
- E2E tests demonstrate forwarded parameters reaching provider and guardrails influencing behavior.

---

## Phase 6 — Persistence and Multi-Agent Orchestration
Goal: Production-grade state and multiple agents.

Tasks
- Add pluggable persistence driver (Redis/Postgres) implementing `state_store` interface.
- Multi-agent registry and selection; support `agentSession` semantics.
- Robust `loadAgentState` and rehydration across processes.

Deliverables
- Persistent state implementation and multi-agent bridging.

Acceptance Criteria
- Scenario with two agents: discovery, selection, state load/save verified across process restarts.

---

## Phase 7 — CrewAI Provider (Follow-on)
Goal: Add CrewAI support via the same provider interface.

Tasks
- Implement `CrewAIProvider` and event mapping.
- Add tests and documentation.

Deliverables
- CrewAI provider operational with parity for the shared contract.

Acceptance Criteria
- Demo scenario using CrewAI passes the same E2E tests as LangGraph (adjusted for framework differences).

---

## Phase 8 — Packaging, CI, and Release
Goal: Prepare for distribution and ongoing maintenance.

Tasks
- Finalize `pyproject.toml` and lockfile using `uv`; define extras (e.g., `[extras.langgraph]`, `[extras.crewai]`).
- Add CI workflows: lint, type-check, tests, package build, optional publish.
- Versioning strategy aligned with CopilotKit releases; changelog updates.
- Documentation pass: README, `_docs/agents.md`, quickstart, and example.

Deliverables
- Installable package and CI pipeline.

Acceptance Criteria
- CI green; package can be installed via `uv add copilotkit-runtime-py` (or organization-equivalent).

---

## Cross-Cutting Concerns
- Security: input validation, redact secrets in logs, limit message/content sizes.
- Robustness: retries with backoff for provider I/O; no infinite loops on failures.
- Compatibility: verify client version compatibility and provide clear errors for mismatches.
- Observability: structured logs with `threadId`/`runId`; optional OpenTelemetry hooks.

---

## Checklists
- Schema parity with TS (types, unions, enums)
- Endpoint path and headers compatible with frontend
- Non-streaming MVP functioning end-to-end
- Streaming incremental delivery with aborts
- LangGraph provider with state and interrupts
- Guardrails and forwarded parameters supported
- Persistence driver pluggable and tested
- Multi-agent orchestration validated
- Packaging and CI finalized
