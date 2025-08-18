## AGUI Runtime Python Port – Comprehensive Porting Plan

### Overview
This plan delivers a Python port of CopilotRuntime that exposes a GraphQL endpoint via FastAPI and bridges to Python agent frameworks starting with LangGraph. The runtime must reproduce the exact GraphQL contract and semantics of the TypeScript implementation to maintain compatibility with existing React clients using `@copilotkit/runtime-client-gql`.

### Architecture Requirements
- **GraphQL Contract Parity**: Must implement identical schema, types, unions, and operations as TypeScript runtime
- **FastAPI Integration**: Runtime designed as pluggable component for existing FastAPI instances
- **Endpoint Compatibility**: Mount at `/api/copilotkit` with identical request/response patterns
- **Streaming Support**: Target GraphQL over SSE (Server-Sent Events) for incremental delivery
- **Connector Reuse**: Leverage existing `CopilotKitRemoteEndpoint` from Python SDK instead of implementing custom connectors
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
python/copilotkit/runtime_py/
  app/
    main.py                 # Standalone FastAPI server example
    runtime_mount.py        # FastAPI pluggable runtime mounting
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
    runtime.py              # CopilotRuntime orchestration class (main entry point)
    conversion.py           # GraphQL ↔ internal message conversion
    events.py               # RuntimeEvent definitions and meta-events
    state_store.py          # State persistence interface and in-memory implementation
    errors.py               # Error normalization and CopilotKit status codes
    lifecycle.py            # threadId/runId management and cleanup
  connectors/
    copilotkit_remote.py    # Bridge to CopilotKitRemoteEndpoint
    agent_registry.py       # Agent discovery through existing connectors
  storage/
    interface.py            # Storage backend interface
    memory.py               # In-memory implementation
    redis.py                # Redis backend (Phase 6)
    postgres.py             # PostgreSQL backend (Phase 6)
