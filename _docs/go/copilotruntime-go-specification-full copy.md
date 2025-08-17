# CopilotRuntime Complete Specification for Go

## Overview

The CopilotRuntime for Go is a comprehensive server implementation that provides GraphQL-based AI chat functionality with support for actions, agents, and real-time streaming. This specification outlines the complete architecture, APIs, and implementation patterns for building a production-ready CopilotRuntime in Go.

## Architecture Overview

The Go CopilotRuntime follows a clean architecture pattern with the following layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    GraphQL API Layer                        │
├─────────────────────────────────────────────────────────────┤
│                 Runtime Engine Core                         │
├─────────────────────────────────────────────────────────────┤
│    Service Adapters    │    Agent Integration    │ Events   │
├─────────────────────────────────────────────────────────────┤
│              Infrastructure & Middleware                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **GraphQL Server**: Built using `gqlgen` or `graphql-go` for schema-first development
- **Runtime Engine**: Core message processing, action execution, and agent coordination
- **Service Adapters**: Pluggable interfaces to various AI services (OpenAI, Anthropic, etc.)
- **Agent System**: Remote and local agent execution with LangGraph integration
- **Event System**: Real-time streaming using channels and Server-Sent Events
- **Middleware**: Request processing, authentication, logging, and observability
- **Error Handling**: Structured error classification and user-friendly messaging

## GraphQL Schema and Protocol

### GraphQL Endpoint

The runtime exposes a single GraphQL endpoint at `/graphql` that handles:
- Queries for agent discovery and health checks
- Mutations for chat completion requests
- Subscriptions for real-time event streaming

### Core Operations

#### Queries

```graphql
type Query {
    health: String!
    availableAgents: [RemoteAgentAction!]!
}
```

#### Mutations

```graphql
type Mutation {
    generateCopilotResponse(input: GenerateCopilotResponseInput!): CopilotResponse!
}
```

#### Subscriptions

```graphql
type Subscription {
    copilotStream(input: GenerateCopilotResponseInput!): RuntimeEvent!
}
```

## Input Types Specification

### Core Input Types

#### `GenerateCopilotResponseInput`

```go
type GenerateCopilotResponseInput struct {
    Messages              []MessageInput              `json:"messages"`
    Actions               []ActionInput               `json:"actions,omitempty"`
    AgentSession          *AgentSessionInput          `json:"agentSession,omitempty"`
    Frontend              *FrontendInput              `json:"frontend,omitempty"`
    ForwardedParameters   *ForwardedParametersInput   `json:"forwardedParameters,omitempty"`
    Cloud                 *CloudInput                 `json:"cloud,omitempty"`
    Guardrails           *GuardrailsInput            `json:"guardrails,omitempty"`
    Extensions           *ExtensionsInput            `json:"extensions,omitempty"`
    MetaEvent            *MetaEventInput             `json:"metaEvent,omitempty"`
    RequestType          CopilotRequestType          `json:"requestType"`
}
```

#### Message Types (Union Type)

```go
type MessageInput interface {
    IsMessageInput()
    GetRole() MessageRole
    GetID() string
}

type TextMessageInput struct {
    ID      string      `json:"id"`
    Role    MessageRole `json:"role"`
    Content string      `json:"content"`
}

func (t TextMessageInput) IsMessageInput() {}
func (t TextMessageInput) GetRole() MessageRole { return t.Role }
func (t TextMessageInput) GetID() string { return t.ID }

type ActionExecutionMessageInput struct {
    ID       string      `json:"id"`
    Role     MessageRole `json:"role"`
    Name     string      `json:"name"`
    Arguments json.RawMessage `json:"arguments"`
}

func (a ActionExecutionMessageInput) IsMessageInput() {}
func (a ActionExecutionMessageInput) GetRole() MessageRole { return a.Role }
func (a ActionExecutionMessageInput) GetID() string { return a.ID }

type ResultMessageInput struct {
    ID     string      `json:"id"`
    Role   MessageRole `json:"role"`
    Result json.RawMessage `json:"result"`
}

func (r ResultMessageInput) IsMessageInput() {}
func (r ResultMessageInput) GetRole() MessageRole { return r.Role }
func (r ResultMessageInput) GetID() string { return r.ID }

type AgentStateMessageInput struct {
    ID            string            `json:"id"`
    Role          MessageRole       `json:"role"`
    AgentName     string            `json:"agentName"`
    NodeName      string            `json:"nodeName"`
    RunningState  string            `json:"runningState"`
    State         map[string]interface{} `json:"state"`
    Active        bool              `json:"active"`
}

func (a AgentStateMessageInput) IsMessageInput() {}
func (a AgentStateMessageInput) GetRole() MessageRole { return a.Role }
func (a AgentStateMessageInput) GetID() string { return a.ID }

type ImageMessageInput struct {
    ID      string      `json:"id"`
    Role    MessageRole `json:"role"`
    Content string      `json:"content"`
    URL     string      `json:"url"`
}

func (i ImageMessageInput) IsMessageInput() {}
func (i ImageMessageInput) GetRole() MessageRole { return i.Role }
func (i ImageMessageInput) GetID() string { return i.ID }
```

#### Supporting Input Types

```go
type FrontendInput struct {
    SDK     string `json:"sdk,omitempty"`
    Version string `json:"version,omitempty"`
}

type ActionInput struct {
    Name        string                 `json:"name"`
    Description string                 `json:"description,omitempty"`
    Parameters  map[string]interface{} `json:"parameters,omitempty"`
}

type AgentSessionInput struct {
    ThreadID string `json:"threadId,omitempty"`
    UserID   string `json:"userId,omitempty"`
}

type ForwardedParametersInput struct {
    OpenAI     map[string]interface{} `json:"openai,omitempty"`
    Anthropic  map[string]interface{} `json:"anthropic,omitempty"`
    Model      string                 `json:"model,omitempty"`
    Custom     map[string]interface{} `json:"custom,omitempty"`
}

type CloudInput struct {
    GuardrailsEnabled bool `json:"guardrailsEnabled,omitempty"`
}

type GuardrailsInput struct {
    Input  []GuardrailsRuleInput `json:"input,omitempty"`
    Output []GuardrailsRuleInput `json:"output,omitempty"`
}

type GuardrailsRuleInput struct {
    Type   string `json:"type"`
    Config map[string]interface{} `json:"config,omitempty"`
}

type ExtensionsInput struct {
    Custom map[string]interface{} `json:"custom,omitempty"`
}

type MetaEventInput struct {
    EventName  MetaEventName          `json:"eventName"`
    Properties map[string]interface{} `json:"properties,omitempty"`
}
```

