import uuid

from tau2.data_model.message import MultiToolMessage, UserMessage
from tau2.domains.banking_knowledge.data_model import TransactionalDB
from tau2.domains.banking_knowledge.environment import get_environment

from teller.agent.teller_agent import TellerAgent
from teller.bank.demo_data import get_demo_database_path
from teller.llm.provider import get_model_name

MAX_TOOL_ROUNDS = 12
RETRIEVAL_VARIANT = "no_knowledge"


class Case:
    # One customer conversation in the web app, with its own copy of the bank database

    def __init__(self):
        self.id = uuid.uuid4().hex[:8]
        database = TransactionalDB.load(str(get_demo_database_path()))
        self.environment = get_environment(db=database, retrieval_variant=RETRIEVAL_VARIANT)
        self.agent = TellerAgent(
            tools=self.environment.get_tools(),
            domain_policy=self.environment.get_policy(),
        )
        self.state = self.agent.get_init_state()
        self.model = get_model_name()

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

    def send_message(self, text):
        trace_size_before = len(self.state["trace"])
        events = []
        cost = 0.0

        message = UserMessage(role="user", content=text)
        reply = None

        for round_number in range(MAX_TOOL_ROUNDS):
            reply, self.state = self.agent.generate_next_message(message, self.state)
            if reply.cost:
                cost += reply.cost

            if not reply.tool_calls:
                break

            message, tool_events = self.run_tool_calls(reply.tool_calls)
            events.extend(tool_events)

        reply_text = "I could not finish this request. Please try again."
        if reply is not None and reply.content:
            reply_text = reply.content

        new_trace = self.state["trace"][trace_size_before:]
        return {
            "reply": reply_text,
            "steps": new_trace,
            "actions": events,
            "cost": cost,
            "documents_found": len(self.state["documents"]),
        }
