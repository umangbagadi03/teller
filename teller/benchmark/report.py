import json

from teller import config

RETRIEVAL_FILE = config.RESULTS_DIR / "retrieval.json"


def summarize_run(run):
    tasks = run["tasks"]

    passed = 0
    total_reward = 0.0
    total_cost = 0.0
    total_seconds = 0.0
    recalls = []
    failures = {}

    for task in tasks:
        total_reward += task["reward"]
        total_cost += task["agent_cost"] + task["user_cost"]
        total_seconds += task["seconds"]

        if task["reward"] == 1.0:
            passed += 1
        if task["document_recall"] is not None:
            recalls.append(task["document_recall"])

        failure = task["failure"]
        failures[failure] = failures.get(failure, 0) + 1

    count = len(tasks)
    success_rate = 0.0
    average_cost = 0.0
    average_seconds = 0.0
    if count > 0:
        success_rate = total_reward / count
        average_cost = total_cost / count
        average_seconds = total_seconds / count

    document_recall = None
    if recalls:
        document_recall = sum(recalls) / len(recalls)

    return {
        "id": run["id"],
        "pipeline": run["pipeline"],
        "label": run["label"],
        "split": run["split"],
        "model": run["model"],
        "tasks_run": count,
        "passed": passed,
        "success_rate": round(success_rate, 3),
        "cost_per_task": round(average_cost, 5),
        "seconds_per_task": round(average_seconds, 1),
        "document_recall": document_recall,
        "failures": failures,
    }


def load_run(run_id):
    path = config.RUNS_DIR / (run_id + ".json")
    if not path.exists():
        return None
    with open(path) as file:
        return json.load(file)


def list_runs():
    summaries = []
    if not config.RUNS_DIR.exists():
        return summaries

    for path in sorted(config.RUNS_DIR.glob("*.json"), reverse=True):
        with open(path) as file:
            run = json.load(file)
        summaries.append(summarize_run(run))
    return summaries


def load_retrieval_report():
    if not RETRIEVAL_FILE.exists():
        return None
    with open(RETRIEVAL_FILE) as file:
        return json.load(file)
