import json
from datetime import datetime

from tau2.data_model.simulation import TextRunConfig
from tau2.runner import get_tasks, run_single_task

from teller import config
from teller.benchmark.failures import classify_failure
from teller.benchmark.pipelines import PIPELINES, get_latest_agent, register_teller_agent
from teller.benchmark.retrieval_eval import measure_recall
from teller.benchmark.task_split import get_required_ids, get_task_ids, load_raw_tasks
from teller.llm.provider import get_llm_settings, get_model_name

DOMAIN = "banking_knowledge"
SEED = 300
TELLER_PIPELINES = ["teller", "teller_no_checks", "teller_golden"]


def get_required_documents():
    required_documents = {}
    for task in load_raw_tasks():
        required_documents[task["id"]] = get_required_ids(task)
    return required_documents


def measure_document_recall(pipeline_name, required_ids):
    # Only Teller keeps a list of what it found, and a golden run is handed the documents
    if pipeline_name not in ["teller", "teller_no_checks"] or not required_ids:
        return None

    agent = get_latest_agent()
    if agent is None or agent.latest_state is None:
        return 0.0

    found_ids = []
    for document in agent.latest_state["documents"]:
        found_ids.append(document["id"])

    return measure_recall(required_ids, found_ids)


def count_tokens(messages):
    prompt_tokens = 0
    completion_tokens = 0
    for message in messages:
        # Only messages written by an LLM carry token counts
        if message.role not in ["assistant", "user"]:
            continue
        if message.usage:
            prompt_tokens += message.usage.get("prompt_tokens", 0)
            completion_tokens += message.usage.get("completion_tokens", 0)
    return prompt_tokens, completion_tokens


def number_or_zero(value):
    if value is None:
        return 0.0
    return value


def summarize_result(result, pipeline_name, required_ids):
    reward = 0.0
    if result.reward_info:
        reward = result.reward_info.reward

    ending = str(result.termination_reason.value)
    document_recall = measure_document_recall(pipeline_name, required_ids)
    prompt_tokens, completion_tokens = count_tokens(result.messages)

    return {
        "task_id": result.task_id,
        "reward": reward,
        "ending": ending,
        "failure": classify_failure(reward, ending, document_recall),
        "document_recall": document_recall,
        "messages": len(result.messages),
        "seconds": round(result.duration, 1),
        "agent_cost": number_or_zero(result.agent_cost),
        "user_cost": number_or_zero(result.user_cost),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def summarize_crash(task_id, error):
    return {
        "task_id": task_id,
        "reward": 0.0,
        "ending": "unexpected_error",
        "failure": "run error",
        "document_recall": None,
        "messages": 0,
        "seconds": 0.0,
        "agent_cost": 0.0,
        "user_cost": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "error": str(error)[:300],
    }


def build_run_config(pipeline):
    model = get_model_name()
    settings = get_llm_settings()
    return TextRunConfig(
        domain=DOMAIN,
        agent=pipeline["agent"],
        llm_agent=model,
        llm_args_agent=settings,
        llm_user=model,
        llm_args_user=settings,
        retrieval_config=pipeline["retrieval"],
        max_steps=config.MAX_STEPS_PER_TASK,
    )


def save_run(run):
    config.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RUNS_DIR / (run["id"] + ".json")
    with open(path, "w") as file:
        json.dump(run, file, indent=2)


def run_benchmark(pipeline_name, split, limit):
    register_teller_agent()

    pipeline = PIPELINES[pipeline_name]
    run_config = build_run_config(pipeline)
    required_documents = get_required_documents()

    task_ids = get_task_ids(split)
    if limit:
        task_ids = task_ids[:limit]
    tasks = get_tasks(DOMAIN, task_ids=task_ids)

    # Teller pipelines search with SEARCH_METHOD. A run with another method than
    # the usual one says so in its label, so the two can be told apart.
    label = pipeline["label"]
    search = pipeline["retrieval"]
    usual_search = True
    if pipeline_name in TELLER_PIPELINES:
        search = config.SEARCH_METHOD
        if search != config.DEFAULT_SEARCH_METHOD:
            usual_search = False
            label += ", search: " + search

    started_at = datetime.now().strftime("%Y%m%d-%H%M%S")
    run = {
        "id": pipeline_name + "-" + started_at,
        "pipeline": pipeline_name,
        "label": label,
        "search": search,
        "usual_search": usual_search,
        "split": split,
        "model": get_model_name(),
        "tasks": [],
    }

    for task in tasks:
        print("Running", task.id)

        # One failed task, such as a rate limit that outlasts the retries, should
        # not lose the rest of the run. It counts as a failed task in the score.
        try:
            result = run_single_task(run_config, task, seed=SEED)
            summary = summarize_result(result, pipeline_name, required_documents[task.id])
        except Exception as error:
            print("  task crashed:", str(error)[:200])
            summary = summarize_crash(task.id, error)

        run["tasks"].append(summary)
        print("  reward", summary["reward"], "ending", summary["ending"])

        # Saved after every task, so a rate limit or crash keeps the finished work
        save_run(run)

    return run
