# CopilotRuntime: Complete Technical Specification

## 1. Overview & Architecture

### 1.1. Purpose

This document provides a complete, self-contained technical specification for the CopilotRuntime. It is designed to guide the implementation of a Python-based version of the runtime, ensuring full feature parity and behavioral consistency with the original TypeScript implementation.

CopilotRuntime is the core backend component of CopilotKit. It functions as a sophisticated GraphQL proxy, bridging frontend components with backend AI services and agentic frameworks (like LangGraph and CrewAI). It orchestrates complex interactions, including chat, tool/action execution, and multi-agent state management, delivering responses and updates via an incremental, real-time event stream.

### 1.2. Architectural Diagram & Components

The CopilotRuntime acts as a central hub in the CopilotKit ecosystem.

```
┌─────────────────────┐    GraphQL     ┌─────────────────────┐    REST-ish    ┌─────────────────────┐
│                     │   over HTTP    │                     │   Protocol     │                     │
│   Frontend React    │ ──────────────▶│   CopilotRuntime    │ ──────────────▶│   Agent Frameworks  │
│   Components        │                │   (Python/FastAPI)  │                │   (LangGraph,       │
│                     │                │                     │                │    CrewAI, etc.)    │
└─────────────────────┘                └─────────────────────┘                └─────────────────────┘
```

#### Key Components:

1.  **GraphQL API Layer**: Exposes the `generateCopilotResponse` mutation and related queries, serving as the single point of entry for clients.
2.  **Runtime Engine**: The core orchestrator for LLM interactions, message processing, and agent execution.
3.  **Event Streaming System**: A real-time, bidirectional communication backbone built on `asyncio` streams, enabling incremental updates to the client.
4.  **Service Adapters**: A pluggable interface to abstract communication with various LLM providers (OpenAI, Anthropic, etc.) and other AI frameworks.
5.  **Agent Integration**: A system for discovering and connecting to external agentic frameworks via a standardized remote action protocol.
6.  **Action System**: A mechanism for defining and executing both server-side and client-side actions (tools).
7.  **Cloud Integration**: An optional layer for integrating with Copilot Cloud to enable enterprise-grade features like guardrails, advanced observability, and analytics.

---

## 2. GraphQL API Specification

This section defines the complete, unabridged GraphQL contract.

### 2.1. Operations

#### Queries

-   **`hello: String`**
    -   A simple health-check query that returns the static string "Hello World".

-   **`availableAgents: AgentsResponse`**
    -   Discovers and returns a list of all available agents from configured local and remote endpoints.
    -   **Response**: `AgentsResponse`

-   **`loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse`**
    -   Loads the persisted state of a specific agent for a given conversation thread.
    -   **Arguments**: `data: LoadAgentStateInput`
    -   **Response**: `LoadAgentStateResponse`

#### Mutations

-   **`generateCopilotResponse(data: GenerateCopilotResponseInput, properties: JSONObject): CopilotResponse`**
    -   The main entry point for all AI interactions. It processes user input, orchestrates backend services, and generates a stream of response messages and events.
    -   **Arguments**:
        -   `data`: `GenerateCopilotResponseInput` - The primary input containing messages, actions, and session information.
        -   `properties`: `JSONObject` (optional) - Additional, arbitrary data for the request context.
    -   **Response**: `CopilotResponse`

### 2.2. Enums

-   **`ActionInputAvailability`**: `disabled`, `enabled`, `remote`
-   **`CopilotRequestType`**: `Chat`, `Task`, `TextareaCompletion`, `TextareaPopover`, `Suggestion`
-   **`FailedResponseStatusReason`**: `GUARDRAILS_VALIDATION_FAILED`, `MESSAGE_STREAM_INTERRUPTED`, `UNKNOWN_ERROR`
-   **`GuardrailsResultStatus`**: `ALLOWED`, `DENIED`
-   **`MessageRole`**: `user`, `assistant`, `system`, `tool`, `developer`
-   **`MessageStatusCode`**: `Pending`, `Success`, `Failed`
-   **`ResponseStatusCode`**: `Pending`, `Success`, `Failed`
-   **`MetaEventName`**: `LangGraphInterruptEvent`, `CopilotKitLangGraphInterruptEvent`

