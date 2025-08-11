## CopilotRuntime GraphQL Protocol – Specification (RED)

This specification documents the GraphQL contract, message and meta-event types, behaviors, and flows implemented by CopilotRuntime. It is derived from the TypeScript implementation to guide a faithful Python port.

RED = Requirements, Events, Data. This spec focuses on externally observable behavior and wire-level types rather than implementation details.

### Overview
- Endpoint: GraphQL HTTP endpoint (Yoga in TS; FastAPI + GraphQL in Python port) exposed under a configurable path (e.g., `/api/copilotkit`).
- Purpose: Bridge React clients to backend AI agents and services, orchestrating chat, tools/actions, and multi-agent state, with incremental streaming of messages and meta-events.

### Operations

1) Query hello
- Request: `hello: String`
- Response: Constant `"Hello World"` string. Used as a health check.

2) Query availableAgents
- Request: `availableAgents: AgentsResponse`
- Response: `{ agents: [{ id: string; name: string; description?: string }] }`
- Semantics: Discovers and returns available agents/endpoints. The TS runtime filters away endpoint details before returning.

3) Query loadAgentState
- Request: `loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse`
- `LoadAgentStateInput`: `{ threadId: string; agentName: string }`
- Response: implementation-defined structure representing serialized state, plus flags such as `running/active` depending on provider.
- Semantics: Validates agent exists; if not, raises `CopilotKitAgentDiscoveryError` with available agents. Returns persisted state for the specific `{threadId, agentName}`.

4) Mutation generateCopilotResponse
- Request: `generateCopilotResponse(data: GenerateCopilotResponseInput!, properties?: JSONObject): CopilotResponse`
- Response: `CopilotResponse` with fields:
  - `threadId: ID!`
  - `runId: ID!`
  - `status: ResponseStatusUnion` (resolves at end; may be deferred)
  - `extensions: ExtensionsResponse` (implementation-defined, e.g., OpenAI Assistant IDs)
  - `messages: [MessageOutput]!` (streamed incrementally)
  - `metaEvents: [MetaEvent]!` (streamed incrementally)

#### GenerateCopilotResponseInput (high level)
- `frontend`: `{ actions: ActionInput[]; url: string }`
- `messages`: `MessageInput[]` (prior conversation and user input)
- `threadId?: string`
- `runId?: string`
- `agentSession?: AgentSessionInput` (pin to an agent or agent session)
- `agentStates?: AgentStateInput[]` (coagent state snapshots)
- `extensions?: ExtensionsInput` (extensible payloads)
- `forwardedParameters?: JSONObject` (arbitrary pass-through to providers)
- `cloud?: CloudInput` (optional Copilot Cloud guardrails)
- `metaEvents?: MetaEventInput[]` (e.g., interrupt intents)
- `metadata`: `{ requestType: "Chat" | "Task" | ... }`

#### Response Streaming Behavior
- Messages and meta-events are delivered incrementally. The TS runtime uses GraphQL Yoga’s Repeater with `@stream`/`@defer` directives.
- Clients should support incremental updates but may also handle non-streaming (MVP in Python port).
- The `status` resolves to success or error after the stream completes or aborts.

### Types

#### Messages (MessageOutput union)
All message outputs include `id: ID!`, `createdAt: DateTime!`, and a `status: MessageStatusUnion` which resolves to one of:
- `SuccessMessageStatus { code }`
- `FailedMessageStatus { code, reason }`
- `PendingMessageStatus { code }`

Message variants:
- TextMessageOutput
  - `role: MessageRole` (user|assistant|system)
  - `content: Stream<string>` (incremental chunks) or `string` once complete
  - `parentMessageId?: ID`

- ImageMessageOutput
  - `role: MessageRole`
  - `format: string`
  - `bytes: Base64String`
  - `parentMessageId?: ID`

- ActionExecutionMessageOutput
  - `name: string`
  - `arguments: Stream<string>` (JSON stringified arguments as streamed chunks) or final string
  - `parentMessageId?: ID`

- ResultMessageOutput
  - `actionExecutionId: ID`
  - `actionName: string`
  - `result: string` (encoded result or error payload)

- AgentStateMessageOutput
  - `threadId: string`
  - `agentName: string`
  - `nodeName: string`
  - `runId: string`
  - `active: boolean`
  - `running: boolean`
  - `state: string` (serialized)
  - `role: MessageRole`

Enums:
- `MessageRole`: `user | assistant | system`
- `ActionInputAvailability`: `enabled | disabled | hidden` (client filters out disabled)

#### Meta-Events (MetaEvent union)
- LangGraphInterruptEvent
  - `type: "MetaEvent"`
  - `name: "LangGraphInterruptEvent"`
  - `value: string`

