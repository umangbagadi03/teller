#!/bin/bash
# Creates the virtual environment and downloads a fixed version of the benchmark.
set -e

BENCHMARK_REPO="https://github.com/sierra-research/tau2-bench.git"
BENCHMARK_COMMIT="033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f"
BENCHMARK_DIR="vendor/tau2-bench"

if [ ! -d "$BENCHMARK_DIR" ]; then
    # Only this one commit is downloaded, because the full history is large
    echo "Downloading the benchmark"
    git init --quiet "$BENCHMARK_DIR"
    git -C "$BENCHMARK_DIR" remote add origin "$BENCHMARK_REPO"
    git -C "$BENCHMARK_DIR" fetch --quiet --depth 1 origin "$BENCHMARK_COMMIT"
    git -C "$BENCHMARK_DIR" checkout --quiet FETCH_HEAD
fi

if [ ! -d ".venv" ]; then
    echo "Creating the virtual environment"
    python3 -m venv .venv
fi

echo "Installing packages"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pip install --quiet -e "$BENCHMARK_DIR"

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

echo "Done. Add an API key to .env, then run: .venv/bin/python main.py index"
