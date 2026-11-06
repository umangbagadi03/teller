from fastapi import APIRouter, HTTPException

from teller.benchmark.report import list_runs, load_retrieval_report, load_run

router = APIRouter()


@router.get("/api/results")
def get_results():
    return {"runs": list_runs(), "retrieval": load_retrieval_report()}


@router.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = load_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run