## Output Types Specification

### Core Output Types

#### `CopilotResponse`

```go
type CopilotResponse struct {
    Messages    []MessageOutput `json:"messages"`
    IsCompleted bool           `json:"isCompleted"`
    ThreadID    *string        `json:"threadId,omitempty"`
}
```

#### Message Output Types

```go
type MessageOutput interface {
    IsMessageOutput()
    GetRole() MessageRole
    GetID() string
}

type BaseMessageOutput struct {
    ID   string      `json:"id"`
    Role MessageRole `json:"role"`
}

func (b BaseMessageOutput) IsMessageOutput() {}
func (b BaseMessageOutput) GetRole() MessageRole { return b.Role }
func (b BaseMessageOutput) GetID() string { return b.ID }

type TextMessageOutput struct {
    BaseMessageOutput
    Content string `json:"content"`
}

type ActionExecutionMessageOutput struct {
    BaseMessageOutput
    Name      string          `json:"name"`
    Arguments json.RawMessage `json:"arguments"`
    Status    string          `json:"status"`
}

type ResultMessageOutput struct {
    BaseMessageOutput
    Result json.RawMessage `json:"result"`
}

type AgentStateMessageOutput struct {
    BaseMessageOutput
    AgentName    string                 `json:"agentName"`
    NodeName     string                 `json:"nodeName"`
    RunningState string                 `json:"runningState"`
    State        map[string]interface{} `json:"state"`
    Active       bool                   `json:"active"`
}

type ImageMessageOutput struct {
    BaseMessageOutput
    Content string `json:"content"`
    URL     string `json:"url"`
}
```

## Enumerations

```go
type ActionInputAvailability string

const (
    ActionInputAvailabilityEnabled  ActionInputAvailability = "ENABLED"
    ActionInputAvailabilityDisabled ActionInputAvailability = "DISABLED"
)

type CopilotRequestType string

const (
    CopilotRequestTypeChat CopilotRequestType = "CHAT"
    CopilotRequestTypeActionExecution CopilotRequestType = "ACTION_EXECUTION"
    CopilotRequestTypeAgentExecution CopilotRequestType = "AGENT_EXECUTION"
)

type MessageRole string

const (
    MessageRoleUser      MessageRole = "user"
    MessageRoleAssistant MessageRole = "assistant"
    MessageRoleSystem    MessageRole = "system"
    MessageRoleTool      MessageRole = "tool"
)

type MetaEventName string

const (
    MetaEventNameOpen  MetaEventName = "open"
    MetaEventNameClose MetaEventName = "close"
)
```

## Runtime Event System

### Runtime Event Types

```go
type RuntimeEventType string

const (
    RuntimeEventTypeTextMessageStart       RuntimeEventType = "text-message-start"
    RuntimeEventTypeTextMessageContent     RuntimeEventType = "text-message-content" 
    RuntimeEventTypeTextMessageEnd         RuntimeEventType = "text-message-end"
    RuntimeEventTypeActionExecutionStart   RuntimeEventType = "action-execution-start"
    RuntimeEventTypeActionExecutionArgs    RuntimeEventType = "action-execution-args"
    RuntimeEventTypeActionExecutionEnd     RuntimeEventType = "action-execution-end"
    RuntimeEventTypeActionExecutionResult  RuntimeEventType = "action-execution-result"
    RuntimeEventTypeAgentStateMessage      RuntimeEventType = "agent-state-message"
    RuntimeEventTypeMetaEvent              RuntimeEventType = "meta-event"
)

type RuntimeMetaEventName string

const (
    RuntimeMetaEventNameStreamStart RuntimeMetaEventName = "stream-start"
    RuntimeMetaEventNameStreamEnd   RuntimeMetaEventName = "stream-end"
    RuntimeMetaEventNameError       RuntimeMetaEventName = "error"
)
```

### Event Flow Patterns

The Go runtime uses channels for event streaming:
1. **Publisher-Subscriber**: Events are published to channels and consumed by subscribers
2. **Backpressure Handling**: Buffered channels prevent blocking on slow consumers
3. **Error Propagation**: Errors are sent as special event types
4. **Graceful Shutdown**: Channels are properly closed to signal completion

### Event Structures

#### Core Event Types

```go
type RuntimeEvent interface {
    GetType() RuntimeEventType
    GetTimestamp() time.Time
}

type BaseRuntimeEvent struct {
    Type      RuntimeEventType `json:"type"`
    Timestamp time.Time        `json:"timestamp"`
}

func (e BaseRuntimeEvent) GetType() RuntimeEventType { return e.Type }
func (e BaseRuntimeEvent) GetTimestamp() time.Time { return e.Timestamp }

type TextMessageStart struct {
    BaseRuntimeEvent
    MessageID string `json:"messageId"`
}

type TextMessageContent struct {
    BaseRuntimeEvent
    MessageID string `json:"messageId"`
    Content   string `json:"content"`
}

type TextMessageEnd struct {
    BaseRuntimeEvent
    MessageID string `json:"messageId"`
}

type ActionExecutionStart struct {
    BaseRuntimeEvent
    MessageID string `json:"messageId"`
    Name      string `json:"name"`
}

type ActionExecutionArgs struct {
    BaseRuntimeEvent
    MessageID string          `json:"messageId"`
    Arguments json.RawMessage `json:"arguments"`
}

type ActionExecutionEnd struct {
    BaseRuntimeEvent
    MessageID string `json:"messageId"`
}

type ActionExecutionResult struct {
    BaseRuntimeEvent
    MessageID string          `json:"messageId"`
    Result    json.RawMessage `json:"result"`
}

type AgentStateMessage struct {
    BaseRuntimeEvent
    MessageID    string                 `json:"messageId"`
    AgentName    string                 `json:"agentName"`
    NodeName     string                 `json:"nodeName"`
    RunningState string                 `json:"runningState"`
    State        map[string]interface{} `json:"state"`
    Active       bool                   `json:"active"`
}

type MetaEvent struct {
    BaseRuntimeEvent
    EventName  RuntimeMetaEventName   `json:"eventName"`
    Properties map[string]interface{} `json:"properties,omitempty"`
}
```

### Response Streaming Behavior

Go implements streaming using Server-Sent Events (SSE) with channels:

