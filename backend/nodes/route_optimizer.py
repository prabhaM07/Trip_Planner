import json
import os
from travelstate import TravelState
from service import DistanceService
from prompts import build_exact_places_context
from utils import invoke_model, remove_markdown
from langfuse.decorators import observe
from langchain_core.messages import AIMessage

# Purpose:
# 
# - Extracts location names from the trip planner output
# - Computes an optimized travel order for the extracted places using distance-based routing logic (nearest-neighbour)


@observe(name="route_optimizer_node")
def route_optimizer_node(state: TravelState, llm):
    
    trip_plan = state.get("trip_planner_result", "")

    # Extract places using LLM 
    context = build_exact_places_context(trip_plan)
    response = invoke_model(
        model=llm,
        systemMessage=(
            "You are a precise information extraction system. "
            "Return only valid JSON with no additional text or formatting."
        ),
        humanMessage=context
    )

    if isinstance(response, AIMessage):
        cleaned = remove_markdown(response=response)
    else:
        cleaned = remove_markdown(response=str(response))
    try:
        data = json.loads(cleaned)
        places = data.get("places", [])
    except json.JSONDecodeError as e:
        places = []


    optimized_route = []
    if places:
        distance_service = DistanceService(os.environ["GEOAPIFY_API_KEY"])
        optimized_places = distance_service.get_optimized_route(places)
        optimized_route = optimized_places
    optimized_route_str = " → ".join(optimized_route)

    return {
        "messages": [response],
        "places_extracted": places,
        "optimized_route": optimized_route_str
    }

