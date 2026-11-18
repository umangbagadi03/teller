import re

from tau2.data_model.message import AssistantMessage, ToolCall

# The offline demo: a short script plays the language model, so the web app works
# with no API key. Search, the checks and the bank tools stay real. The script only
# knows one task end to end, changing an email address. It proves the plumbing,
# not how good a real model is, so it is never used for benchmark scores.

VERIFICATION_TIME = "2025-11-14 03:40:00 EST"
EMAIL_PATTERN = r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.]+"
MAX_TITLES = 4

ASK_FOR_DETAILS = (
    "Before I change anything I need to verify you. Please tell me the email on your account "
    "and one more detail: your date of birth, phone number or address."
)
OFFLINE_LIMIT = (
    "This is the offline demo, so a short script plays the language model and cannot explain "
    "policies. Add your own API key under Model for a full answer. Changing your email works "
    "end to end offline, so try that."
)


def make_reply(text):
    return AssistantMessage(role="assistant", content=text, cost=0.0)


def make_tool_call(messages, name, arguments):
    call_id = "offline_" + str(len(messages))
    tool_call = ToolCall(id=call_id, name=name, arguments=arguments)
    return AssistantMessage(role="assistant", tool_calls=[tool_call], cost=0.0)


def find_emails(text):
    return re.findall(EMAIL_PATTERN, text)


def keep_digits(text):
    digits = ""
    for character in text:
        if character.isdigit():
            digits += character
    return digits


def read_record(text):
    # A lookup result has lines like "   email: aarav.sharma@example.com"
    record = {}
    for line in text.split("\n"):
        if ": " not in line:
            continue
        key, value = line.strip().split(": ", 1)
        record[key] = value
    return record


def count_matching_details(record, text):
    # Verification needs two of four details to match the account
    lower_text = text.lower()
    matches = 0

    email = record.get("email", "").lower()
    if email and email in lower_text:
        matches += 1

    phone_digits = keep_digits(record.get("phone_number", ""))
    if phone_digits and phone_digits[-10:] in keep_digits(text):
        matches += 1

    if record.get("date_of_birth", "") and record["date_of_birth"] in text:
        matches += 1

    # The first part of the address, like "14 MG Road", is enough
    street = record.get("address", "").split(",")[0].lower()
    if street and street in lower_text:
        matches += 1

    return matches


def find_document_titles(system_text):
    # The system prompt lists each document as "### Title (id)"
    titles = []
    for line in system_text.split("\n"):
        if not line.startswith("### "):
            continue
        # Drop the "### " in front and the " (id)" at the end
        title = line[4:]
        id_start = title.rfind(" (")
        if id_start != -1:
            title = title[:id_start]
        titles.append(title)

    # The newest documents are at the end of the list
    return titles[-MAX_TITLES:]


def get_tool_names(messages):
    # Maps each tool call id to the tool's name, so a result can be matched to its call
    names = {}
    for message in messages:
        if message.role != "assistant" or not message.tool_calls:
            continue
        for tool_call in message.tool_calls:
            names[tool_call.id] = tool_call.name
    return names


def get_customer_texts(messages):
    texts = []
    for message in messages:
        if message.role == "user" and message.content:
            texts.append(message.content)
    return texts


def find_verified_record(messages):
    # The account the customer proved they own, or None before verification
    tool_names = get_tool_names(messages)
    record = None
    verified = False

    for message in messages:
        if message.role != "tool" or message.error:
            continue
        name = tool_names.get(message.id, "")
        text = str(message.content)
        if name == "get_user_information_by_email" and text.startswith("Found 1 record"):
            record = read_record(text)
        if name == "log_verification" and text.startswith("Verification logged"):
            verified = True

    if verified:
        return record
    return None


def explain_documents(system_text):
    titles = find_document_titles(system_text)
    if not titles:
        return "I did not find a policy for that yet. " + OFFLINE_LIMIT

    lines = "I found these policies for your request:"
    for title in titles:
        lines += "\n- " + title
    return lines + "\n\n" + OFFLINE_LIMIT


def answer_tool_result(messages, wants_email_change):
    last = messages[-1]
    text = str(last.content)
    tool_names = get_tool_names(messages)
    name = tool_names.get(last.id, "")

    # The check in code stopped a call because nobody was verified yet
    if last.error and text.startswith("Verify the customer first"):
        return make_reply(ASK_FOR_DETAILS)

    if name == "get_user_information_by_email":
        if not text.startswith("Found 1 record"):
            return make_reply("I could not find an account with that email. Please check it and try again.")

        record = read_record(text)
        customer_texts = get_customer_texts(messages)
        latest_text = customer_texts[-1]
        if count_matching_details(record, latest_text) < 2:
            return make_reply(
                "Those details do not match the account for that email. "
                "Please check them and send the email with one more detail."
            )

        arguments = {
            "name": record["name"],
            "user_id": record["user_id"],
            "address": record["address"],
            "email": record["email"],
            "phone_number": record["phone_number"],
            "date_of_birth": record["date_of_birth"],
            "time_verified": VERIFICATION_TIME,
        }
        return make_tool_call(messages, "log_verification", arguments)

    if name == "log_verification":
        record = find_verified_record(messages)
        if record is None:
            return make_reply("I could not complete the verification. Please try again.")
        if wants_email_change:
            return make_reply("Thank you, " + record["name"] + ". You are verified. What should the new email address be?")
        return make_reply("Thank you, " + record["name"] + ". You are verified. " + OFFLINE_LIMIT)

    if name == "change_user_email":
        if text.startswith("Email updated"):
            new_email = find_emails(text)[0]
            return make_reply("Done. Your email is now " + new_email + ". Is there anything else I can help with?")
        return make_reply("I could not change the email. The bank said: " + text)

    return make_reply("Done. Is there anything else I can help with?")


def answer_customer(messages, wants_email_change):
    customer_texts = get_customer_texts(messages)
    latest_text = customer_texts[-1]
    record = find_verified_record(messages)

    if record is None:
        emails = find_emails(latest_text)
        if emails:
            return make_tool_call(messages, "get_user_information_by_email", {"email": emails[0]})

        # On the first message the script jumps straight to the action, as a careless
        # model might. The check in code blocks it, which is what this demo shows.
        if len(customer_texts) == 1 and wants_email_change:
            return make_tool_call(messages, "change_user_email", {"user_id": "unknown", "new_email": "unknown"})

        if len(customer_texts) == 1:
            return make_reply(explain_documents(messages[0].content))

        return make_reply(ASK_FOR_DETAILS)

    if not wants_email_change:
        return make_reply(OFFLINE_LIMIT)

    emails = find_emails(latest_text)
    if not emails:
        return make_reply("What should the new email address be?")

    arguments = {"user_id": record["user_id"], "new_email": emails[0]}
    return make_tool_call(messages, "change_user_email", arguments)


def offline_reply(messages):
    # messages[0] is the system prompt, with the documents found so far
    customer_texts = get_customer_texts(messages)
    if not customer_texts:
        return make_reply("Hello, how can I help you today?")

    wants_email_change = "email" in customer_texts[0].lower()

    last = messages[-1]
    if last.role == "tool":
        return answer_tool_result(messages, wants_email_change)
    return answer_customer(messages, wants_email_change)