```go
type EventStreamer struct {
    events chan RuntimeEvent
    done   chan bool
    mu     sync.RWMutex
}

func (es *EventStreamer) Stream(ctx context.Context) <-chan RuntimeEvent {
    return es.events
}

func (es *EventStreamer) Emit(event RuntimeEvent) {
    select {
    case es.events <- event:
    case <-time.After(time.Second * 5):
        // Handle backpressure
    }
}

func (es *EventStreamer) Close() {
    es.mu.Lock()
    defer es.mu.Unlock()
    close(es.events)
    close(es.done)
}
```

## Core Runtime Flows

### 1. Standard Chat Flow

```
Client Request → GraphQL Mutation → Runtime Engine → Service Adapter → AI Service
                                        ↓
Event Stream ← GraphQL Subscription ← Runtime Engine ← Streaming Response
```

### 2. Action Execution Flow

```
Chat Request → Action Detection → Action Execution → Result Integration → Response
     ↓              ↓                    ↓                ↓              ↓
Event Stream → Action Start → Action Args → Action Result → Complete
```

### 3. Agent Execution Flow

```
Agent Request → Agent Discovery → Remote Execution → State Streaming → Response
     ↓               ↓                  ↓                ↓             ↓
Event Stream → Agent Start → Agent State Updates → Agent Result → Complete
```

### 4. Flow Semantics Details

#### Context Processing
- Request validation and sanitization
- User authentication and authorization
- Input transformation and normalization

#### Guardrails Integration
- Input validation against configured rules
- Output filtering and safety checks
- Policy enforcement and logging

#### Agent vs. General Processing
- Route determination based on request type
- Agent-specific context preparation
- Fallback to general chat processing

## Service Adapter Interface

### Core Interface

```go
type CopilotServiceAdapter interface {
    Process(ctx context.Context, request CopilotRuntimeChatCompletionRequest) (CopilotRuntimeChatCompletionResponse, error)
    ProcessStream(ctx context.Context, request CopilotRuntimeChatCompletionRequest) (<-chan RuntimeEvent, error)
    GetCapabilities() ServiceAdapterCapabilities
}

type CopilotRuntimeChatCompletionRequest struct {
    Messages            []MessageInput              `json:"messages"`
    Model              string                      `json:"model,omitempty"`
    MaxTokens          *int                        `json:"maxTokens,omitempty"`
    Temperature        *float64                    `json:"temperature,omitempty"`
    Tools              []ToolDefinition            `json:"tools,omitempty"`
    ForwardedParams    *ForwardedParametersInput   `json:"forwardedParams,omitempty"`
}

type CopilotRuntimeChatCompletionResponse struct {
    Messages    []MessageOutput `json:"messages"`
    Usage       *UsageStats     `json:"usage,omitempty"`
    Model       string          `json:"model,omitempty"`
    FinishReason string         `json:"finishReason,omitempty"`
}

type ServiceAdapterCapabilities struct {
    SupportsStreaming     bool     `json:"supportsStreaming"`
    SupportsTools         bool     `json:"supportsTools"`
    SupportsImages        bool     `json:"supportsImages"`
    SupportedModels       []string `json:"supportedModels"`
    MaxContextLength      int      `json:"maxContextLength"`
}
```

### Built-in Adapters

```go
type OpenAIAdapter struct {
    client   *openai.Client
    config   OpenAIConfig
}

type AnthropicAdapter struct {
    client   *anthropic.Client
    config   AnthropicConfig
}

type LangGraphAdapter struct {
    client   *http.Client
    endpoint string
    config   LangGraphConfig
}
```

## Agent Integration

### Remote Agent Actions

```go
type RemoteAgentAction struct {
    URL         string                 `json:"url"`
    Name        string                 `json:"name"`
    Description string                 `json:"description"`
    Parameters  map[string]interface{} `json:"parameters,omitempty"`
}
```

### Endpoint Types

#### `CopilotKitEndpoint`

```go
type CopilotKitEndpoint struct {
    URL     string `json:"url"`
    Headers map[string]string `json:"headers,omitempty"`
}

func (e *CopilotKitEndpoint) ExecuteAgent(ctx context.Context, request AgentExecutionRequest) (*AgentExecutionResponse, error) {
    // Implementation for CopilotKit-compatible endpoints
}
```

#### `LangGraphPlatformEndpoint`

```go
type LangGraphPlatformEndpoint struct {
    URL       string `json:"url"`
    APIKey    string `json:"apiKey"`
    GraphID   string `json:"graphId"`
}

func (e *LangGraphPlatformEndpoint) ExecuteAgent(ctx context.Context, request AgentExecutionRequest) (*AgentExecutionResponse, error) {
    // Implementation for LangGraph Platform integration
}
```

### Remote Actions Protocol

#### Discovery
- HTTP GET to `/copilotkit/actions` endpoint
- Returns array of available actions
- Cached for performance with TTL

#### Execution
- HTTP POST to action-specific endpoints
- Streaming support via Server-Sent Events
- Error handling and retry logic

### Server-side Actions

```go
type Action interface {
    GetName() string
    GetDescription() string
    GetParameters() map[string]interface{}
    Execute(ctx context.Context, args json.RawMessage) (json.RawMessage, error)
}

type ActionRegistry struct {
    actions map[string]Action
    mu      sync.RWMutex
}

func (r *ActionRegistry) Register(action Action) {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.actions[action.GetName()] = action
}

func (r *ActionRegistry) Execute(ctx context.Context, name string, args json.RawMessage) (json.RawMessage, error) {
    r.mu.RLock()
    action, exists := r.actions[name]
    r.mu.RUnlock()
    
    if !exists {
        return nil, NewCopilotKitError(CopilotKitErrorCodeActionNotFound, fmt.Sprintf("Action %s not found", name))
    }
    
    return action.Execute(ctx, args)
}
```

## Authentication and Authorization

### Cloud Authentication

```go
type CloudAuthProvider interface {
    ValidateToken(ctx context.Context, token string) (*UserContext, error)
    GetUserPermissions(ctx context.Context, userID string) ([]Permission, error)
}

type JWTAuthProvider struct {
    secretKey []byte
    issuer    string
}

func (p *JWTAuthProvider) ValidateToken(ctx context.Context, token string) (*UserContext, error) {
    // JWT validation logic
}
```

### Request Context

