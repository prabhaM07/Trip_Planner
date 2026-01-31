
import json
from travelstate import TravelState
from prompts import DATE_EXTRACTION_PROMPT, QUERY_INTENT_AGENT_PROMPT, build_date_extraction_context, build_query_intent_context
from utils import invoke_model, remove_markdown
from langfuse import observe
from langchain_core.messages import AIMessage


# Purpose:
# This node analyzes the raw user query and identifies the *intent* of the user.
#
# 1. Which agents are required to answer the query
#    → agents_needed: List[str]

# 2. Destination locations relevant to each agent
#    → agent_locations: Dict[str, str]
#      Format: { "Agent_Name": "Location_Name" }
# 
# 3. Travel-related preferences mentioned by the user
#    → preferences: Dict
#      Includes:
#        - trip_days        : Number of travel days
#        - budget           : Budget constraints
#        - season           : Preferred travel season
#        - month            : Travel month
#        - from_date        : Trip start date
#        - to_date          : Trip end date
#        - experience_type  : Adventure / leisure / pilgrimage / etc.
#        - people           : Number of travelers
#        - source_location  : Starting location of the trip


@observe(name="query_intent_node")
def query_intent_node(state: TravelState, llm):
    
    user_query = state.get("user_query", "")
    pdf_path = state.get("pdf_path", "")
    vector_created = state.get("vector_created", False)

    # Human message context
    context = build_query_intent_context(user_query, pdf_path, vector_created)

    query_intent_response = invoke_model(
        systemMessage=QUERY_INTENT_AGENT_PROMPT,
        humanMessage=context
    )
    context = build_date_extraction_context(user_query)

    date_extract_response = invoke_model(
        model=llm,
        systemMessage=DATE_EXTRACTION_PROMPT,
        humanMessage=context
    )
    
    content1 = remove_markdown(query_intent_response)
    content2 = remove_markdown(date_extract_response)

    try:
        intent_info = json.loads(content1)
        date_info = json.loads(content2)
        
    except json.JSONDecodeError:
        print()
        return {
            "messages": [
                AIMessage(content="I had trouble understanding your request format. Please ask again clearly.")
            ]
        }

    agents_needed = intent_info.get("agents_needed", [])
    agent_locations = intent_info.get("locations", {})
    preferences = intent_info.get("preferences", {})
    preferences.update(date_info)

    # If no agents are required, return the response as-is
    if not agents_needed:
        return {
            "messages": [query_intent_response],
        }

    current_messages = state.get("messages", [])

    return {
        "current_query_start_index": len(current_messages),
        "messages": [query_intent_response],
        "user_query": user_query,
        "agents_needed": agents_needed,
        "agent_locations": agent_locations,
        
        # Travel preferences
        "trip_days": preferences.get("trip_days"),
        "budget": preferences.get("budget"),
        "season": preferences.get("season"),
        "month": preferences.get("month"),
        "experience_type": preferences.get("experience_type"),
        "people": preferences.get("people"),
        
        # Date information
        "from_date": preferences.get("from_date"),
        "to_date": preferences.get("to_date"),
        
        # Location information
        "source_location": preferences.get("source_location"),
        "retrieved_docs": [],
        "pdf_data": "",                        

        # Agent Results 
        "trip_planner_result": "",  
        "general_assistant_result": "",
        "weather_analyst_result": "",
        "route_llm_result": "",
        "final_result": "",
        "last_active_agent": "",

        "places_extracted": "",
        "optimized_route": "",
        # Agent execution flags
        "research_agent_called": False,
        "general_assistant_called": False,
        "trip_planner_called": False,
        "weather_analyst_called": False,
        "needs_general_fallback": False,
        "preferences_collected": False
    }
