from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestIDMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(title=settings.app_name, debug=settings.debug)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
