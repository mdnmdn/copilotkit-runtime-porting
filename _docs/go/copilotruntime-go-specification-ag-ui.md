# CopilotRuntime Go Specification - AG-UI Architecture

## Overview

The CopilotRuntime for Go implements the Agent User Interaction Protocol (AG-UI) architecture, providing a flexible, event-driven system that enables seamless communication between front-end applications and AI agents. This specification follows AG-UI's client-server architecture with standard HTTP communication patterns.

## Architecture Overview

The Go CopilotRuntime follows AG-UI's core architectural principles:

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP API Layer                           │
├─────────────────────────────────────────────────────────────┤
│                 Protocol Layer Core                         │
├─────────────────────────────────────────────────────────────┤
│  Message Types  │  Running Agents  │  Tools & Handoffs     │
├─────────────────────────────────────────────────────────────┤
│                Event System & State Management             │
├─────────────────────────────────────────────────────────────┤
│                Standard HTTP Client Layer                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **HTTP API Layer**: Standard REST endpoints for agent communication
- **Protocol Layer**: AG-UI protocol implementation with message routing
- **Message Types**: Standardized message formats for agent interactions
- **Running Agents**: Agent lifecycle and state management
- **Event System**: Event-driven communication for real-time updates
- **Tools & Handoffs**: Inter-agent coordination and capability management
- **State Management**: Component-based state tracking and persistence

## HTTP API Endpoints

### Core Endpoints

The runtime exposes standard HTTP REST endpoints following AG-UI patterns:

#### Agent Management
```
GET    /agents                    # List available agents
POST   /agents/{id}/start         # Start an agent session
POST   /agents/{id}/stop          # Stop an agent session
GET    /agents/{id}/status        # Get agent status
```

#### Message Handling
```
POST   /messages                  # Send message to agent
GET    /messages/{sessionId}      # Get message history
POST   /messages/{id}/respond     # Respond to specific message
```

#### Event Stream
```
GET    /events/{sessionId}        # Server-sent events for real-time updates
POST   /events/{sessionId}        # Send custom events
```

#### Tools & Handoffs
```
GET    /tools                     # List available tools
POST   /tools/{name}/execute      # Execute a tool
POST   /handoffs/{fromAgent}/{toAgent}  # Agent handoff
```

#### Health & Discovery
```
GET    /health                    # Health check
GET    /capabilities              # System capabilities
```

## Message Types (AG-UI Protocol)

### Core Message Interface

```go
type Message interface {
    GetID() string
    GetType() MessageType
    GetTimestamp() time.Time
    GetSessionID() string
    GetPayload() interface{}
}

type MessageType string

const (
    MessageTypeUserInput      MessageType = "user_input"
    MessageTypeAgentResponse  MessageType = "agent_response"
    MessageTypeToolExecution  MessageType = "tool_execution"
    MessageTypeStateUpdate    MessageType = "state_update"
    MessageTypeHandoff        MessageType = "handoff"
    MessageTypeEvent          MessageType = "event"
)
```

### Message Implementations

#### User Input Message
```go
type UserInputMessage struct {
    ID          string                 `json:"id"`
    Type        MessageType            `json:"type"`
    Timestamp   time.Time              `json:"timestamp"`
    SessionID   string                 `json:"sessionId"`
    Content     string                 `json:"content"`
    Context     map[string]interface{} `json:"context,omitempty"`
    Attachments []Attachment           `json:"attachments,omitempty"`
}

func (m UserInputMessage) GetID() string { return m.ID }
func (m UserInputMessage) GetType() MessageType { return m.Type }
func (m UserInputMessage) GetTimestamp() time.Time { return m.Timestamp }
func (m UserInputMessage) GetSessionID() string { return m.SessionID }
func (m UserInputMessage) GetPayload() interface{} { return m }
```

#### Agent Response Message
```go
type AgentResponseMessage struct {
    ID        string                 `json:"id"`
    Type      MessageType            `json:"type"`
    Timestamp time.Time              `json:"timestamp"`
    SessionID string                 `json:"sessionId"`
    AgentID   string                 `json:"agentId"`
    Content   string                 `json:"content"`
    Actions   []ActionSuggestion     `json:"actions,omitempty"`
    Metadata  map[string]interface{} `json:"metadata,omitempty"`
}
```

