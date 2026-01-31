import calendar
from travelstate import TravelState
from preferences import PREFERENCES
from utils import parse_date , is_null
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

    # If detected dates exist asks the user to confirm or change them
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
            new_from_date = parse_date(interrupt({
                "type": "preference_request",
                "preference": "from_date",
                "question": "Please enter the start date (DD.MM.YYYY):"
            }))

            new_to_date = parse_date(interrupt({
                "type": "preference_request",
                "preference": "to_date",
                "question": "Please enter the end date (DD.MM.YYYY):"
            }))

            update["from_date"] = new_from_date
            update["to_date"] = new_to_date

            if new_from_date and new_to_date:
                if new_from_date.year < new_to_date.year:
                    update["month"] = "any"
                elif new_from_date.month == new_to_date.month:
                    update["month"] = calendar.month_name[new_from_date.month]
                else:
                    update["month"] = (
                        f"{calendar.month_name[new_from_date.month]} "
                        f"to {calendar.month_name[new_to_date.month]}"
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

