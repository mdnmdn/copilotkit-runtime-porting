# CopilotRuntime Python Porting Specification

## Overview

This document provides a comprehensive specification for porting the CopilotRuntime from TypeScript to Python using FastAPI. The CopilotRuntime serves as the backend component of CopilotKit that handles communication with LLMs, message history, state management, and orchestrates AI interactions.

## Architecture Overview

The CopilotRuntime acts as a **GraphQL proxy** that:
1. Exposes a GraphQL endpoint for frontend React components
2. Translates GraphQL requests to REST-like interfaces for Python agentic frameworks (LangGraph, CrewAI)
3. Manages real-time streaming of AI responses
4. Handles action execution and state management
5. Provides observability and error handling

## Core Components Deep Dive

### 1. GraphQL Schema and Types - Deep Analysis

The GraphQL layer serves as the primary interface between frontend React components and the backend runtime. It's built using TypeGraphQL with a resolver-based architecture that supports real-time streaming through GraphQL subscriptions.

#### GraphQL Resolver Architecture

The runtime uses a **resolver-based architecture** with two main resolvers:

1. **CopilotResolver** (`copilot.resolver.ts`):
   - Handles main AI interaction logic
   - Manages streaming responses using RxJS observables
   - Coordinates with service adapters
   - Implements guardrails and error handling

2. **StateResolver** (`state.resolver.ts`):
   - Manages agent state persistence
   - Handles state loading and saving operations

#### Primary GraphQL Operations

**Queries:**
- `hello(): String` - Health check endpoint
- `availableAgents(): AgentsResponse` - Discover available agents from configured endpoints

**Mutations:**
- `generateCopilotResponse(data: GenerateCopilotResponseInput, properties?: JSONObject): CopilotResponse` - Main entry point for AI interactions

#### Streaming Architecture

The GraphQL implementation uses **GraphQL Yoga** with the `@graphql-yoga/plugin-defer-stream` plugin to enable real-time streaming. The streaming works through:

1. **Repeater Pattern**: Uses `graphql-yoga/Repeater` for async iteration
2. **RxJS Integration**: Converts RxJS observables to async iterables
3. **Event Coordination**: Multiple event streams are merged and coordinated
4. **Backpressure Handling**: Manages flow control for high-throughput scenarios

**Streaming Flow:**
```typescript
// Simplified streaming pattern
messages: new Repeater(async (pushMessage, stopStreamingMessages) => {
  const eventStreamSubscription = eventStream.subscribe({
    next: async (event) => {
      // Process event and push to GraphQL stream
      pushMessage(transformedMessage);
    },
    error: (err) => {
      // Handle errors and stop streaming
      stopStreamingMessages();
    },
    complete: () => {
      // Clean up and resolve
      stopStreamingMessages();
    }
  });
})
```

#### Core Input Types

```typescript
// Main request input
class GenerateCopilotResponseInput {
  metadata: GenerateCopilotResponseMetadataInput
  threadId?: string
  runId?: string
  messages: MessageInput[]
  frontend: FrontendInput
  cloud?: CloudInput
  forwardedParameters?: ForwardedParametersInput
  agentSession?: AgentSessionInput
  agentState?: AgentStateInput
  agentStates?: AgentStateInput[]
  extensions?: ExtensionsInput
  metaEvents?: MetaEventInput[]
}

// Message types (union via optional fields)
class MessageInput {
  id: string
  createdAt: Date
  textMessage?: TextMessageInput
  actionExecutionMessage?: ActionExecutionMessageInput
  resultMessage?: ResultMessageInput
  agentStateMessage?: AgentStateMessageInput
  imageMessage?: ImageMessageInput
}

class TextMessageInput {
  content: string
  parentMessageId?: string
  role: MessageRole  // user | assistant | system | tool | developer
}

class ActionExecutionMessageInput {
  name: string
  arguments: string  // JSON string
  parentMessageId?: string
  scope?: string  // deprecated
}

class ResultMessageInput {
  actionExecutionId: string
  actionName: string
  parentMessageId?: string
  result: string  // JSON string with optional error encoding
}

class AgentStateMessageInput {
  threadId: string
  agentName: string
  role: MessageRole
  state: string  // JSON string
  running: boolean
  nodeName: string
  runId: string
  active: boolean
}

class ActionInput {
  name: string
  description: string
  jsonSchema: string  // JSON Schema for parameters
  available?: ActionInputAvailability  // disabled | enabled | remote
}
```

#### Core Output Types