```go
type CopilotRequestContext struct {
    UserID      string                 `json:"userId,omitempty"`
    SessionID   string                 `json:"sessionId,omitempty"`
    ThreadID    string                 `json:"threadId,omitempty"`
    Permissions []Permission           `json:"permissions,omitempty"`
    Metadata    map[string]interface{} `json:"metadata,omitempty"`
    Headers     map[string]string      `json:"headers,omitempty"`
    IPAddress   string                 `json:"ipAddress,omitempty"`
    UserAgent   string                 `json:"userAgent,omitempty"`
    Timestamp   time.Time              `json:"timestamp"`
}
```

## Error Handling

### Error Types

```go
type CopilotKitErrorCode string

const (
    CopilotKitErrorCodeInvalidInput      CopilotKitErrorCode = "INVALID_INPUT"
    CopilotKitErrorCodeActionNotFound    CopilotKitErrorCode = "ACTION_NOT_FOUND"
    CopilotKitErrorCodeAgentNotFound     CopilotKitErrorCode = "AGENT_NOT_FOUND"
    CopilotKitErrorCodeServiceUnavailable CopilotKitErrorCode = "SERVICE_UNAVAILABLE"
    CopilotKitErrorCodeRateLimitExceeded CopilotKitErrorCode = "RATE_LIMIT_EXCEEDED"
    CopilotKitErrorCodeUnauthorized      CopilotKitErrorCode = "UNAUTHORIZED"
    CopilotKitErrorCodeInternal          CopilotKitErrorCode = "INTERNAL_ERROR"
)

type Severity string

const (
    SeverityLow      Severity = "low"
    SeverityMedium   Severity = "medium"
    SeverityHigh     Severity = "high"
    SeverityCritical Severity = "critical"
)

type Visibility string

const (
    VisibilityUser     Visibility = "user"
    VisibilityDeveloper Visibility = "developer"
)

type CopilotKitError struct {
    Code       CopilotKitErrorCode `json:"code"`
    Message    string              `json:"message"`
    Severity   Severity            `json:"severity"`
    Visibility Visibility          `json:"visibility"`
    Details    map[string]interface{} `json:"details,omitempty"`
    Timestamp  time.Time           `json:"timestamp"`
}

func (e *CopilotKitError) Error() string {
    return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

func NewCopilotKitError(code CopilotKitErrorCode, message string) *CopilotKitError {
    return &CopilotKitError{
        Code:      code,
        Message:   message,
        Severity:  SeverityMedium,
        Visibility: VisibilityUser,
        Timestamp: time.Now(),
    }
}

type CopilotKitLowLevelError struct {
    *CopilotKitError
    URL          string      `json:"url,omitempty"`
    StatusCode   int         `json:"statusCode,omitempty"`
    OriginalError error      `json:"originalError,omitempty"`
}

func NewCopilotKitLowLevelError(url string, statusCode int, originalError error) *CopilotKitLowLevelError {
    return &CopilotKitLowLevelError{
        CopilotKitError: NewCopilotKitError(CopilotKitErrorCodeServiceUnavailable, "Service unavailable"),
        URL:             url,
        StatusCode:      statusCode,
        OriginalError:   originalError,
    }
}
```

### Error Classification

```go
type ErrorClassifier struct {
    rules map[CopilotKitErrorCode]ErrorRule
}

type ErrorRule struct {
    Severity   Severity
    Visibility Visibility
    Retryable  bool
    UserMessage string
}

func (ec *ErrorClassifier) Classify(err error) *CopilotKitError {
    // Error classification logic
}
```

### Error Context

```go
type ErrorContext struct {
    RequestContext *CopilotRequestContext `json:"requestContext,omitempty"`
    StackTrace     string                 `json:"stackTrace,omitempty"`
    AdditionalInfo map[string]interface{} `json:"additionalInfo,omitempty"`
}
```

## Security & Cloud Features

### Guardrails Integration

```go
type GuardrailsValidator interface {
    ValidateInput(ctx context.Context, request GuardrailsValidationRequest) (*GuardrailsResult, error)
    ValidateOutput(ctx context.Context, request GuardrailsValidationRequest) (*GuardrailsResult, error)
}

type GuardrailsValidationRequest struct {
    Content string                 `json:"content"`
    Rules   []GuardrailsRuleInput  `json:"rules"`
    Context map[string]interface{} `json:"context,omitempty"`
}

type GuardrailsResult struct {
    Passed    bool                   `json:"passed"`
    Violations []GuardrailsViolation `json:"violations,omitempty"`
    FilteredContent string           `json:"filteredContent,omitempty"`
    Confidence      float64          `json:"confidence"`
}

type GuardrailsViolation struct {
    Rule        string  `json:"rule"`
    Severity    string  `json:"severity"`
    Description string  `json:"description"`
    Position    *Position `json:"position,omitempty"`
}
```

### Cloud Features

- **Rate Limiting**: Token bucket algorithm with Redis backend
- **Analytics**: Usage tracking and performance metrics
- **Monitoring**: Health checks and alerting
- **Scaling**: Horizontal scaling with load balancing

### Headers and Context Properties

```go
const (
    HeaderCopilotCloudToken = "X-Copilot-Cloud-Token"
    HeaderCopilotUserID     = "X-Copilot-User-ID"
    HeaderCopilotSessionID  = "X-Copilot-Session-ID"
    HeaderCopilotThreadID   = "X-Copilot-Thread-ID"
)
```

## Observability and Middleware

### Middleware Hooks

```go
type CopilotMiddleware interface {
    BeforeRequest(ctx context.Context, context *MiddlewareContext) error
    AfterRequest(ctx context.Context, context *MiddlewareContext) error
    OnError(ctx context.Context, context *MiddlewareContext, err error) error
}

type MiddlewareContext struct {
    Request     *GenerateCopilotResponseInput `json:"request"`
    Response    *CopilotResponse              `json:"response,omitempty"`
    UserContext *CopilotRequestContext        `json:"userContext"`
    StartTime   time.Time                     `json:"startTime"`
    EndTime     *time.Time                    `json:"endTime,omitempty"`
    Metadata    map[string]interface{}        `json:"metadata"`
}
```

### Observability Features

```go
type CopilotObservabilityConfig struct {
    EnableLLMLogging      bool           `json:"enableLLMLogging"`
    EnablePerformanceLogging bool        `json:"enablePerformanceLogging"`
    LogLevel              string         `json:"logLevel"`
    SampleRate            float64        `json:"sampleRate"`
    CustomMetrics         []MetricConfig `json:"customMetrics,omitempty"`
}

type LLMRequestData struct {
    Provider    string                 `json:"provider"`
    Model       string                 `json:"model"`
    Messages    []MessageInput         `json:"messages"`
    Parameters  map[string]interface{} `json:"parameters"`
    Timestamp   time.Time              `json:"timestamp"`
    UserContext *CopilotRequestContext `json:"userContext,omitempty"`
}

type LLMResponseData struct {
    Provider     string          `json:"provider"`
    Model        string          `json:"model"`
    Messages     []MessageOutput `json:"messages"`
    Usage        *UsageStats     `json:"usage,omitempty"`
    Duration     time.Duration   `json:"duration"`
    FinishReason string          `json:"finishReason"`
    Timestamp    time.Time       `json:"timestamp"`
}
```

