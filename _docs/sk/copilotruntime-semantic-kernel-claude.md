# CopilotRuntime .NET Core with Semantic Kernel Specification

## Overview

This document provides a comprehensive specification for implementing CopilotRuntime in .NET Core using Microsoft's Semantic Kernel agent framework. CopilotRuntime serves as the backend component of CopilotKit, acting as a GraphQL-based proxy between frontend React components and AI agent frameworks. This .NET implementation leverages Semantic Kernel's powerful agent orchestration capabilities to provide enterprise-grade AI integration.

## Architecture Overview

```
┌─────────────────────┐    GraphQL     ┌─────────────────────┐   Semantic     ┌─────────────────────┐
│                     │   over HTTP    │                     │    Kernel      │                     │
│   Frontend React    │ ──────────────▶│   CopilotRuntime    │ ──────────────▶│  Semantic Kernel    │
│   Components        │                │     (.NET Core)     │   Agents       │   Agent Framework   │
│                     │                │                     │                │                     │
└─────────────────────┘                └─────────────────────┘                └─────────────────────┘
```

### Key Components

1. **ASP.NET Core GraphQL API**: Exposes `generateCopilotResponse` mutation using HotChocolate
2. **Semantic Kernel Runtime Engine**: Orchestrates agent interactions and LLM conversations
3. **SignalR Event Streaming**: Real-time bidirectional communication for streaming responses
4. **Agent Service Provider**: Interface to Semantic Kernel agents (ChatCompletion, OpenAI Assistant, etc.)
5. **Action System**: Execute frontend and server-side actions through Semantic Kernel plugins
6. **State Management**: Thread and conversation state using Entity Framework Core

The CopilotRuntime acts as a **GraphQL proxy** that:
- Exposes a GraphQL endpoint for frontend React components
- Translates GraphQL requests to Semantic Kernel agent invocations
- Manages real-time streaming of AI responses through SignalR
- Handles action execution via Semantic Kernel plugins
- Provides observability and error handling

## .NET Core Technology Stack

### Core Framework Components
- **ASP.NET Core 8.0+**: Web framework and dependency injection
- **HotChocolate GraphQL**: GraphQL server implementation
- **SignalR**: Real-time communication for streaming
- **Entity Framework Core**: Data persistence and state management
- **Microsoft.SemanticKernel**: AI orchestration and agent framework
- **System.Text.Json**: JSON serialization with source generators

### Semantic Kernel Integration
- **Microsoft.SemanticKernel.Agents**: Core agent framework
- **Microsoft.SemanticKernel.Connectors.OpenAI**: OpenAI integration
- **Microsoft.SemanticKernel.Connectors.AzureOpenAI**: Azure OpenAI integration
- **Microsoft.SemanticKernel.Plugins**: Plugin system for actions

## GraphQL Schema Implementation

### Core Operations (HotChocolate)

#### Queries

```csharp
[Query]
public class CopilotQuery
{
    public string Hello() => "Hello World";

    public async Task<AgentsResponse> GetAvailableAgents(
        [Service] IAgentDiscoveryService agentService)
    {
        var agents = await agentService.DiscoverAvailableAgentsAsync();
        return new AgentsResponse { Agents = agents };
    }

    public async Task<LoadAgentStateResponse> LoadAgentState(
        LoadAgentStateInput input,
        [Service] IStateManager stateManager)
    {
        return await stateManager.LoadAgentStateAsync(input.ThreadId, input.AgentName);
    }
}
```

#### Mutations

```csharp
[Mutation]
public class CopilotMutation
{
    public async Task<CopilotResponse> GenerateCopilotResponse(
        GenerateCopilotResponseInput data,
        Optional<JsonDocument> properties,
        [Service] ICopilotRuntime runtime,
        CancellationToken cancellationToken)
    {
        var context = new CopilotContext 
        {
            Properties = properties.HasValue ? properties.Value : null,
            CancellationToken = cancellationToken
        };

        return await runtime.ProcessRequestAsync(data, context);
    }
}
```

#### Subscriptions (SignalR Integration)

```csharp
[Subscription]
public class CopilotSubscription
{
    [Subscribe]
    public async IAsyncEnumerable<CopilotStreamEvent> StreamCopilotResponse(
        GenerateCopilotResponseInput data,
        [Service] ICopilotRuntime runtime,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        await foreach (var streamEvent in runtime.StreamProcessRequestAsync(data, cancellationToken))
        {
            yield return streamEvent;
        }
    }
}
```

## Data Models and Types

### Core Input Types

```csharp
public record GenerateCopilotResponseInput
{
    public required GenerateCopilotResponseMetadataInput Metadata { get; init; }
    public string? ThreadId { get; init; }
    public string? RunId { get; init; }
    public required IReadOnlyList<MessageInput> Messages { get; init; }
    public required FrontendInput Frontend { get; init; }
    public CloudInput? Cloud { get; init; }
    public ForwardedParametersInput? ForwardedParameters { get; init; }
    public AgentSessionInput? AgentSession { get; init; }
    public AgentStateInput? AgentState { get; init; }
    public IReadOnlyList<AgentStateInput>? AgentStates { get; init; }
    public JsonDocument? Extensions { get; init; }
    public IReadOnlyList<MetaEventInput>? MetaEvents { get; init; }
}

public record MessageInput
{
    public required string Id { get; init; }
    public required DateTimeOffset CreatedAt { get; init; }
    
    // Union type implementation using discriminated unions
    public TextMessageInput? TextMessage { get; init; }
    public ActionExecutionMessageInput? ActionExecutionMessage { get; init; }
    public ResultMessageInput? ResultMessage { get; init; }
    public AgentStateMessageInput? AgentStateMessage { get; init; }
    public ImageMessageInput? ImageMessage { get; init; }
}

public record TextMessageInput
{
    public required string Content { get; init; }
    public string? ParentMessageId { get; init; }
    public required MessageRole Role { get; init; }
}

public record ActionInput
{
    public required string Name { get; init; }
    public required string Description { get; init; }
    public required string JsonSchema { get; init; }
    public ActionInputAvailability? Available { get; init; }
}

public enum MessageRole
{
    User,
    Assistant,
    System,
    Tool,
    Developer
}

public enum CopilotRequestType
{
    Chat,
    Task,
    TextareaCompletion,
    TextareaPopover,
    Suggestion
}
```

### Output Types

