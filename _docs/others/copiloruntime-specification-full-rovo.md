# CopilotRuntime Full Specification (Standalone)

## 1. Overview

CopilotRuntime is the backend runtime of CopilotKit. It acts as a GraphQL-based proxy between frontend applications and backend AI services and agent frameworks (such as LangGraph and CrewAI). The runtime orchestrates chat, tool/action execution, and multi-agent state, with incremental streaming of messages and meta-events.

This specification defines the complete public API contract, protocol semantics, event model, error handling, observability, cloud guardrails, and a concrete plan for a Python implementation using FastAPI and Strawberry GraphQL. It is self-contained and does not rely on other documents.

## 2. Architecture

The runtime exposes a GraphQL endpoint to frontend clients, translates inputs into service- and agent-specific requests, coordinates streaming events, and returns structured responses.

```
┌───────────────────────┐   GraphQL     ┌───────────────────────┐    REST-ish    ┌───────────────────────┐
│   Frontend Clients    │ over HTTP     │    CopilotRuntime     │   Protocol     │   Agent Frameworks     │
│ (React, Web, Mobile)  │──────────────▶│   (Python/FastAPI)    │──────────────▶│ (LangGraph, CrewAI…)   │
└───────────────────────┘               └───────────────────────┘               └───────────────────────┘
```

Key components
- GraphQL API Layer: exposes mutations and queries (e.g., generateCopilotResponse, availableAgents, loadAgentState)
- Runtime Engine: orchestrates LLM interactions, message processing, agent execution
- Event Streaming System: provides real-time bidirectional streaming using asyncio
- Service Adapters: abstract provider/framework differences (OpenAI, Anthropic, Google, LangChain, LangServe)
- Agent Integration: remote agents via CopilotKit endpoints and LangGraph Platform
- Action System: local, remote, and MCP-derived actions/tools
- Cloud Integration: optional guardrails, telemetry, and analytics
- Observability: structured logging, telemetry, performance metrics

## 3. GraphQL API Specification

### 3.1 Operations

Queries
- hello: String — health check returning "Hello World"
- availableAgents: AgentsResponse — discovery of agents from configured endpoints
- loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse — load persisted state for a given thread and agent

Mutations
- generateCopilotResponse(data: GenerateCopilotResponseInput, properties: JSONObject): CopilotResponse — main entry point for AI interactions (chat, tools, agents) with streaming responses

### 3.2 Enums

ActionInputAvailability
- disabled
- enabled
- remote

CopilotRequestType
- Chat
- Task
- TextareaCompletion
- TextareaPopover
- Suggestion

FailedResponseStatusReason
- GUARDRAILS_VALIDATION_FAILED
- MESSAGE_STREAM_INTERRUPTED
- UNKNOWN_ERROR

GuardrailsResultStatus
- ALLOWED
- DENIED

MessageRole
- user
- assistant
- system
- tool
- developer

MessageStatusCode
- Pending
- Success
- Failed

ResponseStatusCode
- Pending
- Success
- Failed

MetaEventName
- LangGraphInterruptEvent
- CopilotKitLangGraphInterruptEvent

### 3.3 Input Types

ActionInput
- name: String!
- description: String!
- jsonSchema: String!
- available: ActionInputAvailability

AgentSessionInput
- agentName: String!
- threadId: String
- nodeName: String

AgentStateInput
- agentName: String!
- state: String!
- config: String

CloudInput
- guardrails: GuardrailsInput

ContextPropertyInput
- value: String!
- description: String!

CustomPropertyInput
- key: String!
- value: Primitive!

ExtensionsInput
- openaiAssistantAPI: OpenAIApiAssistantAPIInput

ForwardedParametersInput
- model: String
- maxTokens: Int
- stop: [String]
- toolChoice: String
- toolChoiceFunctionName: String
- temperature: Float

FrontendInput
- toDeprecate_fullContext: String
- actions: [ActionInput!]!
- url: String

GenerateCopilotResponseInput
- metadata: GenerateCopilotResponseMetadataInput!
- threadId: String
- runId: String
- messages: [MessageInput!]!
- frontend: FrontendInput!
- cloud: CloudInput
- forwardedParameters: ForwardedParametersInput
- agentSession: AgentSessionInput
- agentState: AgentStateInput
- agentStates: [AgentStateInput]
- extensions: ExtensionsInput
- metaEvents: [MetaEventInput]

GenerateCopilotResponseMetadataInput
- requestType: CopilotRequestType

