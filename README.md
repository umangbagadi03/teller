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

## Setup

Needs Python 3.12 or 3.13.

```bash
bash setup.sh
.venv/bin/python main.py index
```

Add one key to `.env`. Teller picks the provider from the key it finds, in this order: Gemini, Anthropic, OpenAI. With no key it uses a local Ollama model. Set `LLM_PROVIDER` to force one.

Gemini has a free tier. If you hit its rate limit, set `LLM_PAUSE_SECONDS=4` in `.env`.

## Web app

```bash
.venv/bin/python main.py serve
```

Open http://127.0.0.1:8010. On the Branch desk you play the customer, and the customer file on the left has the details you need to pass verification. The working record on the right shows every search, blocked call and bank action. Each case gets its own copy of the sample database. The web app shows Indian sample customers through a separate demo copy, while the benchmark keeps its original database so scores stay comparable.

## Evaluation

Compare search methods. This runs locally and has no API cost:

```bash
.venv/bin/python main.py retrieval
```

Run benchmark tasks:

```bash
.venv/bin/python main.py benchmark --pipeline teller --limit 5
.venv/bin/python main.py benchmark --pipeline bm25 --limit 5
```

Use `--limit 0` for every task in the split. Each task uses LLM calls for both the agent and the simulated customer, so start small.

20 tasks are kept aside as a holdout set. Tune on `development`, and run `--split holdout` only for the final score.

```bash
.venv/bin/python -m pytest tests
```