```

---

## Phase 0 — Bootstrap and Core Runtime Class - ✅ COMPLETED
**Goal**: Establish foundations, create pluggable runtime class, and ensure contract compatibility.

**Technical Requirements:**
- Extract complete GraphQL schema from TypeScript runtime (`externals/copilotkit/CopilotKit/packages/runtime/src/graphql/`)
- Analyze client contract from `externals/copilotkit/CopilotKit/packages/runtime-client-gql/src/graphql/definitions/`
- Choose GraphQL library: **Strawberry GraphQL** (preferred) for Python 3.8+ compatibility
- Create pluggable runtime class for FastAPI integration
- Establish streaming strategy: **GraphQL over SSE** with multipart responses

**Tasks:**
- Create frozen snapshot of TS GraphQL schema (types, unions, enums, operations)
- Set up Python package structure under `python/copilotkit/runtime_py/`
- Configure `uv` toolchain: ruff, black, mypy, pytest
- Install core dependencies: uvicorn, fastapi, strawberry-graphql, sse-starlette, httpx, copilotkit
- Create `CopilotRuntime` class in `core/runtime.py` as main orchestrator
- Design runtime as pluggable FastAPI component with mount functionality
- Create standalone FastAPI server example in `app/main.py` for testing
- Set up development workflow documentation

**Deliverables:**
- Complete package scaffolding with `pyproject.toml` and `uv.lock`
- Working `CopilotRuntime` class with basic initialization
- Pluggable FastAPI mounting mechanism in `app/runtime_mount.py`
- Standalone test server in `app/main.py`
- Development scripts: `uv run dev`, `uv run test`, `uv run lint`

**Acceptance Criteria:**
- `uvicorn python.copilotkit.runtime_py.app.main:app --reload` starts successfully
- Runtime can be mounted on existing FastAPI instances
- GraphQL playground accessible and loads basic schema
- All linting and type checking passes

---

## Phase 1 — CopilotRuntime Class and FastAPI Integration
**Goal**: Create core runtime class and establish FastAPI mounting patterns.

**Technical Requirements:**
- `CopilotRuntime` class must be the main entry point for all operations
- Runtime must be pluggable into existing FastAPI applications
- FastAPI mounting must preserve all GraphQL contract requirements
- Runtime must support configuration injection and lifecycle management

**Tasks:**
- Implement `CopilotRuntime` class in `core/runtime.py`:
  - Constructor accepting `RuntimeSettings` configuration
  - Methods for connector registration and management
  - GraphQL schema building and resolver binding
  - Request lifecycle and context management
- Create FastAPI integration in `app/runtime_mount.py`:
  - `mount_to_fastapi(app: FastAPI, path: str)` method
  - Proper middleware integration for CORS, auth, logging
  - GraphQL endpoint setup with Strawberry integration
  - SSE endpoint preparation for streaming
- Implement basic GraphQL schema in `graphql/schema.py`:
  - All required types matching TypeScript schema
  - Stubbed resolvers returning valid response shapes
  - Request context integration with FastAPI
- Create standalone test server in `app/main.py`:
  - FastAPI application instance
  - Runtime mounting and configuration
  - Development server setup with hot reload

**Deliverables:**
- Working `CopilotRuntime` class with pluggable architecture
- FastAPI mounting mechanism with proper integration
- Standalone test server for development and validation
- Basic GraphQL schema with stubbed but valid responses

**Acceptance Criteria:**
- `CopilotRuntime` can be instantiated with configuration
- Runtime mounts successfully to existing FastAPI apps
- Standalone server starts and serves GraphQL playground
- All GraphQL operations return valid response shapes

---

## Phase 2 — Complete GraphQL Schema and Request Orchestration
**Goal**: Implement full GraphQL contract with proper request orchestration through runtime.

**Technical Requirements:**
- Complete GraphQL schema exactly matching TypeScript runtime
- All resolvers must delegate to `CopilotRuntime` for orchestration
- Request context must capture and forward all client properties
- State store must support thread-scoped and agent-scoped persistence

**Tasks:**
- Complete GraphQL type system implementation:
  - All input types: `GenerateCopilotResponseInput`, `LoadAgentStateInput`
  - All response types: `CopilotResponse`, `AgentsResponse`, `LoadAgentStateResponse`
  - Complete message union: `TextMessage | ImageMessage | ActionExecutionMessage | ResultMessage | AgentStateMessage`
  - Meta-event union: `LangGraphInterruptEvent | CopilotKitLangGraphInterruptEvent`
  - All enums: message status, roles, event types
- Implement resolver orchestration patterns:
  - All resolvers delegate to `CopilotRuntime` methods
  - Request context properly initialized and forwarded
  - Error handling with proper GraphQL error responses
  - Thread/run ID generation and validation
- Enhance `CopilotRuntime` orchestration capabilities:
  - Complete request lifecycle management
  - Connector coordination and event aggregation
  - State persistence through pluggable store interface
  - Error normalization and logging integration
- Create state store interface and in-memory implementation:
  - Key structure: `{threadId, agentName}` → agent state
  - Atomic operations for concurrent access
  - State serialization/deserialization

**Deliverables:**
- Complete GraphQL schema with all required types and operations
- Runtime orchestration handling all resolver delegations
- Working state persistence with pluggable interface
- Unit tests covering schema, runtime, and state operations

**Acceptance Criteria:**
- All GraphQL operations execute without schema errors
- `CopilotRuntime` properly orchestrates all requests
- State persistence works across multiple requests
- Error handling returns appropriate GraphQL error responses

---

## Phase 3 — CopilotKitRemoteEndpoint Integration
**Goal**: Bridge GraphQL operations to LangGraph through existing CopilotKit Python SDK connector.

**Technical Requirements:**
- Leverage existing `CopilotKitRemoteEndpoint` from `copilotkit` Python package
- Integrate with LangGraph agents using established patterns from `externals/copilotkit/sdk-python/`
- Event translation must map CopilotKit events to GraphQL message/meta-event types
- State persistence must work with existing CopilotKit state management

**Tasks:**
- Implement connector bridge in `connectors/copilotkit_remote.py`:
  - Wrap `CopilotKitRemoteEndpoint` for runtime integration
  - Agent discovery through existing CopilotKit registry patterns
  - Event stream processing and translation to GraphQL types
- Create agent registry in `connectors/agent_registry.py`:
  - Discover agents from CopilotKit remote endpoints
  - Handle agent metadata and availability
  - Support for multiple remote endpoints
- Implement event translation:
  - CopilotKit events → GraphQL `Message` union types
  - CopilotKit state events → `AgentStateMessage`
  - CopilotKit tool calls → `ActionExecutionMessage`/`ResultMessage`
  - CopilotKit text responses → `TextMessage`
- Create demo LangGraph agents using standard CopilotKit patterns:
  - Simple conversational agent with `@copilotkit_runtime_action` decorators
  - State persistence using existing CopilotKit mechanisms
  - Tool integration following `externals/copilotkit/sdk-python/` examples

**Deliverables:**
- CopilotKitRemoteEndpoint integration bridge
- Working agent discovery through existing connector
- End-to-end execution path from GraphQL mutation to CopilotKit remote endpoint
- Demo agents following established CopilotKit patterns

**Acceptance Criteria:**
- `availableAgents` returns agents discovered from CopilotKitRemoteEndpoint
- `generateCopilotResponse` executes agents through existing connector
- `loadAgentState` reflects state managed by CopilotKit SDK
- Integration test demonstrates compatibility with existing CopilotKit agent patterns

---

## Phase 4 — Streaming Implementation (SSE/Incremental Delivery)
**Goal**: Implement real-time streaming of messages and meta-events through CopilotKit connector.

**Technical Requirements:**
- Streaming must deliver events incrementally as they occur from CopilotKitRemoteEndpoint
- SSE implementation must be compatible with GraphQL-over-HTTP spec
- Abort/cancellation must cleanly terminate streams and connector execution
- Event translation from CopilotKit events to GraphQL streaming responses

**Tasks:**
- Implement GraphQL over SSE in `graphql/streaming.py`:
  - Multipart response formatting for GraphQL results
  - Event serialization and chunk boundaries
  - Connection lifecycle and error handling
  - Client disconnection detection
- Enhance `CopilotKitRemoteConnector` for streaming:
  - Stream events from `CopilotKitRemoteEndpoint` in real-time
  - Translate CopilotKit events to GraphQL message/meta-event types
  - Handle connector-level errors and state changes
  - Proper cleanup on stream termination
- Modify `generateCopilotResponse` resolver for streaming:
  - Convert to async generator yielding incremental responses
  - Stream events through runtime connector orchestration
  - Graceful stream termination on completion/error
- Add abort support throughout the stack:
  - Request cancellation propagation to CopilotKit connectors
  - Clean connector and resource cleanup on abort
  - Stream closure with appropriate status codes

**Deliverables:**
- Working SSE-based GraphQL streaming implementation
- Streaming CopilotKitRemoteConnector with event translation
- Abort-capable execution with clean connector termination
- Client compatibility validation with incremental event delivery

**Acceptance Criteria:**
- Messages and meta-events appear incrementally from CopilotKit agents
- Abort functionality stops CopilotKit execution and closes stream
- Event translation maintains proper message ordering and types
- Performance acceptable for typical CopilotKit agent interactions

---

## Phase 5 — Extensions, Guardrails, and Request Metadata
**Goal**: Reach feature parity for advanced request handling and safety features with CopilotKit integration.

**Technical Requirements:**
- Extensions field must support arbitrary metadata from CopilotKit responses
- Request properties and headers must be forwarded to CopilotKitRemoteEndpoint
- Guardrails must work with existing CopilotKit safety mechanisms
- Telemetry must provide comprehensive observability across runtime and connectors

**Tasks:**
- Implement extensions support:
  - Collect metadata from CopilotKitRemoteEndpoint responses
  - Runtime extension contribution interface
  - Client-side extension consumption compatibility
- Add forwarded parameters system:
  - Header extraction and sanitization for CopilotKit context
  - Property forwarding to CopilotKitRemoteEndpoint
  - Secure API key handling for CopilotKit agent backends
- Implement input guardrails:
  - Integration with CopilotKit safety mechanisms
  - Runtime-level content filtering and validation
  - Rate limiting and request size limits
  - Configurable guardrail policies working with CopilotKit patterns
- Add comprehensive logging and telemetry:
  - Structured logging with correlation IDs across runtime and connectors
  - CopilotKit interaction timing and metrics
  - Connector health monitoring and error tracking
  - Optional OpenTelemetry integration for distributed tracing

**Deliverables:**
- Extensions-capable responses with CopilotKit metadata propagation
- Guardrails implementation compatible with CopilotKit safety features
- Comprehensive telemetry covering runtime and connector interactions

**Acceptance Criteria:**
- End-to-end tests demonstrate forwarded parameters reaching CopilotKit agents
- Guardrails work effectively with CopilotKit content filtering
- Telemetry provides visibility into both runtime and CopilotKit performance
- Security review passes for CopilotKit credential and context forwarding

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

## Phase 7 — CrewAI Connector Implementation
**Goal**: Add CrewAI support through connector pattern, demonstrating architecture flexibility.

**Technical Requirements:**
- CrewAI connector must implement identical interface as CopilotKitRemoteConnector
- Event mapping must handle CrewAI-specific execution patterns through CopilotKit bridge
- State management must work with CrewAI persistence via CopilotKit patterns
- Feature parity must be maintained across different connector types

**Tasks:**
- Implement `CrewAIConnector` in `connectors/crewai_connector.py`:
  - Bridge to CrewAI crews using CopilotKit integration patterns
  - Agent discovery from CrewAI crew definitions via CopilotKit
  - Execution orchestration through CopilotKit CrewAI adapter
  - Event streaming and translation from CrewAI to GraphQL types
- Create CrewAI event translation:
  - CrewAI task execution → `AgentStateMessage`
  - Crew member responses → `TextMessage`
  - Tool usage → `ActionExecutionMessage`/`ResultMessage`
  - Crew collaboration → appropriate meta-events
- Add CrewAI-specific connector configuration
- Create comprehensive test suite for CrewAI connector

**Deliverables:**
- Complete CrewAI connector with full feature parity
- Connector-agnostic test suite validating both implementations
- Documentation and examples for CrewAI integration via CopilotKit

**Acceptance Criteria:**
- CrewAI agents discoverable and executable via same GraphQL interface
- All core features work identically between CopilotKit and CrewAI connectors
- E2E tests pass for both connector implementations
- Performance characteristics comparable between connector types

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

## Development directives

- at the start of each phase create a file `_docs/porting-phase-X-execution.md`, the goal of this file is to be a detailed instructions and scratchpad for the phase, also to be used as memory of the ongoing development process in case of interruptions. In detail, it will contain:
  - the goals of the phase
  - the detailed implementation plan (no low level code)
  - the in progress updates of the implementation
- if this file is already existing maybe the sessions is a continuation of the previous development, so check the progress and go on
- at the end of each phase, update the `_docs/porting-implementation.md` in order to have a comphrensive documentation of the actual situation, use it a reference at the start of each new phase
- when starting a potential long running process use `timeout XX ...` in order to not be stuck
- be pragmatic and simple 'simplicity is the ultimate perfection'
- when working to a phase update this document marking as in progress, when completed mark as completed
- at the end of each phase run all the tests and format / lint

### Development Scripts

All development tasks are available through `scripts.py`:

```bash
# Development server
uv run python scripts.py dev              # Start with auto-reload
uv run python scripts.py start            # Production server

