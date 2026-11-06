from fastembed.rerank.cross_encoder import TextCrossEncoder

from teller import config
from teller.knowledge.documents import get_search_text

_model = None


def get_model():
    global _model
    if _model is None:
        _model = TextCrossEncoder(model_name=config.RERANKER_MODEL)
    return _model


def rerank(query, documents, limit):
    if not documents:
        return []

    texts = []
    for document in documents:
        texts.append(get_search_text(document))

    scored_documents = []
    scores = get_model().rerank(query, texts, batch_size=config.RERANKER_BATCH_SIZE)
    for position, score in enumerate(scores):
        scored_documents.append((score, position))
    scored_documents.sort(reverse=True)

    results = []
    for score, position in scored_documents[:limit]:
        results.append(documents[position])
    return results
