import os

from fastapi import UploadFile

from backend.models import Variant
from backend.services.parsers import (
    parse_23andme,
    parse_ancestry,
    parse_ftdna,
    parse_gedmatch,
    parse_livingdna,
    parse_myheritage,
    parse_vcf,
)

from .dna_format_detector import detect_format

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


async def process_dna_file(file: UploadFile) -> list[Variant]:
    # TODO: avoid putting an entire file into memory
    content = await file.read()
    lines = content.decode("utf-8", errors="ignore").splitlines()

    fmt = detect_format(lines)

    PARSERS = {
        "23andme": parse_23andme,
        "ancestry": parse_ancestry,
        "ftdna": parse_ftdna,
        "livingdna": parse_livingdna,
        "myheritage": parse_myheritage,
        "gedmatch": parse_gedmatch,
        "vcf": parse_vcf,
    }

    parser = PARSERS.get(fmt)

    if not parser:
        raise ValueError("Unknown DNA file format")

    return parser(lines).variants
