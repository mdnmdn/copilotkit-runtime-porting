# CopilotRuntime Specification for .NET with Semantic Kernel

## Overview

CopilotRuntime is the backend component of CopilotKit that serves as the core runtime system. It acts as a GraphQL-based proxy between frontend React components and backend agentic frameworks like Microsoft's Semantic Kernel. This document provides a comprehensive specification for implementing CopilotRuntime in C# using ASP.NET Core.

## Architecture Overview

```
┌─────────────────────┐    GraphQL     ┌─────────────────────┐      .NET      ┌─────────────────────┐
│                     │   over HTTP    │                     │   Protocol     │                     │
│   Frontend React    │ ──────────────▶│   CopilotRuntime    │ ──────────────▶│  Semantic Kernel    │
│   Components        │                │   (.NET Core)       │                │   Agents & Skills   │
│                     │                │                     │                │                     │
└─────────────────────┘                └─────────────────────┘                └─────────────────────┘
```

### Key Components

1.  **GraphQL API Layer**: Exposes `generateCopilotResponse` mutation and related queries using Hot Chocolate.
2.  **Runtime Engine**: Orchestrates LLM interactions, message processing, and agent execution.
3.  **Event Streaming System**: Real-time bidirectional communication using `IAsyncEnumerable<T>`.
4.  **Service Adapters**: Interface to various LLM providers (OpenAI, Azure OpenAI, etc.) via Semantic Kernel connectors.
5.  **Agent Integration**: Connects to Semantic Kernel agents and skills.
6.  **Action System**: Execute frontend and server-side actions, mapped as Semantic Kernel functions.

The CopilotRuntime acts as a **GraphQL proxy** that:
- Exposes a GraphQL endpoint for frontend React components.
- Translates GraphQL requests into calls to the Semantic Kernel.
- Manages real-time streaming of AI responses.
- Handles action execution and state management.
- Provides observability and error handling through .NET's built-in logging and diagnostics.

## GraphQL Schema and Protocol

The GraphQL schema remains consistent with the original specification to ensure frontend compatibility. The implementation will use the Hot Chocolate GraphQL server for .NET.

### Core Operations

#### Queries

1.  **`hello: String`** - Health check endpoint.
2.  **`availableAgents: AgentsResponse`** - Discovers and returns available Semantic Kernel agents.
3.  **`loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse`** - Loads persisted agent state.

#### Mutations

**`generateCopilotResponse(data: GenerateCopilotResponseInput!, properties?: JSONObject): CopilotResponse`**

This is the primary mutation. The GraphQL schema definition remains the same as in the reference document.

## Input Types Specification (C# Representation)

C# record types will be used to model the GraphQL input types, providing immutability and conciseness.

### Core Input Types

#### `GenerateCopilotResponseInput`

```csharp
public record GenerateCopilotResponseInput(
    GenerateCopilotResponseMetadataInput Metadata,
    string? ThreadId,
    string? RunId,
    IReadOnlyList<MessageInput> Messages,
    FrontendInput Frontend,
    CloudInput? Cloud,
    ForwardedParametersInput? ForwardedParameters,
    AgentSessionInput? AgentSession,
    IReadOnlyList<AgentStateInput>? AgentStates,
    IReadOnlyDictionary<string, object>? Extensions,
    IReadOnlyList<MetaEventInput>? MetaEvents
);
```

#### Message Types (Union Type)

In Hot Chocolate, this is handled by defining a union type in GraphQL and corresponding C# classes.

```csharp
[UnionType("MessageInput")]
public interface IMessageInput { }

public record TextMessageInput(
    string Content,
    string? ParentMessageId,
    MessageRole Role
) : IMessageInput;

public record ActionExecutionMessageInput(
    string Name,
    string Arguments, // JSON string
    string? ParentMessageId
) : IMessageInput;

// ... other message input types as C# records
```

## Output Types Specification (C# Representation)

### Core Output Types

#### `CopilotResponse`

```csharp
public record CopilotResponse(
    string ThreadId,
    IResponseStatus Status,
    string? RunId,
    IReadOnlyList<IBaseMessageOutput> Messages,
    IReadOnlyDictionary<string, object>? Extensions,
    IReadOnlyList<IBaseMetaEvent>? MetaEvents
);
```

