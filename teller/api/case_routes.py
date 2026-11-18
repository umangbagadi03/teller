import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from teller.bank.case import Case
from teller.bank.customers import load_customers
from teller.llm.provider import (
    KEY_PROVIDERS,
    OFFLINE_MODEL,
    get_default_model,
    get_model_name,
    is_offline,
    make_key_settings,
    make_model_name,
    pick_provider,
)

router = APIRouter()

# Cases are kept in memory, so a restart starts every case again.
# Only the newest ones are kept, so old cases and their keys do not pile up.
MAX_CASES = 50
cases = {}

# Key shapes of the providers: Google AIza..., OpenAI sk-..., Anthropic sk-ant-...
KEY_PATTERNS = [r"AIza[0-9A-Za-z_\-*]{10,}", r"sk-[A-Za-z0-9_\-*]{8,}"]


class MessageRequest(BaseModel):
    text: str


class ModelChoice(BaseModel):
    # "server" uses the server's own model, "offline" the scripted demo,
    # and gemini, anthropic or openai use the visitor's own key for this case only
    provider: str = "server"
    model: str = ""
    api_key: str = ""


def remove_keys(text, api_key):
    # A provider's error message can quote part of a key, so keys never leave in an error
    if api_key:
        text = text.replace(api_key, "[key removed]")
    for pattern in KEY_PATTERNS:
        text = re.sub(pattern, "[key removed]", text)
    return text


def explain_error(error, api_key):
    # A short message for the page. Common provider errors get plain words.
    text = remove_keys(str(error), api_key)

    if "AuthenticationError" in text or "API key not valid" in text:
        return "The provider rejected the API key. Check the key and the provider, then start a new case."
    if "RateLimitError" in text or "quota" in text.lower():
        return "The provider's rate limit or quota was reached. Wait a minute, or use another key."
    if "NotFoundError" in text:
        return "The provider does not know this model name. Check the model, then start a new case."

    return "LLM call failed: " + text[:300]


def describe_model(model_name):
    if is_offline(model_name):
        return "Offline demo"
    return model_name


def build_model(choice):
    # Returns the model name and settings for a new case, or None for the server's model
    if choice.provider == "server":
        return None, None

    if choice.provider == "offline":
        return OFFLINE_MODEL, {}

    if choice.provider not in KEY_PROVIDERS:
        raise HTTPException(status_code=400, detail="Pick Gemini, Anthropic or OpenAI.")

    api_key = choice.api_key.strip()
    if len(api_key) < 10:
        raise HTTPException(status_code=400, detail="Paste a full API key for " + choice.provider + ".")

    model_name = make_model_name(choice.provider, choice.model.strip())
    return model_name, make_key_settings(api_key)


def keep_case(case):
    cases[case.id] = case

    # A dictionary keeps the order things were added, so the first key is the oldest case
    while len(cases) > MAX_CASES:
        oldest_id = list(cases.keys())[0]
        del cases[oldest_id]


@router.get("/api/status")
def get_status():
    default_models = {}
    for provider in KEY_PROVIDERS:
        default_models[provider] = get_default_model(provider)

    model_name = get_model_name()
    return {
        "provider": pick_provider(),
        "model": model_name,
        "label": describe_model(model_name),
        "offline": is_offline(model_name),
        "default_models": default_models,
    }


@router.get("/api/customers")
def get_customers():
    return load_customers()


@router.post("/api/cases")
def create_case(choice: ModelChoice | None = None):
    if choice is None:
        choice = ModelChoice()

    llm, llm_args = build_model(choice)
    case = Case(llm, llm_args)
    keep_case(case)

    return {
        "id": case.id,
        "model": describe_model(case.model),
        "offline": is_offline(case.model),
    }


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
        message = explain_error(error, case.get_api_key())
        raise HTTPException(status_code=502, detail=message)
