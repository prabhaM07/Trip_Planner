import calendar
import json
import re
import os
from pathlib import Path
import uuid
from travelstate import TravelState
from RAG.retriever import Retriever
from RAG.generator import ResponseGenerator
from models import get_embedding_model, get_llm_model
from service import DistanceService, get_route, reverse_geocode
from preferences import PREFERENCES
from prompts import DATE_EXTRACTION_PROMPT, GENERAL_QUERY_PROMPT, QUERY_INTENT_AGENT_PROMPT, SYNTHESIZER_PROMPT, TRIP_PLANNER_PROMPT, WEATHER_ANALYST_PROMPT, build_date_extraction_context, build_exact_places_context, build_general_assistant_context, build_query_intent_context, build_trip_planner_context_with_pdf_data, build_trip_planner_context_with_preferences, build_weather_analyst_context
from utils import collect_tool_results, correct_locations_with_llm, invoke_model, remove_markdown , parse_date , is_null
from langfuse import observe
from langchain_core.messages import ToolMessage, AIMessage
from langgraph.types import Command, interrupt



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




# Purpose:
# This node retrieves the most relevant text chunks from a PDF-based vector store based on the user's query. 
# It is responsible for loading the PDF, extracting text, chunking content, creating embeddings, and performing retrieval.
# 
# PDF Loading:
# - Uses Path from pathlib to handle PDF file paths
# 
# Text Extraction:
# The PDF content is extracted using two methods:
#   1. PdfReader (PyPDF) – Extracts embedded digital text from PDFs
#   2. OCR (pytesseract) – Optical Character Recognition used as a fallback
#      when the PDF contains scanned images instead of text
# 
# Chunking:
# - Extracted text is split into manageable chunks using RecursiveCharacterTextSplitter
# 
# Embedding Model:
# - Uses SentenceTransformerEmbeddings
# - Model: "BAAI/bge-base-en-v1.5"
# 
#  Vector Store:
#  - Uses ChromaDB to store and manage document embeddings
# 
#  Retrieval Techniques:
# - Lexical Search: BM25 retriever (keyword-based matching)
# - Vector Search: Similarity-based retrieval using embeddings
#
# Output:
# - Returns the retrieved document chunks


@observe(name="retriever_node")
def retriever_node(state: TravelState,llm):
    
    user_query = state.get("user_query", "")
    pdf_path = Path(state.get("pdf_path", ""))
    vector_created = state.get("vector_created", False)
    flag = False
    
    if not vector_created:
        
        flag = True
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
    retriever = Retriever(
        pdf_path=pdf_path,
        embedding_model=get_embedding_model()
    )

    retriever.initialize(rebuild=flag)

    docs = retriever.retrieve(user_query)
   
    return {
        "retrieved_docs": docs,
        "vector_created": True
    }


# Purpose:
# This node generates the final answer using the user's query and thedocument chunks retrieved from the vector store.
# 
# Inputs:
# - user_query       : The original query asked by the user
# - retrieved_docs   : Relevant document chunks retrieved by the retriever agent
#
# Model Used:
# - LLM: ChatGroq
# - Model: "llama-3.3-70b-versatile"
# - Temperature: 0.7
# - Max Tokens: 1000
# - Top-p: 1.0


@observe(name="generator_node")
def generator_node(state: TravelState, llm):
    user_query = state.get("user_query", "").strip()
    retrieved_docs = state.get("retrieved_docs", [])

    generator = ResponseGenerator(llm)
    answer = generator.generate(user_query, retrieved_docs)

    is_no_answer = not answer or answer == "NO_ANSWER_FOUND"
    
    # Fallback if:
    # 1. No docs retrieved
    # 2. Answer is NO_ANSWER_FOUND
    # 3. Answer is empty
    needs_fallback = (
        not retrieved_docs or 
        len(retrieved_docs) == 0 or 
        is_no_answer
    )

    response = "" if is_no_answer else answer

    return {
        "research_agent_called": True,
        "needs_general_fallback": needs_fallback,
        "pdf_data": response,
        "messages": [response],
    }


# Purpose:
# This node collects and confirms user travel preferences for a trip.
#
#  Preferences Handled:
# - Source location
# - Destination location
# - Budget
# - Experience type
# - Number of people
# - Trip dates (from_date, to_date)
# - Trip duration (trip_days)
# - Month / Season
#
# Date Confirmation Flow:
# - If detected dates exist, the node asks the user to confirm or change them

