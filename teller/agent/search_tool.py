from tau2.environment.tool import as_tool

SEARCH_TOOL_NAME = "search_policies"


def search_policies(query: str) -> str:
    """Search Rho-Bank policy documents for rules, procedures and tool names.

    Args:
        query: What to look for, for example "dispute a credit card transaction".

    Returns:
        The titles of the documents found. Their text is added to your documents.
    """
    # The agent runs this search itself, so this function is only used for its schema
    return ""


def get_search_tool():
    return as_tool(search_policies)
