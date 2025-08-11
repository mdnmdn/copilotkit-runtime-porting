# CopilotRuntime GraphQL API Specification

This document specifies the GraphQL API for the CopilotRuntime. It is intended to be a comprehensive guide for porting the TypeScript implementation to Python using FastAPI.

## Overview

The CopilotRuntime GraphQL API provides an interface for frontend components to interact with the CopilotKit backend. It handles communication with LLMs, message history, state management, and orchestrates AI interactions.

The API is defined with TypeGraphQL and consists of two main resolvers:

-   **CopilotResolver**: Handles the main chat flow, including generating responses and managing agents.
-   **StateResolver**: Manages the state of agents.

## GraphQL Endpoint

The GraphQL endpoint is served at the root of the application.

## Authentication

Authentication is handled via a public API key passed in the `X-CopilotCloud-Public-API-Key` header. This key is required for all requests to the `generateCopilotResponse` mutation when the `cloud` input is provided.

## Resolvers

### CopilotResolver

#### Queries

**`hello: String`**

A simple query that returns "Hello World". Used for testing the connection.

**`availableAgents: AgentsResponse`**

Returns a list of available agents.

-   **Response:** `AgentsResponse`

#### Mutations

**`generateCopilotResponse(data: GenerateCopilotResponseInput, properties: JSONObject): CopilotResponse`**

The main mutation for generating a response from the Copilot. It takes an input object with the current state of the chat and returns a stream of messages.

-   **Arguments:**
    -   `data`: `GenerateCopilotResponseInput` - The input data for the request.
    -   `properties`: `JSONObject` (optional) - Additional properties for the request context.
-   **Response:** `CopilotResponse`

### StateResolver

#### Queries

**`loadAgentState(data: LoadAgentStateInput): LoadAgentStateResponse`**

Loads the state of an agent for a given thread.

-   **Arguments:**
    -   `data`: `LoadAgentStateInput` - The input data for the request.
-   **Response:** `LoadAgentStateResponse`

## Enums

### `ActionInputAvailability`

-   `disabled`
-   `enabled`
-   `remote`

### `CopilotRequestType`

-   `Chat`
-   `Task`
-   `TextareaCompletion`
-   `TextareaPopover`
-   `Suggestion`

### `FailedResponseStatusReason`

-   `GUARDRAILS_VALIDATION_FAILED`
-   `MESSAGE_STREAM_INTERRUPTED`
-   `UNKNOWN_ERROR`

### `GuardrailsResultStatus`

-   `ALLOWED`
-   `DENIED`

### `MessageRole`

-   `user`
-   `assistant`
-   `system`
-   `tool`
-   `developer`

### `MessageStatusCode`

-   `Pending`
-   `Success`
-   `Failed`

### `ResponseStatusCode`

-   `Pending`
-   `Success`
-   `Failed`

### `MetaEventName`

-   `LangGraphInterruptEvent`
-   `CopilotKitLangGraphInterruptEvent`

## Input Types

### `ActionInput`

-   `name: String!`
-   `description: String!`
-   `jsonSchema: String!`
-   `available: ActionInputAvailability`

### `AgentSessionInput`

-   `agentName: String!`
-   `threadId: String`
-   `nodeName: String`

### `AgentStateInput`

-   `agentName: String!`
-   `state: String!`
-   `config: String`

### `CloudInput`

-   `guardrails: GuardrailsInput`

### `ContextPropertyInput`

-   `value: String!`
-   `description: String!`

### `CustomPropertyInput`

-   `key: String!`
-   `value: Primitive!`

### `ExtensionsInput`

-   `openaiAssistantAPI: OpenAIApiAssistantAPIInput`

### `ForwardedParametersInput`

-   `model: String`
-   `maxTokens: Int`
-   `stop: [String]`
-   `toolChoice: String`
-   `toolChoiceFunctionName: String`
-   `temperature: Float`

### `FrontendInput`

-   `toDeprecate_fullContext: String`
-   `actions: [ActionInput!]!`
-   `url: String`

### `GenerateCopilotResponseInput`

-   `metadata: GenerateCopilotResponseMetadataInput!`
-   `threadId: String`
-   `runId: String`
-   `messages: [MessageInput!]!`
-   `frontend: FrontendInput!`
-   `cloud: CloudInput`
-   `forwardedParameters: ForwardedParametersInput`
-   `agentSession: AgentSessionInput`
-   `agentState: AgentStateInput`
-   `agentStates: [AgentStateInput]`
-   `extensions: ExtensionsInput`
-   `metaEvents: [MetaEventInput]`

### `GenerateCopilotResponseMetadataInput`

-   `requestType: CopilotRequestType`

### `GuardrailsInput`

-   `inputValidationRules: GuardrailsRuleInput!`