#### Tool Execution Message
```go
type ToolExecutionMessage struct {
    ID         string                 `json:"id"`
    Type       MessageType            `json:"type"`
    Timestamp  time.Time              `json:"timestamp"`
    SessionID  string                 `json:"sessionId"`
    ToolName   string                 `json:"toolName"`
    Parameters map[string]interface{} `json:"parameters"`
    Result     *ToolResult            `json:"result,omitempty"`
    Status     ExecutionStatus        `json:"status"`
}

type ExecutionStatus string

const (
    ExecutionStatusPending    ExecutionStatus = "pending"
    ExecutionStatusRunning    ExecutionStatus = "running"
    ExecutionStatusCompleted  ExecutionStatus = "completed"
    ExecutionStatusFailed     ExecutionStatus = "failed"
)
```

#### State Update Message
```go
type StateUpdateMessage struct {
    ID         string                 `json:"id"`
    Type       MessageType            `json:"type"`
    Timestamp  time.Time              `json:"timestamp"`
    SessionID  string                 `json:"sessionId"`
    AgentID    string                 `json:"agentId"`
    StateType  StateType              `json:"stateType"`
    State      map[string]interface{} `json:"state"`
    Previous   map[string]interface{} `json:"previous,omitempty"`
}

type StateType string

const (
    StateTypeAgent     StateType = "agent"
    StateTypeSession   StateType = "session"
    StateTypeComponent StateType = "component"
    StateTypeContext   StateType = "context"
)
```

#### Handoff Message
```go
type HandoffMessage struct {
    ID          string                 `json:"id"`
    Type        MessageType            `json:"type"`
    Timestamp   time.Time              `json:"timestamp"`
    SessionID   string                 `json:"sessionId"`
    FromAgent   string                 `json:"fromAgent"`
    ToAgent     string                 `json:"toAgent"`
    Context     map[string]interface{} `json:"context"`
    Reason      string                 `json:"reason"`
    Status      HandoffStatus          `json:"status"`
}

type HandoffStatus string

const (
    HandoffStatusInitiated HandoffStatus = "initiated"
    HandoffStatusAccepted  HandoffStatus = "accepted"
    HandoffStatusRejected  HandoffStatus = "rejected"
    HandoffStatusCompleted HandoffStatus = "completed"
)
```

## Running Agents Management

### Agent State Tracking

```go
type RunningAgent struct {
    ID            string                 `json:"id"`
    Name          string                 `json:"name"`
    Type          AgentType              `json:"type"`
    Status        AgentStatus            `json:"status"`
    SessionID     string                 `json:"sessionId"`
    StartedAt     time.Time              `json:"startedAt"`
    LastActivity  time.Time              `json:"lastActivity"`
    State         map[string]interface{} `json:"state"`
    Capabilities  []Capability           `json:"capabilities"`
    Configuration AgentConfiguration     `json:"configuration"`
}

type AgentType string

const (
    AgentTypeConversational AgentType = "conversational"
    AgentTypeTask          AgentType = "task"
    AgentTypeAnalytical    AgentType = "analytical"
    AgentTypeCreative      AgentType = "creative"
    AgentTypeSpecialized   AgentType = "specialized"
)

type AgentStatus string

const (
    AgentStatusIdle      AgentStatus = "idle"
    AgentStatusActive    AgentStatus = "active"
    AgentStatusProcessing AgentStatus = "processing"
    AgentStatusWaiting   AgentStatus = "waiting"
    AgentStatusError     AgentStatus = "error"
    AgentStatusStopped   AgentStatus = "stopped"
)
```

### Agent Manager

