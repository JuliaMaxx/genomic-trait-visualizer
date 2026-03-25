from fastapi import FastAPI

from backend.routes import analyze_dna

app = FastAPI(title="Genomic Trait Visualizer")

app.include_router(analyze_dna.router)
