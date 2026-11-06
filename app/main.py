import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import init_db
from app.routers import questions, papers, grading, results, banks

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

# Initialize database on startup
@app.on_event("startup")
def startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("Application startup complete.")

# API routers
app.include_router(banks.router)
app.include_router(questions.router)
app.include_router(papers.router)
app.include_router(grading.router)
app.include_router(results.router)

# Serve frontend
STATIC_DIR = str(settings.STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