```go
type AgentManager struct {
    agents    map[string]*RunningAgent
    sessions  map[string][]*RunningAgent
    mu        sync.RWMutex
    eventBus  *EventBus
}

func NewAgentManager(eventBus *EventBus) *AgentManager {
    return &AgentManager{
        agents:   make(map[string]*RunningAgent),
        sessions: make(map[string][]*RunningAgent),
        eventBus: eventBus,
    }
}

func (am *AgentManager) StartAgent(ctx context.Context, agentID, sessionID string, config AgentConfiguration) (*RunningAgent, error) {
    am.mu.Lock()
    defer am.mu.Unlock()
    
    agent := &RunningAgent{
        ID:            agentID,
        Status:        AgentStatusActive,
        SessionID:     sessionID,
        StartedAt:     time.Now(),
        LastActivity:  time.Now(),
        Configuration: config,
        State:         make(map[string]interface{}),
    }
    
    am.agents[agentID] = agent
    am.sessions[sessionID] = append(am.sessions[sessionID], agent)
    
    // Emit agent started event
    am.eventBus.Emit(ctx, NewAgentStartedEvent(agent))
    
    return agent, nil
}

func (am *AgentManager) StopAgent(ctx context.Context, agentID string) error {
    am.mu.Lock()
    defer am.mu.Unlock()
    
    agent, exists := am.agents[agentID]
    if !exists {
        return fmt.Errorf("agent %s not found", agentID)
    }
    
    agent.Status = AgentStatusStopped
    delete(am.agents, agentID)
    
    // Remove from session
    if agents, ok := am.sessions[agent.SessionID]; ok {
        for i, a := range agents {
            if a.ID == agentID {
                am.sessions[agent.SessionID] = append(agents[:i], agents[i+1:]...)
                break
            }
        }
    }
    
    // Emit agent stopped event
    am.eventBus.Emit(ctx, NewAgentStoppedEvent(agent))
    
    return nil
}

func (am *AgentManager) GetRunningAgents(sessionID string) []*RunningAgent {
    am.mu.RLock()
    defer am.mu.RUnlock()
    
    agents, exists := am.sessions[sessionID]
    if !exists {
        return nil
    }
    
    // Return a copy to prevent concurrent modifications
    result := make([]*RunningAgent, len(agents))
    copy(result, agents)
    return result
}
```

## Event System (AG-UI Style)

### Event Bus

```go
type Event interface {
    GetType() EventType
    GetTimestamp() time.Time
    GetSessionID() string
    GetPayload() interface{}
}

type EventType string

const (
    EventTypeAgentStarted     EventType = "agent_started"
    EventTypeAgentStopped     EventType = "agent_stopped"
    EventTypeAgentStateChange EventType = "agent_state_change"
    EventTypeMessageReceived  EventType = "message_received"
    EventTypeToolExecuted     EventType = "tool_executed"
    EventTypeHandoffInitiated EventType = "handoff_initiated"
    EventTypeSessionCreated   EventType = "session_created"
    EventTypeSessionClosed    EventType = "session_closed"
    EventTypeUserInteraction  EventType = "user_interaction"
)

type EventBus struct {
    subscribers map[EventType][]EventHandler
    mu          sync.RWMutex
    eventChan   chan Event
    stopChan    chan struct{}
}

type EventHandler func(ctx context.Context, event Event) error

func NewEventBus() *EventBus {
    eb := &EventBus{
        subscribers: make(map[EventType][]EventHandler),
        eventChan:   make(chan Event, 1000),
        stopChan:    make(chan struct{}),
    }
    
    go eb.processEvents()
    return eb
}

func (eb *EventBus) Subscribe(eventType EventType, handler EventHandler) {
    eb.mu.Lock()
    defer eb.mu.Unlock()
    
    eb.subscribers[eventType] = append(eb.subscribers[eventType], handler)
}

func (eb *EventBus) Emit(ctx context.Context, event Event) {
    select {
    case eb.eventChan <- event:
    case <-ctx.Done():
    case <-time.After(5 * time.Second):
        // Handle backpressure by dropping events if necessary
    }
}

func (eb *EventBus) processEvents() {
    for {
        select {
        case event := <-eb.eventChan:
            eb.handleEvent(context.Background(), event)
        case <-eb.stopChan:
            return
        }
    }
}

func (eb *EventBus) handleEvent(ctx context.Context, event Event) {
    eb.mu.RLock()
    handlers, exists := eb.subscribers[event.GetType()]
    eb.mu.RUnlock()
    
    if !exists {
        return
    }
    
    for _, handler := range handlers {
        go func(h EventHandler) {
            if err := h(ctx, event); err != nil {
                // Log error but don't fail the entire event processing
                fmt.Printf("Error handling event %s: %v\n", event.GetType(), err)
            }
        }(handler)
    }
}
```

