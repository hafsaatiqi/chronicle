from fastapi import FastAPI

from app.routers import auth, health, works

app = FastAPI(title="Chronicle")

app.include_router(health.router)
app.include_router(works.router)
app.include_router(auth.router)