# Testing
uv run python scripts.py test             # Run all tests
uv run python scripts.py test-unit        # Unit tests only
uv run python scripts.py test-cov         # Tests with coverage

# Code quality
uv run python scripts.py lint             # Run linting
uv run python scripts.py lint-fix         # Auto-fix issues
uv run python scripts.py format           # Format with black
uv run python scripts.py check            # All quality checks

# Utilities
uv run python scripts.py clean            # Clean cache files
uv run python scripts.py schema           # Show GraphQL schema
uv run python scripts.py info             # Runtime information
```

---

## Technical Specifications

### Runtime Integration Architecture
```python
# Core runtime class - main entry point
class CopilotRuntime:
    def __init__(self, settings: RuntimeSettings):
        self.settings = settings
        self.connectors: List[CopilotKitConnector] = []
        self.state_store = self._create_state_store()

    def add_connector(self, connector: CopilotKitConnector):
        """Add CopilotKitRemoteEndpoint or other connectors."""
        self.connectors.append(connector)

    def mount_to_fastapi(self, app: FastAPI, path: str = "/api/copilotkit"):
        """Mount runtime GraphQL endpoint to existing FastAPI app."""
        pass

# Connector interface bridging to CopilotKitRemoteEndpoint
class CopilotKitConnector(ABC):
    @abstractmethod
    async def list_agents(self) -> List[AgentDescriptor]:
        """Return available agents from this connector."""
        pass

    @abstractmethod
    async def execute_run(
        self,
        input_data: GenerateCopilotResponseInput,
        context: RequestContext
    ) -> AsyncIterator[RuntimeEvent]:
        """Execute agent run through CopilotKit connector."""
        pass

