# CopilotRuntime Complete Specification

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

### Key Components

1. **GraphQL API Layer**: Exposes `generateCopilotResponse` mutation and related queries
2. **Runtime Engine**: Orchestrates LLM interactions, message processing, and agent execution
3. **Event Streaming System**: Real-time bidirectional communication using reactive streams
4. **Service Adapters**: Interface to various LLM providers (OpenAI, Anthropic, etc.)
5. **Agent Integration**: Connect to external agentic frameworks
6. **Action System**: Execute frontend and server-side actions

The CopilotRuntime acts as a **GraphQL proxy** that:
- Exposes a GraphQL endpoint for frontend React components
- Translates GraphQL requests to REST-like interfaces for Python agentic frameworks
- Manages real-time streaming of AI responses
- Handles action execution and state management
- Provides observability and error handling

## GraphQL Schema and Protocol

### GraphQL Endpoint

The GraphQL endpoint is served at the root of the application and uses the following operations:

### Core Operations

#### Queries

1. **`hello: String`** - Health check endpoint that returns "Hello World"

2. **`availableAgents: AgentsResponse`** - Discovers and returns available agents/endpoints
   - Response: `{ agents: [{ id: string; name: string; description?: string }] }`
   - Semantics: Filters away endpoint details before returning to maintain security

3. **`loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse`**
   - Input: `{ threadId: string; agentName: string }`
   - Validates agent exists; if not, raises `CopilotKitAgentDiscoveryError` with available agents
   - Returns persisted state for the specific `{threadId, agentName}`

#### Mutations

**`generateCopilotResponse(data: GenerateCopilotResponseInput!, properties?: JSONObject): CopilotResponse`**

This is the primary mutation that processes user interactions and generates AI responses.

**GraphQL Schema:**
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

**Response Fields:**
- `threadId: ID!`
- `runId: ID!`
- `status: ResponseStatusUnion` (resolves at end; may be deferred)
- `extensions: ExtensionsResponse` (implementation-defined, e.g., OpenAI Assistant IDs)
- `messages: [MessageOutput]!` (streamed incrementally)
- `metaEvents: [MetaEvent]!` (streamed incrementally)

## Input Types Specification

### Core Input Types

#### `GenerateCopilotResponseInput`

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

#### Message Types (Union Type)

**`MessageInput`** - Union of optional fields for each message type:
- `textMessage?: TextMessageInput`
- `actionExecutionMessage?: ActionExecutionMessageInput`
- `resultMessage?: ResultMessageInput`
- `agentStateMessage?: AgentStateMessageInput`
- `imageMessage?: ImageMessageInput`

**Message Type Definitions:**

```typescript
interface TextMessageInput {
  content: string;
  parentMessageId?: string;
  role: MessageRole; // "user" | "assistant" | "system" | "tool" | "developer"
}

interface ActionExecutionMessageInput {
  name: string;
  arguments: string; // JSON string
  parentMessageId?: string;
  scope?: string; // deprecated
}

interface ResultMessageInput {
  actionExecutionId: string;
  actionName: string;
  parentMessageId?: string;
  result: string;
}

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

interface ImageMessageInput {
  format: string;
  bytes: string; // base64 encoded
  parentMessageId?: string;
  role: MessageRole;
}
```

#### Supporting Input Types

```typescript
interface FrontendInput {
  toDeprecate_fullContext?: string;
  actions: ActionInput[];
  url?: string;
}

interface ActionInput {
  name: string;
  description: string;
  jsonSchema: string; // JSON schema for parameters
  available?: ActionInputAvailability; // "disabled" | "enabled" | "remote"
}

interface AgentSessionInput {
  agentName: string;
  threadId?: string;
  nodeName?: string;
}

interface ForwardedParametersInput {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stop?: string[];
  toolChoice?: string;
  toolChoiceFunctionName?: string;
}

interface CloudInput {
  guardrails?: GuardrailsInput;
}

interface GuardrailsInput {
  inputValidationRules: GuardrailsRuleInput;
}

interface GuardrailsRuleInput {
  allowList?: string[];
  denyList?: string[];
}

interface ExtensionsInput {
  openaiAssistantAPI?: OpenAIApiAssistantAPIInput;
}

interface MetaEventInput {
  name: MetaEventName;
  value?: string;
  response?: string;
  messages?: MessageInput[];
}
```

## Output Types Specification

### Core Output Types

#### `CopilotResponse`

