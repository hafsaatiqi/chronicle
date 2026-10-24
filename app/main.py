from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Chronicle")

app.include_router(health.router)
