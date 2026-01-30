from langchain_core.messages import SystemMessage, HumanMessage , ToolMessage , AIMessage
import json
import re
import requests
from datetime import date
from typing import Optional
from dateutil import parser

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

    # Try day-first first
    try:
        d1 = parser.parse(value, dayfirst=True, yearfirst=False).date()
    except Exception:
        d1 = None

    # Try month-first
    try:
        d2 = parser.parse(value, dayfirst=False, yearfirst=False).date()
    except Exception:
        d2 = None

    if d1 and d2:
        if d1.month < 12:
            return d1
        if d2.month < 12:
            return d2
        return d1

    return d1 or d2


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