GuardrailsInput
- inputValidationRules: GuardrailsRuleInput!

GuardrailsRuleInput
- allowList: [String]
- denyList: [String]

LoadAgentStateInput
- threadId: String!
- agentName: String!

MessageInput (union by which field is set)
- id: String!
- createdAt: Date!
- textMessage: TextMessageInput
- actionExecutionMessage: ActionExecutionMessageInput
- resultMessage: ResultMessageInput
- agentStateMessage: AgentStateMessageInput
- imageMessage: ImageMessageInput

TextMessageInput
- content: String!
- parentMessageId: String
- role: MessageRole!

ActionExecutionMessageInput
- name: String!
- arguments: String!  (JSON-encoded string)
- parentMessageId: String
- scope: String  (deprecated)

ResultMessageInput
- actionExecutionId: String!
- actionName: String!
- parentMessageId: String
- result: String!  (JSON-encoded string; may include error data)

AgentStateMessageInput
- threadId: String!
- agentName: String!
- role: MessageRole!
- state: String!  (JSON-encoded string)
- running: Boolean!
- nodeName: String!
- runId: String!
- active: Boolean!

ImageMessageInput
- format: String!
- bytes: String!
- parentMessageId: String
- role: MessageRole!

MetaEventInput
- name: MetaEventName!
- value: String
- response: String
- messages: [MessageInput]

OpenAIApiAssistantAPIInput
- runId: String
- threadId: String

### 3.4 Object Types

Agent
- id: String!
- name: String!
- description: String

AgentsResponse
- agents: [Agent!]!

CopilotResponse
- threadId: String!
- status: ResponseStatus!
- runId: String
- messages: [BaseMessageOutput!]!
- extensions: ExtensionsResponse
- metaEvents: [BaseMetaEvent]

BaseMessageOutput (Interface)
- id: String!
- createdAt: Date!
- status: MessageStatus!

TextMessageOutput (implements BaseMessageOutput)
- role: MessageRole!
- content: [String!]!  (streamed chunks)
- parentMessageId: String

ActionExecutionMessageOutput (implements BaseMessageOutput)
- name: String!
- scope: String
- arguments: [String!]!  (streamed chunks)
- parentMessageId: String

ResultMessageOutput (implements BaseMessageOutput)
- actionExecutionId: String!
- actionName: String!
- result: String!

AgentStateMessageOutput (implements BaseMessageOutput)
- threadId: String!
- agentName: String!
- nodeName: String!
- runId: String!
- active: Boolean!
- role: MessageRole!
- state: String!
- running: Boolean!

ImageMessageOutput (implements BaseMessageOutput)
- format: String!
- bytes: String!
- role: MessageRole!
- parentMessageId: String

ExtensionsResponse
- openaiAssistantAPI: OpenAIApiAssistantAPIResponse

OpenAIApiAssistantAPIResponse
- runId: String
- threadId: String

GuardrailsResult
- status: GuardrailsResultStatus!
- reason: String

LoadAgentStateResponse
- threadId: String!
- threadExists: Boolean!
- state: String!
- messages: String!

MessageStatus (Union)
- PendingMessageStatus { code: MessageStatusCode! }
- SuccessMessageStatus { code: MessageStatusCode! }
- FailedMessageStatus { code: MessageStatusCode!, reason: String! }

ResponseStatus (Union)
- PendingResponseStatus { code: ResponseStatusCode! }
- SuccessResponseStatus { code: ResponseStatusCode! }
- FailedResponseStatus { code: ResponseStatusCode!, reason: FailedResponseStatusReason!, details: JSONObject }

BaseMetaEvent (Interface)
- type: String!
- name: MetaEventName!

LangGraphInterruptEvent (implements BaseMetaEvent)
- name: MetaEventName!
- value: String!
- response: String

CopilotKitLangGraphInterruptEvent (implements BaseMetaEvent)
- name: MetaEventName!
- data: { value: String!, messages: [BaseMessageOutput!]! }
- response: String

### 3.5 Authentication

When the `cloud` input is provided to `generateCopilotResponse`, clients must include a public API key in the `X-CopilotCloud-Public-API-Key` header. The runtime validates presence/format and may forward it to Copilot Cloud endpoints for guardrails and analytics.

## 4. Protocol and Flow Semantics

### 4.1 Response Streaming Behavior

