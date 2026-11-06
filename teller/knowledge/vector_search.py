import numpy as np
from fastembed import TextEmbedding

from teller import config
from teller.knowledge.documents import get_search_text, load_documents

EMBEDDINGS_FILE = config.INDEX_DIR / "embeddings.npy"

_model = None
_embeddings = None


def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=config.EMBEDDING_MODEL)
    return _model


def build_index():
    texts = []
    for document in load_documents():
        texts.append(get_search_text(document))

    # Small batches keep memory use low on a laptop
    vectors = []
    for vector in get_model().passage_embed(texts, batch_size=config.EMBEDDING_BATCH_SIZE):
        vectors.append(vector)

    embeddings = np.array(vectors)
    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_FILE, embeddings)
    return len(vectors)


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        if not EMBEDDINGS_FILE.exists():
            build_index()
        _embeddings = np.load(EMBEDDINGS_FILE)
    return _embeddings


def vector_search(query, limit):
    documents = load_documents()
    embeddings = get_embeddings()

    query_vector = None
    for vector in get_model().query_embed([query]):
        query_vector = vector

    # The vectors are normalized, so the dot product is the cosine similarity
    scores = embeddings.dot(query_vector)
    best_positions = np.argsort(scores)[::-1][:limit]

    results = []
    for position in best_positions:
        results.append(documents[int(position)])
    return results
