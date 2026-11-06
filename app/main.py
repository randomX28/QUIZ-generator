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

@app.get("/api/system/network-info", tags=["System"])
def get_network_info():
    """Detect and return host local network IP addresses for mobile QR connection."""
    import socket
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        if ip and not ip.startswith('127.'):
            ips.add(ip)
        s.close()
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.'):
                ips.add(ip)
    except Exception:
        pass

    preferred_ip = list(ips)[0] if ips else "127.0.0.1"
    return {
        "preferred_ip": preferred_ip,
        "available_ips": list(ips),
        "port": settings.PORT,
        "is_loopback": preferred_ip == "127.0.0.1"
    }

# Serve frontend
STATIC_DIR = str(settings.STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