### Event Implementations

```go
type BaseEvent struct {
    Type      EventType   `json:"type"`
    Timestamp time.Time   `json:"timestamp"`
    SessionID string      `json:"sessionId"`
}

func (e BaseEvent) GetType() EventType { return e.Type }
func (e BaseEvent) GetTimestamp() time.Time { return e.Timestamp }
func (e BaseEvent) GetSessionID() string { return e.SessionID }

type AgentStartedEvent struct {
    BaseEvent
    Agent *RunningAgent `json:"agent"`
}

func (e AgentStartedEvent) GetPayload() interface{} { return e.Agent }

func NewAgentStartedEvent(agent *RunningAgent) *AgentStartedEvent {
    return &AgentStartedEvent{
        BaseEvent: BaseEvent{
            Type:      EventTypeAgentStarted,
            Timestamp: time.Now(),
            SessionID: agent.SessionID,
        },
        Agent: agent,
    }
}

type UserInteractionEvent struct {
    BaseEvent
    UserID      string                 `json:"userId"`
    Interaction InteractionType        `json:"interaction"`
    Data        map[string]interface{} `json:"data"`
}

type InteractionType string

const (
    InteractionTypeClick     InteractionType = "click"
    InteractionTypeInput     InteractionType = "input"
    InteractionTypeSelection InteractionType = "selection"
    InteractionTypeUpload    InteractionType = "upload"
)

func (e UserInteractionEvent) GetPayload() interface{} { return e }
```

## Tools and Handoff System

### Tool Definition

```go
type Tool interface {
    GetName() string
    GetDescription() string
    GetParameters() map[string]Parameter
    Execute(ctx context.Context, params map[string]interface{}) (*ToolResult, error)
    GetCapabilities() []Capability
}

type Parameter struct {
    Type        string      `json:"type"`
    Description string      `json:"description"`
    Required    bool        `json:"required"`
    Default     interface{} `json:"default,omitempty"`
    Enum        []string    `json:"enum,omitempty"`
}

type ToolResult struct {
    Success   bool                   `json:"success"`
    Data      interface{}            `json:"data,omitempty"`
    Error     string                 `json:"error,omitempty"`
    Metadata  map[string]interface{} `json:"metadata,omitempty"`
    Duration  time.Duration          `json:"duration"`
}

type Capability struct {
    Name        string                 `json:"name"`
    Type        CapabilityType         `json:"type"`
    Description string                 `json:"description"`
    Parameters  map[string]interface{} `json:"parameters,omitempty"`
}

type CapabilityType string

const (
    CapabilityTypeData        CapabilityType = "data"
    CapabilityTypeComputation CapabilityType = "computation"
    CapabilityTypeIntegration CapabilityType = "integration"
    CapabilityTypeCommunication CapabilityType = "communication"
    CapabilityTypeVisualization CapabilityType = "visualization"
)
```

### Tool Registry

```go
type ToolRegistry struct {
    tools   map[string]Tool
    mu      sync.RWMutex
    eventBus *EventBus
}

func NewToolRegistry(eventBus *EventBus) *ToolRegistry {
    return &ToolRegistry{
        tools:    make(map[string]Tool),
        eventBus: eventBus,
    }
}

func (tr *ToolRegistry) RegisterTool(tool Tool) {
    tr.mu.Lock()
    defer tr.mu.Unlock()
    
    tr.tools[tool.GetName()] = tool
}

func (tr *ToolRegistry) ExecuteTool(ctx context.Context, name string, params map[string]interface{}, sessionID string) (*ToolResult, error) {
    tr.mu.RLock()
    tool, exists := tr.tools[name]
    tr.mu.RUnlock()
    
    if !exists {
        return nil, fmt.Errorf("tool %s not found", name)
    }
    
    startTime := time.Now()
    result, err := tool.Execute(ctx, params)
    duration := time.Since(startTime)
    
    if result != nil {
        result.Duration = duration
    }
    
    // Emit tool execution event
    tr.eventBus.Emit(ctx, &ToolExecutedEvent{
        BaseEvent: BaseEvent{
            Type:      EventTypeToolExecuted,
            Timestamp: time.Now(),
            SessionID: sessionID,
        },
        ToolName: name,
        Result:   result,
        Error:    err,
    })
    
    return result, err
}
```

