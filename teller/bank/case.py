import uuid

from tau2.data_model.message import MultiToolMessage, UserMessage
from tau2.domains.banking_knowledge.data_model import TransactionalDB
from tau2.domains.banking_knowledge.environment import get_environment

from teller.agent.teller_agent import TellerAgent
from teller.bank.demo_data import get_demo_database_path
from teller.llm.provider import get_llm_settings, get_model_name

MAX_TOOL_ROUNDS = 12
RETRIEVAL_VARIANT = "no_knowledge"


class Case:
    # One customer conversation in the web app, with its own copy of the bank database

    def __init__(self, llm=None, llm_args=None):
        # llm and llm_args come from the visitor's own key. None means the server's model.
        if llm is None:
            llm = get_model_name()
            llm_args = get_llm_settings()

        # A random id, cut to its first 8 characters so it is easy to read
        random_id = uuid.uuid4().hex
        self.id = random_id[:8]
        database = TransactionalDB.load(str(get_demo_database_path()))
        self.environment = get_environment(db=database, retrieval_variant=RETRIEVAL_VARIANT)
        self.agent = TellerAgent(
            tools=self.environment.get_tools(),
            domain_policy=self.environment.get_policy(),
            llm=llm,
            llm_args=llm_args,
        )
        self.state = self.agent.get_init_state()
        self.model = llm

    def run_tool_calls(self, tool_calls):
        tool_events = []
        tool_messages = []

        for tool_call in tool_calls:
            tool_message = self.environment.get_response(tool_call)
            tool_messages.append(tool_message)

            event = {
                "kind": "tool",
                "text": tool_call.name,
                "arguments": tool_call.arguments,
                "result": tool_message.content,
                "failed": tool_message.error,
            }
            tool_events.append(event)

        if len(tool_messages) == 1:
            return tool_messages[0], tool_events

        return MultiToolMessage(role="tool", tool_messages=tool_messages), tool_events

    def get_api_key(self):
        # Used only to remove the key from error messages
        return self.agent.llm_args.get("api_key", "")

    def send_message(self, text):
        # Everything that happens for this message, in the order it happened
        activity = []
        cost = 0.0

        message = UserMessage(role="user", content=text)
        reply = None

        for round_number in range(MAX_TOOL_ROUNDS):
            trace_size_before = len(self.state["trace"])
            reply, self.state = self.agent.generate_next_message(message, self.state)
            activity.extend(self.state["trace"][trace_size_before:])
            if reply.cost:
                cost += reply.cost

            if not reply.tool_calls:
                break

            message, tool_events = self.run_tool_calls(reply.tool_calls)
            activity.extend(tool_events)

        reply_text = "I could not finish this request. Please try again."
        if reply is not None and reply.content:
            reply_text = reply.content

        return {
            "reply": reply_text,
            "activity": activity,
            "cost": cost,
            "documents_found": len(self.state["documents"]),
        }
