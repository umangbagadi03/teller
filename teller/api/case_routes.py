from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from teller.bank.case import Case
from teller.bank.customers import load_customers
from teller.llm.provider import get_model_name, pick_provider

router = APIRouter()

# Cases are kept in memory, so a restart starts every case again
cases = {}


class MessageRequest(BaseModel):
    text: str


@router.get("/api/status")
def get_status():
    return {"provider": pick_provider(), "model": get_model_name()}


@router.get("/api/customers")
def get_customers():
    return load_customers()


@router.post("/api/cases")
def create_case():
    case = Case()
    cases[case.id] = case
    return {"id": case.id, "model": case.model}


@router.post("/api/cases/{case_id}/messages")
def send_message(case_id: str, request: MessageRequest):
    case = cases.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found. Open a new case.")

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Write a message first.")

    try:
        return case.send_message(text)
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM call failed: " + str(error))
