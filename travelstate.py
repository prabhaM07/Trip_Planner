from typing import Optional, TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.documents import Document


class TravelState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    pdf_path: str
    vector_created: bool
    update_query: str

    agents_needed: List[str]
    agent_locations: dict
    current_query_start_index: int

    pdf_data: str
    retrieved_docs: List[Document]
    places_extracted: str
    optimized_route: str

    trip_days: str
    budget: str
    season: str
    month: str
    from_date: str
    to_date: str
    experience_type: str
    people: str
    source_location: str

    # ---------- ROUTE AGENT ----------
    route_info: Dict[str, float]                 
    places_along_route: List[Dict[str, Any]]     
    route_llm_result: str                       

    # ---------- AGENT RESULTS ----------
    trip_planner_result: str
    general_assistant_result: str
    weather_analyst_result: str
    final_result: str
    last_active_agent: str

    date_confirmation_done: bool
    preferences_collected: bool
    weather_analyst_called: bool
    trip_planner_called: bool
    general_assistant_called: bool
    research_agent_called: bool
    needs_general_fallback: bool
    ask_preference_called: bool
