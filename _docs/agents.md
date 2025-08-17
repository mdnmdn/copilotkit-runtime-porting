# CopilotRuntime Python Port - Project Overview

## Project Goals

The CopilotRuntime Python Port delivers a production-ready Python implementation of CopilotKit's runtime system, enabling seamless integration with Python-based AI agent frameworks while maintaining complete compatibility with existing React applications.

### Primary Objectives
- **Framework Bridge**: Connect React frontends to Python AI frameworks (LangGraph, CrewAI, etc.)
- **GraphQL Compatibility**: Maintain 100% API compatibility with TypeScript CopilotRuntime
- **Agent Orchestration**: Support multi-agent workflows with proper state management
- **Streaming Support**: Real-time message and event delivery to frontends
- **Production Ready**: Enterprise-grade reliability, security, and observability

### Success Criteria
- Existing CopilotKit React applications work without frontend changes
- Python developers can easily create and deploy AI agents
- Performance meets or exceeds TypeScript implementation
- Comprehensive documentation and examples accelerate adoption

## Project Structure

```
copilotkit-runtime-porting/
├── _docs/                          # Project documentation
│   ├── agents.md                   # This file - project overview and directives
│   └── porting-plan.md            # Detailed phased implementation plan
├── python/                         # Python implementation workspace
│   ├── copilotkit/                 # Main package directory
│   │   └── runtime_py/             # Core CopilotRuntime Python port
│   │       ├── app/                # FastAPI application and server setup
│   │       ├── graphql/            # GraphQL schema, types, and resolvers
│   │       ├── core/               # Runtime orchestration and lifecycle
│   │       ├── providers/          # AI framework integrations (LangGraph, CrewAI)
│   │       └── storage/            # State persistence backends
│   ├── examples/                   # Sample agents and demonstration code
│   │   ├── langgraph_demo/         # LangGraph integration examples
│   │   ├── crewai_demo/            # CrewAI integration examples
│   │   └── custom_agents/          # Custom agent implementations
│   └── tests/                      # Comprehensive Python test suites
│       ├── unit/                   # Unit tests for core components
│       ├── integration/            # Provider integration tests
│       └── e2e/                    # End-to-end workflow tests
├── sample-frontend/                # React SPA for testing and demonstration
│   ├── src/                        # React application source
│   ├── public/                     # Static assets
│   └── package.json               # Frontend dependencies and scripts
├── reference-copilotkit-runtime/   # Node.js reference implementation
│   ├── src/                        # Simple CopilotKit runtime example
│   ├── agents/                     # Sample TypeScript agents
│   └── package.json               # Node.js dependencies
├── externals/                      # External repository references (git submodules)
│   └── copilotkit/                 # Official CopilotKit repository clone
│       ├── sdk-python/             # Existing Python SDK and LangGraph connector
│       │   └── copilotkit/         # Reference implementation patterns
│       └── CopilotKit/             # Main CopilotKit monorepo
│           ├── packages/runtime/   # TypeScript runtime (our porting source)
│           └── packages/runtime-client-gql/  # GraphQL client patterns
└── tools/                          # Development utilities and scripts
    ├── scripts/                    # Build and deployment scripts
    └── docker/                     # Container configurations
```

### Component Descriptions

#### Core Implementation (`python/`)
- **`copilotkit/runtime_py/`**: The main Python port delivering GraphQL API compatibility with TypeScript CopilotRuntime
- **`examples/`**: Practical demonstrations of agent implementations across different frameworks
- **`tests/`**: Multi-layered testing ensuring reliability and compatibility

#### Testing and Validation
- **`sample-frontend/`**: React SPA using `@copilotkit/runtime-client-gql` to validate frontend compatibility
- **`reference-copilotkit-runtime/`**: Minimal Node.js backend for behavioral comparison and regression testing

#### External References (`externals/`)
- **`copilotkit/sdk-python/`**: Existing Python SDK patterns and LangGraph integration approaches
- **`copilotkit/CopilotKit/packages/runtime/`**: Original TypeScript implementation for API contract reference
- **`copilotkit/CopilotKit/packages/runtime-client-gql/`**: Client-side GraphQL patterns and expectations

#### Development Support
- **`_docs/`**: Comprehensive project documentation and implementation guidance
- **`tools/`**: Build automation, deployment scripts, and development utilities

