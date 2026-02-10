import calendar
from travelstate import TravelState
from preferences import PREFERENCES
from utils import ask_for_dates, derive_month, handle_date_update, parse_date , is_null
from langfuse import observe
from langgraph.types import Command, interrupt



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

@observe(name="ask_preference_node")
def ask_preference_node(state: TravelState):
    agent_locations = state.get("agent_locations", {})
    location = agent_locations.get("trip_planner")

    raw_from = state.get("from_date")
    raw_to = state.get("to_date")

    from_date = parse_date(raw_from) if raw_from else None
    to_date = parse_date(raw_to) if raw_to else None

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
    

    

    if state.get("preferences_collected"):
        return Command(goto="route_description", update=update)

    # DATE CONFIRMATION 
    if is_null(season) and from_date and to_date and not state.get("date_confirmation_done"):
        summary = (
            f"From Date: {raw_from}\n"
            f"To Date: {raw_to}\n"
            f"Month: {month or 'Not specified'}"
        )

        response = interrupt({
            "type": "interrupt",
            "key": "dates_confirmation",
            "question": f"We detected the following dates:\n{summary}\nDo you want to keep or change?",
            "input_type": "confirm",
            "options": ["Keep", "Change"],
            "default": "Keep",
            "meta": {
                "from_date": raw_from,
                "to_date": raw_to
            }
            })


        update["date_confirmation_done"] = True

        if response and response.lower() == "change":
            new_from, new_to = ask_for_dates(from_date, to_date)

            handle_date_update(update, new_from, new_to)
            return Command(goto="ask_preference", update=update)

    elif is_null(season) and not state.get("date_confirmation_done"):
        new_from, new_to = ask_for_dates(from_date, to_date)
        handle_date_update(update, new_from, new_to)
        update["date_confirmation_done"] = True
        return Command(goto="ask_preference", update=update)
    
    if from_date and to_date:
        trip_days = max((to_date - from_date).days + 1, 1)
        print(trip_days)
        update["trip_days"] = trip_days

    else:
        preferences["trip_days"] = state.get("trip_days")

    if is_null(season):
        month = derive_month(from_date, to_date)
        preferences["month"] = month
    
    missing = [k for k, v in preferences.items() if is_null(v)]

    if missing:
        pref_key = missing[0]
        pref = PREFERENCES[pref_key]

        response = interrupt({
            "type": "interrupt",
            "key": pref.key,
            "question": pref.question,
            "input_type": "select",
            "options": pref.options,
            "default": state.get(pref.key),
            "meta": {}
            })


        update[pref.key] = str(response).strip() if response else "Not specified"

        if pref.key == "location":
            update["agent_locations"] = {**agent_locations, "trip_planner": update["location"]}

        if len(missing) == 1:
            update["preferences_collected"] = True

        return Command(
            goto="route_description" if update.get("preferences_collected") else "ask_preference",
            update=update
        )

    update["preferences_collected"] = True
    return Command(goto="route_description", update=update)

