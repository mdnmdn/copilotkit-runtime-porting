## CopilotRuntime Python Port (FastAPI + LangGraph)

### Purpose
Port the TypeScript CopilotRuntime to Python, exposing a GraphQL endpoint via FastAPI that proxies frontend requests to Python agent frameworks. First target is LangGraph; CrewAI support comes next. The runtime should handle message history, multi-agent orchestration, state management, and streaming of AI interactions, mirroring CopilotKit’s existing runtime semantics.

### Scope and Goals
- Reproduce the CopilotRuntime behavior and GraphQL contract in Python.
- Expose a GraphQL endpoint using FastAPI to interoperate with existing React clients.
- Implement a provider layer for LangGraph agents (first milestone).
- Preserve core features: multi-agent discovery, chat orchestration, agent state loading, and streamed responses/meta-events.

### Architectural Parity with TypeScript Runtime
The TypeScript runtime builds a GraphQL schema with resolvers for copilot operations and state:

- Schema is built with resolvers for `CopilotResolver` and `StateResolver`.
- Key runtime entry points include:
  - `generateCopilotResponse` mutation: orchestrates a run and streams messages and meta-events.
  - `availableAgents` query: lists discoverable agents/entrypoints.
  - `loadAgentState` query: returns persisted agent state for a thread/agent.

Python port must implement the same public contract to remain compatible with the `@copilotkit/runtime-client-gql` client.

### Public GraphQL Contract (to mirror)
Operations exposed to the frontend client:

- Query `hello`: diagnostic string.
- Query `availableAgents`: returns `AgentsResponse` with available agent descriptors.
- Query `loadAgentState(data: LoadAgentStateInput)`: returns `LoadAgentStateResponse` with stored state and flags.
- Mutation `generateCopilotResponse(data: GenerateCopilotResponseInput!, properties?: JSONObject)`:
  - Returns a `CopilotResponse` containing `threadId`, `runId`, `extensions`, and a stream of `messages` (union types) and `metaEvents`.
  - Messages include: `TextMessage`, `ImageMessage`, `ActionExecutionMessage`, `ResultMessage`, `AgentStateMessage`.
  - Meta-events include: `LangGraphInterruptEvent` and `CopilotKitLangGraphInterruptEvent`.

Notes on streaming:
- The TS client uses GraphQL directives `@stream` and `@defer`. The Python MVP can initially return a completed payload (non-streaming) while we add incremental delivery.
- Target streaming approach: GraphQL over SSE (Incremental Delivery) or WebSocket subscriptions, then evolve to support `@defer/@stream` semantics where possible.

### Python Runtime Design
Top-level components:

1) FastAPI app and GraphQL router
- Use Strawberry (or Ariadne) for GraphQL schema/resolvers.
- Mount at `/api/copilotkit` (configurable) to match frontend expectations.
- Provide optional GraphQL Playground for debugging.

2) Runtime core
- `CopilotRuntime` class (Python) orchestrates runs, loads state, and brokers events.
- Converts GraphQL inputs to internal message structures; emits messages/meta-events as async iterables.
- Manages `threadId` and `runId` lifecycle.

3) Provider layer
- `LangGraphProvider` implements:
  - `list_agents() -> list[AgentDescriptor]`
  - `load_state(thread_id, agent_name) -> LoadAgentStateResponse`
  - `run(input: GenerateCopilotResponseInput, ctx) -> AsyncIterator[RuntimeEvent]`
- Responsible for translating LangGraph events into CopilotRuntime message/meta-event envelopes.

4) State and storage
- Minimal MVP: in-memory store keyed by `threadId` and `agentName`.
- Pluggable interface for Redis/Postgres later.

5) Error handling
- Normalize errors into the CopilotKit error shape and enums.
- No infinite retries; include structured codes for guardrails and network errors.

### Proposed Python Package Layout
```
sdk-python/copilotkit/runtime_py/
  app/
    main.py                 # FastAPI bootstrap
    settings.py             # Config (port, path, logging)
  graphql/
    schema.py               # Strawberry/Ariadne schema root
    types.py                # Message unions, enums, response types
    inputs.py               # Input objects: GenerateCopilotResponseInput, etc.
    resolvers.py            # hello, availableAgents, loadAgentState, generateCopilotResponse
    context.py              # Request context (properties, logger)
  core/
    runtime.py              # CopilotRuntime class (Python)
    conversion.py           # GQL <-> internal messages mapping
    events.py               # RuntimeEvent typed events, meta-events
    state_store.py          # In-memory + interface for pluggable storage
    errors.py               # Error normalization and enums
  providers/
    base.py                 # Provider interface
    langgraph/
      provider.py           # LangGraphProvider implementation
      adapters.py           # Event translation (LangGraph -> RuntimeEvent)
```