## Go Implementation Strategy

### 1. Application Architecture

```go
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/99designs/gqlgen/graphql/handler"
    "github.com/99designs/gqlgen/graphql/handler/extension"
    "github.com/99designs/gqlgen/graphql/handler/lru"
    "github.com/99designs/gqlgen/graphql/handler/transport"
    "github.com/99designs/gqlgen/graphql/playground"
)

type Application struct {
    config         *Config
    runtime        *CopilotRuntime
    server         *http.Server
    eventStreamer  *EventStreamer
    actionRegistry *ActionRegistry
}

func NewApplication(config *Config) *Application {
    return &Application{
        config:         config,
        runtime:        NewCopilotRuntime(config),
        eventStreamer:  NewEventStreamer(),
        actionRegistry: NewActionRegistry(),
    }
}

func (app *Application) Start(ctx context.Context) error {
    router := gin.New()
    router.Use(gin.Logger(), gin.Recovery())
    
    // Health check endpoint
    router.GET("/health", app.healthCheck)
    
    // GraphQL endpoint
    gqlHandler := app.createGraphQLHandler()
    router.POST("/graphql", gin.WrapH(gqlHandler))
    router.GET("/graphql", gin.WrapH(playground.Handler("GraphQL Playground", "/graphql")))
    
    app.server = &http.Server{
        Addr:    app.config.Port,
        Handler: router,
    }
    
    return app.server.ListenAndServe()
}

func (app *Application) Stop(ctx context.Context) error {
    return app.server.Shutdown(ctx)
}

func (app *Application) healthCheck(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}
```

### 2. GraphQL Implementation

```go
//go:generate go run github.com/99designs/gqlgen generate

type Resolver struct {
    runtime        *CopilotRuntime
    eventStreamer  *EventStreamer
    actionRegistry *ActionRegistry
}

type queryResolver struct{ *Resolver }
type mutationResolver struct{ *Resolver }
type subscriptionResolver struct{ *Resolver }

func (r *queryResolver) Health(ctx context.Context) (string, error) {
    return "OK", nil
}

func (r *queryResolver) AvailableAgents(ctx context.Context) ([]*RemoteAgentAction, error) {
    return r.runtime.GetAvailableAgents(ctx)
}

func (r *mutationResolver) GenerateCopilotResponse(ctx context.Context, input GenerateCopilotResponseInput) (*CopilotResponse, error) {
    return r.runtime.ProcessRequest(ctx, input)
}

func (r *subscriptionResolver) CopilotStream(ctx context.Context, input GenerateCopilotResponseInput) (<-chan *RuntimeEvent, error) {
    return r.runtime.ProcessStreamingRequest(ctx, input)
}

func (app *Application) createGraphQLHandler() http.Handler {
    config := generated.Config{Resolvers: &Resolver{
        runtime:        app.runtime,
        eventStreamer:  app.eventStreamer,
        actionRegistry: app.actionRegistry,
    }}

    srv := handler.NewDefaultServer(generated.NewExecutableSchema(config))
    
    // Add extensions
    srv.AddTransport(transport.Websocket{
        KeepAlivePingInterval: 10 * time.Second,
    })
    srv.AddTransport(transport.Options{})
    srv.AddTransport(transport.GET{})
    srv.AddTransport(transport.POST{})
    srv.AddTransport(transport.MultipartForm{})
    
    srv.SetQueryCache(lru.New(1000))
    srv.Use(extension.Introspection{})
    srv.Use(extension.AutomaticPersistedQuery{
        Cache: lru.New(100),
    })
    
    return srv
}
```

### 3. Event Streaming System

```go
type RuntimeEventSource struct {
    events    chan RuntimeEvent
    done      chan struct{}
    mu        sync.RWMutex
    listeners map[string]chan RuntimeEvent
}

func NewRuntimeEventSource() *RuntimeEventSource {
    return &RuntimeEventSource{
        events:    make(chan RuntimeEvent, 1000),
        done:      make(chan struct{}),
        listeners: make(map[string]chan RuntimeEvent),
    }
}

func (res *RuntimeEventSource) Emit(ctx context.Context, event RuntimeEvent) error {
    select {
    case res.events <- event:
        // Broadcast to all listeners
        res.mu.RLock()
        for _, listener := range res.listeners {
            select {
            case listener <- event:
            default:
                // Skip slow consumers
            }
        }
        res.mu.RUnlock()
        return nil
    case <-ctx.Done():
        return ctx.Err()
    case <-time.After(5 * time.Second):
        return fmt.Errorf("timeout emitting event")
    }
}

func (res *RuntimeEventSource) Subscribe(ctx context.Context, id string) (<-chan RuntimeEvent, error) {
    res.mu.Lock()
    defer res.mu.Unlock()
    
    listener := make(chan RuntimeEvent, 100)
    res.listeners[id] = listener
    
    // Cleanup on context cancellation
    go func() {
        <-ctx.Done()
        res.mu.Lock()
        delete(res.listeners, id)
        close(listener)
        res.mu.Unlock()
    }()
    
    return listener, nil
}

func (res *RuntimeEventSource) Close() {
    close(res.done)
    close(res.events)
    
    res.mu.Lock()
    for _, listener := range res.listeners {
        close(listener)
    }
    res.listeners = make(map[string]chan RuntimeEvent)
    res.mu.Unlock()
}
```

### 4. Service Adapter Interface

