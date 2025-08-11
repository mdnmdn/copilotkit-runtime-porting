# CopilotRuntime for .NET + Semantic Kernel: Full Technical Specification (Standalone)

## 1. Overview

CopilotRuntime is the backend runtime of CopilotKit. It acts as a GraphQL-based proxy between frontend applications and backend AI services and agent frameworks. This document defines a complete, self-contained specification for implementing CopilotRuntime on .NET (ASP.NET Core) using Semantic Kernel as the agent framework. It preserves the public GraphQL contract and protocol semantics while adapting the implementation blueprint, streaming, adapters, and observability to the .NET ecosystem.

Primary goals
- Provide a faithful, interoperable GraphQL API for chat, tools/actions, and agent execution with incremental streaming.
- Integrate the Microsoft Semantic Kernel (SK) Agents framework for agent orchestration, tools (functions), and planning.
- Offer a pluggable adapter system for LLM providers (Azure OpenAI, OpenAI, Google AI Gemini), with room for others.
- Support remote agents and actions using a JSONL event protocol, guardrails via Copilot Cloud, and robust error handling/observability.

## 2. Architecture

```
┌────────────────────────┐   GraphQL     ┌────────────────────────┐    Adapters    ┌────────────────────────┐
│   Frontend Clients     │ over HTTP/WS  │    CopilotRuntime      │   (LLM/Agent)  │   Providers/Agents      │
│ (Web, React, Mobile)   │──────────────▶│  (.NET / ASP.NET Core) │──────────────▶│  (SK Agents, Gemini,    │
│                        │               │  + Hot Chocolate GQL)  │               │   Azure OpenAI, Remote) │
└────────────────────────┘               └────────────────────────┘               └────────────────────────┘
```

Key components
- GraphQL API Layer: Hot Chocolate schema, queries/mutations/subscriptions.
- Runtime Engine: Orchestrates LLM generation, tool execution, agent runs.
- Event Streaming System: IAsyncEnumerable-based streaming using Channels.
- Service Adapters: Azure OpenAI, OpenAI, Google AI (Gemini), LangServe/HTTP, Empty.
- Agent Integration: Semantic Kernel Agents framework for in-process agents; remote agents via JSONL protocol.
- Action System: SK Functions as tools, local/remote actions, MCP-derived tools.
- Cloud Integration: Optional Copilot Cloud guardrails and analytics.
- Observability: ILogger + OpenTelemetry Tracing/Metrics.

## 3. GraphQL API Specification

The GraphQL contract remains provider- and platform-agnostic to maintain compatibility across implementations. This section defines the complete schema elements clients rely on.

### 3.1 Operations

Queries
- hello: String — health check
- availableAgents: AgentsResponse — discover agents from configured sources
- loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse — get persisted state for a thread & agent

Mutations
- generateCopilotResponse(data: GenerateCopilotResponseInput, properties: JSONObject): CopilotResponse — main entry point for AI interactions with streaming messages/meta-events

### 3.2 Enums

- ActionInputAvailability: disabled | enabled | remote
- CopilotRequestType: Chat | Task | TextareaCompletion | TextareaPopover | Suggestion
- FailedResponseStatusReason: GUARDRAILS_VALIDATION_FAILED | MESSAGE_STREAM_INTERRUPTED | UNKNOWN_ERROR
- GuardrailsResultStatus: ALLOWED | DENIED
- MessageRole: user | assistant | system | tool | developer
- MessageStatusCode: Pending | Success | Failed
- ResponseStatusCode: Pending | Success | Failed
- MetaEventName: LangGraphInterruptEvent | CopilotKitLangGraphInterruptEvent

### 3.3 Input Types

