import io
import os
from typing import Callable, Iterator

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool

from backend.models import ParseResult
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


# ------------------------
# Streaming helper
# ------------------------
def _stream_text_lines(file: UploadFile) -> Iterator[str]:
    file.file.seek(0)

    with io.TextIOWrapper(
        file.file,
        encoding="utf-8",
        errors="ignore",
        newline="",
    ) as text_wrapper:
        for raw_line in text_wrapper:
            yield raw_line.rstrip("\n")


# ------------------------
# Parser registry
# ------------------------
PARSERS: dict[str, Callable[[list[str]], ParseResult]] = {
    "23andme": parse_23andme,
    "ancestry": parse_ancestry,
    "ftdna": parse_ftdna,
    "livingdna": parse_livingdna,
    "myheritage": parse_myheritage,
    "gedmatch": parse_gedmatch,
    "vcf": parse_vcf,
}


# ------------------------
# Core sync processor
# ------------------------
def _process_dna_file_sync(file: UploadFile) -> ParseResult:
    lines = _stream_text_lines(file)

    # Read only first N lines into a small buffer
    peek_buffer: list[str] = []
    for _ in range(200):
        try:
            peek_buffer.append(next(lines))
        except StopIteration:
            break

    # Detect format
    fmt = detect_format(peek_buffer)

    parser = PARSERS.get(fmt)
    if not parser:
        raise ValueError("Unknown DNA file format")

    def full_stream() -> Iterator[str]:
        yield from peek_buffer
        yield from lines

    result = parser(list(full_stream()))

    return result


# ------------------------
# Async entrypoint
# ------------------------
async def process_dna_file(file: UploadFile) -> ParseResult:
    return await run_in_threadpool(_process_dna_file_sync, file)
