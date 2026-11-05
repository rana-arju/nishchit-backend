from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, health, leads, oauth, products

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(oauth.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(leads.router)
