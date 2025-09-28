import uuid
import streamlit as st
from pydantic import BaseModel, Field
from typing import List, Annotated, Any
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
try:
    from utils.tools import tsp_solver
except:
    from agent.utils.tools import tsp_solver

MODEL = st.secrets.get("OPENAI_MODEL")
API_KEY = st.secrets.get("OPENAI_KEY")
MODEL = ChatOpenAI(model=MODEL, api_key=API_KEY, temperature=0)

class State(MessagesState):
    """Conversation state for the optimizer assistant."""
    solution: dict[str, Any] | None = None

MODEL_SYSTEM_MESSAGE = """
You are an Optimizer Assistant chatbot. Your goal is to identify the 
necessary tool to solve the user's problem.

Available tools:
- tsp_solver: Call this tool when the problem can be modeled as a 
  Traveling Salesperson Problem (TSP). The tool will gather all necessary 
  information internally. 

Core Instructions:

1. Information Gathering:
   - Collect all relevant details about the user's problem to understand it
    and identify wich tool must be called

2. Ask general questions (One per iteration) about main goal and constraints, no more.

3. Optimization Tool Execution:
   - Once the problem is clearly defined, call the appropriate tool.
   - Include reasoning that justifies why the user’s problem can be solved 
     using this tool.
   - Return a detailed solution based on the tool's response, including the reasoning.

IMPORTANT:
    - Your goal is identified which is the necessary tool that solves the user problem.
    - Do not include any file or sourde path in your response
"""
def assistant(state:State):    
    """Main assistant node: combines system message with conversation history."""
    response = MODEL_WITH_TOOLS.invoke(
            [SystemMessage(content=MODEL_SYSTEM_MESSAGE)]+state["messages"]
        )
    return {"messages": response}

def should_continue(state: State):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"


def invoke(message, thread_id="1"):
        
    config = {"configurable": {"thread_id": thread_id }}  # We supply a thread ID for short-term (within-thread) memory
                              
    # The states are returned in reverse chronological order.
    states = list(graph.get_state_history(config))
    
    # get the latest state
    if len(states) > 0:
        last_state = states[0]
        interrupts = last_state.interrupts
    else:
        interrupts = []

    if len(interrupts) > 0:
        user_message = Command(resume=message)
    else:
        user_message = {"messages":  [HumanMessage(content=message)] }

    response = graph.invoke(user_message, config=config)
    
    if "__interrupt__" in response:
        interruption = response["__interrupt__"][0].value
    else:
        interruption = None
    return response, interruption


tools = [tsp_solver]
MODEL_WITH_TOOLS = MODEL.bind_tools(tools)
tool_node = ToolNode(tools)

# Define the graph
builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tools", tool_node)


builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", should_continue,{"tools": "tools", "end": END}
)

builder.add_edge("tools", "assistant")


# Checkpointer for short-term (within-thread) memory
within_thread_memory = MemorySaver()

# Compile the graph with the checkpointer fir and store
graph = builder.compile(checkpointer=within_thread_memory)

# graph_image = graph.get_graph(xray=True).draw_mermaid_png()
# with open("agent.png", "wb") as f:
#    f.write(graph_image)

thread_id = str(uuid.uuid4())

if __name__ == "__main__":
    while True:
        user_message = input("You: ")
        if user_message.lower() == "exit":
            break
        
        response, interruption = invoke(user_message,thread_id=thread_id)
        ai_message =  response["messages"][-1].content
        

        if interruption is not None:
            print("Assistant: ", interruption)
        else:
            print("Assistant:", ai_message )
        
        if "solution" in response:
            solution = response["solution"]
            if "tsp_map_path" in solution:
                print(solution["tsp_map_path"])

        print("-----")