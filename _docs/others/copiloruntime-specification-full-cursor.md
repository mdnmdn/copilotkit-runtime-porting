# CopilotRuntime Specification (Standalone)

CopilotRuntime is the backend runtime of CopilotKit. It exposes a GraphQL API to frontend clients and orchestrates AI interactions with LLM providers and agent frameworks. It manages message history, action/tool execution, multi-agent state, and streams messages and meta-events to clients. This document is a complete, standalone specification of the protocol, runtime behaviors, types, and a Python port plan using FastAPI + GraphQL.

## 1) Overview and Architecture

- Purpose: Backend runtime that bridges frontend React clients (GraphQL) with LLM providers and agent frameworks (REST-ish/JSONL), orchestrating chat, actions/tools, and multi-agent state with streaming.
- Endpoint: GraphQL HTTP endpoint, typically mounted at `/api/copilotkit`.
- Core pieces:
  - GraphQL API layer: queries, mutation `generateCopilotResponse`, streaming via Yoga Repeater/`@defer`/`@stream`.
  - Runtime engine: request orchestration, action discovery, event streaming, error handling.
  - Service adapters: OpenAI/Anthropic/Google/LangChain/etc.
  - Remote actions and agents: self-hosted CopilotKit endpoints, LangGraph Platform, AGUI in-process agents, MCP tools.
  - State management: agent state load/persist, thread/run lifecycle.
  - Observability/guardrails: cloud integration, validation, structured errors, telemetry.

## 2) GraphQL Contract

### Queries
- `hello: String` → "Hello World" health-check.
- `availableAgents: AgentsResponse` → list of `{ id, name, description? }` discovered agents.
- `loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse` → state/messages for `{threadId, agentName}`. Throws `CopilotKitAgentDiscoveryError` if unknown.

### Mutation
- `generateCopilotResponse(data: GenerateCopilotResponseInput!, properties?: JSONObject): CopilotResponse`
  - Returns: `{ threadId, runId?, status: ResponseStatusUnion, messages: [BaseMessageOutput], metaEvents: [BaseMetaEvent], extensions?: ExtensionsResponse }`
  - Streaming: messages/metaEvents incrementally; `status` resolves on completion/abort.

### Inputs (abbrev.)
- `GenerateCopilotResponseInput` fields: `metadata{requestType}`, `threadId?`, `runId?`, `messages: [MessageInput]`, `frontend{actions[], url?}`, `cloud?`, `forwardedParameters?`, `agentSession?`, `agentState?`, `agentStates?`, `extensions?`, `metaEvents?`.
- `MessageInput` union via optional fields: `textMessage`, `imageMessage`, `actionExecutionMessage`, `resultMessage`, `agentStateMessage`.
- `ActionInput { name, description, jsonSchema, available? }` with `ActionInputAvailability = disabled|enabled|remote`.
- `AgentSessionInput { agentName, threadId?, nodeName? }`, `AgentStateInput { agentName, state, config? }`.
- `ForwardedParametersInput { model?, temperature?, maxTokens?, stop?, toolChoice?, toolChoiceFunctionName? }`.
- `CloudInput { guardrails?: { inputValidationRules: { allowList[], denyList[] } } }`.
- `MetaEventInput { name: MetaEventName, value?, response?, messages? }`.

### Outputs and Enums (abbrev.)
- `CopilotResponse { threadId, runId?, status: ResponseStatus, messages: [BaseMessageOutput], metaEvents?: [BaseMetaEvent], extensions?: ExtensionsResponse }`.
- Message outputs implement `BaseMessageOutput { id, createdAt, status: MessageStatus }`:
  - `TextMessageOutput { role: MessageRole, content: [string], parentMessageId? }`
  - `ActionExecutionMessageOutput { name, arguments: [string], parentMessageId?, scope? (deprecated) }`
  - `ResultMessageOutput { actionExecutionId, actionName, result }`
  - `AgentStateMessageOutput { threadId, agentName, nodeName, runId, active, role, state, running }`
  - `ImageMessageOutput { format, bytes, role, parentMessageId? }`
- MessageRole: `user|assistant|system|tool|developer`.
- MessageStatus union: `PendingMessageStatus|SuccessMessageStatus|FailedMessageStatus` with `MessageStatusCode`.
- ResponseStatus union: `Pending|Success|Failed|UnknownError|GuardrailsValidationFailure|MessageStreamInterrupted`.
- Meta events: `LangGraphInterruptEvent { value, response? }`, `CopilotKitLangGraphInterruptEvent { data { value, messages[] }, response? }` with `MetaEventName` enum.
- Extensions: `openaiAssistantAPI { threadId?, runId? }`.

## 3) Runtime Event System and Streaming