### `GuardrailsRuleInput`

-   `allowList: [String]`
-   `denyList: [String]`

### `LoadAgentStateInput`

-   `threadId: String!`
-   `agentName: String!`

### `MessageInput`

-   `id: String!`
-   `createdAt: Date!`
-   `textMessage: TextMessageInput`
-   `actionExecutionMessage: ActionExecutionMessageInput`
-   `resultMessage: ResultMessageInput`
-   `agentStateMessage: AgentStateMessageInput`
-   `imageMessage: ImageMessageInput`

### `TextMessageInput`

-   `content: String!`
-   `parentMessageId: String`
-   `role: MessageRole!`

### `ActionExecutionMessageInput`

-   `name: String!`
-   `arguments: String!`
-   `parentMessageId: String`
-   `scope: String`

### `ResultMessageInput`

-   `actionExecutionId: String!`
-   `actionName: String!`
-   `parentMessageId: String`
-   `result: String!`

### `AgentStateMessageInput`

-   `threadId: String!`
-   `agentName: String!`
-   `role: MessageRole!`
-   `state: String!`
-   `running: Boolean!`
-   `nodeName: String!`
-   `runId: String!`
-   `active: Boolean!`

### `ImageMessageInput`

-   `format: String!`
-   `bytes: String!`
-   `parentMessageId: String`
-   `role: MessageRole!`

### `MetaEventInput`

-   `name: MetaEventName!`
-   `value: String`
-   `response: String`
-   `messages: [MessageInput]`

### `OpenAIApiAssistantAPIInput`

-   `runId: String`
-   `threadId: String`

## Object Types

### `Agent`

-   `id: String!`
-   `name: String!`
-   `description: String`

### `AgentsResponse`

-   `agents: [Agent!]!`

### `CopilotResponse`

-   `threadId: String!`
-   `status: ResponseStatus!`
-   `runId: String`
-   `messages: [BaseMessageOutput!]!`
-   `extensions: ExtensionsResponse`
-   `metaEvents: [BaseMetaEvent]`

### `BaseMessageOutput` (Interface)

-   `id: String!`
-   `createdAt: Date!`
-   `status: MessageStatus!`

### `TextMessageOutput` (implements `BaseMessageOutput`)

-   `role: MessageRole!`
-   `content: [String!]!`
-   `parentMessageId: String`

### `ActionExecutionMessageOutput` (implements `BaseMessageOutput`)

-   `name: String!`
-   `scope: String`
-   `arguments: [String!]!`
-   `parentMessageId: String`

### `ResultMessageOutput` (implements `BaseMessageOutput`)

-   `actionExecutionId: String!`
-   `actionName: String!`
-   `result: String!`

### `AgentStateMessageOutput` (implements `BaseMessageOutput`)

-   `threadId: String!`
-   `agentName: String!`
-   `nodeName: String!`
-   `runId: String!`
-   `active: Boolean!`
-   `role: MessageRole!`
-   `state: String!`
-   `running: Boolean!`

### `ImageMessageOutput` (implements `BaseMessageOutput`)

-   `format: String!`
-   `bytes: String!`
-   `role: MessageRole!`
-   `parentMessageId: String`

### `ExtensionsResponse`

-   `openaiAssistantAPI: OpenAIApiAssistantAPIResponse`

### `OpenAIApiAssistantAPIResponse`

-   `runId: String`
-   `threadId: String`

### `GuardrailsResult`

-   `status: GuardrailsResultStatus!`
-   `reason: String`

### `LoadAgentStateResponse`

-   `threadId: String!`
-   `threadExists: Boolean!`
-   `state: String!`
-   `messages: String!`

### `MessageStatus` (Union)

-   `PendingMessageStatus`
-   `SuccessMessageStatus`
-   `FailedMessageStatus`

### `PendingMessageStatus`

-   `code: MessageStatusCode!`

### `SuccessMessageStatus`

-   `code: MessageStatusCode!`

### `FailedMessageStatus`

-   `code: MessageStatusCode!`
-   `reason: String!`

### `ResponseStatus` (Union)

-   `PendingResponseStatus`
-   `SuccessResponseStatus`
-   `FailedResponseStatus`

### `PendingResponseStatus`

-   `code: ResponseStatusCode!`

### `SuccessResponseStatus`

-   `code: ResponseStatusCode!`

### `FailedResponseStatus`

-   `code: ResponseStatusCode!`
-   `reason: FailedResponseStatusReason!`
-   `details: JSONObject`

### `BaseMetaEvent` (Interface)

-   `type: String!`
-   `name: MetaEventName!`

### `LangGraphInterruptEvent` (implements `BaseMetaEvent`)

-   `name: MetaEventName!`
-   `value: String!`
-   `response: String`