### 2.3. Input Types

-   **`ActionInput`**: `{ name: String!, description: String!, jsonSchema: String!, available: ActionInputAvailability }`
-   **`AgentSessionInput`**: `{ agentName: String!, threadId: String, nodeName: String }`
-   **`AgentStateInput`**: `{ agentName: String!, state: String!, config: String }`
-   **`CloudInput`**: `{ guardrails: GuardrailsInput }`
-   **`ContextPropertyInput`**: `{ value: String!, description: String! }`
-   **`CustomPropertyInput`**: `{ key: String!, value: Primitive! }`
-   **`ExtensionsInput`**: `{ openaiAssistantAPI: OpenAIApiAssistantAPIInput }`
-   **`ForwardedParametersInput`**: `{ model: String, maxTokens: Int, stop: [String], toolChoice: String, toolChoiceFunctionName: String, temperature: Float }`
-   **`FrontendInput`**: `{ toDeprecate_fullContext: String, actions: [ActionInput!]!, url: String }`
-   **`GenerateCopilotResponseInput`**: `{ metadata: GenerateCopilotResponseMetadataInput!, threadId: String, runId: String, messages: [MessageInput!]!, frontend: FrontendInput!, cloud: CloudInput, forwardedParameters: ForwardedParametersInput, agentSession: AgentSessionInput, agentState: AgentStateInput, agentStates: [AgentStateInput], extensions: ExtensionsInput, metaEvents: [MetaEventInput] }`
-   **`GenerateCopilotResponseMetadataInput`**: `{ requestType: CopilotRequestType }`
-   **`GuardrailsInput`**: `{ inputValidationRules: GuardrailsRuleInput! }`
-   **`GuardrailsRuleInput`**: `{ allowList: [String], denyList: [String] }`
-   **`LoadAgentStateInput`**: `{ threadId: String!, agentName: String! }`
-   **`MessageInput`**: A union of the following, distinguished by which field is non-null: `{ id: String!, createdAt: Date!, textMessage: TextMessageInput, actionExecutionMessage: ActionExecutionMessageInput, resultMessage: ResultMessageInput, agentStateMessage: AgentStateMessageInput, imageMessage: ImageMessageInput }`
-   **`TextMessageInput`**: `{ content: String!, parentMessageId: String, role: MessageRole! }`
-   **`ActionExecutionMessageInput`**: `{ name: String!, arguments: String!, parentMessageId: String, scope: String }`
-   **`ResultMessageInput`**: `{ actionExecutionId: String!, actionName: String!, parentMessageId: String, result: String! }`
-   **`AgentStateMessageInput`**: `{ threadId: String!, agentName: String!, role: MessageRole!, state: String!, running: Boolean!, nodeName: String!, runId: String!, active: Boolean! }`
-   **`ImageMessageInput`**: `{ format: String!, bytes: String!, parentMessageId: String, role: MessageRole! }`
-   **`MetaEventInput`**: `{ name: MetaEventName!, value: String, response: String, messages: [MessageInput] }`
-   **`OpenAIApiAssistantAPIInput`**: `{ runId: String, threadId: String }`

### 2.4. Object Types