- ActionInput: { name: String!, description: String!, jsonSchema: String!, available: ActionInputAvailability }
- AgentSessionInput: { agentName: String!, threadId: String, nodeName: String }
- AgentStateInput: { agentName: String!, state: String!, config: String }
- CloudInput: { guardrails: GuardrailsInput }
- ExtensionsInput: { openaiAssistantAPI: OpenAIApiAssistantAPIInput }
- ForwardedParametersInput: { model: String, maxTokens: Int, stop: [String], toolChoice: String, toolChoiceFunctionName: String, temperature: Float }
- FrontendInput: { toDeprecate_fullContext: String, actions: [ActionInput!]!, url: String }
- GenerateCopilotResponseInput: { metadata: GenerateCopilotResponseMetadataInput!, threadId: String, runId: String, messages: [MessageInput!]!, frontend: FrontendInput!, cloud: CloudInput, forwardedParameters: ForwardedParametersInput, agentSession: AgentSessionInput, agentState: AgentStateInput, agentStates: [AgentStateInput], extensions: ExtensionsInput, metaEvents: [MetaEventInput] }
- GenerateCopilotResponseMetadataInput: { requestType: CopilotRequestType }
- GuardrailsInput: { inputValidationRules: GuardrailsRuleInput! }
- GuardrailsRuleInput: { allowList: [String], denyList: [String] }
- LoadAgentStateInput: { threadId: String!, agentName: String! }
- MessageInput: union by non-null field: { id: String!, createdAt: Date!, textMessage?: TextMessageInput, actionExecutionMessage?: ActionExecutionMessageInput, resultMessage?: ResultMessageInput, agentStateMessage?: AgentStateMessageInput, imageMessage?: ImageMessageInput }
- TextMessageInput: { content: String!, parentMessageId: String, role: MessageRole! }
- ActionExecutionMessageInput: { name: String!, arguments: String!, parentMessageId: String, scope: String }
- ResultMessageInput: { actionExecutionId: String!, actionName: String!, parentMessageId: String, result: String! }
- AgentStateMessageInput: { threadId: String!, agentName: String!, role: MessageRole!, state: String!, running: Boolean!, nodeName: String!, runId: String!, active: Boolean! }
- ImageMessageInput: { format: String!, bytes: String!, parentMessageId: String, role: MessageRole! }
- MetaEventInput: { name: MetaEventName!, value: String, response: String, messages: [MessageInput] }
- OpenAIApiAssistantAPIInput: { runId: String, threadId: String }

### 3.4 Object Types

- Agent: { id: String!, name: String!, description: String }
- AgentsResponse: { agents: [Agent!]! }
- CopilotResponse: { threadId: String!, status: ResponseStatus!, runId: String, messages: [BaseMessageOutput!]!, extensions: ExtensionsResponse, metaEvents: [BaseMetaEvent] }
- BaseMessageOutput (Interface): { id: String!, createdAt: Date!, status: MessageStatus! }
- TextMessageOutput: { role: MessageRole!, content: [String!]!, parentMessageId: String }
- ActionExecutionMessageOutput: { name: String!, scope: String, arguments: [String!]!, parentMessageId: String }
- ResultMessageOutput: { actionExecutionId: String!, actionName: String!, result: String! }
- AgentStateMessageOutput: { threadId: String!, agentName: String!, nodeName: String!, runId: String!, active: Boolean!, role: MessageRole!, state: String!, running: Boolean! }
- ImageMessageOutput: { format: String!, bytes: String!, role: MessageRole!, parentMessageId: String }
- ExtensionsResponse: { openaiAssistantAPI: OpenAIApiAssistantAPIResponse }
- OpenAIApiAssistantAPIResponse: { runId: String, threadId: String }
- LoadAgentStateResponse: { threadId: String!, threadExists: Boolean!, state: String!, messages: String! }
- MessageStatus (Union): PendingMessageStatus | SuccessMessageStatus | FailedMessageStatus
- ResponseStatus (Union): PendingResponseStatus | SuccessResponseStatus | FailedResponseStatus
- BaseMetaEvent (Interface): { type: String!, name: MetaEventName! }
- LangGraphInterruptEvent: { name: MetaEventName!, value: String!, response: String }

### 3.5 Authentication

When `cloud` input is used, clients must include `X-CopilotCloud-Public-API-Key`. The runtime validates and forwards this for guardrails and analytics.

## 4. Protocol and Flow Semantics

### 4.1 Streaming Behavior
- Incremental delivery of messages/meta-events. Transport options: GraphQL subscriptions (WebSockets), @defer/@stream where supported, or Server-Sent Events.
- The final `status` resolves to Success or Failed once streaming completes or aborts.

### 4.2 Runtime Event Sequences
- Text: TextMessageStart → TextMessageContent* → TextMessageEnd
- Action: ActionExecutionStart → ActionExecutionArgs* → ActionExecutionEnd → ActionExecutionResult
- Agent state: periodic AgentStateMessage
- Meta: LangGraphInterruptEvent | CopilotKitLangGraphInterruptEvent

### 4.3 Guardrails
- If `cloud.guardrails` is provided and last message is from user, POST to `/guardrails/validate` with `{ input, messages, allowList, denyList }`.
- On DENIED, emit FailedResponseStatus (GUARDRAILS_VALIDATION_FAILED), stream assistant message explaining reason, and stop further generation.

