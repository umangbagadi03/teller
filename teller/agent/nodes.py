import time

from tau2.data_model.message import AssistantMessage, SystemMessage, ToolMessage, UserMessage
from tau2.utils.llm_utils import generate

from teller import config
from teller.agent.prompts import build_system_prompt
from teller.agent.rules import find_problem
from teller.agent.search_tool import SEARCH_TOOL_NAME
from teller.knowledge.hybrid_search import search_documents

CUSTOMER_SEARCH_RESULTS = 4
EMPTY_REPLY_NOTE = "Your last reply was empty. Write a message to the customer or make a tool call."
FALLBACK_REPLY = "I am sorry, could you please say that again?"
SEARCH_LIMIT_NOTE = "Search limit reached. Answer with what you have, or ask the customer."


def add_found_documents(known_documents, found_documents):
    # Found documents always move to the end, which is the newest place in the list.
    # So a document that dropped out of the prompt comes back when it is found again.
    known_ids = []
    for document in known_documents:
        known_ids.append(document["id"])

    found_ids = []
    for document in found_documents:
        found_ids.append(document["id"])

    all_documents = []
    for document in known_documents:
        if document["id"] not in found_ids:
            all_documents.append(document)

    added_documents = []
    for document in found_documents:
        all_documents.append(document)
        if document["id"] not in known_ids:
            added_documents.append(document)

    return all_documents, added_documents


def add_to_trace(state, kind, text, details=None):
    trace = list(state["trace"])
    trace.append({"kind": kind, "text": text, "details": details})
    return trace


def get_titles(documents):
    titles = []
    for document in documents:
        titles.append(document["title"])
    return titles


def is_first_customer_message(messages):
    count = 0
    for message in messages:
        if isinstance(message, UserMessage):
            count += 1
    return count == 1


def retrieve_node(state):
    # Search once on the opening request. This costs no LLM call, so the first LLM
    # call already has the likely policies. Later messages like "yes please" only
    # bring noise, so after this the LLM writes its own searches.
    customer_text = state["customer_text"]
    if not customer_text:
        return {}
    if not is_first_customer_message(state["messages"]):
        return {}

    found = search_documents(customer_text, CUSTOMER_SEARCH_RESULTS)
    documents, added = add_found_documents(state["documents"], found)

    trace = add_to_trace(state, "search", customer_text, get_titles(added))
    return {"documents": documents, "trace": trace}


def think_node(state, agent):
    if config.LLM_PAUSE_SECONDS > 0:
        time.sleep(config.LLM_PAUSE_SECONDS)

    system_prompt = build_system_prompt(
        agent.domain_policy,
        state["documents"],
        state["correction_note"],
    )
    system_message = SystemMessage(role="system", content=system_prompt)

    # Once the limit is reached, the LLM is no longer offered the search tool
    tools = list(agent.tools)
    if state["searches_used"] < config.MAX_SEARCHES_PER_STEP:
        tools.append(agent.search_tool)

    reply = generate(
        model=agent.llm,
        tools=tools,
        messages=[system_message] + state["messages"],
        call_name="agent_response",
        **agent.llm_args,
    )
    return {"reply": reply, "correction_note": ""}


def route_after_think(state):
    reply = state["reply"]
    if not reply.tool_calls:
        return "check"
    if state["searches_used"] >= config.MAX_SEARCHES_PER_STEP:
        return "check"

    for tool_call in reply.tool_calls:
        if tool_call.name == SEARCH_TOOL_NAME:
            return "search"
    return "check"


def keep_step_cost(state, reply):
    # LLM calls made inside a step never reach the benchmark, so their cost and
    # tokens are added to the reply that does.
    extra_cost = state["extra_cost"]
    if reply.cost:
        extra_cost += reply.cost

    extra_usage = dict(state["extra_usage"])
    if reply.usage:
        for key in ["prompt_tokens", "completion_tokens"]:
            extra_usage[key] = extra_usage.get(key, 0) + reply.usage.get(key, 0)

    return extra_cost, extra_usage


