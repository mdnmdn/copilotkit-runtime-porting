# CopilotRuntime Specification

## Overview

CopilotRuntime is the backend component of CopilotKit that serves as the core runtime system. It acts as a GraphQL-based proxy between frontend React components and backend agentic frameworks like LangGraph and CrewAI. This document provides a comprehensive specification for porting CopilotRuntime from TypeScript to Python using FastAPI.

## Architecture Overview

```
┌─────────────────────┐    GraphQL     ┌─────────────────────┐    REST-ish    ┌─────────────────────┐
│                     │   over HTTP    │                     │   Protocol     │                     │
│   Frontend React    │ ──────────────▶│   CopilotRuntime    │ ──────────────▶│   Agent Frameworks  │
│   Components        │                │                     │                │   (LangGraph,       │
│                     │                │                     │                │    CrewAI, etc.)    │
└─────────────────────┘                └─────────────────────┘                └─────────────────────┘
```

### Key Components:

1. **GraphQL API Layer**: Exposes `generateCopilotResponse` mutation and related queries
2. **Runtime Engine**: Orchestrates LLM interactions, message processing, and agent execution
3. **Event Streaming System**: Real-time bidirectional communication using reactive streams
4. **Service Adapters**: Interface to various LLM providers (OpenAI, Anthropic, etc.)
5. **Agent Integration**: Connect to external agentic frameworks
6. **Action System**: Execute frontend and server-side actions

## GraphQL Schema

### Core Mutations

#### `generateCopilotResponse`

**Input**: `GenerateCopilotResponseInput`
**Output**: `CopilotResponse`

This is the primary mutation that processes user interactions and generates AI responses.

```graphql
mutation generateCopilotResponse(
  $data: GenerateCopilotResponseInput!
  $properties: JSONObject
) {
  generateCopilotResponse(data: $data, properties: $properties) {
    threadId
    runId
    status {
      __typename
      ... on SuccessResponseStatus {
        type
      }
      ... on UnknownErrorResponse {
        type
        description
      }
    }
    messages {
      __typename
      id
      createdAt
      status {
        __typename
      }
      ... on TextMessageOutput {
        role
        content
        parentMessageId
      }
      ... on ActionExecutionMessageOutput {
        name
        arguments
        parentMessageId
      }
      ... on ResultMessageOutput {
        actionExecutionId
        actionName
        result
      }
      ... on AgentStateMessageOutput {
        threadId
        agentName
        nodeName
        runId
        active
        role
        state
        running
      }
    }
    extensions {
      # Optional extensions data
    }
    metaEvents {
      __typename
      type
      name
      ... on LangGraphInterruptEvent {
        value
      }
    }
  }
}
```

### Core Queries

#### `availableAgents`

Returns list of available agents from configured endpoints.

#### `loadAgentState` 

Loads the current state of a specific agent.

## Input Types

### `GenerateCopilotResponseInput`

```typescript
interface GenerateCopilotResponseInput {
  metadata: GenerateCopilotResponseMetadataInput;
  threadId?: string;
  runId?: string;
  messages: MessageInput[];
  frontend: FrontendInput;
  cloud?: CloudInput;
  forwardedParameters?: ForwardedParametersInput;
  agentSession?: AgentSessionInput;
  agentState?: AgentStateInput;
  agentStates?: AgentStateInput[];
  extensions?: ExtensionsInput;
  metaEvents?: MetaEventInput[];
}
```

### Message Types

#### `MessageInput` (Union Type)
- `textMessage?: TextMessageInput`
- `actionExecutionMessage?: ActionExecutionMessageInput`
- `resultMessage?: ResultMessageInput`
- `agentStateMessage?: AgentStateMessageInput`
- `imageMessage?: ImageMessageInput`

#### `TextMessageInput`
```typescript
interface TextMessageInput {
  content: string;
  parentMessageId?: string;
  role: MessageRole; // "user" | "assistant" | "system" | "tool" | "developer"
}
```

#### `ActionExecutionMessageInput`
```typescript
interface ActionExecutionMessageInput {
  name: string;
  arguments: string; // JSON string
  parentMessageId?: string;
  scope?: string; // deprecated
}
```

#### `ResultMessageInput`
```typescript
interface ResultMessageInput {
  actionExecutionId: string;
  actionName: string;
  parentMessageId?: string;
  result: string;
}
```

