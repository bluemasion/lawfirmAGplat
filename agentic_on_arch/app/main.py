"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.errors import register_exception_handlers
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting ({settings.ENV})")
    yield
    logger.info("👋 Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    from app.api import auth, agent, chat, knowledge, file
    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
    app.include_router(chat.router, prefix="/api/chat", tags=["对话"])
    app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
    app.include_router(file.router, prefix="/api/file", tags=["文件"])

    # --- Health check ---
    @app.get("/health", tags=["系统"])
    async def health():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "env": settings.ENV,
        }

    return app


app = create_app()