```typescript
class CopilotResponse {
  threadId: string
  status: ResponseStatusUnion  // Success | Error variants
  runId?: string
  messages: BaseMessageOutput[]  // Streaming array
  extensions?: ExtensionsResponse
  metaEvents?: BaseMetaEvent[]
}

// Message output types (interface with implementations)
interface BaseMessageOutput {
  id: string
  createdAt: Date
  status: MessageStatusUnion
}

class TextMessageOutput implements BaseMessageOutput {
  role: MessageRole
  content: string[]  // Streaming content chunks
  parentMessageId?: string
}

class ActionExecutionMessageOutput implements BaseMessageOutput {
  name: string
  scope?: string  // deprecated
  arguments: string[]  // Streaming argument chunks
  parentMessageId?: string
}

class ResultMessageOutput implements BaseMessageOutput {
  actionExecutionId: string
  actionName: string
  result: string
}

class AgentStateMessageOutput implements BaseMessageOutput {
  threadId: string
  agentName: string
  nodeName: string
  runId: string
  active: boolean
  role: MessageRole
  state: string
  running: boolean
}
```

### 2. Event System and Streaming - Deep Analysis

The event system is the **core orchestration mechanism** of the CopilotRuntime. It uses RxJS observables to create a reactive, event-driven architecture that coordinates between multiple async processes (AI services, action execution, state management).

#### Event System Architecture

**Core Components:**
1. **RuntimeEventSource**: Central event emitter and coordinator
2. **Event Streams**: RxJS observables for different event types
3. **Event Processors**: Transform raw events into GraphQL responses
4. **Subscription Management**: Handle multiple concurrent subscriptions

**Event Flow Pattern:**
```typescript
// Event source creation and management
class RuntimeEventSource {
  private eventSubject = new ReplaySubject<RuntimeEvent>();
  private metaEventSubject = new Subject<RunTimeMetaEvent>();
  
  // Emit events to all subscribers
  emit(event: RuntimeEvent) {
    this.eventSubject.next(event);
  }
  
  // Create filtered streams for specific event types
  getEventStream() {
    return this.eventSubject.asObservable();
  }
}
```

#### Event Coordination Patterns

**1. Event Merging**: Multiple event streams are merged using RxJS operators:
```typescript
const combinedStream = merge(
  textMessageEvents$,
  actionExecutionEvents$,
  agentStateEvents$,
  metaEvents$
).pipe(
  shareReplay(1),
  finalize(() => cleanup())
);
```

**2. Event Filtering and Transformation**:
```typescript
// Filter events by message ID and transform
const messageContentStream = eventStream.pipe(
  skipWhile((e: RuntimeEvent) => e !== startEvent),
  takeWhile((e: RuntimeEvent) => e.type !== RuntimeEventTypes.TextMessageEnd),
  filter((e: RuntimeEvent) => e.type === RuntimeEventTypes.TextMessageContent),
  map(event => transformToGraphQLMessage(event))
);
```

**3. Backpressure and Flow Control**:
- Uses `ReplaySubject` for event buffering
- Implements proper cleanup with `finalize()` operators
- Manages subscription lifecycle to prevent memory leaks

#### Event Lifecycle Management

**Event Creation → Processing → Cleanup:**
1. **Event Creation**: Service adapters emit events to `RuntimeEventSource`
2. **Event Processing**: GraphQL resolver subscribes and processes events
3. **Event Transformation**: Events are converted to GraphQL response format
4. **Stream Completion**: Proper cleanup and resource deallocation

The runtime uses an **RxJS-based event streaming system** that must be replicated in Python:

#### Runtime Event Types

```typescript
enum RuntimeEventTypes {
  TextMessageStart = "TextMessageStart"
  TextMessageContent = "TextMessageContent"
  TextMessageEnd = "TextMessageEnd"
  ActionExecutionStart = "ActionExecutionStart"
  ActionExecutionArgs = "ActionExecutionArgs"
  ActionExecutionEnd = "ActionExecutionEnd"
  ActionExecutionResult = "ActionExecutionResult"
  AgentStateMessage = "AgentStateMessage"
  MetaEvent = "MetaEvent"
}

enum RuntimeMetaEventName {
  LangGraphInterruptEvent = "LangGraphInterruptEvent"
  LangGraphInterruptResumeEvent = "LangGraphInterruptResumeEvent"
  CopilotKitLangGraphInterruptEvent = "CopilotKitLangGraphInterruptEvent"
}
```

#### Event Flow Pattern

1. **Event Source Creation**: `RuntimeEventSource` manages the observable stream
2. **Event Subscription**: GraphQL resolver subscribes to events
3. **Event Processing**: Events are transformed into GraphQL response chunks
4. **Streaming Response**: GraphQL uses `Repeater` pattern for real-time streaming

**Python Implementation Requirements:**
- Use `asyncio` streams or `asyncio.Queue` for event handling
- Implement async generators for GraphQL streaming
- Use `asyncio.Event` for coordination between producers/consumers