# Bridge to existing CopilotKit Python SDK
class CopilotKitRemoteConnector(CopilotKitConnector):
    def __init__(self, remote_endpoint: CopilotKitRemoteEndpoint):
        self.remote_endpoint = remote_endpoint

    async def list_agents(self) -> List[AgentDescriptor]:
        """Discover agents from CopilotKitRemoteEndpoint."""
        pass
```

### Example Usage Patterns

#### Basic Runtime Setup with CopilotKit Integration
```python
from fastapi import FastAPI
from copilotkit import CopilotKitRemoteEndpoint
from copilotkit.runtime_py import CopilotRuntime, CopilotKitRemoteConnector

# Create FastAPI app
app = FastAPI()

# Setup CopilotKit remote endpoint (existing pattern)
copilotkit_endpoint = CopilotKitRemoteEndpoint()
# Register your LangGraph agents using existing decorators
# @copilotkit_endpoint.add_langraph_agent(...)

# Create runtime and add connector
runtime = CopilotRuntime()
connector = CopilotKitRemoteConnector(copilotkit_endpoint)
runtime.add_connector(connector)

# Mount to existing FastAPI app
runtime.mount_to_fastapi(app, path="/api/copilotkit")

# Your existing FastAPI routes continue to work
@app.get("/health")
async def health():
    return {"status": "ok"}
