from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage

from teller.agent.rules import (
    CALL_TOOL,
    CHANGE_EMAIL_TOOL,
    GIVE_TOOL,
    UNLOCK_TOOL,
    VERIFICATION_TOOL,
    find_problem,
)

TOOL_NAME = "open_bank_account_4821"
TRANSFER_NAME = "emergency_transfer_1114"
DOCUMENTS = [
    {
        "id": "doc_1",
        "title": "Opening",
        "content": "Use open_bank_account_4821 to open it. Or use emergency_transfer_1114.",
    }
]


def make_call(name, arguments, call_id="1"):
    return ToolCall(id=call_id, name=name, arguments=arguments)


def make_history(tool_call, content="ok", error=False):
    assistant_message = AssistantMessage(role="assistant", tool_calls=[tool_call])
    tool_message = ToolMessage(
        id=tool_call.id,
        role="tool",
        content=content,
        requestor="assistant",
        error=error,
    )
    return [assistant_message, tool_message]


def verified_history():
    return make_history(make_call(VERIFICATION_TOOL, {}, "verify"))


def unlocked_history():
    unlock_call = make_call(UNLOCK_TOOL, {"agent_tool_name": TOOL_NAME}, "unlock")
    return verified_history() + make_history(unlock_call)


def test_other_tools_are_not_checked():
    tool_call = make_call("get_current_time", {})
    assert find_problem(tool_call, [], []) is None


def test_unlock_needs_a_name_from_the_documents():
    tool_call = make_call(UNLOCK_TOOL, {"agent_tool_name": "made_up_tool"})
    assert "does not appear" in find_problem(tool_call, DOCUMENTS, [])


def test_part_of_a_real_name_is_not_enough():
    tool_call = make_call(UNLOCK_TOOL, {"agent_tool_name": "bank_account"})
    assert "does not appear" in find_problem(tool_call, DOCUMENTS, [])


def test_unlock_with_a_known_name_is_fine():
    tool_call = make_call(UNLOCK_TOOL, {"agent_tool_name": TOOL_NAME})
    assert find_problem(tool_call, DOCUMENTS, []) is None


def test_give_needs_a_name_from_the_documents():
    tool_call = make_call(GIVE_TOOL, {"discoverable_tool_name": "made_up_tool"})
    assert "does not appear" in find_problem(tool_call, DOCUMENTS, [])


def test_call_must_come_after_unlock():
    tool_call = make_call(CALL_TOOL, {"agent_tool_name": TOOL_NAME})
    assert "Unlock" in find_problem(tool_call, DOCUMENTS, verified_history())


def test_a_failed_unlock_does_not_count():
    unlock_call = make_call(UNLOCK_TOOL, {"agent_tool_name": TOOL_NAME}, "unlock")
    history = verified_history() + make_history(unlock_call, "Not run", error=True)

    tool_call = make_call(CALL_TOOL, {"agent_tool_name": TOOL_NAME})
    assert "Unlock" in find_problem(tool_call, DOCUMENTS, history)


def test_call_after_verify_and_unlock_is_fine():
    tool_call = make_call(CALL_TOOL, {"agent_tool_name": TOOL_NAME})
    assert find_problem(tool_call, DOCUMENTS, unlocked_history()) is None


def test_call_needs_verification():
    unlock_call = make_call(UNLOCK_TOOL, {"agent_tool_name": TOOL_NAME}, "unlock")
    history = make_history(unlock_call)

    tool_call = make_call(CALL_TOOL, {"agent_tool_name": TOOL_NAME})
    assert "Verify the customer" in find_problem(tool_call, DOCUMENTS, history)


def test_changing_an_email_needs_verification():
    tool_call = make_call(CHANGE_EMAIL_TOOL, {"new_email": "a@example.com"})
    assert "Verify the customer" in find_problem(tool_call, DOCUMENTS, [])


def test_failed_verification_does_not_count():
    verify_call = make_call(VERIFICATION_TOOL, {}, "verify")
    history = make_history(verify_call, "Error: wrong details")

    tool_call = make_call(CHANGE_EMAIL_TOOL, {"new_email": "a@example.com"})
    assert "Verify the customer" in find_problem(tool_call, DOCUMENTS, history)


def test_verification_that_could_not_be_logged_does_not_count():
    verify_call = make_call(VERIFICATION_TOOL, {}, "verify")
    history = make_history(verify_call, "Failed to log verification: Record may already exist.")

    tool_call = make_call(CHANGE_EMAIL_TOOL, {"new_email": "a@example.com"})
    assert "Verify the customer" in find_problem(tool_call, DOCUMENTS, history)


def test_emergency_transfer_does_not_need_verification():
    unlock_call = make_call(UNLOCK_TOOL, {"agent_tool_name": TRANSFER_NAME}, "unlock")
    history = make_history(unlock_call)

    tool_call = make_call(CALL_TOOL, {"agent_tool_name": TRANSFER_NAME})
    assert find_problem(tool_call, DOCUMENTS, history) is None