#### `AgentStateMessageInput`
```typescript
interface AgentStateMessageInput {
  threadId: string;
  agentName: string;
  role: MessageRole;
  state: string; // JSON string
  running: boolean;
  nodeName: string;
  runId: string;
  active: boolean;
}
```

#### `ImageMessageInput`
```typescript
interface ImageMessageInput {
  format: string;
  bytes: string; // base64 encoded
  parentMessageId?: string;
  role: MessageRole;
}
```

### `FrontendInput`
```typescript
interface FrontendInput {
  toDeprecate_fullContext?: string;
  actions: ActionInput[];
  url?: string;
}
```

### `ActionInput`
```typescript
interface ActionInput {
  name: string;
  description: string;
  jsonSchema: string; // JSON schema for parameters
  available?: ActionInputAvailability; // "disabled" | "enabled" | "remote"
}
```

### `AgentSessionInput`
```typescript
interface AgentSessionInput {
  agentName: string;
  threadId?: string;
  nodeName?: string;
}
```

### `ForwardedParametersInput`
```typescript
interface ForwardedParametersInput {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  // ... other LLM parameters
}
```

## Runtime Event System

The runtime uses an event-driven architecture with streaming responses. Events flow through RxJS observables and are streamed to the client via GraphQL subscriptions.

### Runtime Event Types

```typescript
enum RuntimeEventTypes {
  TextMessageStart = "TextMessageStart",
  TextMessageContent = "TextMessageContent", 
  TextMessageEnd = "TextMessageEnd",
  ActionExecutionStart = "ActionExecutionStart",
  ActionExecutionArgs = "ActionExecutionArgs",
  ActionExecutionEnd = "ActionExecutionEnd",
  ActionExecutionResult = "ActionExecutionResult",
  AgentStateMessage = "AgentStateMessage",
  MetaEvent = "MetaEvent"
}
```

### Event Flow

1. **Text Message Events**:
   ```
   TextMessageStart → TextMessageContent* → TextMessageEnd
   ```

2. **Action Execution Events**:
   ```
   ActionExecutionStart → ActionExecutionArgs* → ActionExecutionEnd → ActionExecutionResult
   ```

3. **Agent State Events**:
   ```
   AgentStateMessage (periodic updates during agent execution)
   ```

### Event Structures

#### `TextMessageStart`
```typescript
{
  type: "TextMessageStart";
  messageId: string;
  parentMessageId?: string;
}
```

#### `TextMessageContent`
```typescript
{
  type: "TextMessageContent";
  messageId: string;
  content: string; // streaming chunk
}
```

#### `ActionExecutionStart`
```typescript
{
  type: "ActionExecutionStart";
  actionExecutionId: string;
  actionName: string;
  parentMessageId?: string;
}
```

#### `ActionExecutionArgs`
```typescript
{
  type: "ActionExecutionArgs";
  actionExecutionId: string;
  args: string; // streaming JSON chunk
}
```

#### `ActionExecutionResult`
```typescript
{
  type: "ActionExecutionResult";
  actionName: string;
  actionExecutionId: string;
  result: string; // JSON-encoded result with optional error
}
```

## Core Runtime Flows

### 1. Standard Chat Flow

```
1. Client sends GraphQL mutation with messages
2. Runtime processes messages through service adapter (LLM)
3. LLM generates streaming text response
4. Runtime emits TextMessageStart/Content/End events
5. Client receives streaming response via GraphQL subscription
6. Runtime returns final CopilotResponse with complete messages
```

### 2. Action Execution Flow

```
1. LLM decides to call an action during response generation
2. Runtime emits ActionExecutionStart event
3. Runtime streams action arguments via ActionExecutionArgs events
4. Runtime emits ActionExecutionEnd when arguments complete
5. Runtime executes the action (frontend or server-side)
6. Runtime emits ActionExecutionResult with execution result
7. LLM continues generation using action result
```

### 3. Agent Execution Flow

```
1. Client specifies agentSession in request
2. Runtime routes to agent-specific processing
3. Agent framework (LangGraph) handles the request
4. Runtime streams agent state updates via AgentStateMessage events
5. Agent can call available actions during execution
6. Runtime coordinates between agent and action executions
```

## Service Adapter Interface

Service adapters abstract different LLM providers and execution patterns.

### `CopilotServiceAdapter`

