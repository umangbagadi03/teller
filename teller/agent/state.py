from typing import TypedDict


class AgentState(TypedDict):
    # The conversation so far, in the benchmark's message format
    messages: list

    # The latest customer text, or None when the agent is handling a tool result
    customer_text: str | None

    # Every policy document found during this conversation, oldest first
    documents: list

    # The LLM reply waiting to be checked
    reply: object

    # Limits for the current step, so the agent cannot loop forever
    searches_used: int
    corrections_used: int

    # Extra instruction for the next LLM call, used after an empty reply
    correction_note: str

    # Cost of the LLM calls made inside this step
    extra_cost: float
    extra_usage: dict

    # What happened, for the UI and for debugging
    trace: list