### 3. Service Adapter Pattern - Deep Analysis

The Service Adapter pattern is the **abstraction layer** that enables the runtime to work with multiple AI services and frameworks. It provides a unified interface while allowing each adapter to implement service-specific logic.

#### Adapter Architecture

**Core Interface:**
```typescript
interface CopilotServiceAdapter {
  process(request: CopilotRuntimeChatCompletionRequest): Promise<CopilotRuntimeChatCompletionResponse>
}
```

**Adapter Responsibilities:**
1. **Message Translation**: Convert CopilotKit messages to service-specific formats
2. **Event Emission**: Emit runtime events during processing
3. **Error Handling**: Translate service errors to CopilotKit error format
4. **Streaming Management**: Handle real-time response streaming
5. **Action Execution**: Coordinate tool/function calling

#### Adapter Implementation Patterns

**1. Direct LLM Adapters** (OpenAI, Anthropic, Google):
```typescript
class OpenAIAdapter implements CopilotServiceAdapter {
  async process(request: CopilotRuntimeChatCompletionRequest) {
    // Convert messages to OpenAI format
    const openAIMessages = convertMessages(request.messages);
    
    // Create streaming request
    const stream = await this.openai.chat.completions.create({
      model: request.model,
      messages: openAIMessages,
      tools: convertActions(request.actions),
      stream: true
    });
    
    // Process stream and emit events
    for await (const chunk of stream) {
      this.emitChunkEvents(chunk, request.eventSource);
    }
  }
}
```

**2. Framework Adapters** (LangChain, LangServe):
```typescript
class LangChainAdapter implements CopilotServiceAdapter {
  async process(request: CopilotRuntimeChatCompletionRequest) {
    // Create LangChain runnable
    const chain = this.createChain(request.actions);
    
    // Stream with callbacks
    await chain.stream(
      { messages: request.messages },
      {
        callbacks: [
          new CopilotKitCallbackHandler(request.eventSource)
        ]
      }
    );
  }
}
```

**3. Remote Service Adapters** (LangServe, Custom APIs):
```typescript
class LangServeAdapter implements CopilotServiceAdapter {
  async process(request: CopilotRuntimeChatCompletionRequest) {
    // Make HTTP request to remote service
    const response = await fetch(this.endpoint, {
      method: 'POST',
      body: JSON.stringify(this.formatRequest(request)),
      headers: { 'Content-Type': 'application/json' }
    });
    
    // Process streaming response
    const reader = response.body?.getReader();
    await this.processStreamingResponse(reader, request.eventSource);
  }
}
```

#### Event Emission Patterns

**Adapters emit events at key points:**
1. **Message Start**: When AI begins responding
2. **Content Chunks**: For each piece of streamed content
3. **Action Calls**: When tools/functions are invoked
4. **Action Results**: When tool execution completes
5. **Message End**: When response is complete

**Event Emission Example:**
```typescript
// In adapter implementation
private emitTextMessage(content: string, eventSource: RuntimeEventSource) {
  eventSource.emit({
    type: RuntimeEventTypes.TextMessageStart,
    messageId: this.messageId,
    parentMessageId: this.parentMessageId
  });
  
  eventSource.emit({
    type: RuntimeEventTypes.TextMessageContent,
    messageId: this.messageId,
    content: content
  });
  
  eventSource.emit({
    type: RuntimeEventTypes.TextMessageEnd,
    messageId: this.messageId
  });
}
```

#### Adapter Registration and Selection

**Dynamic Adapter Selection:**
```typescript
class CopilotRuntime {
  private adapters: Map<string, CopilotServiceAdapter> = new Map();
  
  registerAdapter(name: string, adapter: CopilotServiceAdapter) {
    this.adapters.set(name, adapter);
  }
  
  async process(request: CopilotRuntimeRequest) {
    const adapter = this.adapters.get(request.adapterName) || this.defaultAdapter;
    return adapter.process(request);
  }
}
```

The runtime uses a **Service Adapter pattern** to integrate with different AI services:

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
```

**Available Adapters:**
- `OpenAIAdapter` - Direct OpenAI integration
- `AnthropicAdapter` - Anthropic Claude integration
- `LangChainAdapter` - LangChain integration
- `LangServeAdapter` - LangServe remote chains
- `EmptyAdapter` - No-op adapter for testing

### 4. Remote Actions and Agent Integration - Deep Analysis

The remote actions system enables the runtime to **orchestrate external agents and services** while maintaining a unified interface. This is the core mechanism that allows CopilotKit to work with frameworks like LangGraph, CrewAI, and custom agent implementations.

#### Remote Actions Architecture

**Core Components:**
1. **Remote Action Discovery**: Automatic detection of available actions from endpoints
2. **Action Proxy System**: Transparent forwarding of action calls to remote services
3. **Agent Session Management**: Stateful connections to agent frameworks
4. **Event Translation**: Converting between different event formats

**Remote Action Flow:**
```typescript
// Action discovery and registration
class CopilotRuntime {
  async discoverRemoteActions(endpoint: EndpointDefinition): Promise<ActionInput[]> {
    // 1. Query endpoint for available actions
    const response = await fetch(`${endpoint.url}/actions`);
    const actions = await response.json();
    
    // 2. Convert to CopilotKit format
    return actions.map(action => ({
      name: action.name,
      description: action.description,
      jsonSchema: JSON.stringify(action.parameters),
      available: ActionInputAvailability.remote
    }));
  }
  
