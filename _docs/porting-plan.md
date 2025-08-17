## CopilotRuntime Python Port – Comprehensive Porting Plan

### Overview
This plan delivers a Python port of CopilotRuntime that exposes a GraphQL endpoint via FastAPI and bridges to Python agent frameworks starting with LangGraph. The runtime must reproduce the exact GraphQL contract and semantics of the TypeScript implementation to maintain compatibility with existing React clients using `@copilotkit/runtime-client-gql`.

### Architecture Requirements
- **GraphQL Contract Parity**: Must implement identical schema, types, unions, and operations as TypeScript runtime
- **Endpoint Compatibility**: Mount at `/api/copilotkit` with identical request/response patterns
- **Streaming Support**: Target GraphQL over SSE (Server-Sent Events) for incremental delivery
- **Provider Architecture**: Pluggable provider layer starting with LangGraph, followed by CrewAI
- **State Management**: Persistent state store with pluggable backends (in-memory → Redis/Postgres)
- **Package Management**: Use `uv` for Python environment and dependency management

### GraphQL Public Contract (Exact Parity Required)

**Queries:**
- `hello: String!` - Diagnostic health check
- `availableAgents: AgentsResponse!` - Returns list of discoverable agents
- `loadAgentState(data: LoadAgentStateInput!): LoadAgentStateResponse!` - Retrieves persisted agent state

**Mutations:**
- `generateCopilotResponse(data: GenerateCopilotResponseInput!, properties: JSONObject): CopilotResponse!` - Orchestrates agent runs with streaming messages/meta-events

**Message Union Types:**
- `TextMessage`: `{ id, createdAt, role, content, status }`
- `ImageMessage`: `{ id, createdAt, role, format, bytes }`
- `ActionExecutionMessage`: `{ id, name, arguments, parentMessageId }`
- `ResultMessage`: `{ id, actionExecutionId, actionName, result }`
- `AgentStateMessage`: `{ threadId, state, running, agentName, nodeName, runId, active, role }`

**Meta-Event Types:**
- `LangGraphInterruptEvent`: `{ type, name, value }` (raw LangGraph interrupt)
- `CopilotKitLangGraphInterruptEvent`: `{ type, name, data: { messages[], value } }` (enriched)

### Python Package Structure
```
sdk-python/copilotkit/runtime_py/
  app/
    main.py                 # FastAPI application bootstrap
    settings.py             # Configuration (port, paths, logging, providers)
    middleware.py           # CORS, authentication, request context
  graphql/
    schema.py               # Strawberry GraphQL schema definition
    types.py                # Message unions, enums, response types
    inputs.py               # Input objects: GenerateCopilotResponseInput, etc.
    resolvers.py            # Query/mutation resolvers
    context.py              # Request context with properties, headers, logger
    streaming.py            # SSE and incremental delivery implementation
  core/
    runtime.py              # CopilotRuntime orchestration class
    conversion.py           # GraphQL ↔ internal message conversion
    events.py               # RuntimeEvent definitions and meta-events
    state_store.py          # State persistence interface and in-memory implementation
    errors.py               # Error normalization and CopilotKit status codes
    lifecycle.py            # threadId/runId management and cleanup
  providers/
    base.py                 # Abstract provider interface
    registry.py             # Agent discovery and provider management
    langgraph/
      provider.py           # LangGraphProvider implementation
      adapters.py           # LangGraph event → RuntimeEvent translation
      state_bridge.py       # Graph state persistence integration
    crewai/                 # Future: CrewAI provider implementation
      provider.py
      adapters.py
  storage/
    interface.py            # Storage backend interface
    memory.py               # In-memory implementation
    redis.py                # Redis backend (Phase 6)
    postgres.py             # PostgreSQL backend (Phase 6)
```

---

## Phase 0 — Bootstrap and Alignment
**Goal**: Establish foundations and ensure contract compatibility.

