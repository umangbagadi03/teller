from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from teller import config
from teller.api.case_routes import router as case_router
from teller.api.result_routes import router as result_router

app = FastAPI(title="Teller")
app.include_router(case_router)
app.include_router(result_router)

# This comes last, so the API routes above are matched first
app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
