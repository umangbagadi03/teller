# Teller

Teller is a bank support agent that reads policy documents and then acts on them. It talks to the customer, finds the right policy, looks up the account, and makes the change in the bank's database.

It is measured on the `banking_knowledge` domain of [τ-Bench](https://github.com/sierra-research/tau2-bench), an open benchmark for customer service agents. The domain has 698 policy documents and 97 tasks. A simulated customer talks to the agent, and a task passes only when the database ends in the correct state. Many action tools are hidden until the agent finds their exact names in the documents, so weak retrieval fails the task, not just the wording of an answer.

## How it works

```
customer message -> retrieve -> think -> check -> reply or bank tool call
                                 ^  |       |
                                 |  v       |
                                search      |
                                 ^----------+ blocked call goes back to think
```

- **retrieve** searches on the customer's opening message. This needs no LLM call.
- **think** is the LLM call. It can reply, call a bank tool, or ask for another search.
- **search** runs the query the LLM wrote, adds the documents, and goes back to think.
- **check** blocks tool names the agent has not read in a document, tools that are not unlocked, and account actions before verification. The LLM gets the reason and tries again. An empty reply also gets another try.

Search is hybrid: BM25 and local embeddings are combined with Reciprocal Rank Fusion, then a local cross-encoder reranks the top results. Indexing and search need no API key.