#### Message Output Types

```csharp
public interface IBaseMessageOutput
{
    string Id { get; }
    DateTime CreatedAt { get; }
    IMessageStatus Status { get; }
}

public record TextMessageOutput(
    string Id,
    DateTime CreatedAt,
    IMessageStatus Status,
    MessageRole Role,
    string Content, // Can be streamed chunk by chunk
    string? ParentMessageId
) : IBaseMessageOutput;

// ... other message output types as C# records
```

## Enumerations

Standard C# enums will be used.

```csharp
public enum MessageRole
{
    User,
    Assistant,
    System,
    Tool,
    Developer
}

// ... other enums
```

## Runtime Event System

The event system will be built using `System.Threading.Channels` or `IAsyncEnumerable<T>` to manage the flow of events, which integrates naturally with ASP.NET Core and Hot Chocolate's streaming capabilities.

### Runtime Event Types

```csharp
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
```

### Event Flow and Structures

The event flow patterns (Text Message, Action Execution) remain the same. The event structures will be represented by C# records.

```csharp
public record RuntimeEvent(
    RuntimeEventType Type,
    string? MessageId,
    string? ParentMessageId,
    object Payload // Specific payload per event type
);

public record TextMessageContentPayload(string Content);
// ... other payload records
```

## Core Runtime Flows

The core flows (Standard Chat, Action Execution) are conceptually the same but will be implemented using Semantic Kernel's architecture.

### Semantic Kernel Agent Flow

1.  Client specifies `agentSession` in the request.
2.  CopilotRuntime identifies the corresponding Semantic Kernel agent.
3.  A `ChatHistory` is constructed from the input messages.
4.  The runtime invokes the agent using `agent.InvokeAsync()`.
5.  The agent, configured with functions (tools/actions), processes the request. If it decides to call a function, Semantic Kernel handles the invocation.
6.  Frontend actions are exposed to the kernel as functions that signal back to the client.
7.  Streaming responses (text or function calls) from the kernel are translated into `RuntimeEvent`s.
8.  The runtime streams `AgentStateMessage` events to reflect the agent's internal state if the kernel provides hooks for it.

## Service Adapter Interface (Semantic Kernel Integration)

Instead of custom service adapters for each LLM, the runtime will primarily interface with Semantic Kernel, which abstracts away the specifics of different model providers.

### `CopilotServiceAdapter` for Semantic Kernel

```csharp
public interface ICopilotServiceAdapter
{
    IAsyncEnumerable<RuntimeEvent> Process(CopilotRuntimeRequest request);
}

public class SemanticKernelAdapter : ICopilotServiceAdapter
{
    private readonly Kernel _kernel;

    public SemanticKernelAdapter(Kernel kernel)
    {
        _kernel = kernel;
    }

    public async IAsyncEnumerable<RuntimeEvent> Process(CopilotRuntimeRequest request)
    {
        var chatHistory = new ChatHistory();
        // Convert request.Messages to ChatHistory
        
        var agent = _kernel.CreateAgent(
            name: "MyAgent",
            instructions: "You are a helpful assistant."
        );

        // Stream results from the agent
        await foreach (var content in agent.InvokeAsync(chatHistory))
        {
            if (content.Content is not null)
            {
                yield return new RuntimeEvent(
                    RuntimeEventType.TextMessageContent,
                    Payload: new TextMessageContentPayload(content.Content)
                );
            }
            // Handle function calls and other content types
        }
    }
}
```

## Agent Integration

Agents are defined using Semantic Kernel's `Agent` class. Server-side actions and frontend actions are exposed to the agent as "skills" or "plugins" containing functions.

### Representing Actions as Kernel Functions

A frontend action is translated into a kernel function that, when invoked, emits `ActionExecutionStart`/`Args`/`End` events to the client.