## Architecture Principles

### Core Design Tenets
1. **API-First**: GraphQL schema defines all interfaces and contracts
2. **Provider Pattern**: Clean abstraction for multiple AI frameworks
3. **Event-Driven**: Asynchronous message and state event propagation
4. **Pluggable Storage**: Configurable persistence backends (memory, Redis, PostgreSQL)
5. **Security-Minded**: Input validation, credential protection, content filtering
6. **Observable**: Comprehensive logging, metrics, and distributed tracing

### Compatibility Requirements
- **GraphQL Contract**: Identical schema, types, and operation semantics as TypeScript runtime
- **Message Format**: Exact message union types and meta-event structures
- **Client Integration**: Zero changes required for existing `@copilotkit/runtime-client-gql` usage
- **Streaming Protocol**: Server-Sent Events with multipart GraphQL responses
- **Error Handling**: Consistent error codes and response formats

## Agent Development Framework

### Provider Interface
All AI frameworks integrate through a standardized provider interface:

```python
class AgentProvider(ABC):
    async def list_agents() -> List[AgentDescriptor]
    async def load_state(thread_id: str, agent_name: str) -> AgentState
    async def execute_run(input: Input, context: Context) -> AsyncIterator[RuntimeEvent]
    async def save_state(thread_id: str, agent_name: str, state: AgentState) -> None
```

### Supported Frameworks
- **LangGraph** (Primary): Full integration with state management and interrupts
- **CrewAI** (Secondary): Multi-agent crew orchestration support
- **Extensible**: Provider interface supports additional frameworks

### Agent Lifecycle
1. **Discovery**: Agents registered and discoverable via GraphQL `availableAgents` query
2. **Selection**: Frontend selects agent for conversation thread
3. **Execution**: Runtime orchestrates agent execution with proper context
4. **State Management**: Thread-scoped state persistence across conversations
5. **Event Streaming**: Real-time message and meta-event delivery to frontend

## Development Guidelines

### Code Quality Standards
- **Type Safety**: Full type annotations using Python 3.8+ type hints
- **Testing**: Minimum 85% coverage for core runtime, 70% for providers
- **Linting**: Enforced via `ruff` and `black` with CI validation
- **Documentation**: Comprehensive docstrings and API documentation

### Package Management
- **Tool**: Use `uv` for all dependency management and virtual environments
- **Structure**: `pyproject.toml` with optional extras for different providers
- **Versioning**: Semantic versioning aligned with CopilotKit releases

### Security Requirements
- **Input Validation**: All GraphQL inputs validated against schema and business rules
- **Credential Management**: Secure API key handling with no logging exposure
- **Content Filtering**: Configurable guardrails for inappropriate content
- **Rate Limiting**: Request throttling and resource protection

### Performance Targets
- **Response Time**: < 100ms for queries, < 500ms for mutation initiation
- **Concurrency**: Support 1000+ concurrent streaming connections
- **Memory Efficiency**: Optimized for long-running conversation threads
- **State Performance**: Sub-50ms state load/save operations

## Agent Development Directives

### Framework Integration Rules
1. **Provider Isolation**: Each framework provider operates independently
2. **Event Translation**: Map framework events to CopilotKit message/meta-event types
3. **State Compatibility**: Integrate with framework-native state management
4. **Tool Bridge**: Expose framework tools through CopilotKit action system
5. **Error Normalization**: Convert framework errors to CopilotKit error codes

### Message Handling Patterns
- **Text Messages**: Direct LLM responses and agent communications
- **Action Messages**: Tool/function execution requests and responses  
- **State Messages**: Agent state transitions and node execution updates
- **Meta Events**: Framework-specific events (interrupts, errors, etc.)

### State Management Strategy
- **Thread Scoped**: State isolated by conversation thread ID
- **Agent Scoped**: Each agent maintains independent state within thread
- **Persistent**: State survives process restarts via pluggable storage
- **Atomic**: State operations use transactional semantics where possible

## Development Workflow

### Environment Setup
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup project
git clone <repository>
cd copilotkit-runtime-porting

# Initialize git submodules for external references
git submodule update --init --recursive

# Setup Python runtime environment
cd python/
uv sync --all-extras

# Setup sample frontend (React SPA)
cd ../sample-frontend/
npm install

# Setup reference Node.js runtime
cd ../reference-copilotkit-runtime/
npm install