def search_node(state):
    reply = state["reply"]
    messages = list(state["messages"])
    documents = state["documents"]
    trace = state["trace"]
    searches_used = state["searches_used"]

    # Only keep the search calls. Other tools can be called on the next pass,
    # once the LLM has read the new documents.
    search_calls = []
    for tool_call in reply.tool_calls:
        if tool_call.name == SEARCH_TOOL_NAME:
            search_calls.append(tool_call)

    assistant_message = AssistantMessage(role="assistant", tool_calls=search_calls)
    messages.append(assistant_message)

    for tool_call in search_calls:
        searches_used += 1

        if searches_used > config.MAX_SEARCHES_PER_STEP:
            content = SEARCH_LIMIT_NOTE
        else:
            query = tool_call.arguments.get("query", "")
            found = search_documents(query)
            documents, added = add_found_documents(documents, found)
            trace = list(trace)
            trace.append({"kind": "search", "text": query, "details": get_titles(added)})

            titles = get_titles(found)
            content = "Found: " + "; ".join(titles) + ". Their text is in your documents."

        tool_message = ToolMessage(
            id=tool_call.id,
            role="tool",
            content=content,
            requestor="assistant",
        )
        messages.append(tool_message)

    extra_cost, extra_usage = keep_step_cost(state, reply)
    return {
        "messages": messages,
        "documents": documents,
        "searches_used": searches_used,
        "extra_cost": extra_cost,
        "extra_usage": extra_usage,
        "trace": trace,
    }


def find_problems(state, agent):
    problems = {}
    reply = state["reply"]
    if not reply.tool_calls:
        return problems

    # The LLM has also read the policy, so a tool name written there counts too
    readable_documents = list(state["documents"])
    readable_documents.append({"content": agent.domain_policy})

    for tool_call in reply.tool_calls:
        if tool_call.name == SEARCH_TOOL_NAME:
            problems[tool_call.id] = SEARCH_LIMIT_NOTE
            continue

        problem = find_problem(tool_call, readable_documents, state["messages"])
        if problem:
            problems[tool_call.id] = problem
    return problems


def reply_is_empty(reply):
    if reply.tool_calls:
        return False
    if reply.content and reply.content.strip():
        return False
    return True


def check_empty_reply(state, reply):
    # The benchmark raises an error on an empty message. So ask once more,
    # and after the limit send a short reply that keeps the conversation going.
    if state["corrections_used"] >= config.MAX_CORRECTIONS_PER_STEP:
        reply.content = FALLBACK_REPLY
        return {"reply": reply}

    extra_cost, extra_usage = keep_step_cost(state, reply)
    return {
        "reply": None,
        "correction_note": EMPTY_REPLY_NOTE,
        "corrections_used": state["corrections_used"] + 1,
        "extra_cost": extra_cost,
        "extra_usage": extra_usage,
    }


def check_node(state, agent):
    reply = state["reply"]

    if reply_is_empty(reply):
        return check_empty_reply(state, reply)

    # The benchmark rejects a reply that has both text and tool calls
    if reply.tool_calls:
        reply.content = None

    problems = {}
    if agent.use_checks:
        problems = find_problems(state, agent)

    no_more_corrections = state["corrections_used"] >= config.MAX_CORRECTIONS_PER_STEP
    if not problems or no_more_corrections:
        return {"reply": reply}

    # Send the blocked calls back to the LLM instead of to the bank
    messages = list(state["messages"])
    trace = state["trace"]
    assistant_message = AssistantMessage(role="assistant", tool_calls=reply.tool_calls)
    messages.append(assistant_message)

    for tool_call in reply.tool_calls:
        content = "Not run because another call in this turn was blocked."
        if tool_call.id in problems:
            content = problems[tool_call.id]
            trace = list(trace)
            trace.append({"kind": "blocked", "text": tool_call.name, "details": [content]})

        tool_message = ToolMessage(
            id=tool_call.id,
            role="tool",
            content=content,
            requestor="assistant",
            error=True,
        )
        messages.append(tool_message)

    extra_cost, extra_usage = keep_step_cost(state, reply)
    return {
        "messages": messages,
        "reply": None,
        "corrections_used": state["corrections_used"] + 1,
        "extra_cost": extra_cost,
        "extra_usage": extra_usage,
        "trace": trace,
    }


def route_after_check(state):
    if state["reply"] is None:
        return "think"
    return "finish"
