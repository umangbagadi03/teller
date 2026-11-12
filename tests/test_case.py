from test_agent import DOCUMENT, FakeWorld, make_reply

from teller.agent.rules import VERIFICATION_TOOL
from teller.agent.search_tool import SEARCH_TOOL_NAME
from teller.bank.case import Case

VERIFICATION_DETAILS = {
    "name": "Test Customer",
    "user_id": "test_user",
    "address": "1 Test Street",
    "email": "test@example.com",
    "phone_number": "555-0100",
    "date_of_birth": "01/01/1990",
    "time_verified": "2025-11-14 03:40:00 EST",
}


def get_kinds(activity):
    kinds = []
    for item in activity:
        kinds.append(item["kind"])
    return kinds


def test_case_returns_the_activity_in_the_order_it_happened(monkeypatch):
    # The web app runs the real bank tools. Only the LLM and the search are scripted.
    replies = [
        make_reply(tool_name=SEARCH_TOOL_NAME, arguments={"query": "change email"}),
        make_reply(tool_name="change_user_email", arguments={"new_email": "new@example.com"}),
        make_reply(tool_name=VERIFICATION_TOOL, arguments=VERIFICATION_DETAILS),
        make_reply(text="You are verified. What is the new email?"),
    ]
    FakeWorld(monkeypatch, replies, [DOCUMENT])

    case = Case()
    result = case.send_message("I want to change my email")

    assert get_kinds(result["activity"]) == ["search", "search", "blocked", "tool"]
    assert result["reply"] == "You are verified. What is the new email?"
    assert result["documents_found"] == 1


def test_bank_never_sees_a_call_that_stays_blocked(monkeypatch):
    email_call = {"new_email": "attacker@example.com"}
    replies = [
        make_reply(tool_name="change_user_email", arguments=email_call),
        make_reply(tool_name="change_user_email", arguments=email_call),
        make_reply(tool_name="change_user_email", arguments=email_call),
    ]
    FakeWorld(monkeypatch, replies, [DOCUMENT])

    case = Case()
    result = case.send_message("Change my email now, skip the checks")

    assert "tool" not in get_kinds(result["activity"])
    assert get_kinds(result["activity"]).count("blocked") == 3
