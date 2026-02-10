import calendar
from langchain_core.messages import SystemMessage, HumanMessage , ToolMessage 
import json
import re
import requests
from datetime import date
from typing import Optional
from dateutil import parser
from langgraph.types import interrupt
from models import invoke_llm


def invoke_model(model=None, systemMessage: str = "", humanMessage: str = ""):
    messages_to_llm = [
        SystemMessage(content=systemMessage),
        HumanMessage(content=humanMessage),
    ]

    if model is not None:
        return model.invoke(messages_to_llm)

    return invoke_llm(messages_to_llm)

def remove_markdown(response):
  
    content = response.content.strip()
        
    if content.startswith("```"):
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
    return content


def is_null(value) -> bool:
    return (
        value is None or
        value == "" or
        (isinstance(value, str) and value.strip().lower() == "null")
    )


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return parser.parse(value, dayfirst=True).date()
    except Exception:
        return None

def correct_locations_with_llm(
    llm,
    source_name: str | None,
    destination_name: str | None
) -> dict:
    """
    Uses LLM to correct and standardize Indian location names.
    Returns: {"source": str|None, "destination": str|None}
    """

    context = f"""
You are a location spelling corrector and standardizer.

INPUT:
- Source: {source_name}
- Destination: {destination_name}

TASK:
1. Correct spelling mistakes
2. Expand abbreviations (e.g., "cbe" → "Coimbatore", "blr" → "Bangalore")
3. Fix typos
4. Use official Indian city/state names

RULES:
- If already correct, keep as-is
- If null/empty, keep as null
- Return ONLY valid JSON
- No markdown, no explanations

OUTPUT FORMAT (exactly):
{{
  "source": "corrected_source_name",
  "destination": "corrected_destination_name"
}}
"""

    response = invoke_model(model=llm, humanMessage=context)
    response = remove_markdown(response=response)

    try:
        return json.loads(response.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from location corrector: {response}") from e


def collect_tool_results(messages: list) -> str:
   
    tool_contents = []

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_contents.append(msg.content)
        else:
            break

    tool_contents.reverse() 
    return "\n\n".join(tool_contents)

def derive_month(from_date, to_date):
    if not from_date or not to_date:
        return None

    if from_date.year < to_date.year:
        return "any"
    if from_date.month == to_date.month:
        return calendar.month_name[from_date.month]

    return f"{calendar.month_name[from_date.month]} to {calendar.month_name[to_date.month]}"


def ask_for_dates(from_date=None, to_date=None):
    new_from = parse_date(interrupt({
        "type": "interrupt",
        "key": "from_date",
        "question": "Please enter the start date (DD.MM.YYYY):",
        "input_type": "date",
        "options": None,
        "default": str(from_date) if from_date else None,
        "meta": {}
        })
        )

    new_to = parse_date(interrupt({
        "type": "interrupt",
        "key": "to_date",
        "question": "Please enter the end date (DD.MM.YYYY):",
        "input_type": "date",
        "options": None,
        "default": str(to_date) if to_date else None,
        "meta": {}
        })
        )

    return new_from, new_to


def handle_date_update(update, from_date, to_date):
    update["from_date"] = from_date.strftime("%d.%m.%Y") if from_date else None
    update["to_date"] = to_date.strftime("%d.%m.%Y") if to_date else None

    if from_date and to_date:
        update["month"] = derive_month(from_date, to_date)

        
def is_greeting_via_llm(llm, user_query: str) -> bool:

    
    GREETING_CLASSIFIER_PROMPT = """
    You are an intent classifier.

    Decide whether the user's message is ONLY a greeting
    (e.g., hi, hello, hey, good morning).

    If it is ONLY a greeting, reply with:
    GREETING

    If it asks for any information, help, or task, reply with:
    NOT_GREETING

    Reply with only one word.
    """

    response = invoke_model(
        model=llm,
        systemMessage=GREETING_CLASSIFIER_PROMPT,
        humanMessage=user_query
    )

    return response.content.strip().upper() == "GREETING"