@observe(name="ask_preference_node")
def ask_preference_node(state: TravelState):
    agent_locations = state.get("agent_locations", {})
    location = agent_locations.get("trip_planner")

    raw_from_date = state.get("from_date")
    raw_to_date = state.get("to_date")

    from_date = parse_date(raw_from_date) if raw_from_date else None
    to_date = parse_date(raw_to_date) if raw_to_date else None

    month = state.get("month")
    season = state.get("season")

    update = {}

    
    preferences = {
        "source_location": state.get("source_location"),
        "budget": state.get("budget"),
        "experience_type": state.get("experience_type"),
        "people": state.get("people"),
        "location": location,  
    }

    # derive trip_days from dates
    if from_date and to_date:
        trip_days = (to_date - from_date).days + 1
        if trip_days > 0:
            update["trip_days"] = trip_days
        else:
            update["trip_days"] = 1
    else:
        preferences["trip_days"] = state.get("trip_days")


    if is_null(season):
        preferences["month"] = month

    if state.get("preferences_collected"):
        return Command(goto="route_description", update=update)

    # date confirmation flow 
    if is_null(season) and not state.get("date_confirmation_done"):

        date_summary = (
            f"From Date: {raw_from_date or 'Not specified'}\n"
            f"To Date: {raw_to_date or 'Not specified'}\n"
            f"Month: {month or 'Not specified'}"
        )

        user_response = interrupt({
            "type": "confirmation_request",
            "preference": "dates_confirmation",
            "question": f"We detected the following dates for your trip:\n{date_summary}\n"
                        "Do you want to keep these, or change?",
            "options": ["Keep", "Change"]
        })

        update["date_confirmation_done"] = True

        if user_response and user_response.lower() == "change":
            new_from = parse_date(interrupt({
                "type": "preference_request",
                "preference": "from_date",
                "question": "Please enter the start date (DD.MM.YYYY):"
            }))

            new_to = parse_date(interrupt({
                "type": "preference_request",
                "preference": "to_date",
                "question": "Please enter the end date (DD.MM.YYYY):"
            }))

            update["from_date"] = new_from
            update["to_date"] = new_to

            if new_from and new_to:
                if new_from.year < new_to.year:
                    update["month"] = "any"
                elif new_from.month == new_to.month:
                    update["month"] = calendar.month_name[new_from.month]
                else:
                    update["month"] = (
                        f"{calendar.month_name[new_from.month]} "
                        f"to {calendar.month_name[new_to.month]}"
                    )

        return Command(goto="ask_preference", update=update)

    # ask remaining preferences 
    missing = [k for k, v in preferences.items() if is_null(v)]

    if missing:
        pref_key = missing[0]
        pref = PREFERENCES[pref_key]

        user_response = interrupt({
            "type": "preference_request",
            "preference": pref.key,
            "question": pref.question.format(location=location or ""),
            "options": pref.options
        })

        update[pref.key] = str(user_response).strip() if user_response else "Not specified"

        if pref.key == "location":
            update["agent_locations"] = {**agent_locations, "trip_planner": update["location"]}

        if len(missing) == 1:
            update["preferences_collected"] = True

        return Command(
            goto="route_description" if update.get("preferences_collected") else "ask_preference",
            update=update
        )

    # nothing missing 
    update["preferences_collected"] = True

    return Command(goto="route_description", update=update)


# Purpose:
# 
# - Normalizes source & destination names using LLM
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
        place = reverse_geocode(
            lat,
            lon,
            os.environ["GEOAPIFY_API_KEY"]
        )
        places_along_route.append({
            "lat": lat,
            "lon": lon,
            "place_name": place
        })

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



# Purpose:
# This agent answers general travel-related questions
# 
# Output:
# - Returns either a web search tool call or a final answer to the user’s question

@observe(name="general_query_agent")
def general_query_node(state: TravelState, llm) -> dict:

    messages = state.get("messages", [])
    user_query = state.get("user_query", "")
    is_fallback = state.get("needs_general_fallback", False)
    pdf_data = state.get("pdf_data", "")
    vector_created = state.get("vector_created", False)

    tool_results_block = collect_tool_results(messages)


    # After tool results (PDF or web_search)
    if messages and isinstance(messages[-1], ToolMessage):

        context = build_general_assistant_context(
            user_query=user_query,
            tool_results_block=tool_results_block,
            pdf_data=pdf_data if pdf_data or vector_created else ""
        )

        response = invoke_model(
            model=llm,
            systemMessage=GENERAL_QUERY_PROMPT,
            humanMessage=context
        )

        return {
            "messages": [response],
            "general_assistant_called": True,
            "general_assistant_result": response.content,
            "needs_general_fallback": False,
        }

    # No tool results yet, prepare web_search call
    search_query = f"{user_query} travel information guide" if is_fallback else user_query

    tool_calls = [{
        "name": "web_search",
        "args": {"query": search_query},
        "id": f"call_{uuid.uuid4().hex[:8]}"
    }]

    response = AIMessage(
        content="",
        tool_calls=tool_calls
    )


    return {
        "messages": [response],
        "general_assistant_called": True,
        "needs_general_fallback": False,
        "last_active_agent": "general_assistant"
    }


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


@observe(name="refinement_agent")
def refinement_node() -> dict:
    new_query = interrupt({
        "type": "refinement_request",
        "question": "Please provide any additional details or refinements for your trip planning request:"
    })
    # Placeholder for refinement logic
    return {
        "messages": [new_query],
        "update_query": new_query,
        "refinement_added": True
    }


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
    update_query = state.get("update_query")

    # If nothing to synthesize, return early
    if not any([trip_plan, weather_info, general_info, pdf_info]):
        return {
            "messages": [AIMessage(content="I couldn't gather enough information to answer your query.")],
        }
    update_block = ""
    if update_query:
        update_block = f"""
        UPDATE REQUEST:
        {update_query}
        """


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
        "final_result": {
            "answer": final_response,
            "places": places,
            "optimized_route": optimized_route
        }
    }



