import uuid
from travelstate import TravelState
from prompts import WEATHER_ANALYST_PROMPT, build_weather_analyst_context
from utils import collect_tool_results, invoke_model
from langfuse.decorators import observe
from langchain_core.messages import ToolMessage, AIMessage



# Purpose:
# This agent handles weather analysis for the trip.
# It gets weather information for the selected location
# 
# What it does:
# - Reads the destination location from the shared state
# - Uses a weather tool to fetch current or relevant weather data
# 
# Output:
# - Returns either a weather tool call or a clear weather explanation

@observe(name="weather_analyst_agent")
def weather_analyst_node(state: TravelState, llm) -> dict:

    messages = state.get("messages", [])
    user_query = state.get("user_query", "")
    agent_locations = state.get("agent_locations", {})
    location = agent_locations.get("weather_analyst", "")

    # --- Collect tool results ---
    tool_results_block = collect_tool_results(messages)

    # Process get_weather tool output
    if messages and isinstance(messages[-1], ToolMessage):

        context = build_weather_analyst_context(
            user_query,
            location,
            tool_results_block
        )

        response = invoke_model(
            model=llm,
            systemMessage=WEATHER_ANALYST_PROMPT,
            humanMessage=context
        )

        return {
            "messages": [response],
            "weather_analyst_called": True,
            "weather_analyst_result": response.content,
            "last_active_agent": "weather_analyst"
        }

    # Missing location
    if not location:
        return {
            "messages": [AIMessage(content="Please specify a location for weather analysis.")],
            "weather_analyst_called": True,
            "last_active_agent": "weather_analyst"
        }

    # Trigger get_weather tool
    tool_calls = [{
        "name": "get_weather",
        "args": {"city": location},
        "id": f"call_{uuid.uuid4().hex[:8]}"
    }]

    response = AIMessage(content="", tool_calls=tool_calls)


    return {
        "messages": [response],
        "weather_analyst_called": True,
        "last_active_agent": "weather_analyst"
    }
