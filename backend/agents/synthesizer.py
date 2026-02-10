from travelstate import TravelState
from prompts import SYNTHESIZER_PROMPT
from utils import invoke_model
from langfuse import observe
from langchain_core.messages import  AIMessage
from langgraph.types import  interrupt




# Purpose:
# This agent combines all collected information and produces the final answer
# shown to the user.
# It brings together the trip plan, weather details, general travel information,
# document data, and route optimization into one clear response.
# 
# Output:
# - Returns a single, well-structured final answer for the user
# - Includes extracted places and optimized route details when available

@observe(name="synthesizer_agent")
def synthesizer_node(state: TravelState, llm) -> dict:
    
    user_query = state.get("user_query", "")
    num_days = state.get("trip_days", 0)

    trip_plan = state.get("trip_planner_result", "")
    weather_info = state.get("weather_analyst_result", "")
    general_info = state.get("general_assistant_result", "")
    pdf_info = state.get("pdf_data", "")
    places = state.get("places_extracted", [])
    optimized_route = state.get("optimized_route", "")
    trip_planner_called = state.get("trip_planner_called", False)

    update_block = ""
    
    if trip_planner_called :
        update_query = interrupt({
            "type": "refinement_request",
            "question": "Please provide any additional details or refinements for your trip planning request:",
            "trip_plan" : "".join(trip_plan) if trip_plan else "",
        })
        if update_query:
            update_block = f"""
            UPDATE REQUEST:
            {update_query}
            """
    
    # If nothing to synthesize, return early
    if not any([trip_plan, weather_info, general_info, pdf_info]):
        return {
            "messages": [AIMessage(content="I couldn't gather enough information to answer your query.")],
        }
    

    # Build collected information block
    collected_sections = []
    if trip_plan:
        collected_sections.append(f"TRIP ITINERARY:\n{trip_plan}")
    if weather_info:
        collected_sections.append(f"WEATHER INFORMATION:\n{weather_info}")
    if general_info:
        collected_sections.append(f"TRAVEL INFORMATION:\n{general_info}")
    if pdf_info:
        collected_sections.append(f"DOCUMENT INFORMATION:\n{pdf_info}")

    collected_info_block = "\n\n".join(collected_sections)

    # Build instructions for synthesis
    instructions = [
        "if the update request given : modify the existing plan instead of creating a completely new one"
        "Present the itinerary clearly based on the user query",
        "Use day-by-day format if trip duration is specified",
        "Follow the distance-optimized sequence if provided",
        "Include weather and travel info considerations",
        "Group nearby places and suggest logical visiting flow",
        "Keep the plan realistic, actionable, and traveler-friendly",
        "Use a natural professional tone, do not mention agents or tools"
    ]
    instructions_block = "\n- " + "\n- ".join(instructions)

    # Include optimized route if available
    optimized_route_block = f"DISTANCE-OPTIMIZED SEQUENCE:\n{optimized_route}\n" if optimized_route else ""

    # Final context for the LLM
    context = f"""
    USER QUERY:
    {user_query}

    TRIP DURATION:
    {num_days} days

    {collected_info_block}

    {optimized_route_block}

    {update_block}
    SYNTHESIS INSTRUCTIONS:{instructions_block}
    """.strip()

    # Generate final synthesized response
    final_response = invoke_model(
        systemMessage=SYNTHESIZER_PROMPT,
        humanMessage=context
    )

    return {
        "messages": [final_response],
        "final_result": final_response.content
    }

