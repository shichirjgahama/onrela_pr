from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401, чтобы модели зарегистрировались до create_all
from app.database import Base, engine
from app.api.tickets import router as tickets_router
from app.api.brigades import router as brigades_router
from app.api.warehouse import router as warehouse_router
from app.api.refs import router as refs_router
from app.api.clients import router as clients_router
from app.api.keys import router as keys_router
from app.api.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Для учебного проекта create_all допустим.
    # В реальном проекте лучше использовать Alembic.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ISP Field Service ERP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vue/Vite
        "http://localhost:5174",
        "http://localhost:3000",  # React
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(brigades_router, prefix="/api/v1")
app.include_router(warehouse_router, prefix="/api/v1")
app.include_router(refs_router, prefix="/api/v1")
app.include_router(clients_router, prefix="/api/v1")
app.include_router(keys_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