```csharp
public record CopilotResponse
{
    public required string ThreadId { get; init; }
    public required string RunId { get; init; }
    public required ResponseStatusUnion Status { get; init; }
    public required IReadOnlyList<BaseMessageOutput> Messages { get; init; }
    public JsonDocument? Extensions { get; init; }
    public IReadOnlyList<BaseMetaEvent>? MetaEvents { get; init; }
}

[UnionType]
public abstract record BaseMessageOutput
{
    public required string Id { get; init; }
    public required DateTimeOffset CreatedAt { get; init; }
    public required MessageStatusUnion Status { get; init; }
}

public record TextMessageOutput : BaseMessageOutput
{
    public required MessageRole Role { get; init; }
    public required object Content { get; init; } // string or string[] for streaming
    public string? ParentMessageId { get; init; }
}

public record ActionExecutionMessageOutput : BaseMessageOutput
{
    public required string Name { get; init; }
    public required object Arguments { get; init; } // string or string[] for streaming
    public string? ParentMessageId { get; init; }
}

[UnionType]
public abstract record ResponseStatusUnion;

public record SuccessResponseStatus : ResponseStatusUnion
{
    public required string Code { get; init; }
}

public record FailedResponseStatus : ResponseStatusUnion
{
    public required string Code { get; init; }
    public required string Reason { get; init; }
    public string? Details { get; init; }
}
```

## Semantic Kernel Integration Architecture

### Agent Service Provider

```csharp
public interface IAgentServiceProvider
{
    Task<IAgent> CreateChatCompletionAgentAsync(string model, AgentConfiguration config);
    Task<IAgent> CreateOpenAIAssistantAgentAsync(string assistantId, AgentConfiguration config);
    Task<IAgent> GetAgentAsync(string agentName);
    IAsyncEnumerable<RuntimeEvent> ProcessAgentRequestAsync(
        IAgent agent, 
        AgentExecutionRequest request, 
        CancellationToken cancellationToken);
}

public class SemanticKernelAgentProvider : IAgentServiceProvider
{
    private readonly Kernel _kernel;
    private readonly ILogger<SemanticKernelAgentProvider> _logger;
    private readonly ConcurrentDictionary<string, IAgent> _agentCache = new();

    public SemanticKernelAgentProvider(Kernel kernel, ILogger<SemanticKernelAgentProvider> logger)
    {
        _kernel = kernel;
        _logger = logger;
    }

    public async Task<IAgent> CreateChatCompletionAgentAsync(string model, AgentConfiguration config)
    {
        var agentBuilder = new ChatCompletionAgent()
        {
            Instructions = config.SystemMessage,
            Name = config.Name,
            Description = config.Description,
            Kernel = _kernel
        };

        // Configure plugins (actions)
        foreach (var plugin in config.Plugins)
        {
            agentBuilder.Kernel.Plugins.Add(plugin);
        }

        return agentBuilder;
    }

    public async IAsyncEnumerable<RuntimeEvent> ProcessAgentRequestAsync(
        IAgent agent, 
        AgentExecutionRequest request,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var chatHistory = ConvertToChatHistory(request.Messages);
        var agentGroupChat = new AgentGroupChat();
        
        await foreach (var message in agentGroupChat.InvokeAsync(agent, chatHistory, cancellationToken))
        {
            yield return await ConvertToRuntimeEvent(message);
        }
    }

    private ChatHistory ConvertToChatHistory(IReadOnlyList<MessageInput> messages)
    {
        var chatHistory = new ChatHistory();
        
        foreach (var message in messages)
        {
            if (message.TextMessage != null)
            {
                var role = message.TextMessage.Role switch
                {
                    MessageRole.User => AuthorRole.User,
                    MessageRole.Assistant => AuthorRole.Assistant,
                    MessageRole.System => AuthorRole.System,
                    MessageRole.Tool => AuthorRole.Tool,
                    _ => AuthorRole.User
                };
                
                chatHistory.AddMessage(role, message.TextMessage.Content);
            }
        }
        
        return chatHistory;
    }
}
```

### Plugin System for Actions

```csharp
public class CopilotActionPlugin
{
    private readonly IActionExecutor _actionExecutor;
    private readonly ILogger<CopilotActionPlugin> _logger;

    public CopilotActionPlugin(IActionExecutor actionExecutor, ILogger<CopilotActionPlugin> logger)
    {
        _actionExecutor = actionExecutor;
        _logger = logger;
    }

    [KernelFunction, Description("Execute a frontend or server-side action")]
    public async Task<string> ExecuteAction(
        [Description("The name of the action to execute")] string actionName,
        [Description("JSON arguments for the action")] string arguments)
    {
        try
        {
            var result = await _actionExecutor.ExecuteAsync(actionName, arguments);
            return JsonSerializer.Serialize(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to execute action {ActionName}", actionName);
            return JsonSerializer.Serialize(new { error = ex.Message });
        }
    }
}

public interface IActionExecutor
{
    Task<object> ExecuteAsync(string actionName, string arguments);
    Task<IReadOnlyList<ActionDefinition>> GetAvailableActionsAsync();
}

public class ActionExecutor : IActionExecutor
{
    private readonly ConcurrentDictionary<string, Func<string, Task<object>>> _actions = new();
    private readonly IServiceProvider _serviceProvider;

    public ActionExecutor(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
        RegisterBuiltInActions();
    }

    public async Task<object> ExecuteAsync(string actionName, string arguments)
    {
        if (_actions.TryGetValue(actionName, out var actionHandler))
        {
            return await actionHandler(arguments);
        }
        
        throw new ActionNotFoundException($"Action '{actionName}' not found");
    }

    public void RegisterAction(string name, Func<string, Task<object>> handler)
    {
        _actions[name] = handler;
    }

    private void RegisterBuiltInActions()
    {
        // Register server-side actions
        RegisterAction("database_query", async args =>
        {
            // Implement database query logic
            return new { result = "Query executed" };
        });
        
        RegisterAction("send_email", async args =>
        {
            // Implement email sending logic
            return new { result = "Email sent" };
        });
    }
}
```

## Event Streaming System

### SignalR Hub Implementation

