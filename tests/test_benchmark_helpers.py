from teller.benchmark.failures import classify_failure
from teller.benchmark.report import summarize_run
from teller.benchmark.retrieval_eval import measure_best_possible, measure_recall
from teller.benchmark.task_split import get_required_ids, get_task_ids


def test_holdout_is_separate_from_development():
    holdout = get_task_ids("holdout")
    development = get_task_ids("development")

    assert len(holdout) == 20
    assert len(holdout) + len(development) == len(get_task_ids("all"))
    for task_id in holdout:
        assert task_id not in development


def test_split_is_the_same_every_time():
    assert get_task_ids("holdout") == get_task_ids("holdout")


def test_failure_labels():
    assert classify_failure(1.0, "user_stop", 0.1) == "passed"
    assert classify_failure(0.0, "max_steps", 1.0) == "run error"
    assert classify_failure(0.0, "user_stop", 0.2) == "retrieval"
    assert classify_failure(0.0, "user_stop", 0.9) == "reasoning"
    assert classify_failure(0.0, "user_stop", None) == "reasoning"


def test_run_summary():
    run = {
        "id": "x",
        "pipeline": "teller",
        "label": "Teller",
        "usual_search": True,
        "split": "development",
        "model": "m",
        "tasks": [
            {
                "reward": 1.0,
                "agent_cost": 0.02,
                "user_cost": 0.0,
                "seconds": 10.0,
                "document_recall": 1.0,
                "failure": "passed",
            },
            {
                "reward": 0.0,
                "agent_cost": 0.02,
                "user_cost": 0.0,
                "seconds": 30.0,
                "document_recall": 0.5,
                "failure": "reasoning",
            },
        ],
    }

    summary = summarize_run(run)

    assert summary["passed"] == 1
    assert summary["success_rate"] == 0.5
    assert summary["cost_per_task"] == 0.02
    assert summary["seconds_per_task"] == 20.0
    assert summary["document_recall"] == 0.75
    assert summary["failures"] == {"passed": 1, "reasoning": 1}


def test_recall_counts_the_required_documents_that_were_found():
    assert measure_recall(["a", "b", "c", "d"], ["a", "x", "c"]) == 0.5


def test_task_without_required_documents_gives_an_empty_list():
    assert get_required_ids({"required_documents": None}) == []
    assert get_required_ids({}) == []


def test_best_possible_recall_is_limited_by_the_search_size():
    # Ten documents are needed, and one search of five can find half of them at most
    task = {"required_documents": ["d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9"]}

    scores = measure_best_possible([task])

    assert scores["recall_at_5"] == 0.5
    assert scores["recall_at_10"] == 1.0
