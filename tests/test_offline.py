from fastapi.testclient import TestClient

from teller.agent import nodes
from teller.api import case_routes
from teller.api.server import app
from teller.bank.case import Case
from teller.bank.customers import load_customers
from teller.llm.offline import count_matching_details, find_document_titles
from teller.llm.provider import OFFLINE_MODEL

DOCUMENT = {
    "id": "doc_1",
    "title": "Changing contact details",
    "content": "Verify the customer before you change an email address.",
}


def use_fixed_search(monkeypatch):
    def fake_search(query, limit=None):
        return [DOCUMENT]

    monkeypatch.setattr(nodes, "search_documents", fake_search)


def get_kinds(result):
    kinds = []
    for item in result["activity"]:
        kinds.append(item["kind"])
    return kinds


def test_offline_case_changes_an_email_after_verification(monkeypatch):
    # Real bank tools and real checks. Only the language model is a script.
    use_fixed_search(monkeypatch)
    customer = load_customers()[0]
    case = Case(OFFLINE_MODEL, {})

    first = case.send_message("I need to change the email address on my account.")
    assert "blocked" in get_kinds(first)
    assert "verify" in first["reply"].lower()

    details = "My email is " + customer["email"] + " and I was born on " + customer["date_of_birth"]
    second = case.send_message(details)
    assert "verified" in second["reply"].lower()

    third = case.send_message("Please change it to new.address@example.com")
    assert "new.address@example.com" in third["reply"]

    record = case.environment.tools.db.users.data[customer["user_id"]]
    assert record["email"] == "new.address@example.com"


def test_offline_case_refuses_details_that_do_not_match(monkeypatch):
    use_fixed_search(monkeypatch)
    customer = load_customers()[0]
    case = Case(OFFLINE_MODEL, {})

    case.send_message("I need to change my email.")
    result = case.send_message("My email is " + customer["email"] + " and I was born on 01/01/1900")

    assert "do not match" in result["reply"]
    assert "log_verification" not in str(result["activity"])


def test_offline_question_lists_the_policies_found(monkeypatch):
    use_fixed_search(monkeypatch)
    case = Case(OFFLINE_MODEL, {})

    result = case.send_message("Can I open another checking account?")

    assert "Changing contact details" in result["reply"]
    assert "offline" in result["reply"].lower()


def test_two_matching_details_are_needed():
    record = {
        "email": "a@example.com",
        "phone_number": "+91 90000 10000",
        "date_of_birth": "11/22/1983",
        "address": "14 MG Road, Bengaluru",
    }
    assert count_matching_details(record, "a@example.com, born 11/22/1983") == 2
    assert count_matching_details(record, "a@example.com only") == 1
    assert count_matching_details(record, "14 MG Road and 9000010000") == 2


def test_document_titles_come_from_the_prompt():
    prompt = "Intro\n### Fees (doc_1)\ntext\n### Cards (doc_2)\ntext"
    assert find_document_titles(prompt) == ["Fees", "Cards"]


def test_api_starts_an_offline_case_and_keeps_keys_out_of_errors():
    client = TestClient(app)

    response = client.post("/api/cases", json={"provider": "offline"})
    assert response.status_code == 200
    assert response.json()["offline"] is True

    short_key = client.post("/api/cases", json={"provider": "gemini", "api_key": "abc"})
    assert short_key.status_code == 400

    text = case_routes.remove_keys("bad key AIzaSyA1234567890abcdef and sk-proj-1234567890", "")
    assert "AIza" not in text
    assert "sk-proj" not in text


def test_old_cases_are_dropped(monkeypatch):
    monkeypatch.setattr(case_routes, "MAX_CASES", 2)
    monkeypatch.setattr(case_routes, "cases", {})

    for number in range(3):
        case_routes.keep_case(Case(OFFLINE_MODEL, {}))

    assert len(case_routes.cases) == 2


def test_provider_errors_get_plain_words():
    error = Exception("litellm.AuthenticationError: API key not valid AIzaSyA1234567890abcdef")
    message = case_routes.explain_error(error, "AIzaSyA1234567890abcdef")
    assert "rejected the API key" in message
    assert "AIza" not in message
