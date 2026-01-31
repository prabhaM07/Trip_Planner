import os
from travelstate import TravelState
from service import DistanceService, get_route, reverse_geocode
from utils import correct_locations_with_llm, invoke_model
from langfuse import observe


# Purpose:
# 
# - Geocodes both locations to coordinates
# - Fetches a fixed driving route between source & destination
# - Samples points along the route
# - Reverse-geocodes those points to nearby places
# - Asks LLM to describe notable places strictly along this route

@observe(name="route_description_node")
def route_description_node(state: TravelState, llm):

    service = DistanceService(os.environ["GEOAPIFY_API_KEY"])

    source_name = state.get("source_location")
    agent_locations = state.get("agent_locations", {})
    destination_name = agent_locations.get("trip_planner")

    corrected = correct_locations_with_llm(
        llm=llm,
        source_name=source_name,
        destination_name=destination_name
    )

    source_name = corrected["source"]
    destination_name = corrected["destination"]

    # --- Geocoding ---
    source = service.geocode(source_name)
    dest = service.geocode(destination_name)

    if not source or not dest:
        raise Exception("Geocoding failed")

    coordinates = [
        [source[1], source[0]],  # lon, lat
        [dest[1], dest[0]]
    ]

    route_data = get_route(
        coordinates,
        os.environ["ORS_API_KEY"]
    )

    geometry = route_data["geometry"]

    step = max(1, len(geometry) // 8)
    sample_points = geometry[::step]

    # latitude and longitude to place names
    places_along_route = []
    for lat, lon in sample_points:
        place = reverse_geocode(lat,lon,os.environ["GEOAPIFY_API_KEY"])
        places_along_route.append({"lat": lat,"lon": lon,"place_name": place})

    context = f"""
        You are given a FIXED travel route. You MUST NOT change it.

        SOURCE: {source_name}
        DESTINATION: {destination_name}

        ROUTE SUMMARY:
        - Distance: {route_data['distance_km']:.2f} km
        - Duration: {route_data['duration_min']:.1f} minutes

        PLACES ALONG THE ROUTE (in order):
        {places_along_route}

        TASK:
        1. Identify notable places directly on this route
        2. No detours, no optimizations
        3. Say clearly if nothing notable exists
        """

    response = invoke_model(model=llm, humanMessage=context)
    agent_locations["trip_planner"] = destination_name

    return {
        "source_location": source_name,
        "agent_locations": agent_locations,     

        "route_info": {
            "distance_km": route_data["distance_km"],
            "duration_min": route_data["duration_min"]
        },
        "places_along_route": places_along_route,
        "route_llm_result": response
    }