-   **`Agent`**: `{ id: String!, name: String!, description: String }`
-   **`AgentsResponse`**: `{ agents: [Agent!]! }`
-   **`CopilotResponse`**: `{ threadId: String!, status: ResponseStatus!, runId: String, messages: [BaseMessageOutput!]!, extensions: ExtensionsResponse, metaEvents: [BaseMetaEvent] }`
-   **`BaseMessageOutput` (Interface)**: `{ id: String!, createdAt: Date!, status: MessageStatus! }`
-   **`TextMessageOutput` (implements `BaseMessageOutput`)**: `{ role: MessageRole!, content: [String!]!, parentMessageId: String }`
-   **`ActionExecutionMessageOutput` (implements `BaseMessageOutput`)**: `{ name: String!, scope: String, arguments: [String!]!, parentMessageId: String }`
-   **`ResultMessageOutput` (implements `BaseMessageOutput`)**: `{ actionExecutionId: String!, actionName: String!, result: String! }`
-   **`AgentStateMessageOutput` (implements `BaseMessageOutput`)**: `{ threadId: String!, agentName: String!, nodeName: String!, runId: String!, active: Boolean!, role: MessageRole!, state: String!, running: Boolean! }`
-   **`ImageMessageOutput` (implements `BaseMessageOutput`)**: `{ format: String!, bytes: String!, role: MessageRole!, parentMessageId: String }`
-   **`ExtensionsResponse`**: `{ openaiAssistantAPI: OpenAIApiAssistantAPIResponse }`
-   **`OpenAIApiAssistantAPIResponse`**: `{ runId: String, threadId: String }`
-   **`GuardrailsResult`**: `{ status: GuardrailsResultStatus!, reason: String }`
-   **`LoadAgentStateResponse`**: `{ threadId: String!, threadExists: Boolean!, state: String!, messages: String! }`
-   **`MessageStatus` (Union)**: `PendingMessageStatus`, `SuccessMessageStatus`, `FailedMessageStatus`
-   **`PendingMessageStatus`**: `{ code: MessageStatusCode! }`
-   **`SuccessMessageStatus`**: `{ code: MessageStatusCode! }`
-   **`FailedMessageStatus`**: `{ code: MessageStatusCode!, reason: String! }`
-   **`ResponseStatus` (Union)**: `PendingResponseStatus`, `SuccessResponseStatus`, `FailedResponseStatus`
-   **`PendingResponseStatus`**: `{ code: ResponseStatusCode! }`
-   **`SuccessResponseStatus`**: `{ code: ResponseStatusCode! }`
-   **`FailedResponseStatus`**: `{ code: ResponseStatusCode!, reason: FailedResponseStatusReason!, details: JSONObject }`
-   **`BaseMetaEvent` (Interface)**: `{ type: String!, name: MetaEventName! }`
-   **`LangGraphInterruptEvent` (implements `BaseMetaEvent`)**: `{ name: MetaEventName!, value: String!, response: String }`
-   **`CopilotKitLangGraphInterruptEvent` (implements `BaseMetaEvent`)**: `{ name: MetaEventName!, data: CopilotKitLangGraphInterruptEventData!, response: String }`
-   **`CopilotKitLangGraphInterruptEventData`**: `{ value: String!, messages: [BaseMessageOutput!]! }`

---

## 3. Core Flows and Behaviors

### 3.1. `generateCopilotResponse` Flow

1.  **Context & Authentication**: The server receives the mutation. It merges the `properties` argument into the request context and extracts the `x-copilotcloud-public-api-key` header if present for use with cloud features.
2.  **Guardrails (Optional)**: If `cloud.guardrails` is configured and the last message is from a `user`, the runtime makes a `POST` call to the Copilot Cloud `/guardrails/validate` endpoint. If the input is denied, the runtime interrupts the normal flow, streams a `GuardrailsValidationFailureResponse`, and returns an assistant message explaining the reason.
3.  **Agent vs. Standard Run**: The runtime inspects the `agentSession` input.
    -   **Agent Run**: If `agentSession` is present, the runtime delegates to its `processAgentRequest` logic. It identifies the target agent as a special `RemoteAgentAction`, then compiles a list of available tools for that agent, which includes all other server-side actions and *other* agents (to prevent recursion). It then calls the agent's `remoteAgentHandler` to obtain a stream of `RuntimeEvent`s, which are bridged into the main GraphQL response.
    -   **Standard Run**: If `agentSession` is absent, the runtime proceeds with `processRuntimeRequest`. It uses the default configured `serviceAdapter` (e.g., `OpenAIAdapter`) and provides it with all available server-side actions.