- Messages and meta-events are delivered incrementally. The runtime may use streaming transports (e.g., GraphQL subscriptions, @stream/@defer, Server-Sent Events, or WebSockets). A non-streaming fallback is allowed in MVP, but clients should support incremental updates.
- The `status` field resolves to success or failure after the stream completes or aborts.

### 4.2 Runtime Event Types and Sequences

Canonical event sequences
- Text response: TextMessageStart → TextMessageContent* → TextMessageEnd
- Action call: ActionExecutionStart → ActionExecutionArgs* → ActionExecutionEnd → ActionExecutionResult
- Agent state: AgentStateMessage (periodic updates)
- Meta events: LangGraphInterruptEvent | CopilotKitLangGraphInterruptEvent

Event structures (representative JSON)

TextMessageStart
```
{
  "type": "TextMessageStart",
  "messageId": "msg_123",
  "parentMessageId": "msg_parent"  // optional
}
```

TextMessageContent
```
{
  "type": "TextMessageContent",
  "messageId": "msg_123",
  "content": "partial token chunk"
}
```

TextMessageEnd
```
{
  "type": "TextMessageEnd",
  "messageId": "msg_123"
}
```

ActionExecutionStart
```
{
  "type": "ActionExecutionStart",
  "actionExecutionId": "act_001",
  "actionName": "get_weather",
  "parentMessageId": "msg_123" // optional
}
```

ActionExecutionArgs
```
{
  "type": "ActionExecutionArgs",
  "actionExecutionId": "act_001",
  "args": "{\"city\":\"Paris\"}" // streamed JSON chunks allowed
}
```

ActionExecutionEnd
```
{
  "type": "ActionExecutionEnd",
  "actionExecutionId": "act_001"
}
```

ActionExecutionResult
```
{
  "type": "ActionExecutionResult",
  "actionName": "get_weather",
  "actionExecutionId": "act_001",
  "result": "{\"forecast\":\"sunny\"}" // JSON-encoded result; may include error
}
```

AgentStateMessage
```
{
  "type": "AgentStateMessage",
  "threadId": "t_abc",
  "agentName": "planner",
  "nodeName": "plan",
  "runId": "run_1",
  "active": true,
  "role": "assistant",
  "state": "{...}",  // JSON-encoded
  "running": true
}
```

MetaEvent (LangGraphInterruptEvent)
```
{
  "type": "MetaEvent",
  "name": "LangGraphInterruptEvent",
  "value": "{...}",
  "response": "{...}" // optional
}
```

### 4.3 Guardrails (Optional)

- If `cloud.guardrails` is present and the last message is from `user`, the runtime posts to Copilot Cloud `/guardrails/validate` with `{ input, messages, allowList, denyList }`.
- On denial, the runtime interrupts message streaming and returns `FailedResponseStatus` (reason: GUARDRAILS_VALIDATION_FAILED) and an assistant `TextMessageOutput` that explains the reason.

### 4.4 Agent vs Standard Runs

- Agent Run: If `agentSession` is provided (and the runtime is not delegating to the LLM adapter), the request is routed to agent processing. The targeted agent is represented as a `RemoteAgentAction`. The runtime constructs `availableActionsForCurrentAgent` (all actions except self) and streams agent-originated events.
- Standard Run: If not an agent run, the configured LLM service adapter processes the messages, optionally calling actions/tools during generation.

### 4.5 Headers and Context Properties

- `X-CopilotCloud-Public-API-Key` is used for cloud features and telemetry.
- The `properties` argument (JSONObject) is merged into request context. Providers, remote endpoints, or adapters may read these properties.
- Common forwarded properties include authorization (for LangGraph Platform) and dynamic MCP server configuration.

### 4.6 Remote Actions and Agent Protocol

Self-hosted CopilotKit endpoints
- Discovery: `POST {endpoint}/info` → `{ actions: Action[], agents: Agent[] }`
- Actions: `POST {endpoint}/actions/execute` with `{ name, arguments, properties }` → `{ result }`
- Agents: `POST {endpoint}/agents/execute` with `{ name, threadId, nodeName, messages, state, config, properties, actions, metaEvents }` → JSONL stream of runtime events

LangGraph Platform endpoints
- Discovery via SDK (e.g., `assistants.search()`)
- Execution via `runs.stream(...)`; translate events to `RuntimeEvent`

Headers
- Constructed via optional `onBeforeRequest` hooks; include `Content-Type: application/json` and any custom entries.

### 4.7 MCP Tooling (Experimental)

