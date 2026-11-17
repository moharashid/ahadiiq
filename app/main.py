from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.agreements import router as agreements_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dash_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
app = FastAPI()

app.include_router(health_router)
app.include_router(agreements_router)
app.include_router(auth_router)
app.include_router(dash_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/static/images", StaticFiles(directory=STATIC_DIR), name="static_images")

@app.get("/dashboard")
def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard.html")
