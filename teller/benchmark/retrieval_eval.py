import json
import re

from teller import config
from teller.benchmark.task_split import get_required_ids, get_task_ids, load_raw_tasks
from teller.knowledge.documents import load_documents
from teller.knowledge.hybrid_search import hybrid_rerank_search, hybrid_search
from teller.knowledge.keyword_search import keyword_search
from teller.knowledge.vector_search import vector_search

RESULTS_FILE = config.RESULTS_DIR / "retrieval.json"
TOP_K_VALUES = [5, 10, 20]
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
        required_ids = get_required_ids(task)
        if not required_ids:
            continue

        found_ids = []
        for document in search_function(get_query(task), biggest_top_k):
            found_ids.append(document["id"])

        for top_k in TOP_K_VALUES:
            top_ids = found_ids[:top_k]
            totals[top_k] += measure_recall(required_ids, top_ids)
        tasks_counted += 1

    scores = {}
    for top_k in TOP_K_VALUES:
        scores["recall_at_" + str(top_k)] = round(totals[top_k] / tasks_counted, 3)
    return scores


def measure_best_possible(tasks):
    # A task can need more documents than one search returns. This is the score
    # a perfect search would get, so the real scores can be read against it.
    totals = {}
    for top_k in TOP_K_VALUES:
        totals[top_k] = 0.0

    tasks_counted = 0
    for task in tasks:
        needed = len(get_required_ids(task))
        if needed == 0:
            continue

        for top_k in TOP_K_VALUES:
            totals[top_k] += min(top_k, needed) / needed
        tasks_counted += 1

    scores = {}
    for top_k in TOP_K_VALUES:
        scores["recall_at_" + str(top_k)] = round(totals[top_k] / tasks_counted, 3)
    return scores


def looks_like_tool_name(word):
    # Hidden tools are named like open_bank_account_4821:
    # lowercase words joined by underscores, ending in four digits
    parts = word.split("_")
    if len(parts) < 2:
        return False

    last_part = parts[-1]
    if len(last_part) != 4 or not last_part.isdigit():
        return False

    first_part = parts[0]
    return first_part.isalpha() and word == word.lower()


def find_tool_names():
    # Hidden tools have names like open_bank_account_4821. Each name is listed
    # with the documents that mention it, and the agent has to find one of them.
    tool_names = {}
    for document in load_documents():
        for word in re.findall(r"[A-Za-z0-9_]+", document["content"]):
            if not looks_like_tool_name(word):
                continue
            if word not in tool_names:
                tool_names[word] = []
            tool_names[word].append(document["id"])
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
        "Hybrid + reranker": hybrid_rerank_search,
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
    report = {
        "tasks": len(tasks),
        "tool_names": len(tool_names),
        "best_possible": measure_best_possible(tasks),
        "table": table,
    }
    with open(RESULTS_FILE, "w") as file:
        json.dump(report, file, indent=2)

    return report