```

#### Agent Registration Using Existing CopilotKit Patterns
```python
# agents/demo_agent.py - follows existing CopilotKit patterns
from langchain_core.messages import HumanMessage
from copilotkit import CopilotKitRemoteEndpoint
from copilotkit.langchain import copilotkit_runtime_action

# Use existing CopilotKit decorator patterns
@copilotkit_runtime_action(
    name="research_topic",
    description="Research a topic and provide insights"
)
async def research_topic(topic: str) -> str:
    """Research implementation using existing patterns"""
    return f"Research results for: {topic}"

# Register with endpoint (existing CopilotKit pattern)
def create_research_agent():
    endpoint = CopilotKitRemoteEndpoint()
    # Add your LangGraph or other agents
    return endpoint
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
- Code coverage meets minimum threshold (85% for core, 70% for connectors)
- Runtime can be instantiated and mounted to FastAPI
- Performance benchmarks meet requirements
- Security scan passes without high-severity issues
- Implementation reference document (`_docs/porting-implementation.md`) updated with completed functionality, test coverage, known limitations, and progress metrics
- Peer review approval from CopilotKit maintainers

### Production Readiness Checklist
- [ ] Complete GraphQL schema parity with TypeScript implementation
- [ ] CopilotRuntime class functional as pluggable FastAPI component
- [ ] Standalone FastAPI server example working for testing
- [ ] All message types and meta-events properly implemented
- [ ] Streaming functionality working with abort support
- [ ] CopilotKitRemoteEndpoint integration fully functional
- [ ] State persistence working across process restarts
- [ ] Comprehensive error handling and logging
- [ ] Security review passed
- [ ] Performance testing completed
- [ ] Documentation complete and accurate
- [ ] Implementation reference document (`_docs/porting-implementation.md`) maintained with current status, metrics, and technical details
- [ ] CI/CD pipeline operational
- [ ] Package published and installable

### Long-term Success Indicators
- Community adoption and contributor engagement
- Performance parity or improvement over TypeScript implementation
- Successful integration stories from external developers
- Minimal production issues and fast resolution times
- Clear migration path for existing TypeScript users

## Documentation Strategy

### Implementation Reference Document
To ensure accurate tracking of development progress and maintain a reliable reference for what has been implemented, a comprehensive implementation reference document is maintained at `_docs/porting-implementation.md`.

**Purpose:**
- Track actual implementation status vs. planned features
- Document working functionality with source file references
- Record test coverage metrics and validation results
- Identify technical debt and known limitations
- Provide onboarding reference for new developers

**Content Requirements:**
- **Implementation Status**: Current phase completion with detailed breakdowns
- **Functional Components**: Classes, methods, and features actually working
- **Source Code References**: File paths and function names (no line numbers for maintainability)
- **Test Coverage**: Metrics for implemented components with gap analysis
- **Technical Debt**: Known limitations, warnings, and future improvements needed
- **Validation Results**: Acceptance criteria status and manual testing results

**Maintenance Protocol:**
- **Phase Completion**: Document must be updated before phase sign-off
- **Major Changes**: Update when significant functionality is added or modified
- **Quarterly Review**: Comprehensive review and cleanup every quarter
- **Version Control**: Document changes tracked alongside code changes

**Quality Standards:**
- All claims must be verifiable through code inspection or testing
- References must use stable identifiers (class/function names, not line numbers)
- Metrics must be current and automatically updatable where possible
- Technical debt must be prioritized and linked to future phase planning