4.  **Event Streaming**: The core of the response is a real-time stream of `RuntimeEvent` items, which are mapped to the GraphQL `CopilotResponse` object. Messages and meta-events are delivered incrementally to the client as they are generated.
5.  **Completion and Error Handling**: The `status` field of the response resolves to `Success` or `Failed` only after the stream completes or aborts. Any errors that occur during streaming are caught, converted to structured `CopilotKitError` types, and reflected in the final `status`.

### 3.2. Streaming Behavior

-   The response is delivered incrementally. The primary mechanism for this is the `messages` field, which is a stream of `BaseMessageOutput` objects.
-   Within certain messages (`TextMessageOutput`, `ActionExecutionMessageOutput`), the `content` and `arguments` fields are themselves streams of strings, allowing for token-by-token and argument-by-argument streaming.
-   The runtime produces a sequence of internal `RuntimeEvent` items that drive the stream:
    -   **Text Sequence**: `TextMessageStart` → `TextMessageContent*` → `TextMessageEnd`
    -   **Action Sequence**: `ActionExecutionStart` → `ActionExecutionArgs*` → `ActionExecutionEnd` → `ActionExecutionResult`
    -   **Agent State**: `AgentStateMessage` (for real-time updates on agent progress)
    -   **Meta Events**: `MetaEvent` (e.g., for LangGraph interrupts)

### 3.3. Agent Execution Flow

1.  The client specifies an `agentSession` in the `generateCopilotResponse` request.
2.  The runtime routes the request to agent-specific processing logic.
3.  The corresponding agent framework (e.g., LangGraph) takes control of the execution flow.
4.  The runtime continuously streams agent state updates back to the client via `AgentStateMessageOutput` events.
5.  During its execution, the agent can invoke any of the available tools (actions).
6.  The runtime coordinates the execution of these actions and streams the results back to the agent, which then continues its process.

---

## 4. Deep Dive: Core Components & Implementation Patterns

### 4.1. Event System: From RxJS to AsyncIO

The original TypeScript implementation relies heavily on RxJS for managing complex, reactive event streams. The Python implementation will achieve the same behavior using `asyncio`.

**RxJS Pattern Translation:**

-   **`ReplaySubject` / `shareReplay()`**: An `asyncio.Queue` is created for each subscriber. A central `RuntimeEventSource` class manages a list of these queues. When an event is emitted, it is `put` into every subscriber's queue, effectively multicasting the event. A history buffer can be maintained in the source to replay events for new subscribers.
-   **`scan()` (State Accumulation)**: A state dictionary is maintained within the `RuntimeEventSource` or a processing layer. As each event passes through, a reducer function updates the state, making the current state available to subsequent logic.
-   **`concatMap()` (Conditional Stream Branching)**: When an event requires a new, dependent asynchronous operation (like executing a tool after `ActionExecutionEnd`), a new `asyncio.Task` is created (`asyncio.create_task`). The events from this background task are fed back into the main event queue, effectively merging the new stream of events into the main one.
-   **`catchError()`**: Standard `try...except` blocks around the main event processing loop will catch errors. These errors are then converted into structured error events and yielded to the client before gracefully closing the stream.

### 4.2. Service Adapter Pattern

The Service Adapter is an abstraction layer that decouples the runtime core from the specifics of any given LLM or AI framework.

**Adapter Interface (`CopilotServiceAdapter`):**

```python
from abc import ABC, abstractmethod

class CopilotServiceAdapter(ABC):
    @abstractmethod
    async def process(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        pass
```

**Adapter Responsibilities:**

