import argparse


def index_command():
    # Prepares everything that works without an LLM, so the first visitor does not wait
    from teller.bank.demo_data import build_demo_database
    from teller.knowledge.reranker import get_model
    from teller.knowledge.vector_search import build_index

    count = build_index()
    print("Indexed", count, "documents")

    get_model()
    print("Reranker ready")

    build_demo_database()
    print("Demo database ready")


def retrieval_command():
    from teller.benchmark.retrieval_eval import run_retrieval_eval

    run_retrieval_eval()


def benchmark_command(pipeline, split, limit):
    from teller.benchmark.report import summarize_run
    from teller.benchmark.runner import run_benchmark

    run = run_benchmark(pipeline, split, limit)
    print(summarize_run(run))


def serve_command(host, port):
    import uvicorn

    uvicorn.run("teller.api.server:app", host=host, port=port)


def build_parser():
    parser = argparse.ArgumentParser(description="Teller: agentic RAG for bank support")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("index", help="build the local search index")
    commands.add_parser("retrieval", help="compare search methods, no API cost")

    benchmark_parser = commands.add_parser("benchmark", help="run the agent on benchmark tasks")
    benchmark_parser.add_argument(
        "--pipeline",
        default="teller",
        choices=["no_docs", "bm25", "teller", "teller_no_checks", "teller_golden", "golden"],
    )
    benchmark_parser.add_argument(
        "--split",
        default="development",
        choices=["development", "holdout", "all"],
    )
    benchmark_parser.add_argument("--limit", type=int, default=5, help="0 runs every task")

    serve_parser = commands.add_parser("serve", help="start the web app")
    serve_parser.add_argument("--port", type=int, default=8010)
    serve_parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside a container")

    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()

    # The imports sit inside each command, so a command only loads what it needs
    if args.command == "index":
        index_command()
    elif args.command == "retrieval":
        retrieval_command()
    elif args.command == "benchmark":
        benchmark_command(args.pipeline, args.split, args.limit)
    elif args.command == "serve":
        serve_command(args.host, args.port)