  async executeRemoteAction(action: RemoteAgentAction, args: any): Promise<any> {
    // 3. Forward action execution to remote endpoint
    const response = await fetch(`${action.endpoint.url}/execute`, {
      method: 'POST',
      body: JSON.stringify({ action: action.name, arguments: args }),
      headers: createHeaders(action.endpoint)
    });
    
    return response.json();
  }
}
```

#### Agent Session Management

**Session Lifecycle:**
```typescript
interface AgentSessionInput {
  agentName: string
  threadId?: string
  runId?: string
  state?: any
}

class AgentSessionManager {
  private sessions: Map<string, AgentSession> = new Map();
  
  async createSession(input: AgentSessionInput): Promise<AgentSession> {
    const session = new AgentSession({
      id: input.threadId || randomId(),
      agentName: input.agentName,
      state: input.state || {},
      endpoint: this.findEndpointForAgent(input.agentName)
    });
    
    this.sessions.set(session.id, session);
    return session;
  }
  
  async executeWithSession(sessionId: string, request: any): Promise<any> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error('Session not found');
    
    // Maintain state across calls
    const result = await session.execute(request);
    session.updateState(result.state);
    
    return result;
  }
}
```

#### LangGraph Integration

The LangGraph integration is the **most sophisticated agent integration** in the runtime, providing deep integration with LangGraph's event system and state management.

**Integration Architecture:**
```typescript
class LangGraphAgent extends AGUILangGraphAgent {
  constructor(config: LangGraphAgentConfig) {
    super(config);
  }
  
  // Override event dispatching to handle CopilotKit events
  dispatchEvent(event: ProcessedEvents) {
    if (event.type === EventType.CUSTOM) {
      return this.handleCopilotKitCustomEvent(event);
    }
    return super.dispatchEvent(event);
  }
}
```

**Event Mapping System:**
1. **LangGraph → CopilotKit**: Converts LangGraph events to runtime events
2. **CopilotKit → LangGraph**: Translates runtime commands to LangGraph actions
3. **Bidirectional State Sync**: Maintains state consistency between systems

**Custom Event Handling:**
```typescript
enum CustomEventNames {
  CopilotKitManuallyEmitMessage = "copilotkit_manually_emit_message"
  CopilotKitManuallyEmitToolCall = "copilotkit_manually_emit_tool_call"
  CopilotKitManuallyEmitIntermediateState = "copilotkit_manually_emit_intermediate_state"
  CopilotKitExit = "copilotkit_exit"
}

// Custom event processing
handleCopilotKitCustomEvent(customEvent: CustomEvent) {
  switch (customEvent.name) {
    case CustomEventNames.CopilotKitManuallyEmitMessage:
      this.emitTextMessageSequence(customEvent.value);
      break;
    case CustomEventNames.CopilotKitManuallyEmitToolCall:
      this.emitToolCallSequence(customEvent.value);
      break;
    case CustomEventNames.CopilotKitManuallyEmitIntermediateState:
      this.updateIntermediateState(customEvent.value);
      break;
  }
}
```

**LangGraph Platform Integration:**
```typescript
interface LangGraphPlatformEndpoint {
  type: EndpointType.LangGraphPlatform
  deploymentUrl: string
  agents: string[]
  headers?: Record<string, string>
}

class LangGraphPlatformAdapter {
  async connectToDeployment(endpoint: LangGraphPlatformEndpoint) {
    const client = new LangGraphClient({
      apiUrl: endpoint.deploymentUrl,
      headers: endpoint.headers
    });
    
    // Discover available agents
    const agents = await client.assistants.search();
    return agents.filter(agent => 
      endpoint.agents.includes(agent.name)
    );
  }
  