# Start development servers
cd ../python/
uv run dev                          # Python runtime on :8000
cd ../sample-frontend/
npm run dev                         # React frontend on :3000
cd ../reference-copilotkit-runtime/
npm run dev                         # Node.js reference on :8001
```

### Testing Strategy
- **Unit Tests** (`python/tests/unit/`): Core runtime logic and conversion utilities
- **Integration Tests** (`python/tests/integration/`): Provider implementations with real frameworks
- **End-to-End Tests** (`python/tests/e2e/`): Full GraphQL operations with sample frontend
- **Compatibility Tests**: Python runtime vs Node.js reference runtime behavioral comparison
- **Frontend Validation**: Sample React SPA testing actual client integration patterns
- **Performance Tests**: Load testing and resource utilization benchmarks

### Quality Gates
Each development phase requires:
- All tests passing with coverage requirements met
- Linting and type checking without errors
- Security scan passing without high-severity issues
- Performance benchmarks meeting targets
- Peer review approval from project maintainers

## Configuration Management

### Runtime Configuration
```bash
# Python runtime configuration (python/.env)
COPILOTKIT_HOST=0.0.0.0
COPILOTKIT_PORT=8000
COPILOTKIT_GRAPHQL_PATH=/api/copilotkit
COPILOTKIT_ENABLED_PROVIDERS=langgraph,crewai
COPILOTKIT_STATE_STORE_BACKEND=redis
COPILOTKIT_REDIS_URL=redis://localhost:6379

# Sample frontend configuration (sample-frontend/.env)
REACT_APP_COPILOTKIT_RUNTIME_URL=http://localhost:8000/api/copilotkit

# Reference backend configuration (reference-copilotkit-runtime/.env)
PORT=8001
COPILOTKIT_RUNTIME_PORT=8001
```

### Provider Configuration
- **LangGraph**: Graph definitions, checkpointing, tool registrations
- **CrewAI**: Crew definitions, agent configurations, task orchestration
- **Extensible**: Provider-specific configuration sections

### Deployment Options
- **Development**: Multi-service local development with hot reload
- **Standalone**: Direct FastAPI deployment with uvicorn (`python/`)
- **Containerized**: Docker compose orchestrating all services (`tools/docker/`)
- **Cloud**: Individual service deployment to cloud platforms
- **Comparison Testing**: Side-by-side Python vs Node.js runtime validation

## Documentation Requirements

### Developer Documentation
- **API Reference**: Complete GraphQL schema documentation
- **Integration Guides**: Framework-specific setup and configuration
- **Examples**: Working code samples for common use cases
- **Migration Guide**: Porting from TypeScript to Python runtime

### Operations Documentation
- **Deployment Guide**: Production deployment patterns and best practices
- **Monitoring**: Observability setup and key metrics to track
- **Troubleshooting**: Common issues and resolution procedures
- **Security**: Security considerations and hardening recommendations

## References and Resources

### Implementation References
- **Porting Plan**: `_docs/porting-plan.md` - Detailed technical implementation roadmap
- **TypeScript Runtime**: `externals/copilotkit/CopilotKit/packages/runtime/` - Original implementation patterns and API contracts
- **GraphQL Client**: `externals/copilotkit/CopilotKit/packages/runtime-client-gql/` - Frontend integration patterns and expectations
- **Python SDK**: `externals/copilotkit/sdk-python/` - Existing LangGraph connector and integration patterns
- **Sample Frontend**: `sample-frontend/` - React SPA for validating Python runtime compatibility
- **Reference Backend**: `reference-copilotkit-runtime/` - Node.js runtime for behavioral comparison and regression testing
- **Agent Examples**: `python/examples/` - Practical demonstrations across different AI frameworks

### External Dependencies
- **FastAPI**: Modern web framework for building APIs with Python 3.8+
- **Strawberry GraphQL**: Python GraphQL library with type annotations
- **LangGraph**: State-based agent orchestration framework
- **CrewAI**: Multi-agent collaboration framework
- **Redis/PostgreSQL**: Persistent state storage backends

### Community and Support
- **Issues**: GitHub issues for bug reports and feature requests
- **Discussions**: Community discussions for implementation questions
- **Contributing**: See contribution guidelines for development process
- **Releases**: Semantic versioning with comprehensive changelog