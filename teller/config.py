import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent.parent
load_dotenv(PROJECT_DIR / ".env")

# Where things live
BENCHMARK_DIR = PROJECT_DIR / "vendor" / "tau2-bench"
BANKING_DATA_DIR = BENCHMARK_DIR / "data" / "tau2" / "domains" / "banking_knowledge"
DOCUMENTS_DIR = BANKING_DATA_DIR / "documents"
TASKS_FILE = BANKING_DATA_DIR / "tasks.json"
INDEX_DIR = PROJECT_DIR / "data" / "index"
RESULTS_DIR = PROJECT_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
WEB_DIR = PROJECT_DIR / "web"

# LLM settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_CONTEXT_SIZE = int(os.getenv("OLLAMA_CONTEXT_SIZE", "16384"))

LLM_PAUSE_SECONDS = float(os.getenv("LLM_PAUSE_SECONDS", "0"))
LLM_RETRIES = 6

# Retrieval settings
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
EMBEDDING_BATCH_SIZE = 16
RERANKER_BATCH_SIZE = 8
CANDIDATES_PER_SEARCH = 20
RESULTS_PER_SEARCH = 5
RRF_K = 60

# Agent limits
MAX_SEARCHES_PER_STEP = 3
MAX_CORRECTIONS_PER_STEP = 2
MAX_DOCUMENTS_IN_PROMPT = 20

# Benchmark settings
HOLDOUT_SIZE = 20
SPLIT_SEED = 7
MAX_STEPS_PER_TASK = 200
