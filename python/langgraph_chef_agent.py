"""
Chef Advisor Agent using LangGraph and Gemini
Specialized in suggesting recipes and cooking advice

HOW TO RUN THIS AGENT:

1. Install dependencies:
   uv add langgraph langchain-google-genai langchain-core

2. Set environment variable:
   export GOOGLE_API_KEY="your-gemini-api-key"

3. Run the agent:
   # Option A: Run interactive chat
   python backend/agent_lg_chef.py

   # Option B: Use in your code
   from backend.agent_lg_chef import graph, run_chef_agent

   # Simple usage
   response = run_chef_agent("I want to make pasta tonight")
   print(response)

   # Advanced usage with the graph directly
   from langchain_core.messages import HumanMessage
   initial_state = {"messages": [HumanMessage(content="Suggest a healthy breakfast")]}
   result = graph.invoke(initial_state)
   print(result["messages"][-1].content)

4. Helper functions available:
   - suggest_recipe_by_ingredients(["chicken", "rice", "garlic"])
   - suggest_recipe_by_cuisine("Italian", "vegetarian")
   - get_cooking_advice("How to make perfect risotto?")
   - run_chef_agent("Any quick dinner ideas?")
"""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class ChefState(TypedDict):
    """The state of the chef advisor agent."""

    messages: Annotated[list[BaseMessage], add_messages]


def chef_advisor(state: ChefState):
    """Chef advisor node that provides recipe suggestions and cooking advice."""

    # System prompt for the chef advisor
    system_prompt = """You are a professional chef advisor with extensive culinary knowledge. 
    Your role is to:
    - Suggest delicious recipes based on ingredients, dietary preferences, or cuisine types
    - Provide cooking tips and techniques
    - Recommend ingredient substitutions
    - Offer meal planning advice
    - Share cooking time estimates and difficulty levels
    
    Always be helpful, creative, and provide practical cooking advice. 
    Include ingredient lists, step-by-step instructions, and helpful tips when suggesting recipes.
    Consider dietary restrictions and preferences when making recommendations."""

    # Initialize Gemini model
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.8,  # Slightly higher for more creative recipe suggestions
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )

    # Prepare messages with system prompt
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # Get the response from Gemini
    response = llm.invoke(messages)

    # Return the response as part of the state
    return {"messages": [response]}


# Create the graph
chef_graph_builder = StateGraph(ChefState)

# Add nodes
chef_graph_builder.add_node("chef_advisor", chef_advisor)

# Add edges
chef_graph_builder.add_edge(START, "chef_advisor")
chef_graph_builder.add_edge("chef_advisor", END)

checkpointer = MemorySaver()
# Compile the graph
graph = chef_graph_builder.compile(checkpointer=checkpointer)


# Helper functions for common recipe requests
def suggest_recipe_by_ingredients(ingredients: list[str]):
    """Suggest a recipe based on available ingredients."""
    ingredients_text = ", ".join(ingredients)
    user_input = f"I have these ingredients: {ingredients_text}. Can you suggest a recipe I can make with them?"

    initial_state = {"messages": [HumanMessage(content=user_input)]}

    result = graph.invoke(initial_state)
    return result["messages"][-1].content


def suggest_recipe_by_cuisine(cuisine_type: str, dietary_restrictions: str = None):
    """Suggest a recipe based on cuisine type and dietary restrictions."""
    user_input = f"Can you suggest a {cuisine_type} recipe"
    if dietary_restrictions:
        user_input += f" that is {dietary_restrictions}"
    user_input += "?"

    initial_state = {"messages": [HumanMessage(content=user_input)]}

    result = graph.invoke(initial_state)
    return result["messages"][-1].content


def get_cooking_advice(question: str):
    """Get general cooking advice or tips."""
    initial_state = {"messages": [HumanMessage(content=question)]}

    result = graph.invoke(initial_state)
    return result["messages"][-1].content


def run_chef_agent(user_input: str):
    """Run the chef advisor agent with user input."""
    initial_state = {"messages": [HumanMessage(content=user_input)]}

    result = graph.invoke(initial_state)
    return result["messages"][-1].content


def interactive_chef_chat():
    """Run an interactive chat session with the chef advisor agent."""
    print("👨‍🍳 Chef Advisor Agent - Interactive Chat")
    print("=" * 50)
    print("Ask me about recipes, cooking tips, ingredients, and more!")
    print("Type 'quit', 'exit', or 'bye' to end the conversation")
    print("=" * 50)

    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set!")
        print("Please set it with: export GOOGLE_API_KEY='your-api-key'")
        return

    conversation_history = []

    # Add system message to conversation history
    system_prompt = """You are a professional chef advisor with extensive culinary knowledge. 
    Your role is to:
    - Suggest delicious recipes based on ingredients, dietary preferences, or cuisine types
    - Provide cooking tips and techniques
    - Recommend ingredient substitutions
    - Offer meal planning advice
    - Share cooking time estimates and difficulty levels
    
    Always be helpful, creative, and provide practical cooking advice. 
    Include ingredient lists, step-by-step instructions, and helpful tips when suggesting recipes.
    Consider dietary restrictions and preferences when making recommendations."""

    from langchain_core.messages import SystemMessage

    conversation_history.append(SystemMessage(content=system_prompt))

    print("\n👨‍🍳 Chef: Hello! I'm your personal chef advisor. What can I help you cook today?")

    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye", "q"]:
                print(
                    "\n👋 Happy cooking! Feel free to come back anytime for more culinary advice!"
                )
                break

            if not user_input:
                print("Please ask me about recipes, cooking tips, or type 'quit' to exit.")
                continue

            # Add user message to history
            conversation_history.append(HumanMessage(content=user_input))

            # Prepare state with conversation history
            initial_state = {"messages": conversation_history.copy()}

            print("\n👨‍🍳 Chef: ", end="", flush=True)

            # Get response from chef agent
            result = graph.invoke(initial_state)
            chef_response = result["messages"][-1]

            # Print the response
            print(chef_response.content)

            # Add chef response to history
            conversation_history.append(chef_response)

        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Happy cooking!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again or type 'quit' to exit.")


def run_test_examples():
    """Run the original test examples."""
    print("=== Chef Advisor Agent Test Examples ===\n")

    # Test 1: Recipe by ingredients
    print("Test 1: Recipe suggestion by ingredients")
    response1 = suggest_recipe_by_ingredients(["chicken", "rice", "vegetables", "soy sauce"])
    print(f"Chef: {response1}\n")

    # Test 2: Recipe by cuisine
    print("Test 2: Italian recipe suggestion")
    response2 = suggest_recipe_by_cuisine("Italian", "vegetarian")
    print(f"Chef: {response2}\n")

    # Test 3: Cooking advice
    print("Test 3: Cooking advice")
    response3 = get_cooking_advice("How do I make my pasta sauce more flavorful?")
    print(f"Chef: {response3}\n")

    # Test 4: General interaction
    print("Test 4: General interaction")
    response4 = run_chef_agent(
        "I want to cook something special for a dinner party. Any suggestions?"
    )
    print(f"Chef: {response4}")


if __name__ == "__main__":
    load_dotenv()
    # Check if user wants to run test examples
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_test_examples()
    else:
        # Run interactive chat by default
        interactive_chef_chat()