```typescript
interface CopilotServiceAdapter {
  process(request: CopilotRuntimeChatCompletionRequest): Promise<CopilotRuntimeChatCompletionResponse>;
}

interface CopilotRuntimeChatCompletionRequest {
  eventSource: RuntimeEventSource;
  messages: Message[];
  actions: ActionInput[];
  model?: string;
  threadId?: string;
  runId?: string;
  forwardedParameters?: ForwardedParametersInput;
  extensions?: ExtensionsInput;
  agentSession?: AgentSessionInput;
  agentStates?: AgentStateInput[];
}

interface CopilotRuntimeChatCompletionResponse {
  threadId: string;
  runId?: string;
  extensions?: ExtensionsResponse;
}
```

### Built-in Adapters
- **OpenAIAdapter**: OpenAI API integration
- **AnthropicAdapter**: Anthropic Claude integration
- **GoogleAdapter**: Google Gemini integration
- **LangChainAdapter**: LangChain integration
- **EmptyAdapter**: Used for agent-only mode

## Agent Integration

### Remote Agent Actions

Agents are represented as special actions with remote execution handlers:

```typescript
interface RemoteAgentAction extends Action {
  remoteAgentHandler: (params: {
    name: string;
    threadId: string;
    nodeName?: string;
    metaEvents?: MetaEventInput[];
    actionInputsWithoutAgents: ActionInput[];
    additionalMessages?: Message[];
  }) => Promise<AsyncIterable<RuntimeEvent>>;
}
```

### Endpoint Types

#### `CopilotKitEndpoint`
```typescript
interface CopilotKitEndpoint {
  type: EndpointType.CopilotKit;
  url: string;
  onBeforeRequest?: (ctx: GraphQLContext) => Record<string, string>;
}
```

#### `LangGraphPlatformEndpoint`
```typescript
interface LangGraphPlatformEndpoint {
  type: EndpointType.LangGraphPlatform;
  deploymentUrl: string;
  langsmithApiKey?: string;
  agents: string[];
}
```

## Error Handling

### Error Types

1. **CopilotKitError**: Base structured error type
2. **CopilotKitLowLevelError**: Network/infrastructure errors
3. **CopilotKitApiDiscoveryError**: Endpoint discovery failures
4. **CopilotKitAgentDiscoveryError**: Agent discovery failures
5. **CopilotKitMisuseError**: Configuration/usage errors

### Error Context

Errors include rich context for debugging:
```typescript
interface CopilotRequestContext {
  threadId?: string;
  runId?: string;
  source: "runtime" | "agent";
  request: {
    operation: string;
    method: string;
    url?: string;
    startTime: number;
  };
  response?: {
    endTime: number;
    latency: number;
  };
  agent?: {
    name: string;
    nodeName?: string;
  };
  technical?: {
    environment?: string;
    stackTrace?: string;
  };
}
```

## Security & Cloud Features

### Guardrails Integration
- Input validation against allow/deny lists
- Content filtering before LLM processing
- Configurable guardrails rules via cloud configuration

### Authentication
- Public API key authentication for cloud features
- Request context properties for authorization
- Header-based authentication forwarding

## FastAPI Implementation Strategy

### 1. GraphQL Setup
```python
# Using Strawberry GraphQL with FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry import Schema

schema = Schema(
    query=CopilotQuery,
    mutation=CopilotMutation,
    subscription=CopilotSubscription
)

graphql_app = GraphQLRouter(schema)
```

### 2. Event Streaming
```python
# Use asyncio and async generators for event streaming
async def generate_copilot_response(input_data):
    async for event in runtime.process_request(input_data):
        yield event
```

### 3. Agent Integration
```python
# Interface with LangGraph using their Python SDK
from langgraph_sdk import Client

class LangGraphAgent:
    def __init__(self, client: Client):
        self.client = client
    
    async def execute(self, thread_id: str, messages: List[Message]):
        async for event in self.client.runs.stream(...):
            yield convert_to_runtime_event(event)
```

### 4. Service Adapters
```python
from abc import ABC, abstractmethod

class CopilotServiceAdapter(ABC):
    @abstractmethod
    async def process(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        pass

class OpenAIAdapter(CopilotServiceAdapter):
    async def process(self, request):
        # OpenAI API integration
        pass
```

## Data Models (Pydantic)