**Technical Requirements:**
- Extract complete GraphQL schema from TypeScript runtime (`packages/runtime/src/graphql/`)
- Analyze client contract from `packages/runtime-client-gql/src/graphql/definitions/`
- Choose GraphQL library: **Strawberry GraphQL** (preferred) for Python 3.8+ compatibility
- Establish streaming strategy: **GraphQL over SSE** with multipart responses

**Tasks:**
- Create frozen snapshot of TS GraphQL schema (types, unions, enums, operations)
- Set up Python package structure under `sdk-python/copilotkit/runtime_py/`
- Configure `uv` toolchain: ruff, black, mypy, pytest
- Install core dependencies: uvicorn, fastapi, strawberry-graphql, sse-starlette, httpx
- Create basic FastAPI app with GraphQL endpoint mounting
- Set up development workflow documentation

**Deliverables:**
- Complete package scaffolding with `pyproject.toml` and `uv.lock`
- FastAPI app serving GraphQL playground at `/api/copilotkit/graphql`
- Development scripts: `uv run dev`, `uv run test`, `uv run lint`

**Acceptance Criteria:**
- `uvicorn copilotkit.runtime_py.app.main:app --reload` starts successfully
- GraphQL playground accessible and loads schema
- All linting and type checking passes

---

## Phase 1 — GraphQL Schema Implementation (Non-Streaming MVP)
**Goal**: Implement complete schema with static/stubbed resolvers.

**Technical Requirements:**
- Implement all GraphQL types exactly matching TypeScript schema
- All resolvers must return valid response shapes (even if stubbed)
- Request context must capture properties, headers, correlation IDs
- Error handling must return GraphQL-compatible error responses

**Tasks:**
- Define complete type system in `graphql/types.py`:
  - Input types: `GenerateCopilotResponseInput`, `LoadAgentStateInput`
  - Response types: `CopilotResponse`, `AgentsResponse`, `LoadAgentStateResponse`
  - Message union: `TextMessage | ImageMessage | ActionExecutionMessage | ResultMessage | AgentStateMessage`
  - Meta-event union: `LangGraphInterruptEvent | CopilotKitLangGraphInterruptEvent`
  - Enums: message status, roles, event types
- Implement stubbed resolvers in `graphql/resolvers.py`:
  - `hello()` → diagnostic string with version/status
  - `availableAgents()` → static list of mock agents
  - `loadAgentState()` → empty state response
  - `generateCopilotResponse()` → single TextMessage response
- Create request context system with properties forwarding
- Add conversion utilities between GraphQL and internal types
- Implement basic error normalization

**Deliverables:**
- Complete GraphQL schema with all types and resolvers
- Working endpoint returning valid responses for all operations
- Unit tests for type conversion and basic resolver logic

**Acceptance Criteria:**
- Frontend client can execute all queries/mutations without GraphQL errors
- `generateCopilotResponse` returns valid `CopilotResponse` with at least one message
- Request context properly captures and forwards client properties

---

## Phase 2 — Runtime Core and State Management
**Goal**: Implement `CopilotRuntime` orchestrator and state persistence.

**Technical Requirements:**
- `CopilotRuntime` must manage complete request lifecycle
- State store must support thread-scoped and agent-scoped persistence
- Error handling must map to CopilotKit status codes and user-friendly messages
- Thread/run ID generation and validation must be robust

**Tasks:**
- Implement `CopilotRuntime` class in `core/runtime.py`:
  - Thread ID and run ID lifecycle management
  - Request orchestration and provider coordination
  - State loading/saving coordination
  - Error boundary and cleanup handling
- Create state store interface and in-memory implementation:
  - Key structure: `{threadId, agentName}` → agent state
  - Atomic operations for concurrent access
  - State serialization/deserialization
- Implement error normalization system:
  - Map provider errors to CopilotKit error codes
  - Sanitize error messages (no secret leakage)
  - Structured logging with correlation IDs
- Add abort/cancellation support (stubs for streaming)

