from langgraph.graph import END, START, StateGraph

from teller.agent.nodes import (
    check_node,
    retrieve_node,
    route_after_check,
    route_after_think,
    search_node,
    think_node,
)
from teller.agent.state import AgentState


def build_graph(agent):
    # customer message -> retrieve -> think -> check -> reply or tool call
    #                                  ^  |       |
    #                                  |  v       |
    #                                 search      |
    #                                  ^----------+ (blocked call goes back to think)

    def think(state):
        return think_node(state, agent)

    def check(state):
        return check_node(state, agent)

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("think", think)
    graph.add_node("search", search_node)
    graph.add_node("check", check)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "think")
    graph.add_conditional_edges(
        "think",
        route_after_think,
        {"search": "search", "check": "check"},
    )
    graph.add_edge("search", "think")
    graph.add_conditional_edges(
        "check",
        route_after_check,
        {"think": "think", "finish": END},
    )

    return graph.compile()
