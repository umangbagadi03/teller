import json
import re

from teller import config
from teller.benchmark.task_split import get_task_ids, load_raw_tasks
from teller.knowledge.documents import load_documents
from teller.knowledge.hybrid_search import hybrid_search, search_documents
from teller.knowledge.keyword_search import keyword_search
from teller.knowledge.vector_search import vector_search

RESULTS_FILE = config.RESULTS_DIR / "retrieval.json"
TOP_K_VALUES = [5, 10, 20]
TOOL_NAME_PATTERN = r"\b[a-z]+(?:_[a-z0-9]+)*_\d{4}\b"
TOOL_NAME_TOP_K = 5


def get_query(task):
    # Tasks have no ready search queries. In most scenarios the first paragraph describes
    # the character and the second says what the customer wants, so the second is used
    # as a stand-in. Compare methods with this score; it is not real agent recall.
    instructions = str(task["user_scenario"]["instructions"])
    paragraphs = instructions.split("\n\n")

    if len(paragraphs) > 1:
        return paragraphs[1][:500]
    return paragraphs[0][:500]


def measure_recall(required_ids, found_ids):
    hits = 0
    for document_id in required_ids:
        if document_id in found_ids:
            hits += 1
    return hits / len(required_ids)


def measure_method(search_function, tasks):
    # Each method searches once per task, then the score is read at every cutoff
    biggest_top_k = max(TOP_K_VALUES)

    totals = {}
    for top_k in TOP_K_VALUES:
        totals[top_k] = 0.0

    tasks_counted = 0
    for task in tasks:
        required_ids = task.get("required_documents") or []
        if not required_ids:
            continue

        found_ids = []
        for document in search_function(get_query(task), biggest_top_k):
            found_ids.append(document["id"])

        for top_k in TOP_K_VALUES:
            totals[top_k] += measure_recall(required_ids, found_ids[:top_k])
        tasks_counted += 1

    scores = {}
    for top_k in TOP_K_VALUES:
        scores["recall_at_" + str(top_k)] = round(totals[top_k] / tasks_counted, 3)
    return scores


def find_tool_names():
    # Hidden tools have names like open_bank_account_4821. Each name is listed
    # with the documents that mention it, and the agent has to find one of them.
    tool_names = {}
    for document in load_documents():
        for name in re.findall(TOOL_NAME_PATTERN, document["content"]):
            if name not in tool_names:
                tool_names[name] = []
            tool_names[name].append(document["id"])
    return tool_names


def measure_tool_name_search(search_function, tool_names):
    hits = 0
    for name, document_ids in tool_names.items():
        for document in search_function(name, TOOL_NAME_TOP_K):
            if document["id"] in document_ids:
                hits += 1
                break
    return round(hits / len(tool_names), 3)


def run_retrieval_eval():
    # This uses local models only, so it costs nothing to run.
    development_ids = get_task_ids("development")

    tasks = []
    for task in load_raw_tasks():
        if task["id"] in development_ids:
            tasks.append(task)

    methods = {
        "BM25": keyword_search,
        "Embeddings": vector_search,
        "Hybrid": hybrid_search,
        "Hybrid + reranker": search_documents,
    }

    tool_names = find_tool_names()

    table = []
    for method_name, search_function in methods.items():
        row = {"method": method_name}
        row.update(measure_method(search_function, tasks))
        row["tool_name_hit_rate"] = measure_tool_name_search(search_function, tool_names)
        table.append(row)
        print(row)

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {"tasks": len(tasks), "tool_names": len(tool_names), "table": table}
    with open(RESULTS_FILE, "w") as file:
        json.dump(report, file, indent=2)

    return report
