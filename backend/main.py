from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import router
from backend.services.active_traits import load_active_traits


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict[str, object], None]:
    # Request state receives this verified snapshot for the whole app lifetime.
    yield {"active_traits": load_active_traits()}


app = FastAPI(title="Genomic Trait Visualizer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