```typescript
interface CopilotResponse {
  threadId: string;
  status: ResponseStatusUnion;
  runId?: string;
  messages: BaseMessageOutput[];
  extensions?: ExtensionsResponse;
  metaEvents?: BaseMetaEvent[];
}
```

#### Message Output Types

**`BaseMessageOutput`** (Interface):
```typescript
interface BaseMessageOutput {
  id: string;
  createdAt: Date;
  status: MessageStatusUnion;
}
```

**Message Output Implementations:**

```typescript
interface TextMessageOutput extends BaseMessageOutput {
  role: MessageRole;
  content: string[] | string; // Streaming chunks or final content
  parentMessageId?: string;
}

interface ActionExecutionMessageOutput extends BaseMessageOutput {
  name: string;
  scope?: string; // deprecated
  arguments: string[] | string; // Streaming argument chunks or final
  parentMessageId?: string;
}

interface ResultMessageOutput extends BaseMessageOutput {
  actionExecutionId: string;
  actionName: string;
  result: string;
}

interface AgentStateMessageOutput extends BaseMessageOutput {
  threadId: string;
  agentName: string;
  nodeName: string;
  runId: string;
  active: boolean;
  role: MessageRole;
  state: string;
  running: boolean;
}

interface ImageMessageOutput extends BaseMessageOutput {
  format: string;
  bytes: string;
  role: MessageRole;
  parentMessageId?: string;
}
```

#### Status Types

**Response Status (Union):**
- `SuccessResponseStatus: { code }`
- `FailedResponseStatus: { code, reason, details }`
- `UnknownErrorResponse: { description, originalError? }`
- `GuardrailsValidationFailureResponse: { guardrailsReason }`
- `MessageStreamInterruptedResponse: { messageId? }`

**Message Status (Union):**
- `SuccessMessageStatus: { code }`
- `FailedMessageStatus: { code, reason }`
- `PendingMessageStatus: { code }`

## Enumerations

```typescript
enum ActionInputAvailability {
  disabled = "disabled",
  enabled = "enabled", 
  remote = "remote"
}

enum CopilotRequestType {
  Chat = "Chat",
  Task = "Task",
  TextareaCompletion = "TextareaCompletion",
  TextareaPopover = "TextareaPopover",
  Suggestion = "Suggestion"
}

enum MessageRole {
  user = "user",
  assistant = "assistant", 
  system = "system",
  tool = "tool",
  developer = "developer"
}

enum MetaEventName {
  LangGraphInterruptEvent = "LangGraphInterruptEvent",
  CopilotKitLangGraphInterruptEvent = "CopilotKitLangGraphInterruptEvent"
}
```

## Runtime Event System

The runtime uses an event-driven architecture with streaming responses. Events flow through RxJS observables (TypeScript) and must be translated to asyncio patterns (Python).

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

enum RuntimeMetaEventName {
  LangGraphInterruptEvent = "LangGraphInterruptEvent",
  LangGraphInterruptResumeEvent = "LangGraphInterruptResumeEvent", 
  CopilotKitLangGraphInterruptEvent = "CopilotKitLangGraphInterruptEvent"
}
```

### Event Flow Patterns

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

#### Core Event Types

```typescript
interface RuntimeEvent {
  type: RuntimeEventTypes;
  messageId?: string;
  parentMessageId?: string;
  // Event-specific data fields
}

// Text Message Events
interface TextMessageStart {
  type: "TextMessageStart";
  messageId: string;
  parentMessageId?: string;
}

interface TextMessageContent {
  type: "TextMessageContent";
  messageId: string;
  content: string; // streaming chunk
}

interface TextMessageEnd {
  type: "TextMessageEnd";
  messageId: string;
}

// Action Execution Events  
interface ActionExecutionStart {
  type: "ActionExecutionStart";
  actionExecutionId: string;
  actionName: string;
  parentMessageId?: string;
}

interface ActionExecutionArgs {
  type: "ActionExecutionArgs";
  actionExecutionId: string;
  args: string; // streaming JSON chunk
}

interface ActionExecutionEnd {
  type: "ActionExecutionEnd";
  actionExecutionId: string;
}

interface ActionExecutionResult {
  type: "ActionExecutionResult";
  actionName: string;
  actionExecutionId: string;
  result: string; // JSON-encoded result with optional error
}