**Deliverables:**
- Working `CopilotRuntime` with complete lifecycle management
- In-memory state store with persistence interface
- Comprehensive error handling and normalization
- Unit tests covering runtime orchestration and state operations

**Acceptance Criteria:**
- `loadAgentState` returns state persisted during previous `generateCopilotResponse`
- Error conditions return appropriate GraphQL errors with status codes
- Concurrent requests maintain proper state isolation
- Unit tests achieve >85% coverage for core runtime logic

---

## Phase 3 — LangGraph Provider Integration
**Goal**: Bridge GraphQL operations to LangGraph execution with event translation.

**Technical Requirements:**
- Provider must support agent discovery from LangGraph registry/definitions
- Event translation must map all LangGraph events to appropriate message/meta-event types
- State persistence must integrate with LangGraph's checkpointing system
- Tool/action execution must bridge through CopilotKit message patterns

**Tasks:**
- Implement provider interface in `providers/base.py`:
  - `list_agents() → List[AgentDescriptor]`
  - `load_state(thread_id, agent_name) → AgentState`
  - `execute_run(input, context) → AsyncIterator[RuntimeEvent]`
- Create `LangGraphProvider` implementation:
  - Agent registry integration and discovery
  - Graph execution with thread/run correlation
  - State checkpointing and restoration
  - Event stream processing and translation
- Implement event adapters in `providers/langgraph/adapters.py`:
  - Node execution → `AgentStateMessage`
  - Tool calls → `ActionExecutionMessage`
  - Tool responses → `ResultMessage`
  - LLM responses → `TextMessage`
  - Graph interrupts → `LangGraphInterruptEvent`/`CopilotKitLangGraphInterruptEvent`
- Create demo LangGraph agent for testing:
  - Simple conversational agent with tool usage
  - State persistence demonstration
  - Interrupt handling example

**Deliverables:**
- Complete LangGraph provider with event translation
- Working agent discovery returning real LangGraph agents
- End-to-end execution path from GraphQL mutation to LangGraph run
- Demo agent and integration tests

**Acceptance Criteria:**
- `availableAgents` returns agents discovered from LangGraph registry
- `generateCopilotResponse` executes LangGraph run and returns translated events
- `loadAgentState` reflects updated graph state after execution
- Integration test demonstrates full conversation flow with state persistence

---

## Phase 4 — Streaming Implementation (SSE/Incremental Delivery)
**Goal**: Implement real-time streaming of messages and meta-events.

**Technical Requirements:**
- Streaming must deliver events incrementally as they occur during execution
- SSE implementation must be compatible with GraphQL-over-HTTP spec
- Abort/cancellation must cleanly terminate streams and provider execution
- Client compatibility with existing `@copilotkit/runtime-client-gql` patterns

**Tasks:**
- Implement GraphQL over SSE in `graphql/streaming.py`:
  - Multipart response formatting for GraphQL results
  - Event serialization and chunk boundaries
  - Connection lifecycle and error handling
  - Client disconnection detection
- Modify `generateCopilotResponse` resolver for streaming:
  - Convert to async generator yielding incremental responses
  - Proper error handling within stream
  - Graceful stream termination on completion/error
- Add abort support throughout the stack:
  - Request cancellation propagation to providers
  - Clean resource cleanup on abort
  - Stream closure with appropriate status codes
- Implement streaming-compatible event batching:
  - Buffer small events to reduce chattiness
  - Flush on significant events or time intervals
  - Maintain event ordering guarantees

**Deliverables:**
- Working SSE-based GraphQL streaming implementation
- Abort-capable `generateCopilotResponse` with clean cancellation
- Client compatibility validation with incremental event delivery

**Acceptance Criteria:**
- Messages and meta-events appear incrementally in UI during execution
- Abort functionality stops backend execution and closes stream without errors
- No message loss or ordering issues under normal and error conditions
- Performance acceptable for typical conversation loads

---

