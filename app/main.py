import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routers import auth, billing, tokens, api
from .utils.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="SP500 Data Service")

    # Static & templates
    base_dir = os.path.dirname(os.path.dirname(__file__))
    static_dir = os.path.join(base_dir, "static")
    template_dir = os.path.join(base_dir, "templates")

    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    templates = Jinja2Templates(directory=template_dir)
    app.state.templates = templates

    # Routers
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
    app.include_router(api.router, prefix="/api", tags=["api"])

    @app.on_event("startup")
    async def on_startup() -> None:
        init_db()

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """
        首页：解释为什么需要“历史真实”的标普500成分列表，
        并引用《Stocks on the Move》的观点（用自己的话概述，非逐字引用）。
        """
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
            },
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        # 简单重定向到令牌管理页（后续可扩展成真正的仪表盘）
        return RedirectResponse(url="/tokens", status_code=302)

    return app


app = create_app()