// Agent State Events
interface AgentStateMessage {
  type: "AgentStateMessage";
  threadId: string;
  agentName: string;
  nodeName: string;
  runId: string;
  active: boolean;
  role: string;
  state: string;
  running: boolean;
}

// Meta Events
interface MetaEvent {
  type: "MetaEvent";
  name: RuntimeMetaEventName;
  value?: any;
  data?: any;
}
```

### Response Streaming Behavior

- Messages and meta-events are delivered incrementally using GraphQL Yoga's Repeater with `@stream`/`@defer` directives
- Clients should support incremental updates but may also handle non-streaming (MVP in Python port)
- The `status` resolves to success or error after the stream completes or aborts
- Messages field is resolved via nested repeaters:
  - One repeater emits message "containers" with their own sub-streams for content/arguments
  - Sub-streams manage status transitions and accumulate final message records

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

### 4. Flow Semantics Details

#### Context Processing
- Merges `properties` arg into request context properties
- Extracts `x-copilotcloud-public-api-key` header for cloud features and telemetry

#### Guardrails Integration
- If `cloud.guardrails` present and last message is from `user`, calls Copilot Cloud `POST /guardrails/validate`
- On denial: emits `GuardrailsValidationFailureResponse`, interrupts message streaming
- Returns an assistant `TextMessage` explaining the reason

#### Agent vs. General Processing
- If `agentSession` is present and `delegateAgentProcessingToServiceAdapter` is false:
  - Switches to `processAgentRequest`
  - Identifies current agent as a `RemoteAgentAction`
  - Builds `availableActionsForCurrentAgent` (excluding self to avoid loops)
  - Calls agent's `remoteAgentHandler` to obtain Observable of `RuntimeEvent`
- Otherwise uses configured `serviceAdapter` (LLM adapter) and server-side actions

## Service Adapter Interface

Service adapters abstract different LLM providers and execution patterns.

### Core Interface

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
- **OpenAIAdapter**: OpenAI API integration with streaming and tool calling
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

### Remote Actions Protocol

#### Discovery
- **Self-hosted**: `POST {endpoint}/info` with `{ properties, frontendUrl }` → `{ actions: Action[], agents: Agent[] }`
- **LangGraph Platform**: SDK `assistants.search()` → agents with `{ assistant_id, graph_id }`

#### Execution
- **Actions**: `POST {endpoint}/actions/execute` with `{ name, arguments, properties }` → `{ result }`
- **Agents**: `POST {endpoint}/agents/execute` with `{ name, threadId, nodeName, messages, state, config, properties, actions, metaEvents }` → JSONL stream of runtime events
- **Headers**: Constructed via `onBeforeRequest({ ctx })` and include `Content-Type: application/json` plus custom entries

### Server-side Actions

Server-side actions include:
- Locally configured actions (`actions`)
- LangServe chains (`langserve`)
- Remote endpoints (`remoteEndpoints`) transformed via `setupRemoteActions`
- MCP-derived tools (fetched per request via `createMCPClient`, cached by endpoint)

**Remote endpoint discovery and execution:**
- Self-hosted CopilotKit endpoints: `POST /info` for actions/agents, `POST /actions/execute`, `POST /agents/execute`
- LangGraph Platform endpoints: discovered via LangGraph SDK; agent execution via `execute` and JSONL event streaming
- `ActionInputAvailability.remote` actions are excluded from core LLM loop
- Disabled actions are filtered out before request

## Authentication and Authorization

### Cloud Authentication
- **API Key Header**: `X-CopilotCloud-Public-API-Key` used when `cloud` config is present
- **Public API Key**: Required for all cloud features including guardrails
- **Authentication Validation**: Cloud service validates API keys before processing

### Request Context
- **Properties Argument**: Arbitrary JSON merged into server-side context
- **Header Forwarding**: Special keys like `authorization` forwarded as `Bearer` for LangGraph Platform
- **MCP Servers**: Dynamic MCP tool discovery via `properties.mcpServers`

## Error Handling

### Error Types

```typescript
enum CopilotKitErrorCode {
  UNKNOWN = "UNKNOWN",
  AGENT_NOT_FOUND = "AGENT_NOT_FOUND",
  API_NOT_FOUND = "API_NOT_FOUND", 
  REMOTE_ENDPOINT_NOT_FOUND = "REMOTE_ENDPOINT_NOT_FOUND",
  CONFIGURATION_ERROR = "CONFIGURATION_ERROR",
  MISSING_PUBLIC_API_KEY_ERROR = "MISSING_PUBLIC_API_KEY_ERROR",
  AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR",
  NETWORK_ERROR = "NETWORK_ERROR"
}

