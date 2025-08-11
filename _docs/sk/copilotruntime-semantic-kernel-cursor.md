# CopilotRuntime Specification (.NET Core + Semantic Kernel) — Cursor Protocol

## Overview

CopilotRuntime is the backend runtime of CopilotKit. It exposes a GraphQL API to frontend clients and orchestrates AI interactions with LLM providers and agent frameworks. This document specifies a .NET Core implementation aligned with the Cursor protocol while using Microsoft's Semantic Kernel agents as the agent framework.

Goals:
- Maintain wire-compatibility with the Cursor GraphQL contract and streaming semantics
- Implement runtime orchestration in ASP.NET Core with Hot Chocolate GraphQL
- Use Semantic Kernel Agents for agent runs, plugins for actions, and SK connectors for LLMs
- Provide structured errors, guardrails, observability, and remote action/agent support

References:
- Cursor standalone specification: see `/_docs/copiloruntime-specification-full-cursor.md`
- Semantic Kernel agents documentation: [Semantic Kernel Agents (C#)](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/?pivots=programming-language-csharp)

## 1) Architecture

```
┌─────────────────────┐   GraphQL      ┌──────────────────────────┐   Agents / LLMs   ┌──────────────────────┐
│ Frontend React      │  over HTTP     │   CopilotRuntime (.NET)  │  via Semantic     │  Semantic Kernel      │
│ Components          │ ──────────────▶│  (HotChocolate GraphQL)  │  Kernel adapters  │  Agents + Plugins     │
│                     │                │  + Event Streaming       │                  │  (OpenAI/Azure etc.)  │
└─────────────────────┘                └──────────────────────────┘                  └──────────────────────┘
```

Key parts:
- GraphQL API layer: `hello`, `availableAgents`, `loadAgentState`, `generateCopilotResponse`
- Runtime engine: request orchestration, action discovery, event streaming, error handling
- Semantic Kernel integration: Agents for agent runs, plugins for actions, connectors for LLMs
- Remote endpoints (optional): self-hosted CopilotKit endpoints, MCP-derived tools
- State management: thread/run lifecycle, persisted agent state (EF Core or pluggable store)
- Observability/guardrails: cloud integration, structured errors, telemetry

## 2) GraphQL Contract (Cursor-Compatible)

Endpoint: GraphQL HTTP endpoint (e.g., `/api/copilotkit`). Schema must match Cursor spec to remain frontend-compatible.

Queries:
- `hello: String` → health-check
- `availableAgents: AgentsResponse` → `{ agents: [{ id, name, description? }] }`
- `loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse` → persisted state/messages

Mutation:
- `generateCopilotResponse(data: GenerateCopilotResponseInput!, properties?: JSONObject): CopilotResponse`
  - Returns `{ threadId, runId?, status: ResponseStatusUnion, messages: [BaseMessageOutput], metaEvents: [BaseMetaEvent], extensions?: ExtensionsResponse }`
  - Streaming: messages/metaEvents stream incrementally; `status` resolves on completion/abort

Inputs (abbrev., must match Cursor types):
- `GenerateCopilotResponseInput { metadata{requestType}, threadId?, runId?, messages: [MessageInput], frontend{actions[], url?}, cloud?, forwardedParameters?, agentSession?, agentState?, agentStates?, extensions?, metaEvents? }`
- `MessageInput` union via optional fields: `textMessage`, `imageMessage`, `actionExecutionMessage`, `resultMessage`, `agentStateMessage`
- `ActionInput { name, description, jsonSchema, available?: disabled|enabled|remote }`
- `AgentSessionInput { agentName, threadId?, nodeName? }`, `AgentStateInput { agentName, state, config? }`
- `ForwardedParametersInput { model?, temperature?, maxTokens?, stop?, toolChoice?, toolChoiceFunctionName? }`
- `CloudInput { guardrails?: { inputValidationRules: { allowList[], denyList[] } } }`
- `MetaEventInput { name: MetaEventName, value?, response?, messages? }`

Outputs and enums (abbrev.):
- `CopilotResponse { threadId, runId?, status: ResponseStatusUnion, messages: [BaseMessageOutput], metaEvents?: [BaseMetaEvent], extensions?: ExtensionsResponse }`
- Message outputs: `TextMessageOutput | ActionExecutionMessageOutput | ResultMessageOutput | AgentStateMessageOutput | ImageMessageOutput` implementing `BaseMessageOutput { id, createdAt, status }`
- Status unions and enums identical to Cursor spec (MessageRole, MessageStatus, ResponseStatus, MetaEventName)

## 3) Runtime Event System and Streaming

Event types (must map 1:1 to Cursor):
- Text: `TextMessageStart → TextMessageContent* → TextMessageEnd`
- Actions: `ActionExecutionStart → ActionExecutionArgs* → ActionExecutionEnd → ActionExecutionResult`
- Agent: `AgentStateMessage` (periodic)
- Meta: `LangGraphInterruptEvent`, `CopilotKitLangGraphInterruptEvent`

Implementation in .NET:
- Use Hot Chocolate with `IAsyncEnumerable<T>` for GraphQL streaming or SignalR for side-channel/event fan-out
- Internally, use `System.Threading.Channels` to buffer and broadcast `RuntimeEvent` instances
- Convert runtime events to GraphQL `messages` containers and `metaEvents` with sub-streams for content/arguments

Runtime event record (C# sketch):
```csharp
public enum RuntimeEventType { TextMessageStart, TextMessageContent, TextMessageEnd, ActionExecutionStart, ActionExecutionArgs, ActionExecutionEnd, ActionExecutionResult, AgentStateMessage, MetaEvent }

public sealed record RuntimeEvent(
    RuntimeEventType Type,
    DateTimeOffset Timestamp,
    string? MessageId,
    string? ParentMessageId,
    JsonDocument Data
);
```

## 4) Request Processing Flows (Cursor Semantics)

Standard chat (LLM service via SK):
1) Convert GraphQL inputs → internal messages and SK `ChatHistory`
2) Discover server-side actions: local plugins, remote endpoints, MCP tools; exclude `ActionInputAvailability.remote` from core loop; filter disabled
3) Invoke Semantic Kernel to generate streaming content; map to `TextMessage*` events
4) If model/tooling triggers a function, emit action events; execute via plugins; emit result
5) Stream events into GraphQL `messages`/`metaEvents`; resolve `status`