### Core Models
```python
from pydantic import BaseModel
from typing import Optional, List, Union
from enum import Enum

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

class GenerateCopilotResponseInput(BaseModel):
    metadata: Dict
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    messages: List[MessageInput]
    frontend: FrontendInput
    cloud: Optional[CloudInput] = None
    forwarded_parameters: Optional[Dict] = None
    agent_session: Optional[AgentSessionInput] = None
    agent_states: Optional[List[AgentStateInput]] = None
    extensions: Optional[Dict] = None
    meta_events: Optional[List[Dict]] = None
```

## Implementation Considerations

### 1. Async/Await Pattern
- Use asyncio for all async operations
- Implement streaming using async generators
- Handle concurrent operations with asyncio.gather()

### 2. Event System
- Use asyncio queues or async generators for event streaming
- Implement backpressure handling for high-throughput scenarios
- Consider using Redis Streams for distributed deployments

### 3. State Management
- Thread-safe state management for concurrent requests
- Consider Redis or database storage for persistent state
- Implement proper cleanup for abandoned threads

### 4. Type Safety
- Use Pydantic for data validation and serialization
- Implement proper type hints throughout
- Use mypy for static type checking

### 5. Error Handling
- Implement structured error types matching TypeScript version
- Provide detailed error context for debugging
- Handle network errors gracefully with retries

### 6. Testing Strategy
- Unit tests for each component
- Integration tests with real LLM providers
- End-to-end tests with agent frameworks
- Mock external dependencies for reliable testing

## Migration Path

### Phase 1: Core GraphQL API
1. Set up FastAPI with Strawberry GraphQL
2. Implement basic mutations and queries
3. Create Pydantic models for all input/output types
4. Set up basic event streaming infrastructure

### Phase 2: Runtime Engine
1. Implement CopilotRuntime class
2. Create service adapter interface and basic adapters
3. Implement action execution system
4. Add error handling and logging

### Phase 3: Agent Integration  
1. Implement LangGraph agent integration
2. Add support for remote endpoints
3. Implement agent state management
4. Add meta-events and interrupts

### Phase 4: Advanced Features
1. Add cloud features and guardrails
2. Implement observability and logging
3. Add MCP (Model Context Protocol) support
4. Performance optimization and scaling

This specification provides the foundation for creating a comprehensive Python port of CopilotRuntime that maintains compatibility with the existing TypeScript ecosystem while leveraging Python's strengths for agentic AI workflows.

## Deep Dive Analysis

Based on comprehensive analysis of the TypeScript implementation, here are the critical architectural patterns and implementation details:

### Service Adapter Architecture (Deep Dive)

#### OpenAI Adapter Implementation Pattern
The OpenAI adapter demonstrates sophisticated streaming patterns:

```typescript
// Key patterns observed:
1. **Streaming State Machine**: Tracks "message" vs "function" modes
2. **Token Counting**: Smart message truncation based on model limits
3. **Tool Call Allowlisting**: Filters out orphaned tool results
4. **Parallel Tool Control**: Option to disable parallel tool calls

// Critical streaming logic:
async for (const chunk of stream) {
  const toolCall = chunk.choices[0].delta.tool_calls?.[0];
  const content = chunk.choices[0].delta.content;
  
  // Mode transitions emit appropriate start/end events
  if (mode === "message" && toolCall?.id) {
    eventStream$.sendTextMessageEnd({ messageId: currentMessageId });
    mode = "function";
    eventStream$.sendActionExecutionStart({...});
  }
  
  // Content streaming
  if (mode === "message" && content) {
    eventStream$.sendTextMessageContent({ messageId, content });
  }
}
```

**Python Implementation Strategy:**
```python
class OpenAIAdapter(CopilotServiceAdapter):
    async def process(self, request: CopilotRuntimeRequest):
        # Use async generators for streaming
        async def stream_handler():
            mode = None
            current_message_id = None
            
            async for chunk in self.openai.chat.completions.stream(...):
                # Implement state machine logic
                tool_call = chunk.choices[0].delta.tool_calls
                content = chunk.choices[0].delta.content
                
                # Emit appropriate events based on mode transitions
                yield RuntimeEvent(...)
                
        return StreamingResponse(stream_handler())
```

#### Message Conversion Patterns