## Phase 5 — Extensions, Guardrails, and Request Metadata
**Goal**: Reach feature parity for advanced request handling and safety features.

**Technical Requirements:**
- Extensions field must support arbitrary metadata in responses
- Request properties and headers must be properly forwarded to providers
- Guardrails must implement topic filtering and content validation
- Telemetry must provide comprehensive observability

**Tasks:**
- Implement extensions support:
  - Response metadata collection and serialization
  - Provider extension contribution interface
  - Client-side extension consumption compatibility
- Add forwarded parameters system:
  - Header extraction and sanitization
  - Property forwarding to provider context
  - Secure handling of API keys and credentials
- Implement input guardrails:
  - Topic allow/deny list validation
  - Content filtering and safety checks
  - Rate limiting and request size limits
  - Configurable guardrail policies
- Add comprehensive logging and telemetry:
  - Structured logging with correlation IDs
  - Request/response timing and metrics
  - Error rate tracking and alerting hooks
  - Optional OpenTelemetry integration

**Deliverables:**
- Extensions-capable responses with metadata propagation
- Guardrails implementation with configurable policies
- Comprehensive telemetry and logging system

**Acceptance Criteria:**
- End-to-end tests demonstrate forwarded parameters reaching providers
- Guardrails effectively filter inappropriate content and topics
- Telemetry provides sufficient observability for production operation
- Security review passes for credential handling and data sanitization

---

## Phase 6 — Persistence and Multi-Agent Orchestration
**Goal**: Production-ready state management and complex agent workflows.

**Technical Requirements:**
- Pluggable persistence must support Redis and PostgreSQL backends
- Multi-agent orchestration must handle agent selection and state isolation
- Cross-process state consistency must be maintained
- Agent session semantics must match TypeScript implementation

**Tasks:**
- Implement pluggable storage backends:
  - Redis implementation with connection pooling and failover
  - PostgreSQL implementation with proper indexing and migrations
  - Storage backend interface with atomic operations
  - Configuration-driven backend selection
- Add multi-agent registry and orchestration:
  - Agent discovery from multiple provider types
  - Agent selection logic and fallback handling
  - Cross-agent state isolation and security
  - Agent session lifecycle management
- Implement robust state rehydration:
  - Cross-process state consistency
  - State versioning and migration support
  - Conflict resolution for concurrent modifications
  - State garbage collection and cleanup
- Add production hardening:
  - Connection pooling and resource management
  - Retry logic with exponential backoff
  - Circuit breaker patterns for external dependencies
  - Health checks and readiness probes

**Deliverables:**
- Production-grade persistence with Redis/PostgreSQL support
- Multi-agent orchestration with proper state isolation
- Robust state management with cross-process consistency

**Acceptance Criteria:**
- Multi-agent scenario: discovery, selection, execution with different providers
- State persistence survives process restarts and database failovers
- Performance meets production requirements under load
- All race conditions and edge cases properly handled

---

## Phase 7 — CrewAI Provider Implementation
**Goal**: Add CrewAI support demonstrating provider architecture flexibility.

**Technical Requirements:**
- CrewAI provider must implement identical interface as LangGraph provider
- Event mapping must handle CrewAI-specific execution patterns
- State management must integrate with CrewAI's agent persistence
- Feature parity must be maintained across both providers

**Tasks:**
- Implement `CrewAIProvider` in `providers/crewai/`:
  - Agent discovery from CrewAI crew definitions
  - Execution orchestration and event streaming
  - State persistence integration
  - Tool/action bridging for CrewAI agents
- Create CrewAI event adapters:
  - Agent execution events → `AgentStateMessage`
  - Task completion → `TextMessage`
  - Tool usage → `ActionExecutionMessage`/`ResultMessage`
  - Crew collaboration → appropriate meta-events
- Add CrewAI-specific configuration and setup
- Create comprehensive test suite for CrewAI provider