- CopilotKitLangGraphInterruptEvent
  - `type: "MetaEvent"`
  - `name: "CopilotKitLangGraphInterruptEvent"`
  - `data: { value: string; messages: (TextMessage | ActionExecutionMessage | ResultMessage)[] }`

Note: The runtime also recognizes `LangGraphInterruptResumeEvent` internally but the client-facing contract focuses on the two above for interrupt signaling.

#### Response Status (ResponseStatusUnion)
- SuccessResponseStatus: `{ code }`
- FailedResponseStatus: `{ code, reason, details }`
- UnknownErrorResponse: `{ description, originalError? }`
- GuardrailsValidationFailureResponse: `{ guardrailsReason }`
- MessageStreamInterruptedResponse: `{ messageId? }`

#### Extensions
- `extensions.openaiAssistantAPI?: { threadId: string; runId: string }`
- Extensible container for provider-specific metadata.

### Inputs

Key input objects (abbreviated):
- ActionInput: `{ name, description?, parameters, available? }`
- MessageInput: union of `{ textMessage?, imageMessage?, actionExecutionMessage?, resultMessage?, agentStateMessage? }`
- AgentSessionInput: identifies the agent/session for a run
- AgentStateInput: `{ agentName: string; state: string; config?: string }`
- ExtensionsInput: provider-specific request extensions
- ForwardedParametersInput: opaque JSON forwarded to providers
- FrontendInput: `{ actions: ActionInput[]; url: string }`
- CloudInput + CloudGuardrailsInput: `{ guardrails?: { inputValidationRules: { allowList: string[]; denyList: string[] }}}`
- MetaEventInput: optional interrupt intent(s)

### Flow Semantics

1) availableAgents
- Runtime queries provider(s) and returns agents (without exposing endpoint internals).

2) loadAgentState
- Validates `agentName` is known; otherwise throws `CopilotKitAgentDiscoveryError` with a list of available agents.
- Returns stored state for `{ threadId, agentName }`.

3) generateCopilotResponse
- Context
  - Merges `properties` arg into request context properties.
  - Extracts `x-copilotcloud-public-api-key` header for cloud features and telemetry.

- Guardrails (optional)
  - If `cloud.guardrails` present and last message is from `user`, calls Copilot Cloud `POST /guardrails/validate` with `{ input, messages, allowList, denyList }`.
  - On denial: emits `GuardrailsValidationFailureResponse`, interrupts message streaming, and returns an assistant `TextMessage` explaining the reason.

- Event Stream Processing
  - Runtime produces a stream of `RuntimeEvent` items:
    - TextMessageStart -> TextMessageContent* -> TextMessageEnd
    - ActionExecutionStart -> ActionExecutionArgs* -> ActionExecutionEnd -> ActionExecutionResult
    - AgentStateMessage
    - MetaEvent (LangGraph interrupts, CopilotKit enriched interrupts)
  - Messages field is resolved via two nested repeaters:
    - One repeater emits message “containers” (Text/Action/Result/AgentState) with their own sub-streams for content/arguments.
    - Sub-streams manage status transitions to Success/Failed and accumulate final message records for post-run persistence.
  - Meta-events field is a repeater that emits interrupt events mapped from runtime events.

  - Agent runs vs. general runs
    - If `agentSession` is present and `delegateAgentProcessingToServiceAdapter` is false, the runtime switches to `processAgentRequest`:
      - Identifies the current agent as a `RemoteAgentAction` (selected from server-side actions).
      - Builds `availableActionsForCurrentAgent` by including non-agent actions and other agents’ actions (excluding self to avoid loops).
      - Calls the agent’s `remoteAgentHandler` to obtain an Observable of `RuntimeEvent` which is bridged into the GraphQL stream.
    - Otherwise, `processRuntimeRequest` uses the configured `serviceAdapter` (LLM adapter) and server-side actions.

  - Server-side actions and remote endpoints
    - Server-side actions include:
      - Locally configured actions (`actions`),
      - LangServe chains (`langserve`),
      - Remote endpoints (`remoteEndpoints`) transformed via `setupRemoteActions`,
      - MCP-derived tools (fetched per request via `createMCPClient`, cached by endpoint).
    - Remote endpoint discovery and execution:
      - Self-hosted CopilotKit endpoints: `POST /info` for actions/agents, `POST /actions/execute`, `POST /agents/execute`.
      - LangGraph Platform endpoints: discovered via LangGraph SDK; agent execution via `execute` and JSONL event streaming.
    - `ActionInputAvailability.remote` actions are excluded from the core LLM loop, while disabled actions are filtered out before request.

