from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import AsyncMongoClient

from app.auth import router as auth_router
from app.config import Settings
from app.database import ensure_indexes
from app.routers.questions import router as questions_router
from app.routers.topics import router as topics_router


def create_app(
    settings: Settings | None = None,
    *,
    database=None,
    mongo_client=None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        client = mongo_client
        try:
            selected_database = database
            if selected_database is None:
                if client is None:
                    client = AsyncMongoClient(
                        settings.mongodb_uri,
                        tz_aware=True,
                        serverSelectionTimeoutMS=5000,
                    )
                await client.admin.command("ping")
                selected_database = client[settings.mongodb_db_name]

            application.state.settings = settings
            application.state.mongo_client = client
            application.state.database = selected_database
            await ensure_indexes(selected_database)
            yield
        finally:
            if mongo_client is None and client is not None:
                await client.close()

    application = FastAPI(
        title="AI Assessment Generator API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.database = database
    application.state.mongo_client = mongo_client

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @application.middleware("http")
    async def enforce_trusted_origin(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            if request.headers.get("origin") not in settings.allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Request origin is not allowed."},
                )
        return await call_next(request)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        errors = [
            {
                "loc": error.get("loc", ()),
                "msg": error.get("msg", "Invalid value."),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

    application.include_router(auth_router)
    application.include_router(topics_router)
    application.include_router(questions_router)
    return application


app = create_app()