Agent run (Semantic Kernel Agents):
1) If `agentSession` present and not delegated to a raw LLM adapter, route to agent processing
2) Resolve `IAgent` by name; build `AgentExecutionRequest { threadId, runId, messages, actions, nodeName?, metaEvents? }`
3) Invoke SK Agent/Group Chat APIs; map SK outputs and function calls into runtime events
4) Stream `AgentStateMessage`/meta events; collect final messages; resolve `status`

Guardrails (cloud):
- If `cloud.guardrails` configured and last user message present, call `POST /guardrails/validate` with `{ input, messages, allowList, denyList }` using `X-CopilotCloud-Public-API-Key`
- On denial: set `GuardrailsValidationFailureResponse`, interrupt message streaming, add assistant text with reason

## 5) Semantic Kernel Integration

LLMs and chat:
- Use `Microsoft.SemanticKernel` connectors (OpenAI/Azure OpenAI) for chat completion
- Convert Cursor messages → SK `ChatHistory` and roles
- Stream SK content; translate to `TextMessage*` runtime events

Agents:
- Use SK Agents ([docs](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/?pivots=programming-language-csharp)) for agent sessions
- `IAgent` or `ChatCompletionAgent` configured with instructions, functions (plugins), and kernel
- For multi-agent flows, wrap with `AgentGroupChat` and stream messages/events to runtime

Actions (plugins):
- Map `ActionInput` to SK plugin functions using `[KernelFunction]`
- When the model selects a tool, emit `ActionExecutionStart/Args/End` and execute via an `IActionExecutor`
- Return results as JSON strings; emit `ActionExecutionResult`

Sketch: Agent provider and action plugin
```csharp
public interface IAgentServiceProvider {
    Task<IAgent> GetAgentAsync(string agentName);
    IAsyncEnumerable<RuntimeEvent> ProcessAsync(IAgent agent, AgentExecutionRequest request, CancellationToken ct);
}

public sealed class CopilotActionPlugin {
    private readonly IActionExecutor _executor;
    public CopilotActionPlugin(IActionExecutor executor) => _executor = executor;

    [KernelFunction(Description = "Execute a Copilot action")]
    public async Task<string> ExecuteAction(string actionName, string arguments) {
        var result = await _executor.ExecuteAsync(actionName, arguments);
        return JsonSerializer.Serialize(result);
    }
}
```

## 6) Remote Actions and Endpoints

Self-hosted CopilotKit endpoints:
- Discovery: `POST /info` → `{ actions[], agents[] }`
- Actions: `POST /actions/execute` with `{ name, arguments, properties }` → `{ result }`
- Agents: `POST /agents/execute` with `{ name, threadId, nodeName, messages, state, config, properties, actions, metaEvents }` → JSONL runtime events

Notes:
- Construct headers via server context (e.g., `onBeforeRequest`-style middleware); include `Content-Type: application/json`, forward `authorization` if present
- JSONL parsing must handle partial chunks and framing across network boundaries

## 7) Error Handling and Retry

Error classes align to Cursor codes:
- `AuthenticationError`, `ConfigurationError`, `NetworkError`, `AgentNotFound`, `ApiNotFound`, `RemoteEndpointNotFound`, `MissingPublicApiKeyError`, `Unknown`
- Map HTTP status: `401 → AuthenticationError`, `4xx → ConfigurationError`, `5xx → NetworkError`
- Wrap low-level/network exceptions with structured metadata and user-friendly messages

