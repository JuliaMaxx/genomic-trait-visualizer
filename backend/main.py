from fastapi import FastAPI

from backend.routes import router

app = FastAPI(title="Genomic Trait Visualizer")

app.include_router(router)
