import json
import random

from teller import config


def load_raw_tasks():
    with open(config.TASKS_FILE) as file:
        return json.load(file)


def get_task_ids(split):
    # The holdout tasks are kept aside and never used while tuning the agent,
    # so the final score is not inflated by fixes made for specific tasks.
    all_ids = []
    for task in load_raw_tasks():
        all_ids.append(task["id"])
    all_ids.sort()

    shuffled_ids = list(all_ids)
    random.Random(config.SPLIT_SEED).shuffle(shuffled_ids)

    holdout_ids = shuffled_ids[:config.HOLDOUT_SIZE]
    development_ids = shuffled_ids[config.HOLDOUT_SIZE:]

    if split == "holdout":
        return holdout_ids
    if split == "development":
        return development_ids
    if split == "all":
        return all_ids

    raise ValueError("Unknown split '" + split + "'. Use development, holdout or all.")
