from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, health, interactions, recommendations, works

app = FastAPI(title="Chronicle")

if settings.cors_origin_list:
    # Auth is a bearer token in the Authorization header (no cookies), so credentials stay off.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(health.router)
app.include_router(works.router)
app.include_router(auth.router)
app.include_router(interactions.router)
app.include_router(recommendations.router)