### Handoff Manager

```go
type HandoffManager struct {
    agentManager *AgentManager
    eventBus     *EventBus
    mu           sync.RWMutex
    activeHandoffs map[string]*HandoffProcess
}

type HandoffProcess struct {
    ID         string                 `json:"id"`
    FromAgent  string                 `json:"fromAgent"`
    ToAgent    string                 `json:"toAgent"`
    SessionID  string                 `json:"sessionId"`
    Context    map[string]interface{} `json:"context"`
    Status     HandoffStatus          `json:"status"`
    CreatedAt  time.Time              `json:"createdAt"`
    CompletedAt *time.Time            `json:"completedAt,omitempty"`
}

func NewHandoffManager(agentManager *AgentManager, eventBus *EventBus) *HandoffManager {
    return &HandoffManager{
        agentManager:   agentManager,
        eventBus:       eventBus,
        activeHandoffs: make(map[string]*HandoffProcess),
    }
}

func (hm *HandoffManager) InitiateHandoff(ctx context.Context, fromAgent, toAgent, sessionID string, context map[string]interface{}) (*HandoffProcess, error) {
    hm.mu.Lock()
    defer hm.mu.Unlock()
    
    handoffID := generateHandoffID()
    handoff := &HandoffProcess{
        ID:        handoffID,
        FromAgent: fromAgent,
        ToAgent:   toAgent,
        SessionID: sessionID,
        Context:   context,
        Status:    HandoffStatusInitiated,
        CreatedAt: time.Now(),
    }
    
    hm.activeHandoffs[handoffID] = handoff
    
    // Emit handoff initiated event
    hm.eventBus.Emit(ctx, &HandoffInitiatedEvent{
        BaseEvent: BaseEvent{
            Type:      EventTypeHandoffInitiated,
            Timestamp: time.Now(),
            SessionID: sessionID,
        },
        Handoff: handoff,
    })
    
    return handoff, nil
}
```

## State Management (AG-UI Component-Based)

### Session State Manager