```csharp
[Authorize] // Optional: Add authentication
public class CopilotHub : Hub<ICopilotClient>
{
    private readonly ICopilotRuntime _runtime;
    private readonly ILogger<CopilotHub> _logger;

    public CopilotHub(ICopilotRuntime runtime, ILogger<CopilotHub> logger)
    {
        _runtime = runtime;
        _logger = logger;
    }

    public async Task JoinThread(string threadId)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, $"thread-{threadId}");
    }

    public async Task LeaveThread(string threadId)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"thread-{threadId}");
    }

    public async IAsyncEnumerable<RuntimeEvent> StreamResponse(
        GenerateCopilotResponseInput input,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        await foreach (var runtimeEvent in _runtime.StreamProcessRequestAsync(input, cancellationToken))
        {
            // Broadcast to thread group
            await Clients.Group($"thread-{input.ThreadId}").ReceiveRuntimeEvent(runtimeEvent);
            yield return runtimeEvent;
        }
    }
}

public interface ICopilotClient
{
    Task ReceiveRuntimeEvent(RuntimeEvent runtimeEvent);
    Task ReceiveError(string error);
}
```

### Runtime Event System

```csharp
public record RuntimeEvent
{
    public required RuntimeEventType Type { get; init; }
    public required DateTimeOffset Timestamp { get; init; }
    public string? MessageId { get; init; }
    public string? ParentMessageId { get; init; }
    public required JsonDocument Data { get; init; }
}

public enum RuntimeEventType
{
    TextMessageStart,
    TextMessageContent,
    TextMessageEnd,
    ActionExecutionStart,
    ActionExecutionArgs,
    ActionExecutionEnd,
    ActionExecutionResult,
    AgentStateMessage,
    MetaEvent
}

public class RuntimeEventSource
{
    private readonly Channel<RuntimeEvent> _eventChannel;
    private readonly ChannelWriter<RuntimeEvent> _writer;
    private readonly ChannelReader<RuntimeEvent> _reader;
    private readonly ILogger<RuntimeEventSource> _logger;

    public RuntimeEventSource(ILogger<RuntimeEventSource> logger)
    {
        var options = new BoundedChannelOptions(1000)
        {
            FullMode = BoundedChannelFullMode.Wait,
            SingleReader = false,
            SingleWriter = false
        };
        
        _eventChannel = Channel.CreateBounded<RuntimeEvent>(options);
        _writer = _eventChannel.Writer;
        _reader = _eventChannel.Reader;
        _logger = logger;
    }

    public async Task EmitAsync(RuntimeEvent runtimeEvent, CancellationToken cancellationToken = default)
    {
        try
        {
            await _writer.WriteAsync(runtimeEvent, cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to emit runtime event {EventType}", runtimeEvent.Type);
        }
    }

    public IAsyncEnumerable<RuntimeEvent> ReadAllAsync(CancellationToken cancellationToken = default)
    {
        return _reader.ReadAllAsync(cancellationToken);
    }

    public void Complete()
    {
        _writer.Complete();
    }
}
```

## Core Runtime Implementation

### CopilotRuntime Engine

```csharp
public interface ICopilotRuntime
{
    Task<CopilotResponse> ProcessRequestAsync(
        GenerateCopilotResponseInput input, 
        CopilotContext context);
    
    IAsyncEnumerable<RuntimeEvent> StreamProcessRequestAsync(
        GenerateCopilotResponseInput input,
        CancellationToken cancellationToken);
}

public class CopilotRuntime : ICopilotRuntime
{
    private readonly IAgentServiceProvider _agentProvider;
    private readonly IActionExecutor _actionExecutor;
    private readonly IStateManager _stateManager;
    private readonly ILogger<CopilotRuntime> _logger;
    private readonly RuntimeEventSource _eventSource;

    public CopilotRuntime(
        IAgentServiceProvider agentProvider,
        IActionExecutor actionExecutor,
        IStateManager stateManager,
        ILogger<CopilotRuntime> logger)
    {
        _agentProvider = agentProvider;
        _actionExecutor = actionExecutor;
        _stateManager = stateManager;
        _logger = logger;
        _eventSource = new RuntimeEventSource(logger);
    }

    public async Task<CopilotResponse> ProcessRequestAsync(
        GenerateCopilotResponseInput input, 
        CopilotContext context)
    {
        var threadId = input.ThreadId ?? Guid.NewGuid().ToString();
        var runId = input.RunId ?? Guid.NewGuid().ToString();
        
        try
        {
            // Handle guardrails if cloud config present
            if (input.Cloud?.Guardrails != null)
            {
                var guardrailResult = await ValidateGuardrails(input, context);
                if (guardrailResult.Status == "denied")
                {
                    return CreateGuardrailFailureResponse(threadId, runId, guardrailResult.Reason);
                }
            }

            // Determine processing mode
            if (input.AgentSession != null)
            {
                return await ProcessAgentRequestAsync(input, context, threadId, runId);
            }
            else
            {
                return await ProcessLLMRequestAsync(input, context, threadId, runId);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing copilot request for thread {ThreadId}", threadId);
            return CreateErrorResponse(threadId, runId, ex);
        }
    }

    public async IAsyncEnumerable<RuntimeEvent> StreamProcessRequestAsync(
        GenerateCopilotResponseInput input,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var threadId = input.ThreadId ?? Guid.NewGuid().ToString();
        var runId = input.RunId ?? Guid.NewGuid().ToString();

        // Start processing in background
        _ = Task.Run(async () =>
        {
            try
            {
                await ProcessRequestAsync(input, new CopilotContext 
                { 
                    CancellationToken = cancellationToken 
                });
            }
            finally
            {
                _eventSource.Complete();
            }
        }, cancellationToken);

        // Stream events as they occur
        await foreach (var runtimeEvent in _eventSource.ReadAllAsync(cancellationToken))
        {
            yield return runtimeEvent;
        }
    }

    private async Task<CopilotResponse> ProcessAgentRequestAsync(
        GenerateCopilotResponseInput input,
        CopilotContext context,
        string threadId,
        string runId)
    {
        var agentSession = input.AgentSession!;
        var agent = await _agentProvider.GetAgentAsync(agentSession.AgentName);
        
        var request = new AgentExecutionRequest
        {
            ThreadId = threadId,
            RunId = runId,
            Messages = input.Messages,
            Actions = input.Frontend.Actions,
            AgentName = agentSession.AgentName,
            NodeName = agentSession.NodeName
        };

        var messages = new List<BaseMessageOutput>();
        var metaEvents = new List<BaseMetaEvent>();

        await foreach (var runtimeEvent in _agentProvider.ProcessAgentRequestAsync(
            agent, request, context.CancellationToken))
        {
            await _eventSource.EmitAsync(runtimeEvent, context.CancellationToken);
            
            // Convert events to output messages
            var message = ConvertEventToMessage(runtimeEvent);
            if (message != null)
            {
                messages.Add(message);
            }
        }

        return new CopilotResponse
        {
            ThreadId = threadId,
            RunId = runId,
            Status = new SuccessResponseStatus { Code = "success" },
            Messages = messages,
            MetaEvents = metaEvents
        };
    }

    private BaseMessageOutput? ConvertEventToMessage(RuntimeEvent runtimeEvent)
    {
        return runtimeEvent.Type switch
        {
            RuntimeEventType.TextMessageContent => new TextMessageOutput
            {
                Id = runtimeEvent.MessageId ?? Guid.NewGuid().ToString(),
                CreatedAt = runtimeEvent.Timestamp,
                Status = new SuccessMessageStatus { Code = "success" },
                Role = MessageRole.Assistant,
                Content = runtimeEvent.Data.RootElement.GetProperty("content").GetString() ?? "",
                ParentMessageId = runtimeEvent.ParentMessageId
            },
            RuntimeEventType.ActionExecutionStart => new ActionExecutionMessageOutput
            {
                Id = runtimeEvent.MessageId ?? Guid.NewGuid().ToString(),
                CreatedAt = runtimeEvent.Timestamp,
                Status = new PendingMessageStatus { Code = "pending" },
                Name = runtimeEvent.Data.RootElement.GetProperty("actionName").GetString() ?? "",
                Arguments = "",
                ParentMessageId = runtimeEvent.ParentMessageId
            },
            _ => null
        };
    }
}
```