// Error Hierarchy
abstract class CopilotKitError extends Error {
  abstract code: CopilotKitErrorCode;
  abstract severity: Severity;
  abstract visibility: Visibility;
}

class CopilotKitLowLevelError extends CopilotKitError {
  constructor(
    public error: Error,
    public url?: string,
    public message?: string,
    public statusCode?: number
  ) {
    super(message || error.message);
  }
}
```

### Error Classification

**HTTP Status Code Mapping:**
- `401` → `AUTHENTICATION_ERROR`
- `4xx` → `CONFIGURATION_ERROR`
- `5xx` → `NETWORK_ERROR`

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

### Error Handling Flow

- Structured CopilotKit errors are bubbled as GraphQL errors with extensions
- Network/streaming errors are converted to `CopilotKitLowLevelError` with helpful messages
- On errors during streaming, runtime unsubscribes and completes streams
- Error context is preserved and forwarded to error handlers

## Security & Cloud Features

### Guardrails Integration

**Input Validation Pipeline:**
```typescript
interface GuardrailsValidationRequest {
  input: string;
  validTopics: string[];
  invalidTopics: string[];
  messages: Array<{
    role: MessageRole;
    content: string;
  }>;
}

interface GuardrailsResult {
  status: "allowed" | "denied";
  reason?: string;
  confidence?: number;
  categories?: string[];
}
```

**Guardrails Flow:**
1. **Input Validation**: Check user messages against allow/deny lists
2. **API Call**: POST to `/guardrails/validate` endpoint
3. **Response Handling**: Block or allow based on validation result
4. **Error Reporting**: Send guardrails failures to client

### Cloud Features

- **Content Moderation**: Real-time content filtering
- **Usage Analytics**: Request tracking and telemetry
- **Advanced Monitoring**: Error tracking and performance metrics
- **Compliance**: Enterprise-grade security features

### Headers and Context Properties

- **`x-copilotcloud-public-api-key`**: Used when `cloud` config is present; enables trace telemetry
- **`properties` argument**: Arbitrary JSON merged into server-side context; available to providers
- **Context forwarding**: Properties forwarded to remote endpoints via `onBeforeRequest` header injection

## Observability and Middleware

### Middleware Hooks

```typescript
interface CopilotMiddleware {
  onBeforeRequest?: (context: MiddlewareContext) => Promise<void>;
  onAfterRequest?: (context: MiddlewareContext) => Promise<void>;
}

interface MiddlewareContext {
  threadId?: string;
  runId?: string;
  inputMessages: Message[];
  outputMessages?: Message[];
  properties: Record<string, any>;
  url?: string;
}
```

### Observability Features

**Core Interfaces:**
```typescript
interface CopilotObservabilityConfig {
  enabled: boolean;
  progressive: boolean; // Stream each token vs batch complete responses
  hooks: {
    handleRequest: (data: LLMRequestData) => void | Promise<void>;
    handleResponse: (data: LLMResponseData) => void | Promise<void>;
    handleError: (data: LLMErrorData) => void | Promise<void>;
  };
}

interface LLMRequestData {
  threadId?: string;
  runId?: string;
  model?: string;
  messages: any[];
  actions?: any[];
  forwardedParameters?: any;
  timestamp: number;
  provider?: string;
}

interface LLMResponseData {
  threadId: string;
  runId?: string;
  model?: string;
  output: any;
  latency: number;
  timestamp: number;
  provider?: string;
  isProgressiveChunk?: boolean;
  isFinalResponse?: boolean;
}
```

**Features:**
- **Telemetry**: Usage tracking and analytics via telemetry client
- **Logging**: Structured logging with configurable levels
- **Error Reporting**: Centralized error handling with context
- **Performance Monitoring**: Request/response timing and metrics

## MCP Integration (Experimental)

**Model Context Protocol (MCP) Tooling:**
- At request time, runtime can fetch tools from MCP servers
- Tools defined in runtime config or supplied via `properties.mcpServers`
- Tools converted into server-side actions
- Instruction text injected into system message to guide tool usage

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

## FastAPI Implementation Strategy

### 1. Application Architecture

**FastAPI Application Structure:**
```python
# main.py - Application entry point
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .graphql.schema import create_graphql_app
from .runtime.copilot_runtime import CopilotRuntime
from .service_adapters import ServiceAdapterRegistry
from .observability import setup_observability, HealthCheckManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await setup_observability()
    await ServiceAdapterRegistry.initialize()
    yield
    # Shutdown
    await ServiceAdapterRegistry.cleanup()