- Runtime events drive streaming to the client:
  - Text: `TextMessageStart → TextMessageContent* → TextMessageEnd`.
  - Actions: `ActionExecutionStart → ActionExecutionArgs* → ActionExecutionEnd → ActionExecutionResult`.
  - Agent state: `AgentStateMessage` periodic updates.
  - Meta events: `LangGraphInterruptEvent`, `CopilotKitLangGraphInterruptEvent`.
- The GraphQL resolver exposes two repeaters:
  - `messages`: emits containers with sub-streams for text content/arguments; sets message status on completion/failure; collects final outputs.
  - `metaEvents`: emits mapped meta-events.
- Error flow: structured errors terminate streams with appropriate `ResponseStatus`; low-level/network errors are wrapped with helpful messages.

## 4) Request Processing Flows

### A) Standard Chat (service adapter)
1. Filter/convert GQL messages → internal.
2. Discover server-side actions: local `actions`, LangServe chains, remote endpoints, MCP tools; exclude `ActionInputAvailability.remote` from LLM loop; filter disabled actions client-side.
3. Invoke `serviceAdapter.process({ messages, actions, eventSource, threadId?, runId?, forwardedParameters?, extensions?, agentSession?, agentStates? })`.
4. Stream events into GraphQL `messages` and `metaEvents`; resolve `status`.

### B) Agent Run (remote agent)
1. If `agentSession` present and not delegating to adapter, route to `processAgentRequest`.
2. Pick `RemoteAgentAction` for current agent; include non-agent and other-agent actions (exclude self) as available tools.
3. Call `remoteAgentHandler({ name, threadId, nodeName?, actionInputsWithoutAgents, metaEvents })` to get an Observable/AsyncIterable of `RuntimeEvent`.
4. Bridge events to GraphQL streams; map agent state and meta-events.

### C) Guardrails
- If `cloud.guardrails` set and last message from `user`, call `POST /guardrails/validate` with `{ input, messages, allowList, denyList }` using `X-CopilotCloud-Public-API-Key`.
- On `denied`: set `GuardrailsValidationFailureResponse`, interrupt message streaming, push an assistant `TextMessage` with the reason.

## 5) Remote Actions and Endpoints

- Endpoint types:
  - Self-hosted CopilotKit endpoints: discovery `POST /info` → `{ actions[], agents[] }`; execution `POST /actions/execute` and `POST /agents/execute` (JSONL stream for agents).
  - LangGraph Platform: discovered via SDK `assistants.search()`, executed via `execute` with JSONL event streaming.
  - AGUI in-process agents: wrapped as remote agent actions.
- Headers: assembled via `onBeforeRequest({ ctx })`; always include `Content-Type: application/json`; may forward `authorization` from context.
- JSONL streaming: `writeJsonLineResponseToEventStream` boundaries handling; on errors convert to structured errors and complete.

## 6) Context, Middleware, Observability

- Context properties: merge resolver `properties` into `ctx.properties`; forwarded to endpoints; reserved keys like `authorization`, `mcpServers`.
- Middleware hooks: `onBeforeRequest`, `onAfterRequest` with `{ threadId, runId, inputMessages, outputMessages, properties, url }`.
- Observability (optional): if enabled and publicApiKey present, logs request, progressive chunks, final response, and errors via hooks, including provider detection and latencies.

## 7) Error Handling and Retry

- Error types: `CopilotKitError`, `CopilotKitLowLevelError`, `CopilotKitApiDiscoveryError`, `CopilotKitAgentDiscoveryError`, `CopilotKitMisuseError` with `CopilotKitErrorCode` and visibility/severity.
- Retry policy for remote HTTP: exponential backoff on 408/429/5xx and common network failures. Last error re-thrown after retries.
- GraphQL masked errors: suppress noisy user configuration issues; log application errors.

## 8) Python Port (FastAPI + GraphQL) – Plan Snapshot

- Use Strawberry or Ariadne; mount at `/api/copilotkit`.
- MVP non-streaming, then SSE/multipart incremental delivery; target `@defer/@stream` parity later.
- Implement `CopilotRuntime` core, `RuntimeEventSource`, conversion helpers, in-memory state store, and `LangGraphProvider`.
- Implement self-hosted and LangGraph Platform remote protocols; add MCP instruction injection and per-request tool fetching cache.
- Add guardrails, observability, forwarded parameters; normalize errors and map meta-events.

## 9) Minimal Example Exchanges

- Health: `query { hello }` → "Hello World".
- Agents: `query { availableAgents { agents { id name description } } }`.
- Chat: `mutation generateCopilotResponse { ... }` returning streamed messages/metaEvents and final `status`.

## 10) Notes

This standalone specification preserves the wire-level schema, streaming semantics, remote execution protocols, and deep runtime behaviors required to implement a faithful Python port and maintain compatibility with CopilotKit clients.
