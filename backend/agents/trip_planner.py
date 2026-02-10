
import uuid
from travelstate import TravelState
from prompts import TRIP_PLANNER_PROMPT , build_trip_planner_context_with_pdf_data, build_trip_planner_context_with_preferences
from utils import collect_tool_results, invoke_model
from langfuse import observe
from langchain_core.messages import ToolMessage, AIMessage



# Purpose:
# This agent creates a travel plan for the user.
# It uses the user’s preferences (location, budget, season/month, trip days,group size, experience type)
# 
# What it does:
# - Reads all trip preferences from the shared state
# - Adds route details (distance, travel time, en-route places) if available
# 
# Output:
# - Returns either tool calls or a complete trip itinerary

@observe(name="trip_planner_agent")
def trip_planner_node(state: TravelState, llm) -> TravelState:

    messages = state.get("messages", [])
    user_query = state.get("user_query", "")
    pdf_data = state.get("pdf_data", "")
    vector_created = state.get("vector_created", False)

    agent_locations = state.get("agent_locations", {})
    location = agent_locations.get("trip_planner", "")
    budget = state.get("budget", "any")
    season = state.get("season", "null")
    experience_type = state.get("experience_type", "any")
    month = state.get("month", "null")
    num_days = state.get("trip_days", 1)
    people = state.get("people", "solo")

    route_info = state.get("route_info")
    route_llm_result = state.get("route_llm_result")

    route_context_block = ""
    if route_info and route_llm_result:
        route_context_block = f"""
            ROUTE TRAVEL INFORMATION:
            - Distance: {route_info.get("distance_km"):.1f} km
            - Travel time: {route_info.get("duration_min"):.1f} minutes

            IMPORTANT:
            - Travel time MUST be considered on Day 1 / last day
            - Do NOT optimize or reroute

            EN-ROUTE PLACES:
            {route_llm_result}
            """

    # TOOL RESULT HANDLING 
    tool_results_block = collect_tool_results(messages)

    #  Tool results just returned
    if messages and isinstance(messages[-1], ToolMessage):

        context = build_trip_planner_context_with_preferences(
            location,
            num_days,
            budget,
            season,
            month,
            experience_type,
            people,
            route_context_block,
            tool_results_block
        )

        response = invoke_model(
            systemMessage=TRIP_PLANNER_PROMPT,
            humanMessage=context
        )

        return {
            "messages": [response],
            "trip_planner_called": True,
            "trip_planner_result": response.content
        }

    #  PDF-based planning
    if pdf_data or vector_created:

        context = build_trip_planner_context_with_pdf_data(
            pdf_data,
            user_query,
            num_days,
            route_context_block
        )

        response = invoke_model(
            model=llm,
            systemMessage=TRIP_PLANNER_PROMPT,
            humanMessage=context
        )

        return {
            "messages": [response],
            "trip_planner_called": True,
            "trip_planner_result": response.content
        }

    # Trigger tools
    tool_calls = [
        {
        "name": "web_search",
        "args": {
            "query": (
                f"best {experience_type} places to visit in {location} "
                f"for {people} travelers, {budget} budget, "
                f"during {season or month}, {num_days}-day trip"
            )
                    
        },
        "id": f"call_{uuid.uuid4().hex[:8]}"
        },
        {
            "name": "web_search",
            "args": {
                "query": (
                    f"best {experience_type} places to visit in {location} "
                )
                        
            },
            "id": f"call_{uuid.uuid4().hex[:8]}"
        },
        {
            "name": "web_search",
            "args": {
                "query": (
                    f"budget accommodation in {location} "
                    f"for {people} travelers "
                    f"within {budget} budget"
                )
            },
            "id": f"call_{uuid.uuid4().hex[:8]}"
        },
            {
                "name": "get_weather",
                "args": {"city": location},
                "id": f"call_{uuid.uuid4().hex[:8]}"
            }
        ]

    return {
        "messages": [AIMessage(content="", tool_calls=tool_calls)],
        "trip_planner_called": True,
        "last_active_agent": "trip_planner"
    }