app = FastAPI(
    title="CopilotKit Runtime",
    description="Python implementation of CopilotKit Runtime",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL endpoint
graphql_app = create_graphql_app()
app.mount("/graphql", graphql_app)

# Health check
@app.get("/health")
async def health_check():
    health_manager = HealthCheckManager()
    return await health_manager.check_system_health()
```

### 2. GraphQL Implementation

**Using Strawberry GraphQL with FastAPI:**
```python
# graphql/schema.py
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL
from typing import AsyncGenerator, List, Optional
import asyncio

from .types.inputs import GenerateCopilotResponseInput
from .types.outputs import CopilotResponse, AgentsResponse
from .resolvers.copilot_resolver import CopilotResolver
from .resolvers.state_resolver import StateResolver

@strawberry.type
class Query:
    @strawberry.field
    async def hello(self) -> str:
        return "Hello World"
    
    @strawberry.field
    async def available_agents(
        self, 
        info: strawberry.Info
    ) -> AgentsResponse:
        resolver = CopilotResolver()
        return await resolver.available_agents(info.context)

@strawberry.type
class Mutation:
    @strawberry.field
    async def generate_copilot_response(
        self,
        data: GenerateCopilotResponseInput,
        info: strawberry.Info,
        properties: Optional[strawberry.scalars.JSON] = None
    ) -> CopilotResponse:
        resolver = CopilotResolver()
        return await resolver.generate_copilot_response(
            data, info.context, properties
        )

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def copilot_stream(
        self,
        data: GenerateCopilotResponseInput,
        info: strawberry.Info
    ) -> AsyncGenerator[CopilotResponse, None]:
        resolver = CopilotResolver()
        async for response in resolver.stream_copilot_response(data, info.context):
            yield response

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

def create_graphql_app():
    return GraphQLRouter(
        schema,
        subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL],
        context_getter=get_context
    )

async def get_context(request) -> dict:
    return {
        "request": request,
        "runtime": get_runtime_instance(),
        "logger": get_logger()
    }
```

### 3. Event Streaming System

**Python AsyncIO Event System:**
```python
# runtime/event_system.py
import asyncio
import weakref
from typing import AsyncGenerator, Dict, Any, List, Callable, Optional, TypeVar, Generic
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

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
        self._subscribers: List[EventSubscription] = []
        self._event_history: List[RuntimeEvent] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)
    
    async def emit(self, event: RuntimeEvent):
        async with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            # Emit to all subscribers
            tasks = []
            for subscription in self._subscribers[:]:
                if subscription.active:
                    tasks.append(subscription.emit(event))
                else:
                    self._subscribers.remove(subscription)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def subscribe(
        self, 
        filters: List[EventFilter] = None,
        queue_size: int = 100,
        replay_history: bool = False
    ) -> AsyncGenerator[RuntimeEvent, None]:
        queue = asyncio.Queue(maxsize=queue_size)
        subscription = EventSubscription(queue, filters)
        
        async with self._lock:
            self._subscribers.append(subscription)
            
            # Replay history if requested
            if replay_history:
                for event in self._event_history:
                    if subscription.should_receive(event):
                        await queue.put(event)
        
        try:
            while subscription.active:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
        finally:
            subscription.unsubscribe()
```

### 4. Service Adapter Interface

**Python Service Adapter Implementation:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator

class CopilotServiceAdapter(ABC):
    @abstractmethod
    async def process(
        self, 
        request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        pass

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

class LangGraphAdapter(CopilotServiceAdapter):
    async def process(self, request):
        # LangGraph integration logic
        async for event in self.client.runs.stream(
            thread_id=request.thread_id,
            assistant_id=request.agent_name,
            input={"messages": request.messages},
            stream_mode="events"
        ):
            yield convert_langgraph_event_to_runtime_event(event)
```

### 5. Agent Integration

**Python LangGraph Integration:**
```python
# Interface with LangGraph using their Python SDK
from langgraph_sdk import Client

class LangGraphPlatformEndpoint:
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

class CopilotKitEndpoint:
    async def execute_agent(self, request: AgentExecutionRequest):
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.url}/agents/execute",
                json=request.dict()) as response:
                async for line in response.aiter_lines():
                    if line:
                        event_data = json.loads(line)
                        yield RuntimeEvent(**event_data)
```

