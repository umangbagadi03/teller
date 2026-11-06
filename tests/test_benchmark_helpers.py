from teller.benchmark.failures import classify_failure
from teller.benchmark.report import summarize_run
from teller.benchmark.task_split import get_task_ids


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
