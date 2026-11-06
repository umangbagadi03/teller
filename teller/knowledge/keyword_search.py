import re

from rank_bm25 import BM25Okapi

from teller.knowledge.documents import get_search_text, load_documents

_bm25 = None


def split_into_words(text):
    words = re.findall(r"[a-z0-9_]+", text.lower())

    # Keep tool names whole, and also add their parts.
    # "open_bank_account_4821" can then match both the exact name and "bank account".
    all_words = []
    for word in words:
        all_words.append(word)
        if "_" in word:
            parts = word.split("_")
            all_words.extend(parts)

    return all_words


def get_bm25():
    global _bm25
    if _bm25 is None:
        tokenized_documents = []
        for document in load_documents():
            words = split_into_words(get_search_text(document))
            tokenized_documents.append(words)
        _bm25 = BM25Okapi(tokenized_documents)
    return _bm25


def keyword_search(query, limit):
    documents = load_documents()
    scores = get_bm25().get_scores(split_into_words(query))

    scored_positions = []
    for position, score in enumerate(scores):
        if score > 0:
            scored_positions.append((score, position))
    scored_positions.sort(reverse=True)

    results = []
    for score, position in scored_positions[:limit]:
        results.append(documents[position])
    return results
