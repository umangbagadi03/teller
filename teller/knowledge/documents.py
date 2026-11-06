import json

from teller import config

_documents = None


def load_documents():
    global _documents
    if _documents is not None:
        return _documents

    documents = []
    for path in sorted(config.DOCUMENTS_DIR.glob("*.json")):
        with open(path) as file:
            data = json.load(file)

        document = {
            "id": data["id"],
            "title": data["title"],
            "content": data["content"],
        }
        documents.append(document)

    _documents = documents
    return documents


def get_search_text(document):
    return document["title"] + "\n" + document["content"]
