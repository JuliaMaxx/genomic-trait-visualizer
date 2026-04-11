import re
from collections.abc import Iterable
from typing import TypedDict


class Signature(TypedDict, total=False):
    comments: list[str]
    headers: list[set[str]]
    min_columns: int


SIGNATURES: dict[str, Signature] = {
    "23andme": {
        "comments": ["23andme", "this file contains raw dna data"],
        "headers": [{"rsid", "genotype"}],
        "min_columns": 4,
    },
    "ancestry": {
        "comments": ["ancestrydna", "ancestry"],
        "headers": [{"rsid", "allele1", "allele2"}],
        "min_columns": 5,
    },
    "myheritage": {
        "comments": ["myheritage"],
        "headers": [{"rsid", "genotype"}],
        "min_columns": 4,
    },
    "ftdna": {
        "comments": ["familytreedna", "ftdna"],
        "headers": [{"rsid", "result"}],
        "min_columns": 4,
    },
    "livingdna": {
        "comments": ["livingdna", "dna.living"],
        "headers": [{"rsid", "call"}, {"rsid", "genotype"}],
        "min_columns": 4,
    },
    "gedmatch": {
        "comments": ["gedmatch"],
        "headers": [{"rsid"}],  # GEDmatch is inconsistent
        "min_columns": 4,
    },
}


def split_line(line: str) -> list[str]:
    return [p for p in re.split(r"[,\t\s]+", line.strip()) if p]


# -----------------------------
# Detect format function
# -----------------------------


def detect_format(lines: Iterable[str]) -> str:
    """
    Detect DNA file format.
    Supports: 23andMe, AncestryDNA, MyHeritage, FTDNA, LivingDNA, GEDmatch, VCF
    """

    # Normalize
    stripped: list[str] = [line.strip() for line in lines if line.strip()]
    if not stripped:
        raise ValueError("Empty file")

    comments: list[str] = [line.lower() for line in stripped if line.startswith("#")]
    data_lines: list[str] = [line for line in stripped if not line.startswith("#")]

    # 1. Check VCF separately first (very distinct)
    for line in stripped[:20]:
        if line.lower().startswith("##fileformat=vcf") or line.lower().startswith(
            "#chrom"
        ):
            return "vcf"

    # 2. Check comments
    for provider, sig in SIGNATURES.items():
        for key in sig.get("comments", []):
            if any(key.lower() in line for line in comments):
                return provider

    # 3. Check headers
    for line in data_lines[:5]:
        header_parts = set(p.lower() for p in split_line(line))

        for provider, sig in SIGNATURES.items():
            headers_list = sig.get("headers", [])
            for required_header in headers_list:
                if required_header.issubset(header_parts):
                    return provider

    # 4. Row pattern fallback (rsid detection)
    sample_rows: list[str] = data_lines[:5]
    parsed_rows: list[list[str]] = [split_line(row) for row in sample_rows if row]

    def looks_like_rsid(value: str) -> bool:
        return bool(re.fullmatch(r"rs\d+", value.lower()))

    rsid_like: int = sum(1 for row in parsed_rows if row and looks_like_rsid(row[0]))
    if rsid_like >= 3:
        # Column-count based differentiation
        lengths: list[int] = [len(row) for row in parsed_rows]
        candidates = []

        for provider, sig in SIGNATURES.items():
            min_cols = sig.get("min_columns", 0)
            if all(length >= min_cols for length in lengths):
                candidates.append((provider, min_cols))

        if candidates:
            # pick the one with highest column requirement (most specific)
            return max(candidates, key=lambda x: x[1])[0]

    # 5. Fallback
    return "unknown"