Retry policy:
- Exponential backoff for `408/429/5xx` and transient network failures when calling remote endpoints

## 8) Observability and Middleware

Context properties:
- Merge GraphQL `properties` into server-side context for forwarding to remote endpoints and providers
- Reserved keys (examples): `authorization`, `mcpServers`, `x-copilotcloud-public-api-key`

Hooks:
- `onBeforeRequest`, `onAfterRequest`-style middleware with `{ threadId, runId, inputMessages, outputMessages, properties, url }`

Observability:
- Optional OpenTelemetry tracing and metrics
- Track progressive chunks vs final responses; capture model/provider, latency, and errors

## 9) ASP.NET Core Implementation (Outline)

Packages:
- HotChocolate GraphQL server, Semantic Kernel, OpenAI/Azure OpenAI connectors, (optional) SignalR, EF Core, OpenTelemetry

Program startup sketch:
```csharp
var builder = WebApplication.CreateBuilder(args);

// GraphQL
builder.Services
    .AddGraphQLServer()
    .AddQueryType<CopilotQuery>()
    .AddMutationType<CopilotMutation>()
    .AddSubscriptionType<CopilotSubscription>();

// Semantic Kernel
builder.Services.AddScoped<Kernel>(sp => {
    var kb = Kernel.CreateBuilder();
    var apiKey = builder.Configuration["OpenAI:ApiKey"] ?? throw new InvalidOperationException("Missing OpenAI:ApiKey");
    kb.AddOpenAIChatCompletion(builder.Configuration["OpenAI:Model"] ?? "gpt-4", apiKey);
    return kb.Build();
});

// Runtime services
builder.Services.AddScoped<ICopilotRuntime, CopilotRuntime>();
builder.Services.AddScoped<IAgentServiceProvider, SemanticKernelAgentProvider>();
builder.Services.AddScoped<IActionExecutor, ActionExecutor>();

var app = builder.Build();
app.MapGraphQL("/api/copilotkit");
await app.RunAsync();
```

GraphQL resolvers (shape only; must map to Cursor types):
```csharp
[Query]
public sealed class CopilotQuery {
    public string Hello() => "Hello World";
    public Task<AgentsResponse> AvailableAgents([Service] IAgentDiscoveryService svc) => svc.DiscoverAsync();
}

[Mutation]
public sealed class CopilotMutation {
    public Task<CopilotResponse> GenerateCopilotResponse(
        GenerateCopilotResponseInput data,
        Optional<JsonDocument> properties,
        [Service] ICopilotRuntime runtime,
        CancellationToken ct
    ) => runtime.ProcessRequestAsync(data, properties.HasValue ? properties.Value : null, ct);
}

[Subscription]
public sealed class CopilotSubscription {
    [Subscribe]
    public IAsyncEnumerable<CopilotStreamEvent> CopilotStream(
        GenerateCopilotResponseInput data,
        [Service] ICopilotRuntime runtime,
        [EnumeratorCancellation] CancellationToken ct
    ) => runtime.StreamProcessRequestAsync(data, ct);
}
```

## 10) Data and State

Persisted entities (optional, EF Core): `ThreadState`, `MessageRecord`, `AgentState`, `ActionExecution` with JSON payload columns for flexible shape.

Thread lifecycle:
- `threadId` and `runId` are created if absent; used for correlation across requests and streams
- Agent state load on `loadAgentState`; save periodically from `AgentStateMessage` or at run end

## 11) Compatibility Notes

- GraphQL schema and enums must remain identical to Cursor spec
- Message/MetaEvent streaming grammar must be preserved; `status` resolves after stream completion/abort
- Error codes and masking behavior must match Cursor
- Remote protocol (self-hosted endpoints) must preserve `/info`, `/actions/execute`, `/agents/execute` shapes and JSONL streaming

## 12) Minimal Example Exchanges

Health:
```graphql
query { hello }
```

Agents:
```graphql
query { availableAgents { agents { id name description } } }
```

Chat:
```graphql
mutation {
  generateCopilotResponse(
    data: {
      metadata: { requestType: Chat }
      frontend: { actions: [], url: "https://app" }
      messages: [
        { textMessage: { role: user, content: "Hello" } }
      ]
    }
  ) {
    threadId
    runId
    messages { __typename }
    status { __typename }
  }
}
```

---

This document specifies a .NET Core implementation of CopilotRuntime that adheres to the Cursor protocol while leveraging Semantic Kernel Agents for agentic workflows, SK plugins for actions, and SK connectors for LLMs. It preserves wire-level compatibility with CopilotKit clients and supports guardrails, observability, and remote endpoints.


