from tau2.agent.base_agent import HalfDuplexAgent
from tau2.data_model.message import MultiToolMessage, UserMessage

from teller.agent.graph import build_graph
from teller.agent.search_tool import get_search_tool
from teller.llm.provider import get_llm_settings, get_model_name

GRAPH_STEP_LIMIT = 40


class TellerAgent(HalfDuplexAgent):
    def __init__(self, tools, domain_policy, llm=None, llm_args=None, use_checks=True):
        super().__init__(tools=tools, domain_policy=domain_policy)
        # The benchmark passes its own model and settings. The web app passes none.
        if llm is None:
            llm = get_model_name()
        if llm_args is None:
            llm_args = get_llm_settings()

        self.llm = llm
        self.llm_args = llm_args
        self.use_checks = use_checks
        self.search_tool = get_search_tool()
        self.graph = build_graph(self)
        self.latest_state = None

    def get_init_state(self, message_history=None):
        messages = []
        if message_history:
            messages = list(message_history)

        return {"messages": messages, "documents": [], "trace": []}

    def is_stop(self, message):
        return False

    def set_seed(self, seed):
        self.seed = seed

    def generate_next_message(self, message, state):
        messages = list(state["messages"])
        customer_text = None

        if isinstance(message, MultiToolMessage):
            messages.extend(message.tool_messages)
        elif message is not None:
            messages.append(message)
            if isinstance(message, UserMessage):
                customer_text = message.content

        graph_input = {
            "messages": messages,
            "customer_text": customer_text,
            "documents": state["documents"],
            "reply": None,
            "searches_used": 0,
            "corrections_used": 0,
            "correction_note": "",
            "extra_cost": 0.0,
            "extra_usage": {},
            "trace": state["trace"],
        }
        result = self.graph.invoke(graph_input, {"recursion_limit": GRAPH_STEP_LIMIT})

        reply = result["reply"]
        self.add_step_cost(reply, result)

        new_messages = list(result["messages"])
        new_messages.append(reply)

        new_state = {
            "messages": new_messages,
            "documents": result["documents"],
            "trace": result["trace"],
        }
        self.latest_state = new_state
        return reply, new_state

    def add_step_cost(self, reply, result):
        # Adds the LLM calls hidden inside this step to the reply the benchmark sees
        if result["extra_cost"]:
            if reply.cost is None:
                reply.cost = 0.0
            reply.cost += result["extra_cost"]

        if result["extra_usage"]:
            usage = {}
            if reply.usage:
                usage = dict(reply.usage)
            for key, value in result["extra_usage"].items():
                usage[key] = usage.get(key, 0) + value
            reply.usage = usage