  async streamAgent(agentId: string, messages: Message[]) {
    const stream = await this.client.runs.stream(
      agentId,
      { messages: this.convertMessages(messages) }
    );
    
    // Convert LangGraph events to CopilotKit events
    for await (const event of stream) {
      yield this.translateEvent(event);
    }
  }
}
```

The runtime integrates with LangGraph through:

1. **LangGraph Agent Class**: `LangGraphAgent` extends `@ag-ui/langgraph` 
2. **Event Mapping**: Maps LangGraph events to CopilotKit events
3. **Custom Events**: Handles CopilotKit-specific events like manual message emission

```typescript
enum CustomEventNames {
  CopilotKitManuallyEmitMessage = "copilotkit_manually_emit_message"
  CopilotKitManuallyEmitToolCall = "copilotkit_manually_emit_tool_call"
  CopilotKitManuallyEmitIntermediateState = "copilotkit_manually_emit_intermediate_state"
  CopilotKitExit = "copilotkit_exit"
}
```

#### Remote Endpoint Types

```typescript
enum EndpointType {
  CopilotKit = "copilotkit"
  LangGraphPlatform = "langgraph_platform"
}

interface CopilotKitEndpoint {
  type: EndpointType.CopilotKit
  url: string
  headers?: Record<string, string>
}

interface LangGraphPlatformEndpoint {
  type: EndpointType.LangGraphPlatform
  deploymentUrl: string
  agents: string[]
  headers?: Record<string, string>
}
```

### 5. Error Handling and Observability - Deep Analysis

The error handling and observability system provides **comprehensive monitoring, debugging, and error recovery** capabilities. It's designed to handle both user errors and system failures gracefully while providing detailed diagnostics.

#### Error Handling Architecture

**Error Classification System:**
```typescript
enum CopilotKitErrorCode {
  UNKNOWN = "UNKNOWN"
  AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
  API_NOT_FOUND = "API_NOT_FOUND"
  REMOTE_ENDPOINT_NOT_FOUND = "REMOTE_ENDPOINT_NOT_FOUND"
  CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
  MISSING_PUBLIC_API_KEY_ERROR = "MISSING_PUBLIC_API_KEY_ERROR"
}

// Error hierarchy
abstract class CopilotKitError extends Error {
  abstract code: CopilotKitErrorCode;
  abstract severity: Severity;
  abstract visibility: "user" | "developer" | "internal";
}

class CopilotKitLowLevelError extends CopilotKitError {
  constructor(public error: Error, public url: string, public message: string) {
    super(message);
  }
}
```

**Error Context and Enrichment:**
```typescript
interface CopilotRequestContext {
  source: "runtime" | "frontend" | "agent";
  request: {
    operation: string;
    startTime: number;
    threadId?: string;
    runId?: string;
  };
  technical: {
    environment?: string;
    version?: string;
    userAgent?: string;
  };
  metadata: Record<string, any>;
}

class ErrorEnrichment {
  static enrichError(error: any, context: CopilotRequestContext): ResolvedCopilotKitError {
    // Add context information
    const enrichedError = {
      ...error,
      context,
      timestamp: Date.now(),
      stackTrace: error.stack,
      helpfulMessage: generateHelpfulErrorMessage(error, context)
    };
    
    return enrichedError;
  }
}
```

**Error Recovery Strategies:**
```typescript
class ErrorRecoveryManager {
  async handleStreamingError(error: any, eventSource: RuntimeEventSource) {
    // 1. Classify error type
    const errorType = this.classifyError(error);
    
    // 2. Attempt recovery based on type
    switch (errorType) {
      case 'network':
        return this.retryWithBackoff(error);
      case 'authentication':
        return this.refreshCredentials(error);
      case 'rate_limit':
        return this.handleRateLimit(error);
      default:
        return this.gracefulFailure(error, eventSource);
    }
  }
  
  private async gracefulFailure(error: any, eventSource: RuntimeEventSource) {
    // Emit error event to client
    eventSource.emit({
      type: RuntimeEventTypes.MetaEvent,
      name: RuntimeMetaEventName.ErrorEvent,
      data: {
        error: this.sanitizeError(error),
        canRetry: this.isRetryable(error)
      }
    });
  }
}
```

#### Observability System

**Telemetry and Analytics:**
```typescript
class TelemetryClient {
  capture(event: string, properties: Record<string, any>) {
    // Send to analytics service
    this.analyticsService.track({
      event,
      properties: {
        ...this.globalProperties,
        ...properties,
        timestamp: Date.now(),
        sessionId: this.sessionId
      }
    });
  }
  
  setGlobalProperties(properties: Record<string, any>) {
    this.globalProperties = { ...this.globalProperties, ...properties };
  }
}

// Usage throughout runtime
telemetry.capture("oss.runtime.copilot_request_created", {
  "cloud.guardrails.enabled": data.cloud?.guardrails !== undefined,
  requestType: data.metadata.requestType,
  "cloud.api_key_provided": !!publicApiKey
});
```

**Structured Logging:**
```typescript
interface LogContext {
  component: string;
  level: LogLevel;
  requestId?: string;
  threadId?: string;
}

