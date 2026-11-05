import os
from collections.abc import AsyncGenerator

# The ASGI test transport talks to the app over plain "http://test", so a cookie
# marked Secure would never be sent back on the next request within the same test.
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
async def _dispose_engine_after_test() -> AsyncGenerator[None, None]:
    # pytest-asyncio opens a new event loop per test, but the SQLAlchemy engine (and its
    # pooled asyncpg connections) is a module-level singleton created once. A connection
    # left in the pool from a previous test is bound to that test's now-closed event loop,
    # so disposing after every test forces a fresh connection on the next one.
    yield
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