```csharp
public class FrontendAction
{
    private readonly Action<RuntimeEvent> _eventEmitter;

    public FrontendAction(Action<RuntimeEvent> eventEmitter)
    {
        _eventEmitter = eventEmitter;
    }

    [KernelFunction, Description("Triggers a frontend action")]
    public async Task<string> Execute(
        [Description("The name of the action to execute")] string name,
        [Description("The arguments for the action, as a JSON string")] string arguments
    )
    {
        // 1. Emit ActionExecutionStart event
        _eventEmitter(new RuntimeEvent(RuntimeEventType.ActionExecutionStart, ...));
        
        // 2. Wait for the result from the frontend
        var result = await WaitForFrontendResult(); // Logic to await client response
        
        // 3. Emit ActionExecutionResult event
        _eventEmitter(new RuntimeEvent(RuntimeEventType.ActionExecutionResult, ...));
        
        return result;
    }
}
```

## ASP.NET Core Implementation Strategy

### 1. Application Architecture (`Program.cs`)

```csharp
var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddSingleton<CopilotRuntime>();
builder.Services.AddSingleton<ICopilotServiceAdapter, SemanticKernelAdapter>();

// Configure Semantic Kernel
builder.Services.AddKernel()
    .AddAzureOpenAIChatCompletion(
        builder.Configuration["AzureOpenAI:DeploymentName"],
        builder.Configuration["AzureOpenAI:Endpoint"],
        builder.Configuration["AzureOpenAI:ApiKey"]
    );

// Configure GraphQL
builder.Services
    .AddGraphQLServer()
    .AddQueryType<Query>()
    .AddMutationType<Mutation>()
    .AddSubscriptionType<Subscription>()
    .AddInMemorySubscriptions();

var app = builder.Build();

// Configure the HTTP request pipeline.
app.UseWebSockets();
app.MapGraphQL();

app.Run();
```

### 2. GraphQL Implementation (Hot Chocolate)

```csharp
// graphql/Query.cs
public class Query
{
    public string Hello() => "Hello World";

    public async Task<AgentsResponse> AvailableAgents(
        [Service] CopilotRuntime runtime
    ) => await runtime.GetAvailableAgents();
}

// graphql/Mutation.cs
public class Mutation
{
    public async Task<CopilotResponse> GenerateCopilotResponse(
        GenerateCopilotResponseInput data,
        [Service] CopilotRuntime runtime,
        IReadOnlyDictionary<string, object>? properties
    ) => await runtime.GenerateCopilotResponse(data, properties);
}

// graphql/Subscription.cs
public class Subscription
{
    [Subscribe]
    public IAsyncEnumerable<CopilotResponse> CopilotStream(
        GenerateCopilotResponseInput data,
        [Service] CopilotRuntime runtime
    ) => runtime.StreamCopilotResponse(data);
}
```

## Data Models (C# Records)

Use C# `record` types for immutable data transfer objects that map to the GraphQL schema.

```csharp
public enum MessageRole { User, Assistant, System, Tool, Developer }

public record TextMessageInput(string Content, string? ParentMessageId, MessageRole Role);

public record ActionInput(string Name, string Description, string JsonSchema);

public record GenerateCopilotResponseInput(
    // ... fields
);
```

## Error Handling (.NET)

Leverage .NET's built-in exception handling and Hot Chocolate's error filtering to provide structured errors.

```csharp
public class GraphQLErrorFilter : IErrorFilter
{
    public IError OnError(IError error)
    {
        if (error.Exception is CopilotKitException ex)
        {
            return error.WithMessage(ex.Message)
                .WithCode(ex.Code.ToString())
                .SetExtension("severity", ex.Severity.ToString());
        }

        return error.WithMessage("An unexpected error occurred.");
    }
}

// In Program.cs:
// builder.Services.AddErrorFilter<GraphQLErrorFilter>();
```

## Dependencies

### Core Dependencies (NuGet Packages)

```xml
<ItemGroup>
  <PackageReference Include="HotChocolate.AspNetCore" Version="13.9.0" />
  <PackageReference Include="HotChocolate.Subscriptions.InMemory" Version="13.9.0" />
  <PackageReference Include="Microsoft.SemanticKernel" Version="1.10.0" />
  <PackageReference Include="Microsoft.SemanticKernel.Agents" Version="1.10.0-alpha" />
  <PackageReference Include="Microsoft.Extensions.Http" Version="8.0.0" />
</ItemGroup>
```

This specification provides a clear path for porting the CopilotRuntime to a modern .NET stack, ensuring compatibility with the CopilotKit frontend while fully leveraging the power and idiomatic patterns of C#, ASP.NET Core, and the Semantic Kernel.