class Logger {
  child(context: Partial<LogContext>): Logger {
    return new Logger({ ...this.context, ...context });
  }
  
  debug(message: string | object, extra?: object) {
    this.log('debug', message, extra);
  }
  
  error(message: string | object, extra?: object) {
    this.log('error', message, extra);
    // Also send to error tracking service
    this.errorTracker.captureException(message, extra);
  }
}
```

**Performance Monitoring:**
```typescript
class PerformanceMonitor {
  startTimer(operation: string): PerformanceTimer {
    return new PerformanceTimer(operation, Date.now());
  }
  
  recordMetric(name: string, value: number, tags?: Record<string, string>) {
    this.metricsService.gauge(name, value, tags);
  }
}

// Usage in resolvers
const timer = performanceMonitor.startTimer('generateCopilotResponse');
try {
  const result = await this.processRequest(request);
  timer.success();
  return result;
} catch (error) {
  timer.error(error);
  throw error;
}
```

**Health Checks and Monitoring:**
```typescript
class HealthCheckManager {
  async checkSystemHealth(): Promise<HealthStatus> {
    const checks = await Promise.allSettled([
      this.checkDatabase(),
      this.checkExternalServices(),
      this.checkMemoryUsage(),
      this.checkEventQueueHealth()
    ]);
    
    return {
      status: checks.every(c => c.status === 'fulfilled') ? 'healthy' : 'degraded',
      checks: checks.map(this.formatCheckResult),
      timestamp: Date.now()
    };
  }
}
```

#### Error Types

```typescript
enum CopilotKitErrorCode {
  UNKNOWN = "UNKNOWN"
  AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
  API_NOT_FOUND = "API_NOT_FOUND"
  REMOTE_ENDPOINT_NOT_FOUND = "REMOTE_ENDPOINT_NOT_FOUND"
  CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
  MISSING_PUBLIC_API_KEY_ERROR = "MISSING_PUBLIC_API_KEY_ERROR"
}

interface CopilotErrorEvent {
  type: "error" | "warning"
  timestamp: number
  context: CopilotRequestContext
  error?: any
}
```

#### Observability Features

- **Telemetry**: Usage tracking and analytics
- **Logging**: Structured logging with configurable levels
- **Error Reporting**: Centralized error handling with context
- **Performance Monitoring**: Request/response timing

### 6. Cloud Integration and Guardrails - Deep Analysis

The cloud integration system provides **enterprise-grade security, compliance, and content moderation** capabilities. It integrates with CopilotCloud services to enable guardrails, analytics, and advanced monitoring.

#### Cloud Architecture

**Cloud Configuration System:**
```typescript
interface CopilotCloudOptions {
  publicApiKey: string;
  baseUrl?: string;
  guardrails?: {
    inputValidationRules: {
      allowList: string[];
      denyList: string[];
    };
  };
}

class CloudIntegration {
  constructor(private options: CopilotCloudOptions) {
    this.validateConfiguration();
  }
  