### 4.4 Agent vs Standard Runs
- Agent run: presence of `agentSession` routes to agent processing; represent the agent as a remote or local action; stream agent events.
- Standard run: use LLM adapter (provider/tool calling) with available server-side actions.

### 4.5 Remote Protocols
- CopilotKit endpoints:
  - POST {endpoint}/info → { actions: Action[], agents: Agent[] }
  - POST {endpoint}/actions/execute → { result }
  - POST {endpoint}/agents/execute → JSONL stream of RuntimeEvent
- LangServe/HTTP chain endpoints: similar JSONL streaming
- Headers: constructed via onBeforeRequest hooks and include `Content-Type: application/json` plus custom entries.

### 4.6 MCP Tooling (Experimental)
- Tools from MCP servers can be fetched dynamically and converted to actions. Instruction text injected into a system message guides usage.

## 5. .NET Event System and Streaming Architecture

Core concepts
- EventSource: central event emitter with replay buffer.
- Channels: System.Threading.Channels for backpressure and multicasting.
- Streaming: IAsyncEnumerable<T> for GraphQL subscriptions and SSE.

Reference implementation (abridged C#)

```csharp
using System.Collections.Concurrent;
using System.Threading.Channels;

public enum RuntimeEventType {
  TextMessageStart, TextMessageContent, TextMessageEnd,
  ActionExecutionStart, ActionExecutionArgs, ActionExecutionEnd, ActionExecutionResult,
  AgentStateMessage, MetaEvent
}

public record RuntimeEvent(
  RuntimeEventType Type,
  string? MessageId = null,
  string? ParentMessageId = null,
  object? Data = null,
  DateTimeOffset Timestamp = default
);

public class RuntimeEventSource {
  private readonly List<Channel<RuntimeEvent>> _subscribers = new();
  private readonly List<RuntimeEvent> _history = new();
  private readonly SemaphoreSlim _gate = new(1,1);
  private readonly int _maxHistory;

  public RuntimeEventSource(int maxHistory = 1000) => _maxHistory = maxHistory;

  public async Task EmitAsync(RuntimeEvent e) {
    await _gate.WaitAsync();
    try {
      _history.Add(e);
      if (_history.Count > _maxHistory) _history.RemoveAt(0);
      foreach (var ch in _subscribers) await ch.Writer.WriteAsync(e);
    } finally { _gate.Release(); }
  }

  public async IAsyncEnumerable<RuntimeEvent> SubscribeAsync(bool replayHistory = false, int capacity = 256) {
    var ch = Channel.CreateBounded<RuntimeEvent>(capacity);
    await _gate.WaitAsync();
    try {
      _subscribers.Add(ch);
      if (replayHistory) foreach (var e in _history) await ch.Writer.WriteAsync(e);
    } finally { _gate.Release(); }

    try {
      while (await ch.Reader.WaitToReadAsync()) {
        while (ch.Reader.TryRead(out var e)) yield return e;
      }
    }
    finally {
      await _gate.WaitAsync();
      try { _subscribers.Remove(ch); ch.Writer.TryComplete(); } finally { _gate.Release(); }
    }
  }
}
```

JSONL processing utility

```csharp
public static class Jsonl
{
  public static async IAsyncEnumerable<JsonElement> ParseAsync(Stream stream, [EnumeratorCancellation] CancellationToken ct = default) {
    using var reader = new StreamReader(stream, Encoding.UTF8);
    while (!reader.EndOfStream && !ct.IsCancellationRequested) {
      var line = await reader.ReadLineAsync();
      if (string.IsNullOrWhiteSpace(line)) continue;
      if (JsonDocument.TryParseValue(ref Unsafe.AsRef(line.AsSpan()), out var doc)) {
        yield return doc.RootElement.Clone();
      } else {
        // fallback parse
        using var parsed = JsonDocument.Parse(line);
        yield return parsed.RootElement.Clone();
      }
    }
  }
}
```

## 6. Service Adapters (LLMs) and Message Conversion

Adapter interface (C#)

```csharp
public interface ICopilotServiceAdapter {
  Task<CopilotRuntimeResponse> ProcessAsync(CopilotRuntimeRequest request, RuntimeEventSource events, CancellationToken ct = default);
}

public record CopilotRuntimeRequest(
  string? ThreadId,
  string? RunId,
  IReadOnlyList<MessageInput> Messages,
  IReadOnlyList<ActionInput> Actions,
  ForwardedParametersInput? Forwarded,
  ExtensionsInput? Extensions,
  AgentSessionInput? AgentSession,
  IReadOnlyList<AgentStateInput>? AgentStates,
  IReadOnlyDictionary<string, object?>? Properties
);

public record CopilotRuntimeResponse(string ThreadId, string? RunId, ExtensionsResponse? Extensions);
```

Built-in adapters
- AzureOpenAIAdapter (Chat Completions/Responses API; tool calling; streaming)
- OpenAIAdapter (OpenAI API; tool calling; streaming)
- GoogleGeminiAdapter (Google AI Gemini; tool/function calling; streaming via SDK or REST)
- HttpLangServeAdapter (remote chains/functions with JSONL streaming)
- EmptyAdapter (agent-only; no LLM)

Message conversion
- Map GraphQL messages to provider schemas.
- Role mapping: system/developer semantics per provider.
- JSON encode/decode arguments/result/state consistently.

Event emission
- Emit start/content/end for text.
- Emit start/args/end/result for tool calls.
- Convert provider-specific errors to structured failures and final ResponseStatus.

## 7. Semantic Kernel Agent Integration

Semantic Kernel (SK) provides building blocks for agents, tools (functions), planning, and memory. This runtime treats SK agents as first-class in-process agents and exposes them via the same GraphQL contract.

Agent model mapping
- Agent = SK Agent (Microsoft.SemanticKernel.Agents) or composition of kernel + functions + planning loop.
- Actions = SK Functions (plugins) with JSON schema derived from function parameters.
- Agent state = custom state object serialized as JSON.
- Agent session/thread = conversation id; map `threadId`/`runId` to SK constructs.

Typical setup (C#)

```csharp
// Kernel & services
var builder = Kernel.CreateBuilder();
// Add OpenAI/AzureOpenAI/Gemini services here
// e.g., builder.AddAzureOpenAIChatCompletion("gpt-4o", endpoint, apiKey);
// or builder.Services.AddGoogleAIGemini(...); // via official SDK or REST wrapper
var kernel = builder.Build();

// Register functions/tools (plugins)
var weatherPlugin = kernel.ImportPluginFromObject(new WeatherPlugin());

// Create an SK Agent (pseudo; depending on SK Agents APIs)
var agent = new SkAgent(kernel)
  .WithName("planner")
  .WithDescription("Plans tasks and delegates tools")
  .WithTools(weatherPlugin);
```

Agent run flow
1. Build available tools for the agent (exclude self to avoid loops) from FrontendInput.actions and server tools (SK functions).
2. Create/lookup agent session by threadId; attach state/config if provided.
3. Feed messages and context properties into the agent loop.
4. Stream agent events (text chunks, tool calls, state updates) via RuntimeEventSource.
5. On completion, return CopilotResponse with aggregated messages and final status.

Bridging SK function calls to actions
- Each SK function is reflected to an ActionInput with JSON schema.
- Tool call events map to ActionExecution* events.
- Results propagate as ResultMessageOutput and optionally as new context for the agent loop.

Planner support
- Use SK planners (e.g., Stepwise, Handlebars, FunctionCalling) to break down tasks.
- Planner steps emit AgentStateMessage updates (nodeName: current step/tool).

## 8. Remote Agents & Actions

Self-hosted agent endpoints
- /info: advertise actions and agents
- /actions/execute: execute an action and return JSON result
- /agents/execute: produce JSONL stream of RuntimeEvent

LangServe/HTTP tools
- Execute tool endpoints with streaming responses mapped to RuntimeEvent.

Integration with SK
- Remote tools are wrapped as SK functions (via HttpKernelPlugin) and included in toolset.
- Agent output streams are consumed and bridged to GraphQL messages.

## 9. Error Handling

C# error model

```csharp
public enum CopilotErrorCode { AuthenticationError, ConfigurationError, NetworkError, AgentNotFound, ApiNotFound, Unknown }
public enum Severity { Critical, Error, Warning, Info }
public enum Visibility { User, Developer, Internal }

public class CopilotException : Exception {
  public CopilotErrorCode Code { get; }
  public Severity Severity { get; }
  public Visibility Visibility { get; }
  public IDictionary<string, object?> Context { get; }
  public CopilotException(string message, CopilotErrorCode code = CopilotErrorCode.Unknown,
    Severity severity = Severity.Error, Visibility visibility = Visibility.Developer,
    IDictionary<string, object?>? context = null) : base(message) {
    Code = code; Severity = severity; Visibility = visibility; Context = context ?? new Dictionary<string, object?>();
  }
}
```

Helpful error guidance
- Connection refused → check agent service/endpoint configuration.
- Authentication failures → verify API keys (AzureOpenAI/OpenAI/Gemini) and endpoint settings.
- Rate limit/timeouts → implement retries/backoff; surface user-friendly messages.

## 10. Observability

- Logging: Microsoft.Extensions.Logging (ILogger) with structured scopes.
- Tracing: OpenTelemetry.ActivitySource → OTLP/Jaeger.
- Metrics: OpenTelemetry.Metrics (request counts, latency, tokens, errors).
- GraphQL middlewares: request/response tracing; redact secrets.

Telemetry payloads
- LLMRequestData: model, messages/actions count, provider, timestamps, threadId/runId.
- LLMResponseData: output summary, latency, final vs progressive.

## 11. Cloud Integration (Guardrails & Analytics)

- Validate `X-CopilotCloud-Public-API-Key` when cloud features used.
- Guardrails flow: POST /guardrails/validate; on DENIED, fail early with assistant message and FailedResponseStatus.
- Analytics: batched usage/error events with retry; configurable sampling.

## 12. .NET Implementation Blueprint

Project structure

```
CopilotRuntime.Net/
├── Api/
│   ├── Program.cs               # ASP.NET Core host
│   ├── GraphQL/
│   │   ├── Schema.cs            # Hot Chocolate schema
│   │   ├── Types/               # Inputs/Outputs, unions/interfaces
│   │   └── Resolvers/           # Query/Mutation/Subscription
│   ├── Controllers/Health.cs    # /health endpoint
│   └── Middleware/
├── Core/
│   ├── RuntimeEventSource.cs
│   ├── Models/                  # DTOs for messages, actions, statuses
│   ├── Adapters/                # ICopilotServiceAdapter & implementations
│   ├── Agents/                  # SK Agent integration
│   ├── Remote/                  # JSONL client, remote action/agent protocol
│   └── Observability/           # Logging, OTEL
└── Tests/
```

Hot Chocolate schema (conceptual)

```csharp
[QueryType]
public class Query {
  public string Hello() => "Hello World";
  public Task<AgentsResponse> AvailableAgents([Service] IAgentRegistry reg) => reg.ListAsync();
  public Task<LoadAgentStateResponse> LoadAgentState(LoadAgentStateInput input, [Service] IStateStore store) => store.LoadAsync(input);
}

[MutationType]
public class Mutation {
  public Task<CopilotResponse> GenerateCopilotResponse(GenerateCopilotResponseInput data, 
    Dictionary<string, object?>? properties,
    [Service] CopilotResolver resolver,
    [Service] IHttpContextAccessor http) {
    // Extract X-CopilotCloud-Public-API-Key, start processing
    return resolver.ExecuteAsync(data, properties, http.HttpContext!);
  }
}

[SubscriptionType]
public class Subscription {
  [Subscribe]
  [Topic("copilot_stream")] // or dynamic topic per runId
  public async IAsyncEnumerable<CopilotResponse> CopilotStream(GenerateCopilotResponseInput data,
    [Service] CopilotResolver resolver, [EnumeratorCancellation] CancellationToken ct = default) {
    await foreach (var part in resolver.StreamAsync(data, ct)) yield return part;
  }
}
```

Resolver outline
- Build event pipeline, possibly spawn adapter/agent tasks.
- Map RuntimeEvent → GraphQL message objects.
- Merge final status and extensions; flush.

## 13. Compatibility and Migration Notes

- GraphQL contract is identical across implementations; clients remain unchanged.
- Streaming over WS/subscriptions is recommended; SSE fallback acceptable.
- Normalize errors with code/severity/visibility; redact secrets.
- Ensure consistent JSON encoding for action arguments/results and agent state.

## 14. Minimal Examples

Health
```
query { hello }
```

Discovery
```
query { availableAgents { agents { id name description } } }
```

Chat
```
mutation {
  generateCopilotResponse(
    data: {
      metadata: { requestType: Chat },
      frontend: { actions: [], url: "https://app" },
      messages: [{ id: "1", createdAt: "2025-01-01T00:00:00Z", textMessage: { role: user, content: "Plan a trip" } }]
    }
  ) { threadId runId messages { __typename } status { __typename } }
}
```

---

This standalone specification provides an end-to-end blueprint for implementing CopilotRuntime on ASP.NET Core with Semantic Kernel Agents, preserving the GraphQL API and protocol semantics while leveraging .NET-native streaming, adapters, observability, and cloud guardrails.
