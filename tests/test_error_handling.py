from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.error_handlers import register_exception_handlers
from app.core.exceptions import NotFound
from app.core.responses import paginated, success
from app.main import app as real_app
from app.schemas.common.response import PaginationMeta


class _Item(BaseModel):
    id: int
    name: str


class _CreateItem(BaseModel):
    name: str
    quantity: int


def _build_test_app() -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/success")
    async def _success() -> object:
        return success(data=_Item(id=1, name="Order"), message="Order fetched successfully!")

    @test_app.get("/success-list")
    async def _success_list() -> object:
        items = [_Item(id=1, name="Order 1"), _Item(id=2, name="Order 2")]
        meta = PaginationMeta(page=1, limit=20, total=2, total_pages=1)
        return paginated(items=items, meta=meta, message="Orders fetched successfully!")

    @test_app.get("/not-found")
    async def _not_found() -> object:
        raise NotFound("User not found!", error_code="USER_NOT_FOUND")

    @test_app.post("/validate")
    async def _validate(body: _CreateItem) -> object:
        return success(data=body)

    @test_app.get("/integrity")
    async def _integrity() -> object:
        raise IntegrityError(
            "INSERT INTO items", {}, Exception("duplicate key value violates unique constraint")
        )

    @test_app.get("/db-down")
    async def _db_down() -> object:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    @test_app.get("/timeout")
    async def _timeout() -> object:
        raise TimeoutError("upstream timed out")

    @test_app.get("/boom")
    async def _boom() -> object:
        raise RuntimeError("db password=hunter2 leaked in error")

    return test_app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=_build_test_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def real_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=real_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_success_single(client: AsyncClient) -> None:
    response = await client.get("/success")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["statusCode"] == 200
    assert body["message"] == "Order fetched successfully!"
    assert body["data"] == {"id": 1, "name": "Order"}


async def test_success_list_with_meta(client: AsyncClient) -> None:
    response = await client.get("/success-list")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"] == {"page": 1, "limit": 20, "total": 2, "totalPages": 1}
    assert len(body["data"]) == 2


async def test_unknown_route_returns_404(real_client: AsyncClient) -> None:
    response = await real_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["errorCode"] == "NOT_FOUND"
    assert "requestId" in body


async def test_method_not_allowed_returns_405(real_client: AsyncClient) -> None:
    response = await real_client.post("/api/v1/health")

    assert response.status_code == 405
    body = response.json()
    assert body["success"] is False
    assert body["errorCode"] == "METHOD_NOT_ALLOWED"


async def test_validation_error_returns_422_with_field_path(client: AsyncClient) -> None:
    response = await client.post("/validate", json={"name": "Order"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Invalid input."
    assert any(err["path"] == "body.quantity" for err in body["errorMessages"])


async def test_app_exception_not_found(client: AsyncClient) -> None:
    response = await client.get("/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "User not found!"
    assert body["errorCode"] == "USER_NOT_FOUND"


async def test_integrity_error_returns_409(client: AsyncClient) -> None:
    response = await client.get("/integrity")

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["errorCode"] == "ALREADY_EXISTS"


async def test_db_down_returns_503(client: AsyncClient) -> None:
    response = await client.get("/db-down")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Service temporarily unavailable. Please try again."


async def test_timeout_returns_504(client: AsyncClient) -> None:
    response = await client.get("/timeout")

    assert response.status_code == 504
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "The request took too long. Please try again."


async def test_unhandled_exception_returns_generic_500(client: AsyncClient) -> None:
    response = await client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Something went wrong. Please try again later."
    assert "requestId" in body
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text


@pytest.mark.parametrize(
    "path",
    ["/not-found", "/integrity", "/db-down", "/timeout", "/boom"],
)
async def test_no_traceback_leaks_in_error_body(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert "Traceback (most recent call last)" not in response.text
    assert "File \"" not in response.text
