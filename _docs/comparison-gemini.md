# Comparison of CopilotRuntime Specifications

This document analyzes and compares the four different specification documents for the CopilotRuntime port from TypeScript to Python. Each document provides a unique perspective and level of detail, and together they form a comprehensive guide for the implementation.

## High-Level Summary

Each color-coded document has a distinct focus:

-   **`Specification Blue`**: A comprehensive, high-level design document. It covers architecture, GraphQL schema, event systems, and core flows, providing both TypeScript context and a Python implementation strategy. Its key contribution is the "Deep Dive Analysis" section, which meticulously breaks down complex TypeScript patterns (like RxJS streams, error handling, and agent integration) and proposes concrete Python equivalents.

-   **`Specification Green`**: A detailed, Python-focused implementation plan. It provides the most concrete and complete code examples for setting up the FastAPI application, defining the GraphQL schema with Strawberry, and building the core components like the event system and service adapters in Python. It reads like a direct blueprint for the Python codebase.

-   **`Specification Purple`**: A pure GraphQL API reference. It exhaustively lists every query, mutation, enum, input type, and object type in the GraphQL schema. It serves as a strict contract for the API surface, without detailing behavior or implementation.

-   **`Specification Red`**: A protocol-level specification. It focuses on the "wire-level" contract, detailing the externally observable behaviors, data flows, and semantics of the GraphQL operations. It explains *what happens* during a request, how streaming works, and how errors are handled from a client's perspective.

---

## Feature-by-Feature Comparison

| Feature                 | Blue Specification                                                                                             | Green Specification                                                                                              | Purple Specification                                                                                             | Red Specification                                                                                                                            |
| :---------------------- | :------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| **Primary Focus**       | High-level design & deep-dive pattern analysis.                                                                | Concrete Python implementation plan.                                                                             | Exhaustive GraphQL API reference.                                                                                | Protocol semantics and wire-level contract.                                                                                                  |
| **Architecture**        | Provides a high-level architectural diagram and component overview.                                            | Details the Python/FastAPI application structure with a clear module layout.                                     | Implied through the API structure but not explicitly defined.                                                    | Describes the architecture from a protocol perspective, as a bridge between client and backend services.                                     |
| **GraphQL Schema**      | Describes the core mutations/queries with examples and discusses the implementation strategy using FastAPI.      | Provides complete, ready-to-use Python code for the schema using Strawberry, including types, resolvers, and subscriptions. | Provides the most comprehensive and detailed list of all GraphQL types, inputs, enums, and objects.            | Documents the operations and their semantics, focusing on the request/response contract and streaming behavior.                               |
| **Event System**        | Explains the RxJS-based event system and provides a detailed strategy for translating it to Python's `asyncio`. | Offers a complete, advanced implementation of an `asyncio`-based event system in Python, with RxJS-like operators. | Lists event-related GraphQL types but does not describe the streaming mechanism or flow.                         | Describes the event flow from a protocol perspective (e.g., `TextMessageStart` -> `Content` -> `End`).                                       |
| **Implementation Code** | Provides strategic Python code snippets for key patterns (Pydantic models, adapter stubs).                     | Contains extensive, production-ready Python code for nearly every component of the runtime.                      | None.                                                                                                            | None.                                                                                                                                        |
| **Agent Integration**   | Details the agent integration patterns, especially for LangGraph, with a deep dive into discovery and execution. | Shows how to implement the LangGraph adapter and defines the remote endpoint types.                              | Lists agent-related input and output types.                                                                      | Explains the flow for agent runs vs. general runs and the protocol for remote agent discovery and execution.                                 |
| **Error Handling**      | Presents a deep dive into the structured error system, with a strategy for Python implementation.                | Provides a full Python implementation of a structured error classification system and observability hooks.       | Lists error-related response statuses and enums.                                                                 | Details how errors are handled at the protocol level, including structured errors and stream interruption responses.                         |

---

## Synthesis and Conclusion

The four documents are not redundant but complementary, offering different layers of abstraction for the porting process.

-   For a **quick overview of the API contract**, `Specification Purple` is the best resource. It is the definitive dictionary of all available GraphQL types.
-   To **understand the behavior and flow of data**, `Specification Red` is the most useful. It explains the "why" and "how" behind the API calls from a client's perspective.
-   For **translating complex, idiomatic TypeScript patterns to Python**, `Specification Blue` provides the most insightful analysis and strategic guidance.
-   For the **actual Python implementation**, `Specification Green` serves as the most direct and actionable blueprint, providing a clear path forward with extensive code examples.

By combining these four documents, a developer has a complete picture:
1.  **What to build** (Purple: the API contract).
2.  **How it should behave** (Red: the protocol semantics).
3.  **How to solve complex design challenges** (Blue: the pattern-level deep dive).
4.  **How to write the code** (Green: the implementation plan).