**Critical Conversion Logic:**
```typescript
// GraphQL Input → Internal Message Format
convertGqlInputToMessages(inputMessages: MessageInput[]): Message[]

// Internal → OpenAI Format  
convertMessageToOpenAIMessage(message: Message): ChatCompletionMessageParam

// Key patterns:
1. **Union Type Handling**: MessageInput has optional fields for each type
2. **JSON Parsing**: Arguments and state are JSON strings that need parsing
3. **Role Mapping**: System → Developer role conversion for OpenAI
4. **Tool Call Structure**: Complex tool_calls array construction
```

**Python Implementation:**
```python
from typing import Union, Optional
from pydantic import BaseModel, Field

class MessageInput(BaseModel):
    id: str
    created_at: datetime
    text_message: Optional[TextMessageInput] = None
    action_execution_message: Optional[ActionExecutionMessageInput] = None
    result_message: Optional[ResultMessageInput] = None
    agent_state_message: Optional[AgentStateMessageInput] = None
    image_message: Optional[ImageMessageInput] = None
    
def convert_gql_input_to_messages(input_messages: List[MessageInput]) -> List[Message]:
    messages = []
    for msg in input_messages:
        if msg.text_message:
            messages.append(TextMessage(
                id=msg.id,
                created_at=msg.created_at,
                role=msg.text_message.role,
                content=msg.text_message.content
            ))
        elif msg.action_execution_message:
            messages.append(ActionExecutionMessage(
                id=msg.id,
                created_at=msg.created_at,
                name=msg.action_execution_message.name,
                arguments=json.loads(msg.action_execution_message.arguments)
            ))
    return messages
```

### Remote Agent Integration (Deep Dive)

#### Agent Discovery and Execution Patterns

**Multi-Endpoint Agent Discovery:**
```typescript
// Three types of agent endpoints:
1. **CopilotKit Endpoints**: Self-hosted with /info discovery
2. **LangGraph Platform**: Managed service with assistant discovery
3. **AGUI Agents**: In-process Python agent objects

// Discovery flow:
async setupRemoteActions({
  remoteEndpointDefinitions,
  graphqlContext,
  messages,
  agentStates
}): Promise<Action[]>

// Each endpoint type has different discovery and execution patterns
```

**Agent Execution Patterns:**
```typescript
// Remote agent execution involves:
1. **State Management**: Thread state serialization/deserialization
2. **Action Filtering**: Available actions vs agent-specific actions  
3. **Message Threading**: Parent-child relationships
4. **Event Streaming**: JSON-line streaming for real-time updates

// LangGraph Platform integration:
const response = await execute({
  deploymentUrl: endpoint.deploymentUrl,
  langsmithApiKey: endpoint.langsmithApiKey,
  threadId,
  messages: [...messages, ...additionalMessages],
  state: parseJson(jsonState.state, {}),
  actions: actionInputsWithoutAgents.map(convertToLangGraphFormat)
});
```

**Python Implementation Strategy:**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, AsyncGenerator

class AgentEndpoint(ABC):
    @abstractmethod
    async def discover_agents(self, context: GraphQLContext) -> List[Agent]:
        pass
    
    @abstractmethod  
    async def execute_agent(self, request: AgentExecutionRequest) -> AsyncGenerator[RuntimeEvent, None]:
        pass

class LangGraphPlatformEndpoint(AgentEndpoint):
    def __init__(self, deployment_url: str, langsmith_api_key: str):
        self.deployment_url = deployment_url
        self.langsmith_api_key = langsmith_api_key
        self.client = LangGraphClient(api_url=deployment_url, api_key=langsmith_api_key)
    
    async def execute_agent(self, request: AgentExecutionRequest):
        async for event in self.client.runs.stream(
            thread_id=request.thread_id,
            assistant_id=request.agent_name,
            input={"messages": request.messages},
            stream_mode="events"
        ):
            yield convert_langgraph_event_to_runtime_event(event)

class CopilotKitEndpoint(AgentEndpoint):
    async def execute_agent(self, request: AgentExecutionRequest):
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.url}/agents/execute",
                json=request.dict()) as response:
                async for line in response.aiter_lines():
                    if line:
                        event_data = json.loads(line)
                        yield RuntimeEvent(**event_data)
