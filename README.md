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

## Results

### Search methods

Measured locally with no API cost. Recall uses the customer's request from 77 development tasks as the query. The tool name column searches for each of the 46 hidden tool names and checks the top 5 results.

| Method | Recall at 5 | Recall at 10 | Recall at 20 | Exact tool name found |
|---|---|---|---|---|
| BM25 | 2.7% | 6.0% | 12.6% | 100% |
| Embeddings | 12.7% | 17.0% | 25.3% | 95.7% |
| Hybrid | 8.0% | 13.8% | 20.7% | 100% |
| Hybrid + reranker | 9.7% | 16.1% | 20.7% | 97.8% |

Tasks often need many documents and this test makes one search, so recall is low. Embeddings alone lead on recall, while BM25 is stronger on exact names. Teller uses hybrid with reranking as a balance between the two. This is a stand-in test, so the benchmark runs below should make the final call.

### Task success

No scored run has been recorded yet. Run the commands in the Evaluation section, and the Results page in the web app fills in by itself. A single task was run on an earlier version with a small local model to check the full flow. It did not finish within the step limit, so it is not a score.

| Pipeline | What changes | Task success |
|---|---|---|
| `no_docs` | Benchmark's agent, no documents | not measured |
| `bm25` | Benchmark's agent with a BM25 search tool | not measured |
| `teller_no_checks` | Teller without the code checks | not measured |
| `teller` | This project | not measured |
| `teller_golden` | Teller, given the correct documents | not measured |
| `golden` | Benchmark's agent, given the correct documents | not measured |

These comparisons change one thing at a time. `teller` against `teller_no_checks` shows what the checks are worth. `teller` against `teller_golden` shows how much better search could still help. `bm25` against `teller` compares plain RAG with the whole design.

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

## Project layout

```
main.py                  commands
teller/
  config.py              paths and settings
  llm/provider.py        picks the provider and model from .env
  knowledge/             BM25, embeddings, reranker, hybrid search
  agent/                 LangGraph agent: state, prompts, nodes, rules, graph
  bank/                  a customer case in the web app
  benchmark/             pipelines, runner, task split, retrieval eval, reports
  api/                   FastAPI routes
web/                     plain HTML, CSS and JavaScript
tests/                   unit tests, no LLM calls
```

## Design decisions

- **No vector database.** 698 short documents fit in one NumPy file, and a full scan takes milliseconds. A database server would add setup without changing results.
- **LiteLLM for all providers.** The benchmark already depends on it, so the agent and the simulated customer call every provider the same way.
- **Verification is enforced in code.** Hidden account tools and email changes are blocked until verification is logged, except emergency transfers, which the policy allows first. A test replays every reference solution through the rules, and none is blocked.
- **Automatic search runs only on the opening message.** Follow-ups like "yes please" found unrelated documents and pushed useful ones out of the prompt. After the first message, the LLM writes its own searches.
- **Documents go in the system prompt, once.** They are not repeated in the message history. The newest 20 are kept, and a document found again moves back to the newest place. A quarter of the tasks need more than 12 documents.
- **Limits are hard limits.** At three searches in a step the search tool is removed, so the agent cannot loop on it. The step limit is 200, the benchmark's default.

## Limitations

- The bank, customers and tasks are synthetic, so scores say nothing about real customers.
- The verification check confirms that verification was logged. It does not compare the customer's answers itself, which is still the LLM's job.
- The benchmark's tasks are public. Only a holdout score should be reported, and it is not a leaderboard submission unless the submission guide is followed.
- The retrieval comparison uses the customer's request from each scenario as the query, so it compares methods but is not the agent's real recall.
- Failure labels are a rough first guess, based on the documents found and how the run ended. Read the conversation to confirm the cause.
