from travelstate import TravelState
from langgraph.graph import END
from langchain_core.messages import ToolMessage 

AGENT_META = {
    "research_agent": {
        "complete_flag": "research_agent_called",
        "node_name": "retriever"  
    },
    "trip_planner": {
        "complete_flag": "trip_planner_called",
        "node_name": "ask_preference"  
    },
    "weather_analyst": {
        "complete_flag": "weather_analyst_called",
        "node_name": "weather_analyst"
    },
    "general_assistant": {
        "complete_flag": "general_assistant_called",
        "node_name": "general_assistant"
    }
}


def route_after_query_intent(state: TravelState):
    agents = state.get("agents_needed", [])
    query_type = state.get("query_type", "")

    if not agents or query_type == "invalid":
        return END

    pending = []
    for agent in agents:
        if agent in AGENT_META:
            complete_flag = AGENT_META[agent]["complete_flag"]
            if not state.get(complete_flag, False):
                pending.append(agent)
    
    if not pending:
        return END
    
    if "research_agent" in pending and "trip_planner" in pending:
        return "retriever"
    
    return AGENT_META[pending[0]]["node_name"]

def route_after_generator(state: TravelState):
    needs_fallback = state.get("needs_general_fallback", False)
    agents_needed = state.get("agents_needed", [])
    research_agent_called = state.get("research_agent_called", False)
    
    if "trip_planner" in agents_needed and not state.get("trip_planner_called", False):
        return "ask_preference"

    # If fallback needed and research_agent completed, go to general_assistant
    if needs_fallback and research_agent_called:
        return "general_assistant"
    
    return "synthesizer"

def get_pending_agents(state: TravelState):

    agents_needed = state.get("agents_needed", [])
    pending = []
    
    for agent in agents_needed:
        if agent in AGENT_META:
            complete_flag = AGENT_META[agent]["complete_flag"]
            if not state.get(complete_flag, False):
                pending.append(agent)
    
    return pending


def should_continue_to_tools(state: TravelState):
    messages = state.get("messages", [])

    if not messages:
        pending = get_pending_agents(state)
        if pending:
            return AGENT_META[pending[0]]["node_name"]
        return "synthesizer"

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    if isinstance(last_message, ToolMessage):
        last_agent = state.get("last_active_agent")
        if last_agent:
            return last_agent

    pending = get_pending_agents(state)
    if pending:
        return AGENT_META[pending[0]]["node_name"]

    if state.get("trip_planner_called"):
        return "route_optimizer"

    return "synthesizer"



def route_after_tools(state: TravelState):
    last_agent = state.get("last_active_agent")
    
    # Ensure correct node names
    if last_agent == "trip_planner":
        return "trip_planner"
    elif last_agent == "weather_analyst":
        return "weather_analyst"
    elif last_agent == "general_assistant":
        return "general_assistant"
    
    pending = get_pending_agents(state)
    if pending:
        return AGENT_META[pending[0]]["node_name"]
    
    return "synthesizer"