- At request time, the runtime can fetch tools from MCP servers defined in configuration or provided via `properties.mcpServers`.
- Tools are converted to server-side actions; instruction text is injected into a system message to guide tool usage.

## 5. Event System and Streaming Architecture

The TypeScript runtime uses RxJS observables. The Python port replicates this with asyncio constructs.

Core components
- RuntimeEventSource: central event emitter and coordinator with history and per-subscriber queues
- Event streams: async generators that GraphQL resolvers can iterate over to push incremental updates
- Coordination: asyncio.Event/Task for branching flows (e.g., execute actions while continuing message streaming)

Python reference implementation (abridged)

```python
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator

class RuntimeEventTypes(Enum):
    TEXT_MESSAGE_START = "TextMessageStart"
    TEXT_MESSAGE_CONTENT = "TextMessageContent"
    TEXT_MESSAGE_END = "TextMessageEnd"
    ACTION_EXECUTION_START = "ActionExecutionStart"
    ACTION_EXECUTION_ARGS = "ActionExecutionArgs"
    ACTION_EXECUTION_END = "ActionExecutionEnd"
    ACTION_EXECUTION_RESULT = "ActionExecutionResult"
    AGENT_STATE_MESSAGE = "AgentStateMessage"
    META_EVENT = "MetaEvent"

@dataclass
class RuntimeEvent:
    type: RuntimeEventTypes
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    message_id: Optional[str] = None
    parent_message_id: Optional[str] = None

class RuntimeEventSource:
    def __init__(self, max_history: int = 1000):
        self._subscribers: List[asyncio.Queue] = []
        self._history: List[RuntimeEvent] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    async def emit(self, event: RuntimeEvent):
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            for q in list(self._subscribers):
                await q.put(event)

    async def subscribe(self, replay_history: bool = False, qsize: int = 100) -> AsyncGenerator[RuntimeEvent, None]:
        q = asyncio.Queue(maxsize=qsize)
        async with self._lock:
            self._subscribers.append(q)
            if replay_history:
                for e in self._history:
                    await q.put(e)
        try:
            while True:
                yield await q.get()
        finally:
            async with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)
```

JSON-Line streaming utility

```python
import json
from typing import AsyncGenerator, Dict, List

async def process_jsonl_stream(response_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[Dict, None]:
    buffer: List[str] = []
    async for chunk in response_stream:
        buffer.append(chunk.decode('utf-8'))
        current = ''.join(buffer)
        if '\n' not in current:
            continue
        parts = current.split('\n')
        trailing_complete = current.endswith('\n')
        buffer = []
        if not trailing_complete:
            buffer.append(parts.pop())
        for part in parts:
            part = part.strip()
            if part:
                try:
                    yield json.loads(part)
                except json.JSONDecodeError:
                    continue
```

## 6. Service Adapters and Message Conversion

Adapter interface (conceptual TypeScript; mirrored in Python)

```typescript
interface CopilotServiceAdapter {
  process(request: CopilotRuntimeChatCompletionRequest): Promise<CopilotRuntimeChatCompletionResponse>
}

interface CopilotRuntimeChatCompletionRequest {
  eventSource: RuntimeEventSource
  messages: Message[]
  actions: ActionInput[]
  model?: string
  threadId?: string
  runId?: string
  forwardedParameters?: ForwardedParametersInput
  extensions?: ExtensionsInput
  agentSession?: AgentSessionInput
  agentStates?: AgentStateInput[]
}

interface CopilotRuntimeChatCompletionResponse {
  threadId: string
  runId?: string
  extensions?: ExtensionsResponse
}
```

Typical built-in adapters
- OpenAIAdapter — direct OpenAI Chat API
- AnthropicAdapter — Claude
- GoogleAdapter — Gemini
- LangChainAdapter — LangChain runnables
- LangServeAdapter — remote chains via HTTP streaming
- EmptyAdapter — agent-only mode, no LLM

Message conversion patterns
- GraphQL input → internal message model
- Internal model → provider-specific formats (OpenAI, Anthropic, Google)
- Role mapping (e.g., system → developer for specific providers)
- Parse JSON-bearing fields: action arguments, results, agent state

Event emission in adapters
- Emit TextMessageStart/Content/End for model output
- Emit ActionExecutionStart/Args/End and ActionExecutionResult for tool calls
- Convert provider errors to structured runtime errors

## 7. Agent and Remote Endpoint Integration