**Deliverables:**
- Complete CrewAI provider with full feature parity
- Provider-agnostic test suite validating both implementations
- Documentation and examples for CrewAI integration

**Acceptance Criteria:**
- CrewAI agents discoverable and executable via same GraphQL interface
- All core features work identically between LangGraph and CrewAI providers
- E2E tests pass for both provider implementations
- Performance characteristics comparable between providers

---

## Phase 8 — Packaging, CI/CD, and Release Preparation
**Goal**: Production-ready package with automated testing and deployment.

**Technical Requirements:**
- Package must be installable via standard Python package managers
- CI/CD must validate all supported Python versions and dependencies
- Documentation must be comprehensive and maintainable
- Release process must integrate with CopilotKit versioning

**Tasks:**
- Finalize package configuration:
  - Complete `pyproject.toml` with proper metadata and dependencies
  - Lock file generation and validation with `uv`
  - Optional extras: `[langgraph]`, `[crewai]`, `[redis]`, `[postgres]`
  - Entry point scripts and CLI tools
- Implement comprehensive CI/CD:
  - Multi-version Python testing (3.8, 3.9, 3.10, 3.11, 3.12)
  - Linting, type checking, and security scanning
  - Integration tests with real provider backends
  - Performance regression testing
  - Automated package building and publishing
- Complete documentation suite:
  - API reference documentation
  - Integration guides for LangGraph and CrewAI
  - Deployment and configuration documentation
  - Troubleshooting and FAQ sections
- Establish release process:
  - Semantic versioning aligned with CopilotKit releases
  - Automated changelog generation
  - Release notes and migration guides
  - Deprecation and backward compatibility policies

**Deliverables:**
- Production-ready Python package with comprehensive CI/CD
- Complete documentation and integration guides
- Automated release pipeline with quality gates

**Acceptance Criteria:**
- Package installs correctly via `pip install copilotkit-runtime-py`
- All CI checks pass consistently across supported Python versions
- Documentation enables successful integration by external developers
- Release process produces reliable, versioned artifacts

---

## Technical Specifications

### Provider Interface Contract
```python
from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Optional
from .events import RuntimeEvent, AgentDescriptor, AgentState

class AgentProvider(ABC):
    @abstractmethod
    async def list_agents(self) -> List[AgentDescriptor]:
        """Return available agents from this provider."""
        pass
    
    @abstractmethod
    async def load_state(self, thread_id: str, agent_name: str) -> Optional[AgentState]:
        """Load persisted state for agent in thread."""
        pass
    
    @abstractmethod
    async def execute_run(
        self, 
        input_data: GenerateCopilotResponseInput,
        context: RequestContext
    ) -> AsyncIterator[RuntimeEvent]:
        """Execute agent run and yield events."""
        pass
    
    @abstractmethod
    async def save_state(self, thread_id: str, agent_name: str, state: AgentState) -> None:
        """Persist agent state for thread."""
        pass
```

### Message Type Definitions
```python
from enum import Enum
from typing import Union, Any, Dict, Optional
from datetime import datetime

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"

class MessageStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"

@strawberry.type
class TextMessage:
    id: str
    created_at: datetime
    role: MessageRole
    content: str
    status: MessageStatus

@strawberry.type
class AgentStateMessage:
    thread_id: str
    state: Dict[str, Any]
    running: bool
    agent_name: str
    node_name: Optional[str]
    run_id: str
    active: bool
    role: MessageRole

# Union type for all messages
Message = Union[TextMessage, ImageMessage, ActionExecutionMessage, ResultMessage, AgentStateMessage]
```

### Error Handling Standards
```python
from enum import Enum
from typing import Optional, Dict, Any

class CopilotErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    STATE_ERROR = "STATE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    GUARDRAIL_VIOLATION = "GUARDRAIL_VIOLATION"

class CopilotKitError(Exception):
    def __init__(
        self,
        message: str,
        code: CopilotErrorCode,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
```