## State Management with Entity Framework Core

### Database Context

```csharp
public class CopilotDbContext : DbContext
{
    public CopilotDbContext(DbContextOptions<CopilotDbContext> options) : base(options) { }

    public DbSet<ThreadState> ThreadStates { get; set; } = null!;
    public DbSet<MessageRecord> Messages { get; set; } = null!;
    public DbSet<AgentState> AgentStates { get; set; } = null!;
    public DbSet<ActionExecution> ActionExecutions { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ThreadState>(entity =>
        {
            entity.HasKey(e => e.ThreadId);
            entity.Property(e => e.State).HasColumnType("jsonb"); // PostgreSQL JSON column
            entity.HasIndex(e => e.LastUpdated);
        });

        modelBuilder.Entity<MessageRecord>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => new { e.ThreadId, e.CreatedAt });
            entity.Property(e => e.Content).HasColumnType("jsonb");
        });

        modelBuilder.Entity<AgentState>(entity =>
        {
            entity.HasKey(e => new { e.ThreadId, e.AgentName });
            entity.Property(e => e.State).HasColumnType("jsonb");
        });
    }
}

public class ThreadState
{
    public required string ThreadId { get; set; }
    public required JsonDocument State { get; set; }
    public required DateTimeOffset LastUpdated { get; set; }
    public string? CurrentAgentName { get; set; }
    public string? CurrentNodeName { get; set; }
}

public class MessageRecord
{
    public required string Id { get; set; }
    public required string ThreadId { get; set; }
    public required DateTimeOffset CreatedAt { get; set; }
    public required MessageRole Role { get; set; }
    public required JsonDocument Content { get; set; }
    public string? ParentMessageId { get; set; }
}

public class AgentState
{
    public required string ThreadId { get; set; }
    public required string AgentName { get; set; }
    public required JsonDocument State { get; set; }
    public required DateTimeOffset LastUpdated { get; set; }
    public bool Active { get; set; }
    public bool Running { get; set; }
    public string? NodeName { get; set; }
    public string? RunId { get; set; }
}
```

### State Manager Service

```csharp
public interface IStateManager
{
    Task<LoadAgentStateResponse> LoadAgentStateAsync(string threadId, string agentName);
    Task SaveAgentStateAsync(string threadId, string agentName, JsonDocument state);
    Task<ThreadState?> GetThreadStateAsync(string threadId);
    Task SaveThreadStateAsync(ThreadState threadState);
    Task<IReadOnlyList<MessageRecord>> GetMessagesAsync(string threadId, int limit = 100);
    Task SaveMessageAsync(MessageRecord message);
}

public class EntityFrameworkStateManager : IStateManager
{
    private readonly CopilotDbContext _context;
    private readonly ILogger<EntityFrameworkStateManager> _logger;

    public EntityFrameworkStateManager(CopilotDbContext context, ILogger<EntityFrameworkStateManager> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<LoadAgentStateResponse> LoadAgentStateAsync(string threadId, string agentName)
    {
        var agentState = await _context.AgentStates
            .FirstOrDefaultAsync(a => a.ThreadId == threadId && a.AgentName == agentName);

        if (agentState == null)
        {
            return new LoadAgentStateResponse
            {
                State = JsonDocument.Parse("{}"),
                Active = false,
                Running = false
            };
        }

        return new LoadAgentStateResponse
        {
            State = agentState.State,
            Active = agentState.Active,
            Running = agentState.Running,
            NodeName = agentState.NodeName,
            RunId = agentState.RunId
        };
    }

    public async Task SaveAgentStateAsync(string threadId, string agentName, JsonDocument state)
    {
        var existingState = await _context.AgentStates
            .FirstOrDefaultAsync(a => a.ThreadId == threadId && a.AgentName == agentName);

        if (existingState != null)
        {
            existingState.State = state;
            existingState.LastUpdated = DateTimeOffset.UtcNow;
        }
        else
        {
            _context.AgentStates.Add(new AgentState
            {
                ThreadId = threadId,
                AgentName = agentName,
                State = state,
                LastUpdated = DateTimeOffset.UtcNow,
                Active = true,
                Running = false
            });
        }

        await _context.SaveChangesAsync();
    }

    public async Task<IReadOnlyList<MessageRecord>> GetMessagesAsync(string threadId, int limit = 100)
    {
        return await _context.Messages
            .Where(m => m.ThreadId == threadId)
            .OrderByDescending(m => m.CreatedAt)
            .Take(limit)
            .OrderBy(m => m.CreatedAt) // Re-order for chronological display
            .ToListAsync();
    }

    public async Task SaveMessageAsync(MessageRecord message)
    {
        _context.Messages.Add(message);
        await _context.SaveChangesAsync();
    }
}
```

## Error Handling System

### Custom Exception Types