```go
type SessionState struct {
    ID              string                 `json:"id"`
    UserID          string                 `json:"userId"`
    Status          SessionStatus          `json:"status"`
    CreatedAt       time.Time              `json:"createdAt"`
    LastActivity    time.Time              `json:"lastActivity"`
    Context         map[string]interface{} `json:"context"`
    MessageHistory  []Message              `json:"messageHistory"`
    ActiveAgents    []string               `json:"activeAgents"`
    ComponentStates map[string]ComponentState `json:"componentStates"`
}

type ComponentState struct {
    ID         string                 `json:"id"`
    Type       ComponentType          `json:"type"`
    State      map[string]interface{} `json:"state"`
    UpdatedAt  time.Time              `json:"updatedAt"`
}

type ComponentType string

const (
    ComponentTypeChat        ComponentType = "chat"
    ComponentTypeForm        ComponentType = "form"
    ComponentTypeVisualization ComponentType = "visualization"
    ComponentTypeWorkflow    ComponentType = "workflow"
    ComponentTypeCustom      ComponentType = "custom"
)

type SessionStatus string

const (
    SessionStatusActive    SessionStatus = "active"
    SessionStatusInactive  SessionStatus = "inactive"
    SessionStatusPaused    SessionStatus = "paused"
    SessionStatusClosed    SessionStatus = "closed"
)

type StateManager struct {
    sessions map[string]*SessionState
    mu       sync.RWMutex
    eventBus *EventBus
}

func NewStateManager(eventBus *EventBus) *StateManager {
    return &StateManager{
        sessions: make(map[string]*SessionState),
        eventBus: eventBus,
    }
}

func (sm *StateManager) CreateSession(ctx context.Context, userID string) (*SessionState, error) {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    
    sessionID := generateSessionID()
    session := &SessionState{
        ID:              sessionID,
        UserID:          userID,
        Status:          SessionStatusActive,
        CreatedAt:       time.Now(),
        LastActivity:    time.Now(),
        Context:         make(map[string]interface{}),
        MessageHistory:  make([]Message, 0),
        ActiveAgents:    make([]string, 0),
        ComponentStates: make(map[string]ComponentState),
    }
    
    sm.sessions[sessionID] = session
    
    // Emit session created event
    sm.eventBus.Emit(ctx, &SessionCreatedEvent{
        BaseEvent: BaseEvent{
            Type:      EventTypeSessionCreated,
            Timestamp: time.Now(),
            SessionID: sessionID,
        },
        Session: session,
    })
    
    return session, nil
}

func (sm *StateManager) UpdateComponentState(ctx context.Context, sessionID, componentID string, componentType ComponentType, state map[string]interface{}) error {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    
    session, exists := sm.sessions[sessionID]
    if !exists {
        return fmt.Errorf("session %s not found", sessionID)
    }
    
    componentState := ComponentState{
        ID:        componentID,
        Type:      componentType,
        State:     state,
        UpdatedAt: time.Now(),
    }
    
    session.ComponentStates[componentID] = componentState
    session.LastActivity = time.Now()
    
    return nil
}
```

## HTTP API Implementation

### REST Handlers

```go
type APIServer struct {
    agentManager  *AgentManager
    stateManager  *StateManager
    toolRegistry  *ToolRegistry
    handoffManager *HandoffManager
    eventBus      *EventBus
    router        *gin.Engine
}

func NewAPIServer(agentManager *AgentManager, stateManager *StateManager, toolRegistry *ToolRegistry, handoffManager *HandoffManager, eventBus *EventBus) *APIServer {
    server := &APIServer{
        agentManager:   agentManager,
        stateManager:   stateManager,
        toolRegistry:   toolRegistry,
        handoffManager: handoffManager,
        eventBus:       eventBus,
        router:         gin.New(),
    }
    
    server.setupRoutes()
    return server
}

func (s *APIServer) setupRoutes() {
    // Agent management endpoints
    s.router.GET("/agents", s.listAgents)
    s.router.POST("/agents/:id/start", s.startAgent)
    s.router.POST("/agents/:id/stop", s.stopAgent)
    s.router.GET("/agents/:id/status", s.getAgentStatus)
    
    // Message handling endpoints
    s.router.POST("/messages", s.sendMessage)
    s.router.GET("/messages/:sessionId", s.getMessageHistory)
    s.router.POST("/messages/:id/respond", s.respondToMessage)
    
    // Event streaming endpoint
    s.router.GET("/events/:sessionId", s.streamEvents)
    s.router.POST("/events/:sessionId", s.sendEvent)
    
    // Tools endpoints
    s.router.GET("/tools", s.listTools)
    s.router.POST("/tools/:name/execute", s.executeTool)
    
    // Handoff endpoints
    s.router.POST("/handoffs/:fromAgent/:toAgent", s.initiateHandoff)
    s.router.GET("/handoffs/:sessionId", s.getHandoffs)
    
    // Health and discovery
    s.router.GET("/health", s.healthCheck)
    s.router.GET("/capabilities", s.getCapabilities)
}

// Agent Management Handlers
func (s *APIServer) listAgents(c *gin.Context) {
    sessionID := c.Query("sessionId")
    if sessionID == "" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "sessionId required"})
        return
    }
    
    agents := s.agentManager.GetRunningAgents(sessionID)
    c.JSON(http.StatusOK, gin.H{"agents": agents})
}

func (s *APIServer) startAgent(c *gin.Context) {
    agentID := c.Param("id")
    
    var req struct {
        SessionID     string            `json:"sessionId" binding:"required"`
        Configuration AgentConfiguration `json:"configuration"`
    }
    
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    agent, err := s.agentManager.StartAgent(c.Request.Context(), agentID, req.SessionID, req.Configuration)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, gin.H{"agent": agent})
}

// Message Handling
func (s *APIServer) sendMessage(c *gin.Context) {
    var message UserInputMessage
    if err := c.ShouldBindJSON(&message); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // Process message through the system
    if err := s.processUserMessage(c.Request.Context(), &message); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, gin.H{"status": "message sent", "messageId": message.ID})
}

// Event Streaming
func (s *APIServer) streamEvents(c *gin.Context) {
    sessionID := c.Param("sessionId")
    
    c.Header("Content-Type", "text/event-stream")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Header("Access-Control-Allow-Origin", "*")
    
    // Create event channel for this connection
    eventChan := make(chan Event, 100)
    
    // Subscribe to relevant events for this session
    s.eventBus.Subscribe(EventTypeAgentStateChange, func(ctx context.Context, event Event) error {
        if event.GetSessionID() == sessionID {
            select {
            case eventChan <- event:
            default:
                // Skip if channel is full
            }
        }
        return nil
    })
    
    defer close(eventChan)
    
    for {
        select {
        case event := <-eventChan:
            data, err := json.Marshal(event)
            if err != nil {
                continue
            }
            c.SSEvent("message", string(data))
            c.Writer.Flush()
        case <-c.Request.Context().Done():
            return
        }
    }
}

// Tool Execution
func (s *APIServer) executeTool(c *gin.Context) {
    toolName := c.Param("name")
    
    var req struct {
        Parameters map[string]interface{} `json:"parameters"`
        SessionID  string                 `json:"sessionId" binding:"required"`
    }
    
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    result, err := s.toolRegistry.ExecuteTool(c.Request.Context(), toolName, req.Parameters, req.SessionID)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, gin.H{"result": result})
}

func (s *APIServer) healthCheck(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{
        "status": "healthy",
        "timestamp": time.Now(),
        "version": "1.0.0",
    })
}
```

