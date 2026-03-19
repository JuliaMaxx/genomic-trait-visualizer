from fastapi import FastAPI

from backend.routes import traits, upload

app = FastAPI(title="Genomic Trait Visualizer")

app.include_router(upload.router)
app.include_router(traits.router)
