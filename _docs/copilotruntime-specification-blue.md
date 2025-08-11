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