```csharp
public enum CopilotKitErrorCode
{
    Unknown,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    AgentNotFound,
    ApiNotFound,
    RemoteEndpointNotFound,
    MissingPublicApiKeyError
}

public enum Severity
{
    Critical,
    Error,
    Warning,
    Info
}

public enum Visibility
{
    User,
    Developer,
    Internal
}

public abstract class CopilotKitException : Exception
{
    protected CopilotKitException(
        string message,
        CopilotKitErrorCode code,
        Severity severity,
        Visibility visibility,
        Exception? innerException = null) : base(message, innerException)
    {
        Code = code;
        Severity = severity;
        Visibility = visibility;
        Context = new Dictionary<string, object>();
    }

    public CopilotKitErrorCode Code { get; }
    public Severity Severity { get; }
    public Visibility Visibility { get; }
    public Dictionary<string, object> Context { get; }
}

public class CopilotKitLowLevelException : CopilotKitException
{
    public CopilotKitLowLevelException(
        Exception originalError,
        string? url = null,
        string? message = null,
        int? statusCode = null) 
        : base(
            message ?? $"Low-level error: {originalError.Message}",
            ClassifyHttpError(statusCode),
            Severity.Error,
            Visibility.Developer,
            originalError)
    {
        Url = url;
        StatusCode = statusCode;
        OriginalError = originalError;
    }

    public string? Url { get; }
    public int? StatusCode { get; }
    public Exception OriginalError { get; }

    private static CopilotKitErrorCode ClassifyHttpError(int? statusCode) => statusCode switch
    {
        401 => CopilotKitErrorCode.AuthenticationError,
        >= 400 and < 500 => CopilotKitErrorCode.ConfigurationError,
        >= 500 => CopilotKitErrorCode.NetworkError,
        _ => CopilotKitErrorCode.NetworkError
    };
}

public class AgentNotFoundException : CopilotKitException
{
    public AgentNotFoundException(string agentName, IReadOnlyList<string> availableAgents)
        : base(
            $"Agent '{agentName}' not found. Available agents: {string.Join(", ", availableAgents)}",
            CopilotKitErrorCode.AgentNotFound,
            Severity.Error,
            Visibility.User)
    {
        AgentName = agentName;
        AvailableAgents = availableAgents;
    }

    public string AgentName { get; }
    public IReadOnlyList<string> AvailableAgents { get; }
}
```

### Error Handling Middleware

```csharp
public class CopilotErrorHandlingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<CopilotErrorHandlingMiddleware> _logger;

    public CopilotErrorHandlingMiddleware(RequestDelegate next, ILogger<CopilotErrorHandlingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (CopilotKitException ex)
        {
            await HandleCopilotKitExceptionAsync(context, ex);
        }
        catch (Exception ex)
        {
            await HandleUnknownExceptionAsync(context, ex);
        }
    }

    private async Task HandleCopilotKitExceptionAsync(HttpContext context, CopilotKitException ex)
    {
        _logger.LogError(ex, "CopilotKit error: {Code} - {Message}", ex.Code, ex.Message);

        var response = new
        {
            error = new
            {
                code = ex.Code.ToString(),
                message = ex.Visibility == Visibility.User ? ex.Message : "An error occurred",
                severity = ex.Severity.ToString(),
                visibility = ex.Visibility.ToString(),
                context = ex.Context
            }
        };

        context.Response.StatusCode = ex.Code switch
        {
            CopilotKitErrorCode.AuthenticationError => 401,
            CopilotKitErrorCode.AgentNotFound => 404,
            CopilotKitErrorCode.ConfigurationError => 400,
            _ => 500
        };

        context.Response.ContentType = "application/json";
        await context.Response.WriteAsync(JsonSerializer.Serialize(response));
    }

    private async Task HandleUnknownExceptionAsync(HttpContext context, Exception ex)
    {
        _logger.LogError(ex, "Unhandled exception");

        var response = new
        {
            error = new
            {
                code = CopilotKitErrorCode.Unknown.ToString(),
                message = "An unexpected error occurred",
                severity = Severity.Error.ToString()
            }
        };

        context.Response.StatusCode = 500;
        context.Response.ContentType = "application/json";
        await context.Response.WriteAsync(JsonSerializer.Serialize(response));
    }
}
```

## Application Startup and Configuration

### Program.cs

```csharp
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;
using Microsoft.SemanticKernel;
using CopilotRuntime.GraphQL;
using CopilotRuntime.Services;
using CopilotRuntime.Hubs;
using CopilotRuntime.Data;
using CopilotRuntime.Middleware;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddDbContext<CopilotDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// Add Semantic Kernel
builder.Services.AddScoped<Kernel>(serviceProvider =>
{
    var kernelBuilder = Kernel.CreateBuilder();
    
    // Add OpenAI connector
    var openAiApiKey = builder.Configuration["OpenAI:ApiKey"] ?? 
        throw new InvalidOperationException("OpenAI API key not configured");
    kernelBuilder.AddOpenAIChatCompletion("gpt-4", openAiApiKey);
    
    // Add Azure OpenAI connector if configured
    var azureEndpoint = builder.Configuration["AzureOpenAI:Endpoint"];
    if (!string.IsNullOrEmpty(azureEndpoint))
    {
        kernelBuilder.AddAzureOpenAIChatCompletion(
            builder.Configuration["AzureOpenAI:DeploymentName"]!,
            azureEndpoint,
            builder.Configuration["AzureOpenAI:ApiKey"]!);
    }
    
    return kernelBuilder.Build();
});

// Add CopilotRuntime services
builder.Services.AddScoped<ICopilotRuntime, CopilotRuntime>();
builder.Services.AddScoped<IAgentServiceProvider, SemanticKernelAgentProvider>();
builder.Services.AddScoped<IActionExecutor, ActionExecutor>();
builder.Services.AddScoped<IStateManager, EntityFrameworkStateManager>();
builder.Services.AddScoped<IAgentDiscoveryService, AgentDiscoveryService>();

// Add GraphQL
builder.Services
    .AddGraphQLServer()
    .AddQueryType<CopilotQuery>()
    .AddMutationType<CopilotMutation>()
    .AddSubscriptionType<CopilotSubscription>()
    .AddType<GenerateCopilotResponseInput>()
    .AddType<CopilotResponse>()
    .AddProjections()
    .AddFiltering()
    .AddSorting();

// Add SignalR
builder.Services.AddSignalR();

// Add CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy
            .AllowAnyOrigin()
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

// Add authentication if needed
builder.Services.AddAuthentication()
    .AddJwtBearer(options =>
    {
        // Configure JWT authentication
        options.Authority = builder.Configuration["Authentication:Authority"];
        options.Audience = builder.Configuration["Authentication:Audience"];
    });

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

// Add custom error handling middleware
app.UseMiddleware<CopilotErrorHandlingMiddleware>();

// Configure GraphQL
app.MapGraphQL("/graphql");

// Configure SignalR
app.MapHub<CopilotHub>("/copilothub");

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTimeOffset.UtcNow }));

// Run database migrations
using (var scope = app.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<CopilotDbContext>();
    await context.Database.MigrateAsync();
}

await app.RunAsync();
```