- Error Handling
  - Structured CopilotKit errors are bubbled as GraphQL errors with extensions and also reflected in `status` via `UnknownErrorResponse` where appropriate.
  - Network/streaming errors are converted to `CopilotKitLowLevelError` with helpful messages.
  - On errors during streaming, the runtime unsubscribes and completes streams, resolving status accordingly.

- Completion
  - On normal completion, `status` resolves to `SuccessResponseStatus` after optional guardrails result is received.
  - Collected output messages are returned to middleware/higher layers for persistence.

### Interrupts and Meta-Events
- LangGraph-originated interrupts map to `LangGraphInterruptEvent` (raw value) or `CopilotKitLangGraphInterruptEvent` (includes related messages).
- Frontend can also send `metaEvents` input to influence the run (e.g., resume).

### Headers and Context Properties
- `x-copilotcloud-public-api-key`: used when `cloud` config is present; also enables onTrace telemetry.
- `properties` argument: arbitrary JSON merged into server-side context; providers can read it.

### Context, Middleware, and Observability
- Context properties
  - `properties` are merged from resolver `properties` argument and any server defaults, available to remote endpoints via `onBeforeRequest` header injection.
  - Special keys may include `authorization` (forwarded as `Bearer` for LangGraph Platform) and `mcpServers` for dynamic MCP tool discovery.

- Middleware hooks
  - `onBeforeRequest({ threadId, runId, inputMessages, properties, url })` and `onAfterRequest({ threadId, runId, inputMessages, outputMessages, properties, url })` allow request-scoped processing.

- Observability (optional, cloud)
  - When enabled and a public API key is provided, the runtime logs request, progressive chunks, final responses, and errors via `observability.hooks`.

### Retry and Networking
- All remote HTTP calls use `fetchWithRetry` with exponential backoff and a retry policy targeting 408/429/5xx and network errors (ETIMEDOUT, ECONNREFUSED, etc.).
- JSONL streams are parsed by `writeJsonLineResponseToEventStream`, which converts each line to a runtime event and completes the stream on EOF.

### Remote Actions Protocol (Self-hosted and LangGraph Platform)
- Discovery
  - Self-hosted: `POST {endpoint}/info` with `{ properties, frontendUrl }` → `{ actions: Action[], agents: Agent[] }`.
  - LangGraph Platform: SDK `assistants.search()` → agents with `{ assistant_id, graph_id }`.

- Execution
  - Actions: `POST {endpoint}/actions/execute` with `{ name, arguments, properties }` → `{ result }`.
  - Agents: `POST {endpoint}/agents/execute` with `{ name, threadId, nodeName, messages, state, config, properties, actions, metaEvents }` → JSONL stream of runtime events.
  - Headers are constructed via `onBeforeRequest({ ctx })` and include `Content-Type: application/json` plus any custom entries.

### MCP Tooling (Experimental)
- At request time, the runtime can fetch tools from MCP servers defined either in runtime config or supplied via `properties.mcpServers`.
- Tools are converted into server-side actions and instruction text is injected into a system message to guide tool usage.

### Compatibility Considerations for Python Port
- Support non-streaming first; ensure union types and fields match the TS contract so the client library continues to function.
- For streaming, implement SSE/multipart incremental delivery with per-message sub-streams for content and arguments.
- Normalize errors to include `extensions.code`, `statusCode`, `severity`, and `visibility` when applicable.
- Agent discovery must filter internal endpoint details from public response.

### Minimal Example Exchanges (Conceptual)

1) Health check
- Request: `query { hello }`
- Response: `{ "data": { "hello": "Hello World" } }`

2) Agent discovery
- Request: `query { availableAgents { agents { id name description } } }`
- Response: `{ "data": { "availableAgents": { "agents": [{ "id": "planner", "name": "planner" }] } } }`

3) Chat run (simplified, non-streaming)
- Request: `mutation { generateCopilotResponse(data: { frontend: { actions: [] , url: "https://app" }, messages: [...], metadata: { requestType: Chat } }) { threadId runId messages { __typename ... on TextMessageOutput { content role } } status { ... on BaseResponseStatus { code } ... on FailedResponseStatus { reason } } } }`
- Response: As messages complete, messages array contains incremental or final entries; status resolves to success or failure.

### References
- Resolvers: `packages/runtime/src/graphql/resolvers/copilot.resolver.ts`, `state.resolver.ts`
- Types/Inputs: `packages/runtime/src/graphql/types/*`, `packages/runtime/src/graphql/inputs/*`
- Runtime Events: `packages/runtime/src/service-adapters/events.ts`
- LangGraph Events: `packages/runtime/src/agents/langgraph/events.ts`


