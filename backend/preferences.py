from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class Preference:
    key: str
    question: str
    options: List[str]
    
PREFERENCES: Dict[str, Preference] = {
    "location": Preference(
        key="location",
        question="Which location or city are you planning to visit?",
        options=[
            "Paris", "New York", "Tokyo", "London", "Sydney", 
            "Rome", "Bali", "Istanbul", "Dubai", "Other / Not decided"
        ]
    ),

    "source_location": Preference(
        key="source_location",
        question="From which city will you be starting your journey?",
        options=[
            "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad",
            "Kolkata", "Pune", "Coimbatore", "Other / Not decided"
        ]
    ),

    "budget": Preference(
        key="budget",
        question="What's your budget range for this trip to {location}?",
        options=["Budget-friendly", "Mid-range", "Luxury", "No specific budget"]
    ),

    "season": Preference(
        key="season",
        question="What season or time of year are you planning to travel?",
        options=["Spring", "Summer", "Fall", "Winter", "Flexible"]
    ),

    "month": Preference(
        key="month",
        question="Which month are you planning to travel?",
        options=[
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December",
            "Not decided / Flexible"
        ]
    ),

    "experience_type": Preference(
        key="experience_type",
        question="What type of experience are you looking for?",
        options=[
            "Spiritual/Religious",
            "Relaxing/Leisure",
            "Cultural/Sightseeing",
            "Adventure/Active",
            "Mix of everything"
        ]
    ),

    "trip_days": Preference(
        key="trip_days",
        question="How many days are you planning to spend on this trip?",
        options=["1–3 days", "4–7 days", "8–14 days", "More than 14 days"]
    ),

    "people": Preference(
        key="people",
        question="How many people will be traveling?",
        options=["Solo", "Couple", "Family", "Group (3+ people)"]
    ),
}