### Configuration (appsettings.json)

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Database=copilotruntime;Username=postgres;Password=password"
  },
  "OpenAI": {
    "ApiKey": "",
    "Model": "gpt-4"
  },
  "AzureOpenAI": {
    "Endpoint": "",
    "ApiKey": "",
    "DeploymentName": "gpt-4"
  },
  "Authentication": {
    "Authority": "https://your-identity-provider",
    "Audience": "copilot-runtime-api"
  },
  "CopilotCloud": {
    "GuardrailsEndpoint": "https://api.copilotkit.ai/guardrails/validate",
    "PublicApiKey": ""
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning",
      "Microsoft.SemanticKernel": "Information"
    }
  },
  "AllowedHosts": "*"
}
```

## Semantic Kernel Agent Examples

### Chat Completion Agent

```csharp
public class ChatCompletionAgentFactory
{
    private readonly Kernel _kernel;
    
    public ChatCompletionAgentFactory(Kernel kernel)
    {
        _kernel = kernel;
    }
    
    public ChatCompletionAgent CreateCustomerServiceAgent()
    {
        return new ChatCompletionAgent
        {
            Instructions = """
                You are a helpful customer service assistant. 
                You can help users with their questions and execute actions on their behalf.
                Always be polite and professional.
                """,
            Name = "CustomerService",
            Description = "A customer service agent that can help with inquiries and actions",
            Kernel = _kernel
        };
    }
    
    public ChatCompletionAgent CreateDataAnalystAgent()
    {
        var kernel = _kernel.Clone();
        
        // Add specialized plugins for data analysis
        kernel.Plugins.AddFromType<DataAnalysisPlugin>();
        kernel.Plugins.AddFromType<ChartGenerationPlugin>();
        
        return new ChatCompletionAgent
        {
            Instructions = """
                You are a data analyst expert. You can analyze data, create visualizations,
                and provide insights. Use the available tools to query databases and 
                generate charts when appropriate.
                """,
            Name = "DataAnalyst",
            Description = "A specialized agent for data analysis and visualization",
            Kernel = kernel
        };
    }
}

public class DataAnalysisPlugin
{
    private readonly IDbService _dbService;
    
    public DataAnalysisPlugin(IDbService dbService)
    {
        _dbService = dbService;
    }
    
    [KernelFunction, Description("Query the database for analytics")]
    public async Task<string> QueryDatabase(
        [Description("SQL query to execute")] string query)
    {
        var results = await _dbService.ExecuteQueryAsync(query);
        return JsonSerializer.Serialize(results);
    }
    
    [KernelFunction, Description("Generate statistical summary of data")]
    public Task<string> GenerateStatistics(
        [Description("JSON data to analyze")] string data)
    {
        // Implement statistical analysis
        return Task.FromResult("Statistics generated");
    }
}
```

### OpenAI Assistant Agent

```csharp
public class OpenAIAssistantAgentFactory
{
    private readonly IOpenAIAssistantService _assistantService;
    private readonly Kernel _kernel;
    
    public OpenAIAssistantAgentFactory(IOpenAIAssistantService assistantService, Kernel kernel)
    {
        _assistantService = assistantService;
        _kernel = kernel;
    }
    
    public async Task<OpenAIAssistantAgent> CreateCodeAnalysisAssistantAsync()
    {
        // Create or retrieve OpenAI Assistant
        var assistantId = await _assistantService.CreateAssistantAsync(new AssistantCreateRequest
        {
            Name = "Code Analyzer",
            Instructions = "You are a code analysis expert. You can review code, suggest improvements, and identify potential issues.",
            Model = "gpt-4",
            Tools = new[]
            {
                new AssistantTool { Type = "code_interpreter" },
                new AssistantTool { Type = "retrieval" }
            }
        });
        
        return new OpenAIAssistantAgent(kernel: _kernel, clientProvider: _assistantService, assistantId: assistantId)
        {
            Name = "CodeAnalyzer",
            Description = "An assistant specialized in code analysis and review"
        };
    }
}
```

## Advanced Features

### Cloud Integration and Guardrails

```csharp
public interface IGuardrailsService
{
    Task<GuardrailsResult> ValidateAsync(GuardrailsValidationRequest request);
}

public class CopilotCloudGuardrailsService : IGuardrailsService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<CopilotCloudGuardrailsService> _logger;

    public CopilotCloudGuardrailsService(
        HttpClient httpClient, 
        IConfiguration configuration,
        ILogger<CopilotCloudGuardrailsService> logger)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _logger = logger;
    }

    public async Task<GuardrailsResult> ValidateAsync(GuardrailsValidationRequest request)
    {
        var endpoint = _configuration["CopilotCloud:GuardrailsEndpoint"];
        var apiKey = _configuration["CopilotCloud:PublicApiKey"];

        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey))
        {
            throw new ConfigurationException("Guardrails endpoint or API key not configured");
        }

        _httpClient.DefaultRequestHeaders.Authorization = 
            new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", apiKey);

        var response = await _httpClient.PostAsJsonAsync(endpoint, request);
        
        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError("Guardrails validation failed with status {StatusCode}", response.StatusCode);
            throw new GuardrailsException($"Validation failed: {response.StatusCode}");
        }

        var result = await response.Content.ReadFromJsonAsync<GuardrailsResult>();
        return result ?? new GuardrailsResult { Status = "allowed" };
    }
}

public record GuardrailsValidationRequest
{
    public required string Input { get; init; }
    public required IReadOnlyList<string> ValidTopics { get; init; }
    public required IReadOnlyList<string> InvalidTopics { get; init; }
    public required IReadOnlyList<GuardrailsMessage> Messages { get; init; }
}

public record GuardrailsMessage
{
    public required MessageRole Role { get; init; }
    public required string Content { get; init; }
}

