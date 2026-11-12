from teller import config
from teller.knowledge.keyword_search import keyword_search
from teller.knowledge.reranker import rerank
from teller.knowledge.vector_search import vector_search


def get_score(scored_item):
    document_id, score = scored_item
    return score


def combine_results(first_list, second_list, limit):
    # Reciprocal Rank Fusion: a document scores higher the nearer it is to the
    # top of each list. It only uses ranks, so BM25 and cosine scores never mix.
    scores = {}
    documents_by_id = {}

    for results in [first_list, second_list]:
        for rank, document in enumerate(results, start=1):
            document_id = document["id"]
            documents_by_id[document_id] = document

            if document_id not in scores:
                scores[document_id] = 0.0
            scores[document_id] += 1.0 / (config.RRF_K + rank)

    scored_items = list(scores.items())
    scored_items.sort(key=get_score, reverse=True)

    combined = []
    for document_id, score in scored_items[:limit]:
        combined.append(documents_by_id[document_id])
    return combined


def hybrid_search(query, limit):
    keyword_results = keyword_search(query, config.CANDIDATES_PER_SEARCH)
    vector_results = vector_search(query, config.CANDIDATES_PER_SEARCH)
    return combine_results(keyword_results, vector_results, limit)


def hybrid_rerank_search(query, limit):
    candidates = hybrid_search(query, config.CANDIDATES_PER_SEARCH)
    return rerank(query, candidates, limit)


# SEARCH_METHOD in .env picks one of these, so the same agent can be scored
# with each search method and nothing else changed.
SEARCH_METHODS = {
    "bm25": keyword_search,
    "embeddings": vector_search,
    "hybrid": hybrid_search,
    "hybrid_rerank": hybrid_rerank_search,
}


def search_documents(query, limit=None):
    if limit is None:
        limit = config.RESULTS_PER_SEARCH

    if config.SEARCH_METHOD not in SEARCH_METHODS:
        raise ValueError(
            "Unknown SEARCH_METHOD '" + config.SEARCH_METHOD + "'. "
            "Use one of: bm25, embeddings, hybrid, hybrid_rerank."
        )

    search_function = SEARCH_METHODS[config.SEARCH_METHOD]
    return search_function(query, limit)