## Protocol Layer Implementation

### Message Router

```go
type MessageRouter struct {
    agentManager *AgentManager
    stateManager *StateManager
    eventBus     *EventBus
}

func NewMessageRouter(agentManager *AgentManager, stateManager *StateManager, eventBus *EventBus) *MessageRouter {
    return &MessageRouter{
        agentManager: agentManager,
        stateManager: stateManager,
        eventBus:     eventBus,
    }
}

func (mr *MessageRouter) RouteMessage(ctx context.Context, message Message) error {
    switch message.GetType() {
    case MessageTypeUserInput:
        return mr.handleUserInput(ctx, message.(*UserInputMessage))
    case MessageTypeToolExecution:
        return mr.handleToolExecution(ctx, message.(*ToolExecutionMessage))
    case MessageTypeHandoff:
        return mr.handleHandoff(ctx, message.(*HandoffMessage))
    case MessageTypeStateUpdate:
        return mr.handleStateUpdate(ctx, message.(*StateUpdateMessage))
    default:
        return fmt.Errorf("unknown message type: %s", message.GetType())
    }
}

func (mr *MessageRouter) handleUserInput(ctx context.Context, message *UserInputMessage) error {
    // Get active agents for this session
    agents := mr.agentManager.GetRunningAgents(message.SessionID)
    
    // Route to appropriate agent(s)
    for _, agent := range agents {
        if agent.Status == AgentStatusActive {
            // Process message with agent
            go mr.processWithAgent(ctx, agent, message)
        }
    }
    
    // Emit message received event
    mr.eventBus.Emit(ctx, &MessageReceivedEvent{
        BaseEvent: BaseEvent{
            Type:      EventTypeMessageReceived,
            Timestamp: time.Now(),
            SessionID: message.SessionID,
        },
        Message: message,
    })
    
    return nil
}

func (mr *MessageRouter) processWithAgent(ctx context.Context, agent *RunningAgent, message *UserInputMessage) {
    // Update agent activity
    agent.LastActivity = time.Now()
    
    // Process message through agent's capabilities
    // This would integrate with the specific agent implementation
    
    // For now, simulate processing
    time.Sleep(100 * time.Millisecond)
    
    // Generate response
    response := &AgentResponseMessage{
        ID:        generateMessageID(),
        Type:      MessageTypeAgentResponse,
        Timestamp: time.Now(),
        SessionID: message.SessionID,
        AgentID:   agent.ID,
        Content:   fmt.Sprintf("Processed: %s", message.Content),
    }
    
    // Emit agent response event
    mr.eventBus.Emit(ctx, &AgentResponseEvent{
        BaseEvent: BaseEvent{
            Type:      EventTypeAgentStateChange,
            Timestamp: time.Now(),
            SessionID: message.SessionID,
        },
        Response: response,
    })
}
```

