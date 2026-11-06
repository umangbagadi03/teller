import re

UNLOCK_TOOL = "unlock_discoverable_agent_tool"
CALL_TOOL = "call_discoverable_agent_tool"
GIVE_TOOL = "give_discoverable_user_tool"
VERIFICATION_TOOL = "log_verification"
CHANGE_EMAIL_TOOL = "change_user_email"

# Emergency transfers are the one case the policy allows before verification
NO_VERIFICATION_WORD = "transfer"


def get_discoverable_name(tool_call):
    arguments = tool_call.arguments
    if "agent_tool_name" in arguments:
        return arguments["agent_tool_name"]
    return arguments.get("discoverable_tool_name", "")


def name_is_in_documents(tool_name, documents):
    if not tool_name:
        return False

    # The whole name must match, so "account" does not pass because of "bank_account"
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(tool_name) + r"(?![A-Za-z0-9_])"

    for document in documents:
        if re.search(pattern, document["content"]):
            return True
    return False


def get_successful_results(messages):
    # A call only counts if its result came back without an error
    successful_ids = []
    for message in messages:
        if getattr(message, "role", "") != "tool":
            continue
        if message.error:
            continue
        text = str(message.content)
        if text.startswith("Error") or text.startswith("Failed"):
            continue
        successful_ids.append(message.id)
    return successful_ids


def get_successful_calls(messages):
    successful_ids = get_successful_results(messages)

    successful_calls = []
    for message in messages:
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for tool_call in tool_calls:
            if tool_call.id in successful_ids:
                successful_calls.append(tool_call)
    return successful_calls


def get_unlocked_tools(messages):
    unlocked_tools = []
    for tool_call in get_successful_calls(messages):
        if tool_call.name == UNLOCK_TOOL:
            unlocked_tools.append(get_discoverable_name(tool_call))
    return unlocked_tools


def customer_is_verified(messages):
    for tool_call in get_successful_calls(messages):
        if tool_call.name == VERIFICATION_TOOL:
            return True
    return False


def needs_verification(tool_call):
    if tool_call.name == CHANGE_EMAIL_TOOL:
        return True

    if tool_call.name == CALL_TOOL:
        tool_name = get_discoverable_name(tool_call)
        return NO_VERIFICATION_WORD not in tool_name

    return False


def find_problem(tool_call, documents, messages):
    # These checks run in code, so a rule still holds when the LLM forgets it.
    # They return the correction to send back to the LLM, or None when all is fine.
    if needs_verification(tool_call) and not customer_is_verified(messages):
        return (
            "Verify the customer first. Confirm two details with them, call "
            + VERIFICATION_TOOL + ", and then try this again."
        )

    if tool_call.name not in [UNLOCK_TOOL, CALL_TOOL, GIVE_TOOL]:
        return None

    tool_name = get_discoverable_name(tool_call)

    if not name_is_in_documents(tool_name, documents):
        return (
            "'" + tool_name + "' does not appear in any policy document you have read. "
            "Use search_policies to find the exact tool name. Do not guess it."
        )

    if tool_call.name == CALL_TOOL:
        if tool_name not in get_unlocked_tools(messages):
            return "Unlock '" + tool_name + "' with " + UNLOCK_TOOL + " before calling it."

    return None