### Resolver Behavior
- `hello` returns a literal for health checks.
- `availableAgents(ctx)`
  - Queries provider(s) for agent descriptors.
  - Returns `AgentsResponse` with `{ name, id, description? }`.
- `loadAgentState(ctx, data)`
  - Validates `agentName` exists in registry.
  - Loads persisted state for `{ threadId, agentName }` via provider/state store.
- `generateCopilotResponse(ctx, data, properties)`
  - Validates inputs and agent availability.
  - Starts a new run (`runId`) or resumes based on inputs.
  - Streams back message union items and meta-events mapped from provider events.
  - Finalizes response status and persists new state.

### Message and Event Mapping
Messages (GraphQL union) map to internal events:
- TextMessage: `{ id, createdAt, role, content, status }`
- ImageMessage: `{ id, createdAt, role, format, bytes }`
- ActionExecutionMessage: `{ id, name, arguments, parentMessageId }`
- ResultMessage: `{ id, actionExecutionId, actionName, result }`
- AgentStateMessage: `{ threadId, state, running, agentName, nodeName, runId, active, role }`

Meta-events:
- LangGraphInterruptEvent: `{ type, name, value }` (raw LangGraph interrupt)
- CopilotKitLangGraphInterruptEvent: `{ type, name, data: { messages[], value } }` (enriched)

### LangGraph Provider Guidelines
- Agent registry
  - Discover agents/nodes and expose via `availableAgents`.
- Running a graph
  - Start or continue a run with `threadId` and optional `runId`.
  - Stream node execution updates as `AgentStateMessage`.
  - Emit LangGraph interrupts as meta-events.
- Tool/action bridge
  - Surface callable tools as `ActionExecutionMessage` and expect `ResultMessage` upon completion.
- State persistence
  - Save/restore graph state per thread/agent; support partial snapshots.

### Streaming Plan
Phases:
1) MVP: Synchronous mutation response (no incremental delivery). Client still works without `@stream/@defer` when responses are reasonably sized.
2) SSE: Implement incremental delivery using GraphQL over SSE (multipart responses), yielding messages/meta-events as they occur.
3) Full parity: Support `@defer/@stream` semantics where the client benefits from partial hydration.

### Configuration and Context
- Request `properties` forwarded from client are included in context for providers.
- Headers may carry API keys for external LLMs; use dependency-injected settings.
- Logger attached to context; include structured correlation with `threadId`/`runId`.

### Error and Guardrails
- Convert provider/runtime errors into a consistent GraphQL union status with codes.
- Validate inputs; return actionable details but avoid leaking secrets.
- Abort handling: promptly stop ongoing runs and close streams.

### Testing and Validation
- Unit tests for conversion, resolvers, and provider adapters.
- Integration test: run the FastAPI app, execute `availableAgents`, `loadAgentState`, and `generateCopilotResponse` with a toy LangGraph.
- Compatibility test with the existing React client pointing to the Python endpoint.

### Milestones
1) Skeleton FastAPI + GraphQL app with `hello` and `availableAgents` (static).
2) Implement `loadAgentState` and in-memory state store.
3) Implement `generateCopilotResponse` with LangGraph provider (non-streaming).
4) Add SSE incremental delivery for messages/meta-events.
5) Extend provider to CrewAI; add pluggable persistence and retries.

### Developer Guidelines
- Use the `uv` python package manager
- Keep public GraphQL types stable; add fields via extensions when necessary.
- Separate schema/types from business logic; maintain pure adapters for conversion.
- Prefer explicit, typed models and enums over loosely-typed dicts.
- Ensure no tight coupling to a single framework (LangGraph or CrewAI) in the core runtime.

### Runbook (MVP)
1) `uvicorn copilotkit.runtime_py.app.main:app --reload`
2) Navigate to `/api/copilotkit/graphql` for the playground.
3) Execute `availableAgents` to verify registry.
4) Execute `generateCopilotResponse` with a sample message to trigger a LangGraph run.

### References
- TS schema/resolvers: `packages/runtime/src/graphql/resolvers/*`
- Client GQL contract: `packages/runtime-client-gql/src/graphql/definitions/*`
- Python SDK entry points: `sdk-python/copilotkit/*`

