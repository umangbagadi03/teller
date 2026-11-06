from teller.knowledge.hybrid_search import combine_results
from teller.knowledge.keyword_search import keyword_search, split_into_words


def make_documents(ids):
    documents = []
    for document_id in ids:
        documents.append({"id": document_id})
    return documents


def test_tool_names_stay_whole_and_are_split():
    words = split_into_words("Use open_bank_account_4821")
    assert "open_bank_account_4821" in words
    assert "bank" in words
    assert "account" in words


def test_document_in_both_lists_ranks_first():
    keyword_results = make_documents(["a", "shared"])
    vector_results = make_documents(["b", "shared"])

    combined = combine_results(keyword_results, vector_results, 3)

    assert combined[0]["id"] == "shared"
    assert len(combined) == 3


def test_combined_results_have_no_duplicates():
    combined = combine_results(make_documents(["a"]), make_documents(["a"]), 5)
    assert len(combined) == 1


def test_keyword_search_finds_an_exact_tool_name():
    results = keyword_search("open_bank_account_4821", 3)
    assert "open_bank_account_4821" in results[0]["content"]
