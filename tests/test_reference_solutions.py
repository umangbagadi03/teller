from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage

from teller.agent.rules import find_problem
from teller.benchmark.task_split import load_raw_tasks
from teller.knowledge.documents import load_documents


def replay_task(task, documents):
    # Runs one correct solution through the rules, as if the agent had written it
    problems = []
    messages = []
    actions = task["evaluation_criteria"].get("actions") or []

    for position, action in enumerate(actions):
        if action.get("requestor") != "assistant":
            continue

        tool_call = ToolCall(
            id=str(position),
            name=action["name"],
            arguments=action.get("arguments") or {},
        )

        problem = find_problem(tool_call, documents, messages)
        if problem:
            problems.append(task["id"] + " " + action["name"] + ": " + problem)

        messages.append(AssistantMessage(role="assistant", tool_calls=[tool_call]))
        messages.append(
            ToolMessage(id=str(position), role="tool", content="ok", requestor="assistant")
        )

    return problems


def test_rules_never_block_a_correct_solution():
    # A guardrail is only safe if it lets every known correct path through
    documents = load_documents()

    all_problems = []
    for task in load_raw_tasks():
        all_problems.extend(replay_task(task, documents))

    assert all_problems == []