public record GuardrailsResult
{
    public required string Status { get; init; } // "allowed" or "denied"
    public string? Reason { get; init; }
    public double? Confidence { get; init; }
    public IReadOnlyList<string>? Categories { get; init; }
}
```

### Observability and Monitoring

```csharp
public interface IObservabilityService
{
    Task TrackRequestAsync(LLMRequestData data);
    Task TrackResponseAsync(LLMResponseData data);
    Task TrackErrorAsync(LLMErrorData data);
}

public class OpenTelemetryObservabilityService : IObservabilityService
{
    private readonly ILogger<OpenTelemetryObservabilityService> _logger;
    private readonly ActivitySource _activitySource;
    private readonly Counter<long> _requestCounter;
    private readonly Histogram<double> _requestDuration;

    public OpenTelemetryObservabilityService(ILogger<OpenTelemetryObservabilityService> logger)
    {
        _logger = logger;
        _activitySource = new ActivitySource("CopilotRuntime");
        
        var meter = new Meter("CopilotRuntime");
        _requestCounter = meter.CreateCounter<long>("copilot_requests_total");
        _requestDuration = meter.CreateHistogram<double>("copilot_request_duration_seconds");
    }

    public Task TrackRequestAsync(LLMRequestData data)
    {
        using var activity = _activitySource.StartActivity("copilot_request");
        
        activity?.SetTag("thread_id", data.ThreadId);
        activity?.SetTag("model", data.Model);
        activity?.SetTag("provider", data.Provider);
        
        _requestCounter.Add(1, 
            new KeyValuePair<string, object?>("model", data.Model),
            new KeyValuePair<string, object?>("provider", data.Provider));

        _logger.LogInformation("Processing request for thread {ThreadId} with model {Model}", 
            data.ThreadId, data.Model);

        return Task.CompletedTask;
    }

    public Task TrackResponseAsync(LLMResponseData data)
    {
        _requestDuration.Record(data.Latency,
            new KeyValuePair<string, object?>("model", data.Model),
            new KeyValuePair<string, object?>("provider", data.Provider));

        _logger.LogInformation("Completed request for thread {ThreadId} in {Latency}ms", 
            data.ThreadId, data.Latency);

        return Task.CompletedTask;
    }

    public Task TrackErrorAsync(LLMErrorData data)
    {
        _logger.LogError("Request failed for thread {ThreadId}: {Error}", 
            data.ThreadId, data.Error);

        return Task.CompletedTask;
    }
}

public record LLMRequestData
{
    public string? ThreadId { get; init; }
    public string? RunId { get; init; }
    public string? Model { get; init; }
    public object? Messages { get; init; }
    public object? Actions { get; init; }
    public object? ForwardedParameters { get; init; }
    public DateTimeOffset Timestamp { get; init; }
    public string? Provider { get; init; }
}

public record LLMResponseData
{
    public required string ThreadId { get; init; }
    public string? RunId { get; init; }
    public string? Model { get; init; }
    public object? Output { get; init; }
    public double Latency { get; init; }
    public DateTimeOffset Timestamp { get; init; }
    public string? Provider { get; init; }
    public bool IsProgressiveChunk { get; init; }
    public bool IsFinalResponse { get; init; }
}

public record LLMErrorData
{
    public string? ThreadId { get; init; }
    public string? RunId { get; init; }
    public required string Error { get; init; }
    public DateTimeOffset Timestamp { get; init; }
}
```

## Deployment and Scaling Considerations

### Docker Configuration

```dockerfile
# Dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 8080
EXPOSE 8081

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG BUILD_CONFIGURATION=Release
WORKDIR /src
COPY ["CopilotRuntime.csproj", "."]
RUN dotnet restore "./CopilotRuntime.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "./CopilotRuntime.csproj" -c $BUILD_CONFIGURATION -o /app/build

FROM build AS publish
ARG BUILD_CONFIGURATION=Release
RUN dotnet publish "./CopilotRuntime.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "CopilotRuntime.dll"]
```

### Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  copilot-runtime:
    build: .
    ports:
      - "5000:8080"
      - "5001:8081"
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
      - ConnectionStrings__DefaultConnection=Host=postgres;Database=copilotruntime;Username=postgres;Password=password
      - OpenAI__ApiKey=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: copilotruntime
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: copilot-runtime
spec:
  replicas: 3
  selector:
    matchLabels:
      app: copilot-runtime
  template:
    metadata:
      labels:
        app: copilot-runtime
    spec:
      containers:
      - name: copilot-runtime
        image: copilot-runtime:latest
        ports:
        - containerPort: 8080
        env:
        - name: ConnectionStrings__DefaultConnection
          valueFrom:
            secretKeyRef:
              name: copilot-secrets
              key: database-connection-string
        - name: OpenAI__ApiKey
          valueFrom:
            secretKeyRef:
              name: copilot-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"

---
apiVersion: v1
kind: Service
metadata:
  name: copilot-runtime-service
spec:
  selector:
    app: copilot-runtime
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

## Testing Strategy

### Unit Tests

```csharp
[TestClass]
public class CopilotRuntimeTests
{
    private Mock<IAgentServiceProvider> _mockAgentProvider = null!;
    private Mock<IActionExecutor> _mockActionExecutor = null!;
    private Mock<IStateManager> _mockStateManager = null!;
    private Mock<ILogger<CopilotRuntime>> _mockLogger = null!;
    private CopilotRuntime _runtime = null!;

    [TestInitialize]
    public void Setup()
    {
        _mockAgentProvider = new Mock<IAgentServiceProvider>();
        _mockActionExecutor = new Mock<IActionExecutor>();
        _mockStateManager = new Mock<IStateManager>();
        _mockLogger = new Mock<ILogger<CopilotRuntime>>();
        
        _runtime = new CopilotRuntime(
            _mockAgentProvider.Object,
            _mockActionExecutor.Object,
            _mockStateManager.Object,
            _mockLogger.Object);
    }

    [TestMethod]
    public async Task ProcessRequestAsync_WithTextMessage_ReturnsSuccessResponse()
    {
        // Arrange
        var input = new GenerateCopilotResponseInput
        {
            Metadata = new GenerateCopilotResponseMetadataInput { RequestType = CopilotRequestType.Chat },
            Messages = new[]
            {
                new MessageInput
                {
                    Id = "1",
                    CreatedAt = DateTimeOffset.UtcNow,
                    TextMessage = new TextMessageInput
                    {
                        Content = "Hello, world!",
                        Role = MessageRole.User
                    }
                }
            },
            Frontend = new FrontendInput { Actions = Array.Empty<ActionInput>(), Url = "http://localhost" }
        };

        var context = new CopilotContext();

        // Act
        var response = await _runtime.ProcessRequestAsync(input, context);

        // Assert
        Assert.IsNotNull(response);
        Assert.IsTrue(response.Status is SuccessResponseStatus);
        Assert.IsNotNull(response.ThreadId);
        Assert.IsNotNull(response.RunId);
    }

