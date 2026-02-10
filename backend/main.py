from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Union, Dict
from dotenv import load_dotenv

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from graph import create_travel_workflow
from travelstate import TravelState

load_dotenv()

# ------------------ APP ------------------

app = FastAPI(title="AI Travel Assistant")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ GRAPH ------------------

memory = MemorySaver()
graph = create_travel_workflow()

# ------------------ REQUEST MODEL ------------------

class ChatRequest(BaseModel):
    user_query: Optional[str] = None
    interrupt_response: Optional[str] = None
    session_id: str
    pdf: Optional[str] = None

# ------------------ RESPONSE MODELS ------------------

class FinalResponse(BaseModel):
    type: str = "final"
    answer: str

class InterruptResponse(BaseModel):
    type: str = "interrupt"
    key: Optional[str]
    question: str
    input_type: str
    options: Optional[List[str]] = None
    default: Optional[str] = None
    trip_plan: Optional[str] = None
    meta: Dict = {}

# ------------------ ENDPOINT ------------------

@app.post(
    "/travel",
    response_model=Union[FinalResponse, InterruptResponse]
)
def travel_assistant(request: ChatRequest):

    config = {
        "configurable": {
            "thread_id": request.session_id
        }
    }

    # RESUME AFTER INTERRUPT
    if request.interrupt_response is not None:
        result = graph.invoke(
            Command(resume=request.interrupt_response),
            config=config
        )

    # INITIAL MESSAGE
    else:
        initial_state = TravelState(user_query=request.user_query)
        result = graph.invoke(initial_state, config=config)

    # INTERRUPT
    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value
        
        # Use 'key' instead of 'preference'
        preference_key = interrupt_data.get("key")
        question = interrupt_data.get("question", "")
        interrupt_type = interrupt_data.get("type")
        
        # Use input_type directly from interrupt_data if provided
        input_type = interrupt_data.get("input_type")
        
        # Fallback logic if input_type not in interrupt_data
        if not input_type:
            if interrupt_type == "confirmation_request":
                input_type = "confirm"
            elif interrupt_type == "refinement_request":
                input_type = "type"
            elif preference_key in ["from_date", "to_date"]:
                input_type = "date"
            elif interrupt_data.get("options"):
                input_type = "select"
            else:
                input_type = "type"
        

        return InterruptResponse(
            key=preference_key,
            question=question,
            input_type=input_type,
            options=interrupt_data.get("options"),
            default=interrupt_data.get("default"),
            trip_plan=interrupt_data.get("trip_plan"),
            meta=interrupt_data.get("meta", {})
        )

    # FINAL ANSWER
    return FinalResponse(
        answer=result.get(
            "final_result",
            "Sorry, I couldn't process your request."
        )
    )