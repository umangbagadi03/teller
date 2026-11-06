import argparse


def index_command(args):
    from teller.knowledge.vector_search import build_index

    count = build_index()
    print("Indexed", count, "documents")


def retrieval_command(args):
    from teller.benchmark.retrieval_eval import run_retrieval_eval

    run_retrieval_eval()


def benchmark_command(args):
    from teller.benchmark.report import summarize_run
    from teller.benchmark.runner import run_benchmark

    run = run_benchmark(args.pipeline, args.split, args.limit)
    print(summarize_run(run))


def serve_command(args):
    import uvicorn

    uvicorn.run("teller.api.server:app", host="127.0.0.1", port=args.port)


def build_parser():
    parser = argparse.ArgumentParser(description="Teller: agentic RAG for bank support")
    commands = parser.add_subparsers(dest="command", required=True)

    index_parser = commands.add_parser("index", help="build the local search index")
    index_parser.set_defaults(run=index_command)

    retrieval_parser = commands.add_parser("retrieval", help="compare search methods, no API cost")
    retrieval_parser.set_defaults(run=retrieval_command)

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
    benchmark_parser.set_defaults(run=benchmark_command)

    serve_parser = commands.add_parser("serve", help="start the web app")
    serve_parser.add_argument("--port", type=int, default=8010)
    serve_parser.set_defaults(run=serve_command)

    return parser


if __name__ == "__main__":
    parsed_args = build_parser().parse_args()
    parsed_args.run(parsed_args)
