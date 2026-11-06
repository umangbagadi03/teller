from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage

from teller import config
from teller.agent import nodes
from teller.agent.rules import UNLOCK_TOOL, VERIFICATION_TOOL
from teller.agent.search_tool import SEARCH_TOOL_NAME
from teller.agent.teller_agent import TellerAgent

DOCUMENT = {
    "id": "doc_1",
    "title": "Opening accounts",
    "content": "Use open_bank_account_4821 to open an account.",
}


def make_document(number):
    return {"id": "doc_" + str(number), "title": "Doc " + str(number), "content": "Text " + str(number)}


def make_reply(text=None, tool_name=None, arguments=None, cost=0.01):
    tool_calls = None
    if tool_name:
        tool_calls = [ToolCall(id="call_1", name=tool_name, arguments=arguments)]

    usage = {"prompt_tokens": 100, "completion_tokens": 10}
    return AssistantMessage(
        role="assistant",
        content=text,
        tool_calls=tool_calls,
        cost=cost,
        usage=usage,
    )


class FakeWorld:
    # Replaces the LLM and the search with fixed answers
    def __init__(self, monkeypatch, scripted_replies, found_documents):
        self.remaining_replies = list(scripted_replies)
        self.found_documents = found_documents
        self.llm_prompts = []
        self.llm_tool_lists = []
        self.search_count = 0

        def fake_generate(**kwargs):
            self.llm_prompts.append(kwargs["messages"][0].content)
            self.llm_tool_lists.append(kwargs["tools"])
            return self.remaining_replies.pop(0)

        def fake_search(query, limit=None):
            self.search_count += 1
            return self.found_documents

        monkeypatch.setattr(nodes, "generate", fake_generate)
        monkeypatch.setattr(nodes, "search_documents", fake_search)

    def make_agent(self, use_checks=True):
        return TellerAgent(
            tools=[],
            domain_policy="Bank policy",
            llm="test",
            llm_args={},
            use_checks=use_checks,
        )


def run_agent(monkeypatch, scripted_replies, found_documents, use_checks=True):
    world = FakeWorld(monkeypatch, scripted_replies, found_documents)
    agent = world.make_agent(use_checks)
    state = agent.get_init_state()
    message = UserMessage(role="user", content="Open an account")
    reply, state = agent.generate_next_message(message, state)
    return reply, state, world


def test_plain_reply_goes_to_the_customer(monkeypatch):
    replies = [make_reply(text="Happy to help.")]
    reply, state, world = run_agent(monkeypatch, replies, [])
    assert reply.content == "Happy to help."


def test_first_message_adds_documents_to_the_first_prompt(monkeypatch):
    replies = [make_reply(text="Happy to help.")]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])
    assert "open_bank_account_4821" in world.llm_prompts[0]
    assert state["documents"] == [DOCUMENT]


def test_later_customer_messages_are_not_searched(monkeypatch):
    replies = [make_reply(text="What is your email?"), make_reply(text="Thanks.")]
    world = FakeWorld(monkeypatch, replies, [DOCUMENT])
    agent = world.make_agent()

    state = agent.get_init_state()
    first_message = UserMessage(role="user", content="Open an account")
    reply, state = agent.generate_next_message(first_message, state)

    second_message = UserMessage(role="user", content="Yes please go ahead")
    reply, state = agent.generate_next_message(second_message, state)

    assert world.search_count == 1


def test_search_call_loops_back_and_is_hidden_from_the_benchmark(monkeypatch):
    replies = [
        make_reply(tool_name=SEARCH_TOOL_NAME, arguments={"query": "open account"}),
        make_reply(text="Here is how."),
    ]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert len(world.llm_prompts) == 2
    assert reply.content == "Here is how."
    assert not reply.tool_calls


def test_found_document_moves_to_the_newest_place():
    old_documents = [make_document(1), make_document(2), make_document(3)]

    documents, added = nodes.add_found_documents(old_documents, [make_document(1)])

    assert documents[-1]["id"] == "doc_1"
    assert len(documents) == 3
    assert added == []


def test_document_that_left_the_prompt_comes_back_when_found_again(monkeypatch):
    many_documents = []
    for number in range(config.MAX_DOCUMENTS_IN_PROMPT + 3):
        many_documents.append(make_document(number))

    oldest_document = many_documents[0]
    documents, added = nodes.add_found_documents(many_documents, [oldest_document])

    prompt = nodes.build_system_prompt("policy", documents)
    assert "Text 0" in prompt


def test_cost_of_inner_calls_is_kept(monkeypatch):
    replies = [
        make_reply(tool_name=SEARCH_TOOL_NAME, arguments={"query": "open account"}),
        make_reply(text="Here is how."),
    ]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert round(reply.cost, 4) == 0.02
    assert reply.usage["prompt_tokens"] == 200