Endpoint types
- CopilotKit endpoints: `/info`, `/actions/execute`, `/agents/execute` (agents return JSONL stream of runtime events)
- LangGraph Platform: discovery via SDK; execution via `runs.stream`

Execution flow (agent run)
1. Determine target agent (from `agentSession`), represent it as `RemoteAgentAction`.
2. Build available action/tool set excluding the agent itself to avoid loops.
3. Forward messages, state, config, properties, actions, and metaEvents to the agent endpoint.
4. Process JSONL events from the agent; convert each line into a RuntimeEvent and integrate into the main stream.
5. Continue LLM generation after action results if applicable.

## 8. Error Handling and Helpful Messages

Error codes and classes (Python)

```python
from enum import Enum
from typing import Optional, Dict, Any

class CopilotKitErrorCode(Enum):
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    API_NOT_FOUND = "API_NOT_FOUND"
    UNKNOWN = "UNKNOWN"

class Severity(Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

class Visibility(Enum):
    USER = "USER"
    DEVELOPER = "DEVELOPER"
    INTERNAL = "INTERNAL"

class CopilotKitError(Exception):
    def __init__(self, message: str, code: CopilotKitErrorCode = CopilotKitErrorCode.UNKNOWN,
                 severity: Severity = Severity.ERROR, visibility: Visibility = Visibility.DEVELOPER,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.severity = severity
        self.visibility = visibility
        self.context = context or {}

class CopilotKitLowLevelError(CopilotKitError):
    def __init__(self, error: Exception, url: Optional[str] = None, message: Optional[str] = None, status_code: Optional[int] = None):
        self.original_error = error
        self.url = url
        self.status_code = status_code
        if status_code == 401:
            code = CopilotKitErrorCode.AUTHENTICATION_ERROR
        elif status_code and 400 <= status_code < 500:
            code = CopilotKitErrorCode.CONFIGURATION_ERROR
        elif status_code and status_code >= 500:
            code = CopilotKitErrorCode.NETWORK_ERROR
        else:
            code = CopilotKitErrorCode.NETWORK_ERROR
        super().__init__(message or f"Low-level error: {str(error)}", code=code)
```

Helpful error messages

```python
ERROR_PATTERNS = {
    "ConnectionError": {
        "message": "Connection refused - the agent service is not running or not accessible. Please check that your agent is started and listening on the correct port.",
        "category": "network",
        "actionable": True
    },
    "AuthenticationError": {
        "message": "OpenAI authentication failed. Please check your OPENAI_API_KEY environment variable or API key configuration.",
        "category": "authentication",
        "actionable": True
    },
    "RateLimitError": {
        "message": "OpenAI rate limit exceeded. Please wait and try again, or check your usage limits.",
        "category": "network",
        "actionable": True
    }
}

def generate_helpful_error_message(error: Exception, context: str = "connection") -> str:
    et = type(error).__name__
    base = str(error)
    if et in ERROR_PATTERNS:
        return ERROR_PATTERNS[et]["message"].replace("{context}", context)
    for pattern, cfg in ERROR_PATTERNS.items():
        if pattern.lower() in base.lower():
            return cfg["message"].replace("{context}", context)
    if isinstance(error, (ConnectionError, ConnectionRefusedError)):
        return "A network error occurred while connecting to the agent service. Please check your connection and ensure the agent service is running."
    if "authentication" in base.lower() or "api key" in base.lower():
        return "Authentication failed. Please check your API keys and credentials."
    return "An unexpected error occurred. Please check the logs for more details."
```

Error context and enrichment (conceptual)
- Capture request/response timing, threadId/runId, agent info, environment, and stack traces
- Attach helpful messages and retry guidance

## 9. Observability and Middleware

Progressive vs batched logging
- Progressive mode: stream and log each content chunk as it is emitted
- Batched mode: log only final responses

Lifecycle middleware hooks

```python
class MiddlewareContext:
    def __init__(self, thread_id, run_id, input_messages, properties, url=None):
        self.thread_id = thread_id
        self.run_id = run_id
        self.input_messages = input_messages
        self.properties = properties
        self.url = url

class CopilotMiddleware:
    def __init__(self, on_before_request=None, on_after_request=None):
        self.on_before_request = on_before_request
        self.on_after_request = on_after_request
```

Observability hooks and payloads