```go
type CopilotServiceAdapter interface {
    Process(ctx context.Context, request *CopilotRuntimeChatCompletionRequest) (*CopilotRuntimeChatCompletionResponse, error)
    ProcessStream(ctx context.Context, request *CopilotRuntimeChatCompletionRequest) (<-chan RuntimeEvent, error)
    GetCapabilities() *ServiceAdapterCapabilities
}

type OpenAIAdapter struct {
    client *openai.Client
    config *OpenAIConfig
}

func NewOpenAIAdapter(apiKey string) *OpenAIAdapter {
    return &OpenAIAdapter{
        client: openai.NewClient(apiKey),
        config: &OpenAIConfig{
            Model:       "gpt-4",
            Temperature: 0.7,
            MaxTokens:   2048,
        },
    }
}

func (adapter *OpenAIAdapter) Process(ctx context.Context, request *CopilotRuntimeChatCompletionRequest) (*CopilotRuntimeChatCompletionResponse, error) {
    messages := adapter.convertMessages(request.Messages)
    
    resp, err := adapter.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
        Model:       request.Model,
        Messages:    messages,
        MaxTokens:   request.MaxTokens,
        Temperature: request.Temperature,
        Tools:       adapter.convertTools(request.Tools),
    })
    
    if err != nil {
        return nil, adapter.handleError(err)
    }
    
    return adapter.convertResponse(resp), nil
}

func (adapter *OpenAIAdapter) ProcessStream(ctx context.Context, request *CopilotRuntimeChatCompletionRequest) (<-chan RuntimeEvent, error) {
    events := make(chan RuntimeEvent, 100)
    
    go func() {
        defer close(events)
        
        stream, err := adapter.client.CreateChatCompletionStream(ctx, openai.ChatCompletionRequest{
            Model:     request.Model,
            Messages:  adapter.convertMessages(request.Messages),
            MaxTokens: request.MaxTokens,
            Stream:    true,
        })
        
        if err != nil {
            events <- &MetaEvent{
                BaseRuntimeEvent: BaseRuntimeEvent{
                    Type:      RuntimeEventTypeMetaEvent,
                    Timestamp: time.Now(),
                },
                EventName: RuntimeMetaEventNameError,
                Properties: map[string]interface{}{
                    "error": err.Error(),
                },
            }
            return
        }
        defer stream.Close()
        
        for {
            response, err := stream.Recv()
            if errors.Is(err, io.EOF) {
                events <- &TextMessageEnd{
                    BaseRuntimeEvent: BaseRuntimeEvent{
                        Type:      RuntimeEventTypeTextMessageEnd,
                        Timestamp: time.Now(),
                    },
                    MessageID: "msg_" + generateID(),
                }
                break
            }
            
            if err != nil {
                events <- &MetaEvent{
                    BaseRuntimeEvent: BaseRuntimeEvent{
                        Type:      RuntimeEventTypeMetaEvent,
                        Timestamp: time.Now(),
                    },
                    EventName: RuntimeMetaEventNameError,
                    Properties: map[string]interface{}{
                        "error": err.Error(),
                    },
                }
                break
            }
            
            if len(response.Choices) > 0 {
                events <- &TextMessageContent{
                    BaseRuntimeEvent: BaseRuntimeEvent{
                        Type:      RuntimeEventTypeTextMessageContent,
                        Timestamp: time.Now(),
                    },
                    MessageID: "msg_" + generateID(),
                    Content:   response.Choices[0].Delta.Content,
                }
            }
        }
    }()
    
    return events, nil
}

type LangGraphAdapter struct {
    client   *http.Client
    endpoint string
    apiKey   string
}

func NewLangGraphAdapter(endpoint, apiKey string) *LangGraphAdapter {
    return &LangGraphAdapter{
        client:   &http.Client{Timeout: 30 * time.Second},
        endpoint: endpoint,
        apiKey:   apiKey,
    }
}

func (adapter *LangGraphAdapter) Process(ctx context.Context, request *CopilotRuntimeChatCompletionRequest) (*CopilotRuntimeChatCompletionResponse, error) {
    // Implementation for LangGraph integration
    return nil, fmt.Errorf("not implemented")
}
```

### 5. Agent Integration

```go
type AgentEndpoint interface {
    ExecuteAgent(ctx context.Context, request *AgentExecutionRequest) (*AgentExecutionResponse, error)
    GetCapabilities() *AgentCapabilities
}

type LangGraphPlatformEndpoint struct {
    URL       string `json:"url"`
    APIKey    string `json:"apiKey"`
    GraphID   string `json:"graphId"`
    client    *http.Client
}

func NewLangGraphPlatformEndpoint(url, apiKey, graphID string) *LangGraphPlatformEndpoint {
    return &LangGraphPlatformEndpoint{
        URL:     url,
        APIKey:  apiKey,
        GraphID: graphID,
        client:  &http.Client{Timeout: 30 * time.Second},
    }
}

func (endpoint *LangGraphPlatformEndpoint) ExecuteAgent(ctx context.Context, request *AgentExecutionRequest) (*AgentExecutionResponse, error) {
    payload := map[string]interface{}{
        "input":     request.Input,
        "config":    request.Config,
        "graph_id":  endpoint.GraphID,
    }
    
    jsonPayload, err := json.Marshal(payload)
    if err != nil {
        return nil, fmt.Errorf("failed to marshal request: %w", err)
    }
    
    req, err := http.NewRequestWithContext(ctx, "POST", endpoint.URL+"/invoke", bytes.NewBuffer(jsonPayload))
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+endpoint.APIKey)
    
    resp, err := endpoint.client.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("agent execution failed: %s", string(body))
    }
    
    var response AgentExecutionResponse
    if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &response, nil
}

type CopilotKitEndpoint struct {
    URL     string            `json:"url"`
    Headers map[string]string `json:"headers"`
    client  *http.Client
}

func NewCopilotKitEndpoint(url string, headers map[string]string) *CopilotKitEndpoint {
    return &CopilotKitEndpoint{
        URL:     url,
        Headers: headers,
        client:  &http.Client{Timeout: 30 * time.Second},
    }
}

func (endpoint *CopilotKitEndpoint) ExecuteAgent(ctx context.Context, request *AgentExecutionRequest) (*AgentExecutionResponse, error) {
    jsonPayload, err := json.Marshal(request)
    if err != nil {
        return nil, fmt.Errorf("failed to marshal request: %w", err)
    }
    
    req, err := http.NewRequestWithContext(ctx, "POST", endpoint.URL, bytes.NewBuffer(jsonPayload))
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    req.Header.Set("Content-Type", "application/json")
    for key, value := range endpoint.Headers {
        req.Header.Set(key, value)
    }
    
    resp, err := endpoint.client.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to execute request: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("agent execution failed: %s", string(body))
    }
    
    var response AgentExecutionResponse
    if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
        return nil, fmt.Errorf("failed to decode response: %w", err)
    }
    
    return &response, nil
}
```

## Data Models (Go Structs)

### Core Models