## Main Application Structure

```go
type Application struct {
    config         *Config
    agentManager   *AgentManager
    stateManager   *StateManager
    toolRegistry   *ToolRegistry
    handoffManager *HandoffManager
    eventBus       *EventBus
    messageRouter  *MessageRouter
    apiServer      *APIServer
    httpServer     *http.Server
}

func NewApplication(config *Config) *Application {
    eventBus := NewEventBus()
    agentManager := NewAgentManager(eventBus)
    stateManager := NewStateManager(eventBus)
    toolRegistry := NewToolRegistry(eventBus)
    handoffManager := NewHandoffManager(agentManager, eventBus)
    messageRouter := NewMessageRouter(agentManager, stateManager, eventBus)
    apiServer := NewAPIServer(agentManager, stateManager, toolRegistry, handoffManager, eventBus)
    
    return &Application{
        config:         config,
        agentManager:   agentManager,
        stateManager:   stateManager,
        toolRegistry:   toolRegistry,
        handoffManager: handoffManager,
        eventBus:       eventBus,
        messageRouter:  messageRouter,
        apiServer:      apiServer,
    }
}

func (app *Application) Start(ctx context.Context) error {
    app.httpServer = &http.Server{
        Addr:    app.config.Port,
        Handler: app.apiServer.router,
    }
    
    return app.httpServer.ListenAndServe()
}

func (app *Application) Stop(ctx context.Context) error {
    return app.httpServer.Shutdown(ctx)
}
```

## Configuration

```go
type Config struct {
    Port                string                 `json:"port"`
    LogLevel            string                 `json:"logLevel"`
    EventBusBufferSize  int                    `json:"eventBusBufferSize"`
    AgentTimeout        time.Duration          `json:"agentTimeout"`
    SessionTimeout      time.Duration          `json:"sessionTimeout"`
    EnableMetrics       bool                   `json:"enableMetrics"`
    EnableTracing       bool                   `json:"enableTracing"`
    AgentConfigurations map[string]AgentConfiguration `json:"agentConfigurations"`
}

type AgentConfiguration struct {
    Type         AgentType              `json:"type"`
    Endpoint     string                 `json:"endpoint,omitempty"`
    APIKey       string                 `json:"apiKey,omitempty"`
    Model        string                 `json:"model,omitempty"`
    Temperature  float64                `json:"temperature,omitempty"`
    MaxTokens    int                    `json:"maxTokens,omitempty"`
    Capabilities []Capability           `json:"capabilities,omitempty"`
    Custom       map[string]interface{} `json:"custom,omitempty"`
}
```

This revised specification transforms the CopilotRuntime Go implementation to fully adhere to AG-UI's architecture principles:

1. **Standard HTTP REST endpoints** instead of GraphQL
2. **Event-driven architecture** with proper event bus implementation
3. **Component-based state management** following AG-UI patterns
4. **Running agents** tracking and lifecycle management
5. **Tools and handoff system** for inter-agent coordination
6. **Message types** aligned with AG-UI protocol
7. **Protocol layer** for message routing and processing

The implementation maintains Go's strengths (concurrency, type safety, performance) while conforming to AG-UI's architectural patterns and communication protocols.

<citations>
<document>
<document_type>WEB_PAGE</document_type>
<document_id>https://docs.ag-ui.com/concepts/architecture</document_id>
</document>
</citations>
