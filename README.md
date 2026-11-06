# Teller

Teller is a bank support agent that reads policy documents and then acts on them. It talks to the customer, finds the right policy, looks up the account, and makes the change in the bank's database.

It is measured on the `banking_knowledge` domain of [τ-Bench](https://github.com/sierra-research/tau2-bench), an open benchmark for customer service agents. The domain has 698 policy documents and 97 tasks. A simulated customer talks to the agent, and a task passes only when the database ends in the correct state. Many action tools are hidden until the agent finds their exact names in the documents, so weak retrieval fails the task, not just the wording of an answer.