### `CopilotKitLangGraphInterruptEvent` (implements `BaseMetaEvent`)

-   `name: MetaEventName!`
-   `data: CopilotKitLangGraphInterruptEventData!`
-   `response: String`

### `CopilotKitLangGraphInterruptEventData`

-   `value: String!`
-   `messages: [BaseMessageOutput!]!`

## Deep Dive into Core Components

### `CopilotRuntime` Class

The `CopilotRuntime` class is the heart of the CopilotKit backend. It is responsible for processing requests, managing state, and orchestrating interactions between the various components of the system.

#### Initialization

The `CopilotRuntime` is initialized with a `CopilotRuntimeConstructorParams` object, which allows for extensive customization of its behavior. Key parameters include:

-   **`middleware`**: Allows for the injection of custom logic before and after a request is processed.
-   **`actions`**: Defines server-side actions that can be executed by the Copilot.
-   **`remoteEndpoints`**: Configures remote agents and actions that can be invoked by the Copilot.
-   **`langserve`**: Connects to LangServe instances to expose them as actions.
-   **`agents`**: Defines AGUI agents.
-   **`observability_c`**: Configures logging and telemetry.
-   **`onError`**: Provides a centralized error handling mechanism.

#### Request Processing

The main entry point for processing requests is the `processRuntimeRequest` method. This method takes a `CopilotRuntimeRequest` object and returns a `CopilotRuntimeResponse`. The request processing flow is as follows:

1.  **Request Validation**: The request is validated, and the appropriate service adapter is selected.
2.  **Agent Handling**: If the request is for an agent, it is delegated to the `processAgentRequest` method.
3.  **Action Discovery**: Server-side actions, including local, remote, and MCP actions, are discovered and prepared.
4.  **Message Processing**: Messages are processed, and MCP tool instructions are injected if necessary.
5.  **Service Adapter Invocation**: The `serviceAdapter.process` method is called to interact with the LLM.
6.  **Event Streaming**: An `eventSource` is created to stream events back to the client.
7.  **Middleware Execution**: The `onBeforeRequest` and `onAfterRequest` middleware hooks are executed.
8.  **Error Handling**: Any errors that occur during processing are caught and handled by the `onError` handler.

### `CopilotServiceAdapter` Interface

The `CopilotServiceAdapter` interface defines a contract for interacting with different LLM services. Each service adapter must implement a `process` method that takes a `CopilotRuntimeChatCompletionRequest` and returns a `CopilotRuntimeChatCompletionResponse`.

This abstraction allows the `CopilotRuntime` to remain agnostic of the specific LLM service being used, making it easy to switch between different services or even use multiple services at the same time.

### Event Streaming

Event streaming is a core feature of the CopilotRuntime, enabling real-time communication between the backend and the client. The event streaming mechanism is built on top of RxJS and consists of the following components:

-   **`RuntimeEventTypes`**: An enum that defines the different types of events that can be streamed.
-   **`RuntimeEvent`**: A union type that represents all possible runtime events.
-   **`RuntimeEventSubject`**: An RxJS `ReplaySubject` that is used to send and receive runtime events.
-   **`RuntimeEventSource`**: A class that manages the event stream and processes runtime events.

When a request is processed, the `ServiceAdapter` sends events to the `RuntimeEventSubject`. The `RuntimeEventSource` then processes these events, executes any necessary server-side actions, and streams the events back to the client through a GraphQL subscription.

## Flows and Behaviors

### `generateCopilotResponse` Flow

1.  The client sends a `generateCopilotResponse` mutation with the current chat messages and other relevant data.
2.  The server receives the request and validates the input.
3.  If guardrails are enabled, the server validates the input against the defined rules. If the validation fails, the server returns a `FailedResponseStatus` with the reason.
4.  The server calls the `copilotRuntime.processRuntimeRequest` method to process the request. This method is responsible for interacting with the LLM and any configured agents.
5.  The `processRuntimeRequest` method returns an event source (`eventSource`) that emits events as the LLM processes the request.
6.  The server subscribes to the `eventSource` and streams the events back to the client as `CopilotResponse` messages.
7.  The client receives the stream of messages and updates the UI accordingly.

### State Management

The `StateResolver` is responsible for loading the state of an agent. The `loadAgentState` query takes a `threadId` and `agentName` and returns the saved state for that agent in that thread. This allows agents to maintain state across multiple requests.

### Error Handling

The API uses a combination of GraphQL errors and custom error responses to handle errors.

-   **GraphQL Errors:** Used for validation errors and other general errors.
-   **`FailedResponseStatus`:** Used to indicate that the request failed due to a specific reason, such as a guardrails validation failure.
-   **`FailedMessageStatus`:** Used to indicate that a specific message in the stream failed to generate.