```

### Event Streaming Architecture (Deep Dive)

#### RxJS to AsyncIO Pattern Translation

**TypeScript RxJS Pattern:**
```typescript
// Complex reactive stream composition
const eventStream = eventSource
  .processRuntimeEvents({...})
  .pipe(
    shareReplay(),  // Replay events for late subscribers
    scan((acc, event) => {...}, initialState), // State accumulation
    concatMap((eventWithState) => {
      // Conditional stream branching for action execution
      if (eventWithState.event.type === ActionExecutionEnd) {
        const toolCallEventStream$ = new RuntimeEventSubject();
        executeAction(...).catch(error => {});
        return concat(of(event), toolCallEventStream$);
      }
      return of(event);
    }),
    catchError(error => {...}) // Error handling
  );
```

**Python AsyncIO Translation:**
```python
import asyncio
from typing import AsyncGenerator, Dict, Any

class RuntimeEventSource:
    def __init__(self):
        self.event_queue = asyncio.Queue()
        self.subscribers: List[asyncio.Queue] = []
        self.state: Dict[str, Any] = {}
    
    async def process_runtime_events(self, 
                                   server_side_actions: List[Action],
                                   action_inputs_without_agents: List[ActionInput],
                                   thread_id: str) -> AsyncGenerator[RuntimeEvent, None]:
        
        try:
            async for event in self._event_stream():
                # State management (scan equivalent)
                self._update_state(event)
                
                # Conditional processing (concatMap equivalent)  
                if event.type == RuntimeEventTypes.ACTION_EXECUTION_END:
                    if self._should_execute_action(event):
                        # Spawn action execution as background task
                        asyncio.create_task(
                            self._execute_action(event, server_side_actions)
                        )
                
                # Emit to subscribers (shareReplay equivalent)
                for subscriber in self.subscribers:
                    await subscriber.put(event)
                
                yield event
                
        except Exception as error:
            structured_error = self._convert_to_structured_error(error)
            error_event = RuntimeEvent(
                type=RuntimeEventTypes.ERROR,
                error=structured_error
            )
            yield error_event

    async def _execute_action(self, event: RuntimeEvent, actions: List[Action]):
        # Background action execution
        action = next(a for a in actions if a.name == event.action_name)
        try:
            result = await action.handler(json.loads(event.args))
            result_event = RuntimeEvent(
                type=RuntimeEventTypes.ACTION_EXECUTION_RESULT,
                action_execution_id=event.action_execution_id,
                result=json.dumps(result)
            )
            await self.event_queue.put(result_event)
        except Exception as e:
            error_event = RuntimeEvent(
                type=RuntimeEventTypes.ACTION_EXECUTION_RESULT,
                action_execution_id=event.action_execution_id,
                result=json.dumps({"error": {"code": "HANDLER_ERROR", "message": str(e)}})
            )
            await self.event_queue.put(error_event)
```

#### JSON-Line Streaming Pattern

**Critical Streaming Implementation:**
```typescript
// Handles partial JSON chunks across network boundaries
async function writeJsonLineResponseToEventStream<T>(
  response: ReadableStream<Uint8Array>,
  eventStream$: ReplaySubject<T>,
) {
  const decoder = new TextDecoder();
  let buffer = [];
  
  function flushBuffer() {
    const currentBuffer = buffer.join("");
    const parts = currentBuffer.split("\n");
    const lastPartIsComplete = currentBuffer.endsWith("\n");
    
    buffer = [];
    if (!lastPartIsComplete) {
      buffer.push(parts.pop()); // Keep incomplete part
    }
    
    parts
      .map((part) => part.trim())
      .filter((part) => part != "")
      .forEach((part) => {
        eventStream$.next(JSON.parse(part));
      });
  }
}
```

**Python Implementation:**
```python
import asyncio
import json
from typing import AsyncGenerator

