from tau2.registry import registry

from teller.agent.teller_agent import TellerAgent

TELLER_AGENT_NAME = "teller"
TELLER_NO_CHECKS_AGENT_NAME = "teller_no_checks"

# no_docs, bm25 and golden use the benchmark's own agent. The other three use Teller,
# so comparing them shows what the checks and the search are each worth.
PIPELINES = {
    "no_docs": {
        "label": "No documents",
        "agent": "llm_agent",
        "retrieval": "no_knowledge",
    },
    "bm25": {
        "label": "Plain RAG (BM25 tool)",
        "agent": "llm_agent",
        "retrieval": "bm25",
    },
    "teller": {
        "label": "Teller (hybrid, rerank, checks)",
        "agent": TELLER_AGENT_NAME,
        "retrieval": "no_knowledge",
    },
    "teller_no_checks": {
        "label": "Teller without checks",
        "agent": TELLER_NO_CHECKS_AGENT_NAME,
        "retrieval": "no_knowledge",
    },
    "teller_golden": {
        "label": "Teller, correct documents given",
        "agent": TELLER_AGENT_NAME,
        "retrieval": "golden_retrieval",
    },
    "golden": {
        "label": "Benchmark agent, correct documents given",
        "agent": "llm_agent",
        "retrieval": "golden_retrieval",
    },
}

latest_agent = None


def create_agent(tools, domain_policy, use_checks, **kwargs):
    # Kept so the runner can read which documents the agent found
    global latest_agent
    latest_agent = TellerAgent(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm"),
        llm_args=kwargs.get("llm_args"),
        use_checks=use_checks,
    )
    return latest_agent


def create_teller_agent(tools, domain_policy, **kwargs):
    return create_agent(tools, domain_policy, True, **kwargs)


def create_teller_agent_without_checks(tools, domain_policy, **kwargs):
    return create_agent(tools, domain_policy, False, **kwargs)


def register_teller_agent():
    if registry.get_agent_factory(TELLER_AGENT_NAME) is None:
        registry.register_agent_factory(create_teller_agent, TELLER_AGENT_NAME)

    if registry.get_agent_factory(TELLER_NO_CHECKS_AGENT_NAME) is None:
        registry.register_agent_factory(
            create_teller_agent_without_checks,
            TELLER_NO_CHECKS_AGENT_NAME,
        )


def get_latest_agent():
    return latest_agent
