import os
import time
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.tools import lookup_data, calculate

load_dotenv()

# Register tools so the agent can discover them
TOOLS = [lookup_data, calculate]

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a helpful and precise AI agent equipped with tools.\n"
        "Use 'lookup_data' to retrieve stored facts or knowledge.\n"
        "Use 'calculate' for mathematical computations.\n"
        "Always use available tools when needed, and provide clear, accurate responses."
    )
)


# Typed state that flows through the graph
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def create_agent():
    # Initialize Groq LLM with tool bindings
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    ).bind_tools(TOOLS)

    def agent_node(state: AgentState) -> AgentState:
        # LLM decides: respond directly or call a tool
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        # Route to tools if the LLM requested a tool call
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(TOOLS)

    # Wire up the graph: agent -> conditional -> tools -> agent
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def run_agent(question: str) -> dict:
    agent = create_agent()
    start_time = time.time()
    # Invoke the graph with system prompt and user question
    initial_messages = [SYSTEM_PROMPT, HumanMessage(content=question)]
    result = agent.invoke({"messages": initial_messages})
    elapsed_ms = int((time.time() - start_time) * 1000)

    final_message = result["messages"][-1]
    return {
        "output": final_message.content,
        "messages": result["messages"],
        "latency_ms": elapsed_ms,
    }