async def process_jsonl_stream(response_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[Dict, None]:
    """Process JSON-line streaming with proper boundary handling"""
    buffer = []
    
    async for chunk in response_stream:
        buffer.append(chunk.decode('utf-8'))
        
        # Process complete lines
        current_buffer = ''.join(buffer)
        if '\n' not in current_buffer:
            continue
            
        parts = current_buffer.split('\n')
        last_part_complete = current_buffer.endswith('\n')
        
        # Reset buffer
        buffer = []
        if not last_part_complete:
            buffer.append(parts.pop())  # Keep incomplete part
        
        # Yield complete JSON objects
        for part in parts:
            part = part.strip()
            if part:
                try:
                    yield json.loads(part)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {part}, error: {e}")
                    continue
```

### Error Handling System (Deep Dive)

#### Structured Error Classification

**TypeScript Error Hierarchy:**
```typescript
// Comprehensive error classification system
class CopilotKitError extends Error {
  code: CopilotKitErrorCode;
  severity: Severity;
  visibility: Visibility;
}

class CopilotKitLowLevelError extends CopilotKitError {
  url?: string;          // Where the error occurred
  statusCode?: number;   // HTTP status if applicable  
  originalError: Error;  // Preserve original error
}

// Error classification by HTTP status:
401 → AUTHENTICATION_ERROR
4xx → CONFIGURATION_ERROR  
5xx → NETWORK_ERROR
```

**Python Error System:**
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
    USER = "USER"      # Show to end users
    DEVELOPER = "DEVELOPER"  # Show to developers only
    INTERNAL = "INTERNAL"    # Internal errors

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
    def __init__(self,
                 error: Exception,
                 url: Optional[str] = None,
                 message: Optional[str] = None,
                 status_code: Optional[int] = None):
        self.original_error = error
        self.url = url
        self.status_code = status_code
        
        # Classify error based on HTTP status
        if status_code == 401:
            code = CopilotKitErrorCode.AUTHENTICATION_ERROR
        elif status_code and 400 <= status_code < 500:
            code = CopilotKitErrorCode.CONFIGURATION_ERROR
        elif status_code and status_code >= 500:
            code = CopilotKitErrorCode.NETWORK_ERROR
        else:
            code = CopilotKitErrorCode.NETWORK_ERROR
            
        super().__init__(
            message or f"Low-level error: {str(error)}", 
            code=code
        )

def convert_service_adapter_error(error: Exception, adapter_name: str) -> CopilotKitLowLevelError:
    """Convert service adapter errors to structured format"""
    status_code = getattr(error, 'status_code', None) or getattr(error, 'status', None)
    
    return CopilotKitLowLevelError(
        error=error,
        url=f"{adapter_name} service adapter",
        message=f"{adapter_name} API error: {str(error)}",
        status_code=status_code
    )
```

#### Intelligent Error Message System

**Context-Aware Error Messages:**
```typescript
// Centralized error message configuration
export const errorConfig = {
  errorPatterns: {
    "ECONNREFUSED": {
      message: "Connection refused - the agent service is not running...",
      category: "network",
      actionable: true
    },
    "AuthenticationError": {
      message: "OpenAI authentication failed. Check your OPENAI_API_KEY...",
      category: "authentication", 
      actionable: true
    }
  },
  fallbacks: {
    network: "A network error occurred while connecting...",
    authentication: "Authentication failed. Please check your API keys..."
  }
};
```

**Python Error Message System:**
```python
from typing import Dict, Optional

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
        "message": "OpenAI rate limit exceeded. Please wait a moment and try again, or check your OpenAI usage limits.",
        "category": "network",
        "actionable": True
    }
}

FALLBACK_MESSAGES = {
    "network": "A network error occurred while connecting to the agent service. Please check your connection and ensure the agent service is running.",
    "authentication": "Authentication failed. Please check your API keys and credentials.",
    "default": "An unexpected error occurred. Please check the logs for more details."
}

def generate_helpful_error_message(error: Exception, context: str = "connection") -> str:
    """Generate context-aware error messages"""
    error_type = type(error).__name__
    base_message = str(error)
    
    # Check for specific error patterns
    if error_type in ERROR_PATTERNS:
        return ERROR_PATTERNS[error_type]["message"].replace("{context}", context)
    
    # Pattern matching in error message
    for pattern, config in ERROR_PATTERNS.items():
        if pattern.lower() in base_message.lower():
            return config["message"].replace("{context}", context)
    
    # Fallback based on error category
    if isinstance(error, (ConnectionError, ConnectionRefusedError)):
        return FALLBACK_MESSAGES["network"]
    elif "authentication" in base_message.lower() or "api key" in base_message.lower():
        return FALLBACK_MESSAGES["authentication"]
    
    return FALLBACK_MESSAGES["default"]
```

### Observability and Middleware (Deep Dive)

#### Progressive vs Batched Logging

**TypeScript Observability Pattern:**
```typescript
interface CopilotObservabilityConfig {
  enabled: boolean;
  progressive: boolean;  // Stream each token vs batch complete responses
  hooks: {
    handleRequest: (data: LLMRequestData) => void | Promise<void>;
    handleResponse: (data: LLMResponseData) => void | Promise<void>; 
    handleError: (data: LLMErrorData) => void | Promise<void>;
  };
}

// Progressive logging implementation:
if (this.observability?.progressive) {
  eventSource.stream = async (callback) => {
    eventStream$.subscribe({
      next: (event) => {
        if (event.type === RuntimeEventTypes.TextMessageContent) {
          // Log each chunk separately for progressive mode
          this.observability.hooks.handleResponse({
            threadId,
            output: event.content,
            isProgressiveChunk: true,
            timestamp: Date.now()
          });
        }
      }
    });
  };
}
```

**Python Observability Implementation:**
```python
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Union, Any
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

class ObservabilityHooks:
    def __init__(self,
                 handle_request: Optional[Callable[[LLMRequestData], Awaitable[None]]] = None,
                 handle_response: Optional[Callable[[LLMResponseData], Awaitable[None]]] = None,
                 handle_error: Optional[Callable[[LLMErrorData], Awaitable[None]]] = None):
        self.handle_request = handle_request
        self.handle_response = handle_response  
        self.handle_error = handle_error

class CopilotObservabilityConfig:
    def __init__(self, 
                 enabled: bool = False,
                 progressive: bool = True,
                 hooks: Optional[ObservabilityHooks] = None):
        self.enabled = enabled
        self.progressive = progressive
        self.hooks = hooks or ObservabilityHooks()

class RuntimeObservability:
    def __init__(self, config: CopilotObservabilityConfig):
        self.config = config
        self.streamed_chunks = []
        
    async def track_request(self, request_data: LLMRequestData):
        if self.config.enabled and self.config.hooks.handle_request:
            await self.config.hooks.handle_request(request_data)
    
    async def track_streaming_chunk(self, thread_id: str, content: str, **kwargs):
        if not self.config.enabled or not self.config.progressive:
            return
            
        self.streamed_chunks.append(content)
        
        if self.config.hooks.handle_response:
            await self.config.hooks.handle_response(LLMResponseData(
                thread_id=thread_id,
                output=content,
                timestamp=time.time(),
                is_progressive_chunk=True,
                **kwargs
            ))
    
    async def track_final_response(self, thread_id: str, **kwargs):
        if not self.config.enabled:
            return
            
        output = self.streamed_chunks if self.config.progressive else kwargs.get('output', [])
        
        if self.config.hooks.handle_response:
            await self.config.hooks.handle_response(LLMResponseData(
                thread_id=thread_id,
                output=output,
                timestamp=time.time(),
                is_final_response=True,
                **kwargs
            ))
```

#### Lifecycle Middleware Hooks

**Request/Response Middleware:**
```python
from typing import Dict, Any, Optional, Callable, Awaitable

class CopilotMiddleware:
    def __init__(self,
                 on_before_request: Optional[Callable] = None,
                 on_after_request: Optional[Callable] = None):
        self.on_before_request = on_before_request
        self.on_after_request = on_after_request

class MiddlewareContext:
    def __init__(self,
                 thread_id: Optional[str],
                 run_id: Optional[str], 
                 input_messages: List[Message],
                 properties: Dict[str, Any],
                 url: Optional[str] = None):
        self.thread_id = thread_id
        self.run_id = run_id
        self.input_messages = input_messages
        self.properties = properties
        self.url = url

# Usage in runtime:
async def process_runtime_request(self, request: CopilotRuntimeRequest):
    # Before request middleware
    if self.middleware and self.middleware.on_before_request:
        await self.middleware.on_before_request(MiddlewareContext(
            thread_id=request.thread_id,
            run_id=request.run_id,
            input_messages=request.messages,
            properties=request.properties
        ))
    
    # Process request...
    result = await self._process_request(request)
    
    # After request middleware  
    if self.middleware and self.middleware.on_after_request:
        await self.middleware.on_after_request(MiddlewareContext(
            thread_id=result.thread_id,
            run_id=result.run_id,
            input_messages=request.messages,
            output_messages=result.messages,
            properties=request.properties
        ))
    
    return result
```

This specification provides the foundation for creating a comprehensive Python port of CopilotRuntime that maintains compatibility with the existing TypeScript ecosystem while leveraging Python's strengths for agentic AI workflows.