    [TestMethod]
    public async Task ProcessRequestAsync_WithAgentSession_CallsAgentProvider()
    {
        // Arrange
        var input = new GenerateCopilotResponseInput
        {
            Metadata = new GenerateCopilotResponseMetadataInput { RequestType = CopilotRequestType.Chat },
            Messages = Array.Empty<MessageInput>(),
            Frontend = new FrontendInput { Actions = Array.Empty<ActionInput>() },
            AgentSession = new AgentSessionInput { AgentName = "TestAgent", ThreadId = "test-thread" }
        };

        var mockAgent = new Mock<IAgent>();
        _mockAgentProvider.Setup(x => x.GetAgentAsync("TestAgent"))
            .ReturnsAsync(mockAgent.Object);

        _mockAgentProvider.Setup(x => x.ProcessAgentRequestAsync(
                It.IsAny<IAgent>(), 
                It.IsAny<AgentExecutionRequest>(), 
                It.IsAny<CancellationToken>()))
            .Returns(AsyncEnumerable.Empty<RuntimeEvent>());

        var context = new CopilotContext();

        // Act
        var response = await _runtime.ProcessRequestAsync(input, context);

        // Assert
        _mockAgentProvider.Verify(x => x.GetAgentAsync("TestAgent"), Times.Once);
        _mockAgentProvider.Verify(x => x.ProcessAgentRequestAsync(
            It.IsAny<IAgent>(), 
            It.IsAny<AgentExecutionRequest>(), 
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
```

### Integration Tests

```csharp
[TestClass]
public class CopilotRuntimeIntegrationTests
{
    private WebApplication _app = null!;
    private HttpClient _httpClient = null!;
    private CopilotDbContext _dbContext = null!;

    [TestInitialize]
    public async Task Setup()
    {
        var builder = WebApplication.CreateBuilder();
        
        // Configure test services
        builder.Services.AddDbContext<CopilotDbContext>(options =>
            options.UseInMemoryDatabase($"TestDb_{Guid.NewGuid()}"));
        
        // Add test-specific services
        builder.Services.AddScoped<ICopilotRuntime, CopilotRuntime>();
        // ... other services
        
        _app = builder.Build();
        
        // Configure test pipeline
        _app.MapGraphQL("/graphql");
        
        await _app.StartAsync();
        _httpClient = new HttpClient { BaseAddress = new Uri(_app.Urls.First()) };
        
        // Get database context for test data setup
        using var scope = _app.Services.CreateScope();
        _dbContext = scope.ServiceProvider.GetRequiredService<CopilotDbContext>();
    }

    [TestMethod]
    public async Task GraphQL_Hello_ReturnsHelloWorld()
    {
        // Arrange
        var query = """
            query {
                hello
            }
            """;

        var request = new { query };

        // Act
        var response = await _httpClient.PostAsJsonAsync("/graphql", request);
        var content = await response.Content.ReadAsStringAsync();

        // Assert
        Assert.IsTrue(response.IsSuccessStatusCode);
        Assert.IsTrue(content.Contains("Hello World"));
    }

    [TestCleanup]
    public async Task Cleanup()
    {
        await _app.StopAsync();
        _app.Dispose();
        _httpClient.Dispose();
    }
}
```

## Migration Guide from TypeScript

### Key Differences and Mappings

1. **Type System**: TypeScript union types → C# discriminated unions or inheritance
2. **Async Patterns**: RxJS observables → IAsyncEnumerable and Channels
3. **GraphQL**: GraphQL Yoga → HotChocolate
4. **Streaming**: WebStreams → SignalR and ASP.NET Core streaming
5. **Event System**: RxJS subjects → .NET Channels and EventSource
6. **Error Handling**: JavaScript errors → structured exception hierarchy

### Migration Steps

1. **Phase 1**: Set up ASP.NET Core with HotChocolate GraphQL
2. **Phase 2**: Implement data models and basic GraphQL operations
3. **Phase 3**: Add Semantic Kernel integration and agent support
4. **Phase 4**: Implement streaming with SignalR
5. **Phase 5**: Add state management with Entity Framework Core
6. **Phase 6**: Implement error handling and observability
7. **Phase 7**: Add cloud features and guardrails
8. **Phase 8**: Performance optimization and deployment

## Compatibility and Interoperability

This .NET Core implementation maintains full compatibility with the existing CopilotKit ecosystem:

- **GraphQL Schema**: Identical to TypeScript version
- **Message Formats**: Compatible input/output types
- **Error Responses**: Same error structure and codes
- **Event Streaming**: Compatible event types and flow patterns
- **Agent Protocol**: Compatible with existing agent implementations
- **Action System**: Same action execution interface

## Dependencies

```xml
<PackageReference Include="Microsoft.AspNetCore.App" Version="8.0.0" />
<PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
<PackageReference Include="Microsoft.EntityFrameworkCore.Design" Version="8.0.0" />
<PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" Version="8.0.0" />
<PackageReference Include="HotChocolate.AspNetCore" Version="13.5.0" />
<PackageReference Include="Microsoft.SemanticKernel" Version="1.0.0" />
<PackageReference Include="Microsoft.SemanticKernel.Agents" Version="1.0.0-alpha" />
<PackageReference Include="Microsoft.SemanticKernel.Connectors.OpenAI" Version="1.0.0" />
<PackageReference Include="Microsoft.SemanticKernel.Connectors.AzureOpenAI" Version="1.0.0" />
<PackageReference Include="System.Text.Json" Version="8.0.0" />
<PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.0" />
<PackageReference Include="OpenTelemetry.Extensions.Hosting" Version="1.6.0" />
<PackageReference Include="OpenTelemetry.Instrumentation.AspNetCore" Version="1.6.0" />
```

This comprehensive specification provides the foundation for building a production-ready CopilotRuntime implementation in .NET Core using Semantic Kernel, maintaining full compatibility with the existing TypeScript ecosystem while leveraging the power and performance of .NET for enterprise AI applications.