```python
from dataclasses import dataclass
from typing import Optional, Any
import time

@dataclass
class LLMRequestData:
    thread_id: Optional[str]
    run_id: Optional[str]
    model: Optional[str]
    messages: list
    actions: Optional[list]
    forwarded_parameters: Optional[dict]
    timestamp: float
    provider: Optional[str]

@dataclass
class LLMResponseData:
    thread_id: str
    run_id: Optional[str]
    model: Optional[str]
    output: Any
    latency: float
    timestamp: float
    provider: Optional[str]
    is_progressive_chunk: bool = False
    is_final_response: bool = False
```

Telemetry and analytics (conceptual)
- Track request creation, progressive chunks (optional), final responses, and errors
- Support global properties and per-event properties

Performance monitoring (conceptual)
- Record per-operation timers and custom metrics

Health checks (HTTP)
- Provide `/health` endpoint with aggregated system checks

## 10. Cloud Integration and Guardrails

Authentication and headers
- Validate `X-CopilotCloud-Public-API-Key` when cloud features used
- Forward authenticated headers on cloud calls

Guardrails flow
1. Extract validation context (messages, lists)
2. POST to `/guardrails/validate` with API key
3. On DENIED, block and return failure response with reason and assistant message

Analytics and monitoring
- Optional usage tracking and error reporting endpoints
- Batched metrics with interval flush and retry

## 11. Python Implementation Strategy

Web framework
- FastAPI application with Strawberry GraphQL
- Async-first implementation with asyncio

GraphQL schema structure (Strawberry example)

```python
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import AsyncGenerator

@strawberry.type
class Query:
    @strawberry.field
    async def hello(self) -> str:
        return "Hello World"

@strawberry.type
class Mutation:
    @strawberry.field
    async def generate_copilot_response(self, data: "GenerateCopilotResponseInput") -> "CopilotResponse":
        ...

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def copilot_stream(self, data: "GenerateCopilotResponseInput") -> AsyncGenerator["CopilotResponse", None]:
        ...

schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
graphql_app = GraphQLRouter(schema)
```

Pydantic data models (example)

```python
from pydantic import BaseModel
from enum import Enum
from typing import Optional, List

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    DEVELOPER = "developer"

class TextMessageInput(BaseModel):
    content: str
    parent_message_id: Optional[str] = None
    role: MessageRole

class ActionInput(BaseModel):
    name: str
    description: str
    json_schema: str
    available: Optional[str] = None
```

Event streaming (async generators)
- Use `RuntimeEventSource` and per-request coordinators
- GraphQL subscription yields events/messages as they arrive

Service adapters (Python interface)
- Abstract base with `process(request) -> response`
- Implement adapters for OpenAI, Anthropic, Google, LangChain, LangServe

Remote endpoints
- HTTP client with retries and streaming readers
- JSONL parsing for agent event streams

## 12. Implementation Phases and Dependencies

Phases
1. Core infrastructure: FastAPI, Strawberry, Pydantic models
2. Event system and GraphQL streaming
3. Service adapters (Empty, OpenAI) + registry
4. LangGraph integration (discovery + streaming)
5. Cloud guardrails and observability
6. Testing (unit, integration, E2E) and documentation

Core dependencies
- fastapi, uvicorn
- strawberry-graphql (or ariadne)
- pydantic
- httpx
- langgraph, langchain (as needed)
- openai/anthropic/google SDKs (as needed)

## 13. Compatibility and Migration Notes

- Maintain API compatibility with the TypeScript implementation
- Support non-streaming responses first; add streaming with subscriptions/SSE/multipart
- Normalize errors with `code`, `severity`, `visibility`; include debugging context
- Filter internal endpoint details from public responses
- Provide progressive logging configuration; allow batched mode

## 14. Minimal Example Exchanges

Health check
```
query { hello }
```

Agent discovery
```
query { availableAgents { agents { id name description } } }
```

Simplified chat (non-streaming)
```
mutation {
  generateCopilotResponse(
    data: {
      metadata: { requestType: Chat },
      frontend: { actions: [], url: "https://app" },
      messages: [
        { id: "1", createdAt: "2024-01-01T00:00:00Z", textMessage: { role: user, content: "Hello" } }
      ]
    }
  ) {
    threadId
    runId
    messages {
      __typename
      ... on TextMessageOutput { content role }
    }
    status { __typename }
  }
}
```

---

This standalone specification unifies the GraphQL contract, protocol semantics, runtime event model, adapter patterns, agent integrations, error handling, observability, cloud guardrails, and a detailed Python implementation plan to guide a faithful and maintainable CopilotRuntime implementation.