  private validateConfiguration() {
    if (!this.options.publicApiKey) {
      throw new CopilotKitError({
        code: CopilotKitErrorCode.MISSING_PUBLIC_API_KEY_ERROR,
        message: "Public API key is required for cloud features"
      });
    }
  }
}
```

**Authentication and Authorization:**
```typescript
class CloudAuthManager {
  async validateApiKey(publicApiKey: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/validate`, {
        headers: {
          'X-CopilotCloud-Public-API-Key': publicApiKey,
          'Content-Type': 'application/json'
        }
      });
      
      return response.ok;
    } catch (error) {
      console.warn('Cloud API key validation failed:', error);
      return false;
    }
  }
  
  createAuthenticatedHeaders(publicApiKey: string): Record<string, string> {
    return {
      'X-CopilotCloud-Public-API-Key': publicApiKey,
      'Content-Type': 'application/json',
      'User-Agent': `CopilotKit-Runtime/${packageJson.version}`
    };
  }
}
```

#### Guardrails System

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

class GuardrailsValidator {
  async validateInput(
    request: GuardrailsValidationRequest,
    publicApiKey: string
  ): Promise<GuardrailsResult> {
    const response = await fetch(`${this.baseUrl}/guardrails/validate`, {
      method: 'POST',
      headers: this.createHeaders(publicApiKey),
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      throw new Error(`Guardrails validation failed: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  private shouldValidate(messages: MessageInput[]): boolean {
    // Only validate if last message is from user
    const lastMessage = messages[messages.length - 1];
    return lastMessage?.textMessage?.role === MessageRole.user;
  }
}
```

**Guardrails Integration Flow:**
```typescript
// In GraphQL resolver
async generateCopilotResponse(data: GenerateCopilotResponseInput) {
  if (data.cloud?.guardrails) {
    // 1. Extract validation context
    const validationRequest = this.buildValidationRequest(data);
    
    // 2. Validate with cloud service
    const guardrailsResult = await this.guardrailsValidator.validateInput(
      validationRequest,
      publicApiKey
    );
    
    // 3. Handle validation result
    if (guardrailsResult.status === "denied") {
      // Block request and return reason
      return this.createGuardrailsFailureResponse(guardrailsResult);
    }
  }
  
  // 4. Continue with normal processing
  return this.processRequest(data);
}
```

**Content Filtering and Moderation:**
```typescript
class ContentModerator {
  async moderateContent(content: string, context: ModerationContext): Promise<ModerationResult> {
    // 1. Check against allow/deny lists
    const listResult = this.checkAgainstLists(content, context.lists);
    if (listResult.blocked) {
      return listResult;
    }
    
    // 2. AI-powered content analysis
    const aiResult = await this.analyzeWithAI(content, context);
    if (aiResult.blocked) {
      return aiResult;
    }
    
    // 3. Custom rule evaluation
    const customResult = this.evaluateCustomRules(content, context.rules);
    return customResult;
  }
  
  private checkAgainstLists(content: string, lists: ContentLists): ModerationResult {
    // Check deny list first
    for (const deniedTopic of lists.denyList) {
      if (this.matchesTopic(content, deniedTopic)) {
        return {
          blocked: true,
          reason: `Content matches denied topic: ${deniedTopic}`,
          confidence: 1.0
        };
      }
    }
    
    // Check allow list
    if (lists.allowList.length > 0) {
      const allowed = lists.allowList.some(topic => 
        this.matchesTopic(content, topic)
      );
      
      if (!allowed) {
        return {
          blocked: true,
          reason: "Content does not match any allowed topics",
          confidence: 0.8
        };
      }
    }
    
    return { blocked: false };
  }
}
```

#### Cloud Analytics and Monitoring

**Usage Analytics:**
```typescript
class CloudAnalytics {
  async trackUsage(event: UsageEvent): Promise<void> {
    await fetch(`${this.baseUrl}/analytics/usage`, {
      method: 'POST',
      headers: this.createHeaders(),
      body: JSON.stringify({
        ...event,
        timestamp: Date.now(),
        version: packageJson.version
      })
    });
  }
  
  async trackError(error: ErrorEvent): Promise<void> {
    await fetch(`${this.baseUrl}/analytics/errors`, {
      method: 'POST',
      headers: this.createHeaders(),
      body: JSON.stringify({
        ...error,
        timestamp: Date.now(),
        stackTrace: error.error?.stack
      })
    });
  }
}
```

**Real-time Monitoring:**
```typescript
class CloudMonitoring {
  private metricsBuffer: MetricEvent[] = [];
  private flushInterval: NodeJS.Timeout;
  
  constructor() {
    // Batch and flush metrics every 30 seconds
    this.flushInterval = setInterval(() => {
      this.flushMetrics();
    }, 30000);
  }
  
  recordMetric(name: string, value: number, tags?: Record<string, string>) {
    this.metricsBuffer.push({
      name,
      value,
      tags,
      timestamp: Date.now()
    });
    
    // Flush if buffer is full
    if (this.metricsBuffer.length >= 100) {
      this.flushMetrics();
    }
  }
  
  private async flushMetrics() {
    if (this.metricsBuffer.length === 0) return;
    
    const metrics = [...this.metricsBuffer];
    this.metricsBuffer = [];
    
    try {
      await fetch(`${this.baseUrl}/monitoring/metrics`, {
        method: 'POST',
        headers: this.createHeaders(),
        body: JSON.stringify({ metrics })
      });
    } catch (error) {
      // Re-add metrics to buffer on failure
      this.metricsBuffer.unshift(...metrics);
      console.error('Failed to flush metrics:', error);
    }
  }
}
```

#### Cloud Features

```typescript
interface CloudInput {
  guardrails?: CloudGuardrailsInput
}

interface CloudGuardrailsInput {
  inputValidationRules: {
    allowList: string[]
    denyList: string[]
  }
}
```

#### Guardrails Flow

1. **Input Validation**: Check user messages against allow/deny lists
2. **API Call**: POST to `/guardrails/validate` endpoint
3. **Response Handling**: Block or allow based on validation result
4. **Error Reporting**: Send guardrails failures to client

## Python Implementation Architecture

### 1. FastAPI Application Structure

```python
# Main application structure
app = FastAPI()

# GraphQL endpoint using Strawberry or Ariadne
@app.post("/graphql")
async def graphql_endpoint(request: Request):
    # GraphQL processing logic
    pass

# Health check
@app.get("/")
async def health_check():
    return {"status": "ok"}
```

### 2. GraphQL Implementation Options

**Option A: Strawberry GraphQL**
- Type-safe Python GraphQL library
- Dataclass-based schema definition
- Built-in async support
- Good FastAPI integration

**Option B: Ariadne**
- Schema-first approach
- Flexible resolver system
- Good streaming support

### 3. Event System Implementation

```python
import asyncio
from typing import AsyncGenerator, Dict, Any
from enum import Enum

class RuntimeEventTypes(Enum):
    TEXT_MESSAGE_START = "TextMessageStart"
    TEXT_MESSAGE_CONTENT = "TextMessageContent"
    TEXT_MESSAGE_END = "TextMessageEnd"
    # ... other events

class RuntimeEventSource:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: List[asyncio.Queue] = []
    
    async def emit(self, event: Dict[str, Any]):
        await self._queue.put(event)
        for subscriber in self._subscribers:
            await subscriber.put(event)
    
    async def subscribe(self) -> AsyncGenerator[Dict[str, Any], None]:
        subscriber_queue = asyncio.Queue()
        self._subscribers.append(subscriber_queue)
        try:
            while True:
                event = await subscriber_queue.get()
                yield event
        finally:
            self._subscribers.remove(subscriber_queue)
```

### 4. Service Adapter Pattern

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

class LangGraphAdapter(CopilotServiceAdapter):
    async def process(self, request):
        # LangGraph integration logic
        pass
```

### 5. LangGraph Integration

```python
from langgraph import StateGraph
from copilotkit import CopilotKitSDK

class LangGraphCopilotIntegration:
    def __init__(self, graph: StateGraph, sdk: CopilotKitSDK):
        self.graph = graph
        self.sdk = sdk
    
    async def stream_events(self, messages: List[Message]) -> AsyncGenerator:
        # Convert CopilotKit messages to LangGraph format
        # Stream LangGraph events
        # Convert back to CopilotKit events
        pass
```

## Implementation Phases

### Phase 1: Core GraphQL Infrastructure
1. Set up FastAPI application
2. Implement GraphQL schema with Strawberry/Ariadne
3. Create basic input/output types
4. Implement health check and basic resolvers

### Phase 2: Event System and Streaming
1. Implement `RuntimeEventSource` with asyncio
2. Create event streaming for GraphQL subscriptions
3. Add message streaming support
4. Test real-time communication

### Phase 3: Service Adapter Framework
1. Define service adapter interface
2. Implement basic adapters (Empty, OpenAI)
3. Add LangGraph adapter foundation
4. Create adapter registration system

### Phase 4: LangGraph Integration
1. Integrate with existing Python SDK
2. Implement event mapping between LangGraph and CopilotKit
3. Add agent discovery and management
4. Support custom events and interrupts

### Phase 5: Advanced Features
1. Add cloud integration and guardrails
2. Implement error handling and observability
3. Add telemetry and logging
4. Performance optimization

### Phase 6: Testing and Documentation
1. Comprehensive test suite
2. Integration tests with LangGraph
3. Performance benchmarks
4. Complete documentation

## Key Considerations

### 1. Async/Await Patterns
- All I/O operations must be async
- Use `asyncio.Queue` for event coordination
- Implement proper cancellation handling

### 2. Type Safety
- Use Pydantic models for data validation
- Implement proper type hints throughout
- Use dataclasses for internal types

### 3. Error Handling
- Implement structured error types
- Provide helpful error messages
- Support error context and tracing

### 4. Performance
- Optimize event streaming performance
- Implement connection pooling for external services
- Add caching where appropriate

### 5. Compatibility
- Maintain API compatibility with TypeScript version
- Support same GraphQL schema
- Ensure feature parity

## Dependencies

### Core Dependencies
```python
# Web framework
fastapi>=0.104.0
uvicorn>=0.24.0

# GraphQL
strawberry-graphql>=0.215.0  # or ariadne>=0.22.0

# Async and streaming
asyncio-mqtt>=0.16.0  # if needed for external messaging
aiohttp>=3.9.0

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

## Migration Strategy

1. **Parallel Development**: Develop Python version alongside TypeScript
2. **Feature Parity**: Ensure all TypeScript features are supported
3. **Testing**: Extensive testing against TypeScript version
4. **Gradual Migration**: Allow users to migrate incrementally
5. **Documentation**: Comprehensive migration guides

This specification provides the foundation for implementing a fully-featured CopilotRuntime in Python that maintains compatibility with the existing TypeScript ecosystem while leveraging Python's strengths in AI/ML development.