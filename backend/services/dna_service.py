import os

import pandas as pd
from fastapi import UploadFile

from backend.models.schemas import Variant

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


async def process_dna_file(file: UploadFile) -> list[Variant]:

    df = pd.read_csv(file.file, sep="\t", comment="#")

    variants: list[Variant] = df[["rsid", "genotype"]].to_dict(orient="records")

    return variants