```go
type MessageRole string

const (
    MessageRoleUser      MessageRole = "user"
    MessageRoleAssistant MessageRole = "assistant"
    MessageRoleSystem    MessageRole = "system"
    MessageRoleTool      MessageRole = "tool"
)

type CopilotRequestType string

const (
    CopilotRequestTypeChat            CopilotRequestType = "CHAT"
    CopilotRequestTypeActionExecution CopilotRequestType = "ACTION_EXECUTION"
    CopilotRequestTypeAgentExecution  CopilotRequestType = "AGENT_EXECUTION"
)

type TextMessageInput struct {
    ID      string      `json:"id" validate:"required"`
    Role    MessageRole `json:"role" validate:"required"`
    Content string      `json:"content" validate:"required"`
}

type ActionExecutionMessageInput struct {
    ID        string          `json:"id" validate:"required"`
    Role      MessageRole     `json:"role" validate:"required"`
    Name      string          `json:"name" validate:"required"`
    Arguments json.RawMessage `json:"arguments"`
}

type MessageInput interface {
    IsMessageInput()
    GetRole() MessageRole
    GetID() string
}

type ActionInput struct {
    Name        string                 `json:"name" validate:"required"`
    Description string                 `json:"description"`
    Parameters  map[string]interface{} `json:"parameters"`
}

type GenerateCopilotResponseInput struct {
    Messages            []MessageInput             `json:"messages" validate:"required,min=1"`
    Actions             []ActionInput              `json:"actions"`
    AgentSession        *AgentSessionInput         `json:"agentSession"`
    Frontend            *FrontendInput             `json:"frontend"`
    ForwardedParameters *ForwardedParametersInput  `json:"forwardedParameters"`
    Cloud               *CloudInput                `json:"cloud"`
    Guardrails          *GuardrailsInput           `json:"guardrails"`
    Extensions          *ExtensionsInput           `json:"extensions"`
    MetaEvent           *MetaEventInput            `json:"metaEvent"`
    RequestType         CopilotRequestType         `json:"requestType"`
}
```

## Error Handling (Go Implementation)

```go
type CopilotKitErrorCode string

const (
    CopilotKitErrorCodeInvalidInput       CopilotKitErrorCode = "INVALID_INPUT"
    CopilotKitErrorCodeActionNotFound     CopilotKitErrorCode = "ACTION_NOT_FOUND"
    CopilotKitErrorCodeAgentNotFound      CopilotKitErrorCode = "AGENT_NOT_FOUND"
    CopilotKitErrorCodeServiceUnavailable CopilotKitErrorCode = "SERVICE_UNAVAILABLE"
    CopilotKitErrorCodeRateLimitExceeded  CopilotKitErrorCode = "RATE_LIMIT_EXCEEDED"
    CopilotKitErrorCodeUnauthorized       CopilotKitErrorCode = "UNAUTHORIZED"
)

type Severity string

const (
    SeverityLow      Severity = "low"
    SeverityMedium   Severity = "medium"
    SeverityHigh     Severity = "high"
    SeverityCritical Severity = "critical"
)

type Visibility string

const (
    VisibilityUser      Visibility = "user"
    VisibilityDeveloper Visibility = "developer"
)

type CopilotKitError struct {
    Code       CopilotKitErrorCode    `json:"code"`
    Message    string                 `json:"message"`
    Severity   Severity               `json:"severity"`
    Visibility Visibility             `json:"visibility"`
    Details    map[string]interface{} `json:"details,omitempty"`
    Timestamp  time.Time              `json:"timestamp"`
    cause      error
}

func (e *CopilotKitError) Error() string {
    return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

func (e *CopilotKitError) Unwrap() error {
    return e.cause
}

func NewCopilotKitError(code CopilotKitErrorCode, message string) *CopilotKitError {
    return &CopilotKitError{
        Code:       code,
        Message:    message,
        Severity:   SeverityMedium,
        Visibility: VisibilityUser,
        Timestamp:  time.Now(),
    }
}

type CopilotKitLowLevelError struct {
    *CopilotKitError
    URL           string `json:"url,omitempty"`
    StatusCode    int    `json:"statusCode,omitempty"`
    OriginalError error  `json:"originalError,omitempty"`
}

func NewCopilotKitLowLevelError(url string, statusCode int, originalError error, message string) *CopilotKitLowLevelError {
    baseError := NewCopilotKitError(CopilotKitErrorCodeServiceUnavailable, message)
    baseError.cause = originalError
    
    return &CopilotKitLowLevelError{
        CopilotKitError: baseError,
        URL:             url,
        StatusCode:      statusCode,
        OriginalError:   originalError,
    }
}

func ConvertServiceAdapterError(err error, context string) *CopilotKitError {
    if copilotErr, ok := err.(*CopilotKitError); ok {
        return copilotErr
    }
    
    // Handle common HTTP errors
    if httpErr, ok := err.(*http.Client); ok {
        // Convert HTTP errors to CopilotKit errors
        _ = httpErr // placeholder
    }
    
    // Default fallback
    return NewCopilotKitError(CopilotKitErrorCodeInternal, fmt.Sprintf("Internal error in %s: %v", context, err))
}
```

### Error Message System (Go)

```go
type ErrorMessageConfig struct {
    UserFriendlyMessages map[CopilotKitErrorCode]string
    TechnicalMessages    map[CopilotKitErrorCode]string
    SuggestedActions     map[CopilotKitErrorCode]string
}

var DefaultErrorConfig = &ErrorMessageConfig{
    UserFriendlyMessages: map[CopilotKitErrorCode]string{
        CopilotKitErrorCodeInvalidInput:       "The request contains invalid information. Please check your input and try again.",
        CopilotKitErrorCodeActionNotFound:     "The requested action is not available. Please check the action name and try again.",
        CopilotKitErrorCodeAgentNotFound:      "The requested agent is not available. Please check the agent configuration.",
        CopilotKitErrorCodeServiceUnavailable: "The service is temporarily unavailable. Please try again in a few moments.",
        CopilotKitErrorCodeRateLimitExceeded:  "Too many requests. Please wait a moment before trying again.",
        CopilotKitErrorCodeUnauthorized:       "You don't have permission to perform this action.",
    },
    TechnicalMessages: map[CopilotKitErrorCode]string{
        CopilotKitErrorCodeInvalidInput:       "Request validation failed",
        CopilotKitErrorCodeActionNotFound:     "Action not found in registry",
        CopilotKitErrorCodeAgentNotFound:      "Agent endpoint not configured",
        CopilotKitErrorCodeServiceUnavailable: "Service adapter returned error",
        CopilotKitErrorCodeRateLimitExceeded:  "Rate limit threshold exceeded",
        CopilotKitErrorCodeUnauthorized:       "Authentication/authorization failed",
    },
}

func GenerateHelpfulErrorMessage(err *CopilotKitError, isDevelopmentMode bool) string {
    config := DefaultErrorConfig
    
    if isDevelopmentMode && err.Visibility == VisibilityDeveloper {
        if techMsg, exists := config.TechnicalMessages[err.Code]; exists {
            return fmt.Sprintf("%s: %s", techMsg, err.Message)
        }
    }
    
    if userMsg, exists := config.UserFriendlyMessages[err.Code]; exists {
        return userMsg
    }
    
    return "An unexpected error occurred. Please try again or contact support if the problem persists."
}
```

