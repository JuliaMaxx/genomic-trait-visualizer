import os

from fastapi import UploadFile

from backend.models.schemas import Variant
from backend.services.parsers.parser_23andme import parse_23andme
from backend.services.parsers.parser_ancestry_dna import parse_ancestry_dna
from backend.services.parsers.parser_myheritage import parse_myheritage

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
        "ancestry": parse_ancestry_dna,
        "myheritage": parse_myheritage,
        # "ftdna": parse_ftdna,
        # "livingdna": parse_livingdna,
        # "gedmatch": parse_gedmatch,
        # "vcf": parse_vcf,
    }

    parser = PARSERS.get(fmt)

    if not parser:
        raise ValueError("Unknown DNA file format")

    return parser(lines).variants
