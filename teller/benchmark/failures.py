ERROR_ENDINGS = [
    "max_steps",
    "timeout",
    "too_many_errors",
    "agent_error",
    "user_error",
    "infrastructure_error",
    "context_window_exceeded",
    "unexpected_error",
]

LOW_DOCUMENT_RECALL = 0.5


def classify_failure(reward, ending, document_recall):
    # A rough first label that shows where to start reading the failed conversation
    if reward == 1.0:
        return "passed"

    if ending in ERROR_ENDINGS:
        return "run error"

    if document_recall is not None and document_recall < LOW_DOCUMENT_RECALL:
        return "retrieval"

    return "reasoning"
