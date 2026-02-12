import os
import uuid
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union, Dict
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from graph import create_travel_workflow
from travelstate import TravelState

load_dotenv()

app = FastAPI(title="AI Travel Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = create_travel_workflow()

class ChatRequest(BaseModel):
    user_query: Optional[str] = None
    interrupt_response: Optional[str] = None
    session_id: str
    pdf: Optional[str] = None


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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

    if request.interrupt_response is not None:
        result = graph.invoke(
            Command(resume=request.interrupt_response),
            config=config
        )

    else:
        initial_state = TravelState(user_query=request.user_query,pdf_path=request.pdf if request.pdf else None)
        result = graph.invoke(initial_state, config=config)

    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value
        
        preference_key = interrupt_data.get("key")
        question = interrupt_data.get("question", "")
        interrupt_type = interrupt_data.get("type")
        
        input_type = interrupt_data.get("input_type")
        
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

    return FinalResponse(
        answer=result.get(
            "final_result",
            "Sorry, I couldn't process your request."
        )
    )


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    allowed_types = {
        "application/pdf",
        "image/png",
        "image/jpeg"
    }

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only PDF, PNG, JPG files are allowed"
        )
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return JSONResponse({
        "path": file_path
    })


