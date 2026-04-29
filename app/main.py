import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routers import admin, chat, images, models
from app.services.admin_auth import has_admin_session
from app.services.image_cache import image_cache
from app.services.pollinations import close_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
LOGIN_PAGE = STATIC_DIR / "login.html"
ADMIN_PAGE = STATIC_DIR / "index.html"
PROTECTED_ASSETS = {
    "admin.css": STATIC_DIR / "admin.css",
    "admin.js": STATIC_DIR / "admin.js",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await image_cache.start_cleanup_loop()
    logger.info("Ready")
    yield
    logger.info("Shutting down...")
    await image_cache.stop_cleanup_loop()
    await close_client()


app = FastAPI(title="zimage", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(admin.router)


@app.get("/")
async def root(request: Request):
    return _panel_page(request)


@app.get("/static/index.html")
async def static_index(request: Request):
    return _panel_page(request)


@app.get("/static/{asset_name}")
async def static_asset(asset_name: str, request: Request):
    asset_path = PROTECTED_ASSETS.get(asset_name)
    if asset_path is None:
        raise HTTPException(status_code=404, detail="Static asset not found")
    if not has_admin_session(request):
        raise HTTPException(status_code=401, detail="Admin login required")
    return FileResponse(asset_path)


@app.get("/health")
async def health():
    return {"status": "ok"}


def _panel_page(request: Request):
    if has_admin_session(request):
        return FileResponse(ADMIN_PAGE)
    return FileResponse(LOGIN_PAGE)
