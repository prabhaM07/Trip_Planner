from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.synthesizer import synthesizer_node
from agents.trip_planner import trip_planner_node
from agents.weather_analyst import weather_analyst_node
from agents.general_assistant import general_query_node

from nodes.ask_preference import ask_preference_node
from nodes.route_description import route_description_node
from nodes.route_optimizer import route_optimizer_node
from nodes.query_intent import query_intent_node
from nodes.retriever import retriever_node
from nodes.generator import generator_node

from routes import (
    route_after_generator,
    route_after_query_intent,
    route_after_tools,
    should_continue_to_tools,
)
from langgraph.prebuilt import ToolNode
from tools import web_search, get_weather
from models import get_llm
from travelstate import TravelState
from langfuse import get_client
from dotenv import load_dotenv
load_dotenv()

langfuse = get_client()


def create_travel_workflow():
    llm = get_llm()
    
    tools = [web_search, get_weather]

    workflow = StateGraph(TravelState)

    #  Nodes 
    workflow.add_node("query_intent", lambda s: query_intent_node(s, llm))
    workflow.add_node("retriever", lambda s: retriever_node(s, llm))
    workflow.add_node("generator", lambda s: generator_node(s, llm))
    workflow.add_node("ask_preference", ask_preference_node)
    workflow.add_node("route_description", lambda s: route_description_node(s, llm))
    workflow.add_node("trip_planner", lambda s: trip_planner_node(s, llm))
    workflow.add_node("route_optimizer", lambda s: route_optimizer_node(s,llm))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("weather_analyst", lambda s: weather_analyst_node(s, llm))
    workflow.add_node("general_assistant", lambda s: general_query_node(s, llm))
    workflow.add_node("synthesizer", lambda s: synthesizer_node(s, llm))
    
    #  Edges 
    workflow.add_edge(START, "query_intent")

    workflow.add_conditional_edges(
        "query_intent",
        route_after_query_intent,
    )

    workflow.add_edge("retriever", "generator")

    workflow.add_conditional_edges(
        "generator",
        route_after_generator,
    )
    workflow.add_edge("route_description", "trip_planner")
    
    workflow.add_conditional_edges("trip_planner", should_continue_to_tools)
    workflow.add_conditional_edges("weather_analyst", should_continue_to_tools)
    workflow.add_conditional_edges("general_assistant", should_continue_to_tools)

    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
    )
    workflow.add_edge("route_optimizer", "synthesizer")
    workflow.add_edge("synthesizer", END)
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