## Go Implementation Considerations

### 1. Concurrency Pattern

Go's goroutines and channels provide excellent concurrency primitives:
- Use goroutines for handling concurrent requests
- Channels for event streaming and inter-goroutine communication
- Context for cancellation and timeout handling
- Mutex/RWMutex for protecting shared state

### 2. Event System

Leverage Go's channel-based approach:
- Buffered channels to prevent blocking
- Select statements for non-blocking operations
- Context cancellation for cleanup
- Worker pools for processing events

### 3. State Management

Use Go's built-in concurrency primitives:
- sync.Map for concurrent access to maps
- sync.Pool for object reuse
- atomic package for simple counters
- Channels for state synchronization

### 4. Type Safety

Leverage Go's type system:
- Interface-based design for pluggability
- Struct embedding for composition
- Type assertions for union types
- Generic types for reusable components

### 5. Error Handling

Follow Go's explicit error handling:
- Return errors as values
- Wrap errors with context
- Use custom error types for structured handling
- Implement error interfaces (Error, Unwrap)

### 6. Testing Strategy

Utilize Go's testing ecosystem:
- Table-driven tests for comprehensive coverage
- Testify for assertions and mocking
- httptest for HTTP endpoint testing
- Race detector for concurrency testing

## Migration Path

### Phase 1: Core GraphQL API

1. Set up basic Go project structure with modules
2. Implement GraphQL schema using gqlgen
3. Create basic resolvers for queries and mutations
4. Add health check and basic error handling
5. Implement request validation

### Phase 2: Runtime Engine

1. Build message processing pipeline
2. Implement service adapter interface
3. Add OpenAI adapter with streaming support
4. Create event system with channels
5. Add middleware support

### Phase 3: Agent Integration

1. Implement agent discovery mechanism
2. Add remote agent execution
3. Create LangGraph Platform integration
4. Build agent state management
5. Add agent-specific error handling

### Phase 4: Advanced Features

1. Implement guardrails integration
2. Add cloud authentication
3. Create observability features
4. Build rate limiting
5. Add comprehensive monitoring

## Compatibility Considerations for Go Port

### Protocol Compatibility
- Maintain GraphQL schema compatibility
- Preserve JSON message formats
- Keep HTTP endpoint behavior consistent
- Support same authentication mechanisms

### Performance Considerations
- Optimize for Go's garbage collector
- Use object pooling for frequently allocated objects
- Implement efficient JSON marshaling/unmarshaling
- Leverage Go's efficient HTTP server

### Deployment Considerations
- Single binary deployment advantage
- Docker container optimization
- Kubernetes deployment patterns
- Health check and monitoring integration

## Dependencies

### Core Dependencies

```go
// Core web framework and GraphQL
"github.com/gin-gonic/gin"
"github.com/99designs/gqlgen"
"github.com/99designs/gqlgen/graphql/handler"
"github.com/99designs/gqlgen/graphql/handler/extension"
"github.com/99designs/gqlgen/graphql/handler/transport"
"github.com/99designs/gqlgen/graphql/playground"

// HTTP client and utilities
"net/http"
"context"
"time"
"sync"

// JSON processing
"encoding/json"
"io"

// Validation
"github.com/go-playground/validator/v10"

// Logging
"github.com/sirupsen/logrus"
"go.uber.org/zap"

// Configuration
"github.com/spf13/viper"
"github.com/joho/godotenv"

// Database (if needed)
"github.com/redis/go-redis/v9"
"gorm.io/gorm"
"gorm.io/driver/postgres"
```

### Optional Dependencies

```go
// AI Service Integrations
"github.com/sashabaranov/go-openai"
"github.com/anthropics/anthropic-sdk-go"

// Monitoring and Observability
"github.com/prometheus/client_golang"
"go.opentelemetry.io/otel"
"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

// Testing
"github.com/stretchr/testify"
"github.com/golang/mock/gomock"
"github.com/jarcoal/httpmock"

// Security
"github.com/golang-jwt/jwt/v5"
"golang.org/x/crypto/bcrypt"
"golang.org/x/time/rate"
```

## Minimal Example Exchanges

### 1. Health Check

**Request:**
```graphql
query {
  health
}
```

**Response:**
```json
{
  "data": {
    "health": "OK"
  }
}
```

### 2. Agent Discovery

**Request:**
```graphql
query {
  availableAgents {
    url
    name
    description
    parameters
  }
}
```

**Response:**
```json
{
  "data": {
    "availableAgents": [
      {
        "url": "https://api.example.com/agent1",
        "name": "DataAnalyst",
        "description": "Analyzes data and generates insights",
        "parameters": {
          "type": "object",
          "properties": {
            "dataset": {"type": "string"},
            "analysis_type": {"type": "string"}
          }
        }
      }
    ]
  }
}
```

### 3. Chat Run (Simplified)

**Request:**
```graphql
mutation {
  generateCopilotResponse(input: {
    messages: [{
      id: "msg_1",
      role: user,
      content: "Hello, how can you help me?"
    }],
    requestType: CHAT
  }) {
    messages {
      id
      role
      content
    }
    isCompleted
  }
}
```

**Response:**
```json
{
  "data": {
    "generateCopilotResponse": {
      "messages": [
        {
          "id": "msg_2",
          "role": "assistant", 
          "content": "Hello! I'm here to help you with various tasks. I can assist with questions, provide information, help with analysis, and much more. What would you like to work on today?"
        }
      ],
      "isCompleted": true
    }
  }
}
```

This comprehensive specification provides a complete roadmap for implementing CopilotRuntime in Go, maintaining compatibility with the TypeScript version while leveraging Go's strengths in concurrency, performance, and deployment simplicity.