## Data Models (Pydantic)

### Core Models

```python
from pydantic import BaseModel
from typing import Optional, List, Union
from enum import Enum
from datetime import datetime

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    DEVELOPER = "developer"

class CopilotRequestType(str, Enum):
    CHAT = "Chat"
    TASK = "Task"
    TEXTAREA_COMPLETION = "TextareaCompletion"
    TEXTAREA_POPOVER = "TextareaPopover"
    SUGGESTION = "Suggestion"

class TextMessageInput(BaseModel):
    content: str
    parent_message_id: Optional[str] = None
    role: MessageRole

class ActionExecutionMessageInput(BaseModel):
    name: str
    arguments: str  # JSON string
    parent_message_id: Optional[str] = None
    scope: Optional[str] = None  # deprecated

class MessageInput(BaseModel):
    id: str
    created_at: datetime
    text_message: Optional[TextMessageInput] = None
    action_execution_message: Optional[ActionExecutionMessageInput] = None
    result_message: Optional[ResultMessageInput] = None
    agent_state_message: Optional[AgentStateMessageInput] = None
    image_message: Optional[ImageMessageInput] = None

class ActionInput(BaseModel):
    name: str
    description: str
    json_schema: str
    available: Optional[str] = None

class GenerateCopilotResponseMetadataInput(BaseModel):
    request_type: CopilotRequestType

class GenerateCopilotResponseInput(BaseModel):
    metadata: GenerateCopilotResponseMetadataInput
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

## Error Handling (Python Implementation)

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

### Error Message System (Python)

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

## Python Implementation Considerations

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

## Compatibility Considerations for Python Port

- **Support non-streaming first**: Ensure union types and fields match TS contract
- **Streaming Implementation**: Use SSE/multipart incremental delivery with per-message sub-streams
- **Error Normalization**: Include `extensions.code`, `statusCode`, `severity`, and `visibility`
- **Agent Discovery**: Must filter internal endpoint details from public response
- **Retry and Networking**: All remote HTTP calls use retry with exponential backoff
- **JSONL Parsing**: Handle partial JSON chunks across network boundaries properly

## Dependencies

### Core Dependencies
```python
# Web framework
fastapi>=0.104.0
uvicorn>=0.24.0

# GraphQL
strawberry-graphql>=0.215.0  # or ariadne>=0.22.0

# Async and streaming
aiohttp>=3.9.0
httpx>=0.25.0

# Data validation and serialization
pydantic>=2.5.0
typing-extensions>=4.8.0

# LangGraph integration
langgraph>=0.2.0
langchain>=0.3.0

# Existing CopilotKit SDK
# (from ./sdk-python)
```

### Optional Dependencies
```python
# Observability
opentelemetry-api>=1.21.0
structlog>=23.2.0

# Cloud integrations
httpx>=0.25.0
```

## Minimal Example Exchanges

### 1. Health Check
```graphql
# Request
query { hello }

# Response
{ "data": { "hello": "Hello World" } }
```

### 2. Agent Discovery
```graphql
# Request
query { 
  availableAgents { 
    agents { 
      id 
      name 
      description 
    } 
  } 
}

# Response
{ 
  "data": { 
    "availableAgents": { 
      "agents": [
        { 
          "id": "planner", 
          "name": "planner" 
        }
      ] 
    } 
  } 
}
```

### 3. Chat Run (Simplified)
```graphql
# Request
mutation { 
  generateCopilotResponse(
    data: { 
      frontend: { 
        actions: [], 
        url: "https://app" 
      }, 
      messages: [...], 
      metadata: { 
        requestType: Chat 
      } 
    }
  ) { 
    threadId 
    runId 
    messages { 
      __typename 
      ... on TextMessageOutput { 
        content 
        role 
      } 
    } 
    status { 
      ... on SuccessResponseStatus { 
        code 
      } 
      ... on FailedResponseStatus { 
        reason 
      } 
    } 
  } 
}

# Response
# As messages complete, messages array contains incremental or final entries
# Status resolves to success or failure
```

This comprehensive specification provides the foundation for creating a complete Python port of CopilotRuntime that maintains compatibility with the existing TypeScript ecosystem while leveraging Python's strengths for agentic AI workflows.