1.  **Message Translation**: Convert the generic CopilotKit message format into the provider-specific format (e.g., OpenAI's `ChatCompletionMessageParam`).
2.  **Tool/Action Formatting**: Convert CopilotKit actions into the provider's tool-calling format.
3.  **Streaming & Event Emission**: Handle the provider's response stream (e.g., an `AsyncStream` from `openai.chat.completions.create`). For each chunk received, it must parse the content and emit the corresponding `RuntimeEvent` (e.g., `TextMessageContent`, `ActionExecutionStart`) to the central `RuntimeEventSource`.
4.  **Error Translation**: Catch provider-specific exceptions (e.g., `openai.APIError`) and convert them into structured `CopilotKitError`s.

### 4.3. Remote Actions & Agent Integration

Agents are treated as a special type of remote action, allowing for a unified orchestration mechanism.

**Multi-Endpoint Agent Discovery:**

The runtime can discover agents from multiple sources:
1.  **Self-Hosted CopilotKit Endpoints**: These expose a `/info` endpoint that the runtime can query to get a list of available actions and agents.
2.  **LangGraph Platform**: A managed service where agents are discovered via the LangGraph SDK.
3.  **In-Process Agents**: Python agent objects defined directly in the runtime configuration.

**Remote Execution & Event Streaming:**

Execution of a remote agent involves a `POST` request to the agent's endpoint. The crucial requirement is that the endpoint must respond with a **JSON-line (`jsonl`) stream**. Each line in the response body is a JSON object representing a single `RuntimeEvent`. The runtime consumes this stream and processes each event as if it were generated locally.

This `jsonl` streaming contract is the key to interoperability, allowing any framework capable of producing this format to be integrated as an agent.

### 4.4. Error Handling System

A robust, structured error system is critical for debugging and client-side handling.

**Structured Error Hierarchy (Python Implementation):**

```python
from enum import Enum
from typing import Optional, Dict, Any

class CopilotKitErrorCode(Enum):
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    UNKNOWN = "UNKNOWN"

class Severity(Enum): CRITICAL, ERROR, WARNING, INFO = "CRITICAL", "ERROR", "WARNING", "INFO"
class Visibility(Enum): USER, DEVELOPER, INTERNAL = "USER", "DEVELOPER", "INTERNAL"

class CopilotKitError(Exception):
    def __init__(self,
                 message: str,
                 code: CopilotKitErrorCode = CopilotKitErrorCode.UNKNOWN,
                 severity: Severity = Severity.ERROR,
                 visibility: Visibility = Visibility.DEVELOPER,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.severity = severity
        self.visibility = visibility
        self.context = context or {}

class CopilotKitLowLevelError(CopilotKitError):
    # ... specialized for network errors with status codes, etc.
```

**Intelligent Error Messages:**

The system includes a centralized configuration to map raw error messages or types (e.g., `ConnectionRefusedError`, `AuthenticationError`) to user-friendly, actionable error messages, improving the developer experience.

### 4.5. Cloud Integration & Guardrails

This system provides enterprise-grade security and content moderation by integrating with Copilot Cloud.

**Guardrails Flow:**

1.  **Trigger**: When a `generateCopilotResponse` request is received with `cloud.guardrails` configured, and the last message is from a user.
2.  **Validation Request**: The runtime constructs a `GuardrailsValidationRequest` containing the user's input, the message history, and the allow/deny lists from the configuration.
3.  **API Call**: It sends a `POST` request to the `/guardrails/validate` endpoint of the Copilot Cloud service, authenticated with the public API key.
4.  **Handle Response**: 
    -   If the result is `"ALLOWED"`, processing continues as normal.
    -   If the result is `"DENIED"`, the runtime immediately stops processing, returns a `FailedResponseStatus` with reason `GUARDRAILS_VALIDATION_FAILED`, and streams a message to the client explaining that the request was blocked.

### 4.6. Observability and Middleware

**Lifecycle Middleware Hooks:**

The runtime provides hooks to inject custom logic at key points in the request lifecycle:

-   `on_before_request(context)`: Called before any processing begins. Useful for logging, custom authentication, or modifying the request.
-   `on_after_request(context)`: Called after the response stream has completed. Useful for logging the final outcome, cleanup, or metrics.

**Progressive vs. Batched Logging:**

When cloud observability is enabled, the runtime supports two logging modes:
-   **Progressive (default)**: Every single token chunk (`TextMessageContent`) is logged as it's generated. This provides real-time insight but is high-volume.
-   **Batched**: Only the final, complete response is logged after the stream ends.

---

## 5. Python Implementation Blueprint

### 5.1. FastAPI Application Structure

The application will be built with FastAPI, with a modular structure designed for clarity and scalability:

```
copilot_runtime_python/
├── main.py              # FastAPI app entry point & lifespan management
├── graphql/             # GraphQL schema, resolvers, and types
│   ├── schema.py
│   └── types/
│       ├── inputs.py
│       └── outputs.py
├── runtime/             # Core runtime, event system, and session management
│   ├── copilot_runtime.py
│   └── event_system.py
├── service_adapters/    # Service adapter interface and implementations
│   ├── base.py
│   ├── openai_adapter.py
│   └── langgraph_adapter.py
├── integrations/        # Logic for cloud, guardrails, etc.
├── observability/       # Logging, telemetry, and monitoring hooks
└── utils/               # Common Pydantic types and error classes
```

### 5.2. GraphQL Implementation with Strawberry

**Strawberry** is the recommended library for its type-safety, modern Python features, and seamless integration with FastAPI and Pydantic.

**Example Schema Definition (`graphql/schema.py`):**

```python
import strawberry
import asyncio
from typing import AsyncGenerator
from strawberry.fastapi import GraphQLRouter
from .types.inputs import GenerateCopilotResponseInput
from .types.outputs import CopilotResponse
from ..runtime.copilot_runtime import CopilotResolver # Hypothetical resolver class

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello World"

@strawberry.type
class Mutation:
    @strawberry.field
    async def generate_copilot_response(
        self,
        data: GenerateCopilotResponseInput,
        properties: strawberry.scalars.JSON = None
    ) -> CopilotResponse:
        resolver = CopilotResolver()
        # Note: In a real app, the response object would be constructed
        # from the streaming parts, and this might just initiate the process.
        return await resolver.generate_copilot_response(data, properties)

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def copilot_stream(
        self, 
        data: GenerateCopilotResponseInput
    ) -> AsyncGenerator[CopilotResponse, None]:
        resolver = CopilotResolver()
        async for response_part in resolver.stream_copilot_response(data):
            yield response_part

schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)

graphql_app = GraphQLRouter(schema)
```

### 5.3. Pydantic Data Models

**Pydantic** will be used for all data validation and serialization. It serves as the single source of truth for data structures, automatically enforcing type constraints and integrating with both FastAPI's request handling and Strawberry's GraphQL type generation.

```python
# utils/types.py
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class TextMessage(BaseModel):
    role: MessageRole
    content: str

class Message(BaseModel):
    id: str
    created_at: str
    text_message: Optional[TextMessage] = None
    # ... other message types
```

### 5.4. Event System Implementation

The core of the streaming logic will be a Python-native event system that emulates the necessary RxJS patterns.

**Core `RuntimeEventSource` Class (`runtime/event_system.py`):**

```python
import asyncio
from typing import List, AsyncGenerator

class RuntimeEventSource:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self.history = [] # For replaying events

    async def emit(self, event):
        self.history.append(event)
        async with self._lock:
            for queue in self._subscribers:
                await queue.put(event)

    async def subscribe(self) -> AsyncGenerator[any, None]:
        queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)
        
        try:
            # Replay history for new subscriber
            for event in self.history:
                await queue.put(event)

            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers.remove(queue)
```

### 5.5. Testing Strategy & Dependencies

-   **Testing Strategy**:
    -   **Unit Tests**: `pytest` will be used to test individual components in isolation (e.g., adapters, utility functions).
    -   **Integration Tests**: Verify interactions between components (e.g., ensuring the runtime correctly processes events from a mocked service adapter).
    -   **End-to-End (E2E) Tests**: Test the full GraphQL API lifecycle with real (sandboxed) LLM providers and agent frameworks to ensure behavioral correctness.

-   **Core Dependencies**:
    -   `fastapi`: For the web framework.
    -   `uvicorn`: As the ASGI server.
    -   `strawberry-graphql[fastapi]`: For the GraphQL layer.
    -   `pydantic`: For data modeling and validation.
    -   `openai`: For the OpenAI service adapter.
    -   `langgraph`: For the LangGraph service adapter.
    -   `httpx`: For making async HTTP requests to remote agents and cloud services.