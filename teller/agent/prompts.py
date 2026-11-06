from teller import config

AGENT_INSTRUCTIONS = """You are a customer service agent for Rho-Bank.

How to work:
- The policy documents below were found for this conversation. Read them before you act.
- Only the first customer message is searched automatically. For anything new or missing,
  call search_policies with a specific query.
- Search again with other words if the first search misses. Do not guess a policy.
- Tool names for discoverable tools must come exactly from a policy document.
- In each turn, either send a message to the customer or make tool calls, not both.
- Verify the customer before you read or change their private information.
"""


def format_documents(documents):
    if not documents:
        return "No policy documents found yet."

    # The newest documents are the most likely to matter, and this keeps prompts small
    recent_documents = documents[-config.MAX_DOCUMENTS_IN_PROMPT:]

    parts = []
    for document in recent_documents:
        part = "### " + document["title"] + " (" + document["id"] + ")\n" + document["content"]
        parts.append(part)

    return "\n\n".join(parts)


def build_system_prompt(policy, documents, correction_note=""):
    prompt = AGENT_INSTRUCTIONS
    prompt += "\n<policy>\n" + policy + "\n</policy>\n"
    prompt += "\n<documents>\n" + format_documents(documents) + "\n</documents>"

    if correction_note:
        prompt += "\n\n" + correction_note

    return prompt