### Streaming Protocol Specification
The streaming implementation uses GraphQL over Server-Sent Events with multipart responses:

1. **Connection Establishment**: Client sends `Accept: text/event-stream` header
2. **Event Format**: Each SSE event contains a JSON object with GraphQL response fragment
3. **Event Types**: `data` (incremental results), `error` (error conditions), `complete` (stream end)
4. **Ordering**: Events maintain strict ordering guarantees within each stream
5. **Cancellation**: Client disconnect or explicit abort terminates provider execution

### Configuration Management
```python
from pydantic import BaseSettings
from typing import Optional, List

class RuntimeSettings(BaseSettings):
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    graphql_path: str = "/api/copilotkit"
    enable_playground: bool = True
    
    # Provider configuration
    enabled_providers: List[str] = ["langgraph"]
    langgraph_config: Optional[Dict] = None
    crewai_config: Optional[Dict] = None
    
    # Storage configuration
    state_store_backend: str = "memory"  # memory, redis, postgres
    redis_url: Optional[str] = None
    postgres_url: Optional[str] = None
    
    # Security and guardrails
    enable_guardrails: bool = True
    allowed_topics: Optional[List[str]] = None
    denied_topics: Optional[List[str]] = None
    max_message_length: int = 10000
    
    # Telemetry
    enable_telemetry: bool = True
    log_level: str = "INFO"
    structured_logging: bool = True
    
    class Config:
        env_prefix = "COPILOTKIT_"
```

---

## Cross-Cutting Concerns

### Security Requirements
- **Input Validation**: All GraphQL inputs validated against schema and additional business rules
- **Credential Management**: API keys and secrets handled securely with no logging exposure
- **Content Filtering**: Configurable content filtering for inappropriate material
- **Rate Limiting**: Request rate limiting to prevent abuse and resource exhaustion
- **CORS Configuration**: Proper CORS headers for frontend integration

### Performance Requirements
- **Response Times**: < 100ms for non-streaming operations, < 500ms for streaming initiation
- **Throughput**: Support 1000+ concurrent WebSocket connections
- **Memory Usage**: Efficient memory management for long-running conversations
- **State Storage**: Optimized state serialization and retrieval performance

### Reliability Requirements
- **Error Recovery**: Graceful handling of provider failures with appropriate fallbacks
- **Retry Logic**: Exponential backoff for transient failures with circuit breaker protection
- **Resource Management**: Proper cleanup of resources on connection termination
- **Monitoring**: Comprehensive health checks and observability for production operation

### Compatibility Requirements
- **Python Versions**: Support Python 3.8+ with type hints and async/await
- **Client Compatibility**: Full compatibility with existing `@copilotkit/runtime-client-gql` client
- **GraphQL Compliance**: Adherence to GraphQL specification and best practices
- **Provider Flexibility**: Clean abstraction allowing additional providers without core changes

---

## Success Metrics and Validation

### Development Phase Gates
Each phase must pass the following criteria before proceeding:
- All automated tests pass (unit, integration, e2e)
- Code coverage meets minimum threshold (85% for core, 70% for providers)
- Performance benchmarks meet requirements
- Security scan passes without high-severity issues
- Peer review approval from CopilotKit maintainers

### Production Readiness Checklist
- [ ] Complete GraphQL schema parity with TypeScript implementation
- [ ] All message types and meta-events properly implemented
- [ ] Streaming functionality working with abort support
- [ ] At least one provider (LangGraph) fully functional
- [ ] State persistence working across process restarts
- [ ] Comprehensive error handling and logging
- [ ] Security review passed
- [ ] Performance testing completed
- [ ] Documentation complete and accurate
- [ ] CI/CD pipeline operational
- [ ] Package published and installable

### Long-term Success Indicators
- Community adoption and contributor engagement
- Performance parity or improvement over TypeScript implementation
- Successful integration stories from external developers
- Minimal production issues and fast resolution times
- Clear migration path for existing TypeScript users