def test_search_tool_is_removed_at_the_limit(monkeypatch):
    search_arguments = {"query": "open account"}
    replies = []
    for number in range(config.MAX_SEARCHES_PER_STEP):
        replies.append(make_reply(tool_name=SEARCH_TOOL_NAME, arguments=search_arguments))
    replies.append(make_reply(text="Done searching."))

    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert reply.content == "Done searching."
    assert len(world.llm_tool_lists[0]) == 1
    assert len(world.llm_tool_lists[-1]) == 0


def test_search_call_after_the_limit_cannot_loop_forever(monkeypatch):
    search_arguments = {"query": "open account"}
    replies = []
    total_llm_calls = config.MAX_SEARCHES_PER_STEP + config.MAX_CORRECTIONS_PER_STEP + 1
    for number in range(total_llm_calls):
        replies.append(make_reply(tool_name=SEARCH_TOOL_NAME, arguments=search_arguments))

    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert len(world.llm_prompts) == total_llm_calls


def test_made_up_tool_is_blocked_and_llm_tries_again(monkeypatch):
    replies = [
        make_reply(tool_name=UNLOCK_TOOL, arguments={"agent_tool_name": "made_up"}),
        make_reply(tool_name=UNLOCK_TOOL, arguments={"agent_tool_name": "open_bank_account_4821"}),
    ]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert len(world.llm_prompts) == 2
    assert reply.tool_calls[0].arguments["agent_tool_name"] == "open_bank_account_4821"

    kinds = []
    for step in state["trace"]:
        kinds.append(step["kind"])
    assert "blocked" in kinds


def test_without_checks_a_made_up_tool_is_not_blocked(monkeypatch):
    replies = [make_reply(tool_name=UNLOCK_TOOL, arguments={"agent_tool_name": "made_up"})]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT], use_checks=False)

    assert len(world.llm_prompts) == 1
    assert reply.tool_calls[0].arguments["agent_tool_name"] == "made_up"


def test_tool_name_in_the_policy_passes_the_check(monkeypatch):
    replies = [make_reply(tool_name=UNLOCK_TOOL, arguments={"agent_tool_name": "policy_tool_1234"})]
    world = FakeWorld(monkeypatch, replies, [])
    agent = TellerAgent(
        tools=[],
        domain_policy="Use policy_tool_1234 here.",
        llm="test",
        llm_args={},
    )
    message = UserMessage(role="user", content="Help")
    reply, state = agent.generate_next_message(message, agent.get_init_state())

    assert len(world.llm_prompts) == 1


def test_corrections_stop_at_the_limit(monkeypatch):
    bad_call = {"agent_tool_name": "made_up"}
    replies = [
        make_reply(tool_name=UNLOCK_TOOL, arguments=bad_call),
        make_reply(tool_name=UNLOCK_TOOL, arguments=bad_call),
        make_reply(tool_name=UNLOCK_TOOL, arguments=bad_call),
    ]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert len(world.llm_prompts) == 3
    assert reply.tool_calls[0].name == UNLOCK_TOOL


def test_empty_reply_gets_another_try(monkeypatch):
    replies = [make_reply(text="  "), make_reply(text="Happy to help.")]
    reply, state, world = run_agent(monkeypatch, replies, [])

    assert reply.content == "Happy to help."
    assert nodes.EMPTY_REPLY_NOTE in world.llm_prompts[1]
    assert round(reply.cost, 4) == 0.02


def test_always_empty_replies_end_with_a_short_message(monkeypatch):
    replies = [make_reply(), make_reply(), make_reply()]
    reply, state, world = run_agent(monkeypatch, replies, [])

    assert reply.content == nodes.FALLBACK_REPLY
    reply.validate()


def test_reply_with_text_and_tool_call_keeps_only_the_tool_call(monkeypatch):
    replies = [
        make_reply(
            text="One moment.",
            tool_name=UNLOCK_TOOL,
            arguments={"agent_tool_name": "open_bank_account_4821"},
        ),
    ]
    reply, state, world = run_agent(monkeypatch, replies, [DOCUMENT])

    assert reply.content is None
    assert reply.tool_calls


def test_verification_counts_across_steps(monkeypatch):
    # The agent logs verification in one step, and acts on it in a later one
    replies = [
        make_reply(tool_name=VERIFICATION_TOOL, arguments={}),
        make_reply(tool_name="change_user_email", arguments={"new_email": "a@example.com"}),
    ]
    world = FakeWorld(monkeypatch, replies, [DOCUMENT])
    agent = world.make_agent()

    message = UserMessage(role="user", content="Change my email")
    reply, state = agent.generate_next_message(message, agent.get_init_state())

    tool_result = ToolMessage(id="call_1", role="tool", content="ok", requestor="assistant")
    reply, state = agent.generate_next_message(tool_result, state)

    assert reply.tool_calls[0].name == "change_user_email"
    assert len(world.llm_prompts) == 2
