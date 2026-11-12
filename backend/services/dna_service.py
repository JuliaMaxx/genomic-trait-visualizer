import io
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterator, Literal

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool

from backend.models import ParseResult
from backend.models.interpretation import VariantRequirements
from backend.services.parsers import (
    parse_23andme,
    parse_ancestry,
    parse_ftdna,
    parse_gedmatch,
    parse_livingdna,
    parse_myheritage,
    parse_vcf,
)
from backend.services.parsers.common import split_line
from backend.services.trait_curation.offline import Observation

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


# Stage 6 operations are separate from the legacy upload/API path above.
ObservationStatus = Literal[
    "usable",
    "absent",
    "no_call",
    "partial",
    "invalid",
    "conflicting",
    "unresolved",
    "incompatible",
    "unsupported",
]


@dataclass(frozen=True)
class IngestionResult:
    provider: str
    observations: list[Observation]
    diagnostics: list[str]
    metadata: list[str]
    invalid_rsids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ObservationMatch:
    status: ObservationStatus
    diagnostics: list[str]
    observation: Observation | None = None


# GRCh37 primary autosomes, independently of any interpretation requirements.
# https://www.ncbi.nlm.nih.gov/grc/human/data?asm=GRCh37
GRCH37_ACCESSIONS = {
    "1": "NC_000001.10",
    "2": "NC_000002.11",
    "3": "NC_000003.11",
    "4": "NC_000004.11",
    "5": "NC_000005.9",
    "6": "NC_000006.11",
    "7": "NC_000007.13",
    "8": "NC_000008.10",
    "9": "NC_000009.11",
    "10": "NC_000010.10",
    "11": "NC_000011.9",
    "12": "NC_000012.11",
    "13": "NC_000013.10",
    "14": "NC_000014.8",
    "15": "NC_000015.9",
    "16": "NC_000016.9",
    "17": "NC_000017.10",
    "18": "NC_000018.9",
    "19": "NC_000019.9",
    "20": "NC_000020.10",
    "21": "NC_000021.8",
    "22": "NC_000022.10",
}


def _metadata_value(values: set[str], name: str, diagnostics: list[str]) -> str | None:
    if len(values) != 1:
        reason = "missing" if not values else "conflicting"
        diagnostics.append(f"{reason.capitalize()} {name} metadata.")
        return None
    return next(iter(values))


def ingest_dna(lines: list[str]) -> IngestionResult:
    """Read identified 23andMe TSV; retain raw calls before strict matching."""
    lines = [line.lstrip("\ufeff") for line in lines]
    metadata = [line.strip() for line in lines if line.strip().startswith("#")]
    comments = "\n".join(metadata).lower()
    if not re.search(r"\b23andme\b", comments) or detect_format(lines) != "23andme":
        raise ValueError("Unsupported DNA format; Stage 6 requires identified 23andMe.")

    diagnostics: list[str] = []
    builds = {
        value.rstrip(".")
        for value in re.findall(r"\b(?:build\s*|grch)([^\s(),]+)", comments)
    }
    build = _metadata_value(builds, "genome build", diagnostics)
    genome_build = f"GRCh{build}" if build in {"37", "38"} else build
    strands: set[str] = set()
    for line in metadata:
        if "strand" in line.lower():
            strands.update(
                re.findall(
                    r"\b(plus|minus|forward|reverse|unknown)"
                    r"(?:\s+\([+-]\))?\s+strand\b",
                    line.lower(),
                )
                or ["unknown"]
            )
    orientations = {
        {
            "plus": "forward_genomic",
            "forward": "forward_genomic",
            "minus": "reverse_genomic",
            "reverse": "reverse_genomic",
        }.get(value, value)
        for value in strands
    }
    orientation = _metadata_value(orientations, "orientation", diagnostics)

    parser_lines = list(lines)
    source_counts: Counter[str] = Counter()
    invalid_rsids: set[str] = set()
    for index, line in enumerate(lines):
        if not line.strip() or line.strip().startswith("#"):
            continue
        parts = split_line(line)
        if parts and parts[0].lower() == "rsid":
            continue
        columns = line.rstrip("\r\n").split("\t")
        if len(columns) != 4 or any(
            len(split_line(value)) != 1 for value in columns[:3]
        ):
            diagnostics.append(
                f"Line {index + 1}: unsupported layout; "
                "expected four tab-separated columns"
            )
            if parts:
                invalid_rsids.add(parts[0].lower())
            parser_lines[index] = ""
        elif parts:
            source_counts[parts[0].lower()] += 1

    parsed = parse_23andme(parser_lines)
    diagnostics.extend(parsed.errors)
    parsed_counts = Counter(variant.rsid.lower() for variant in parsed.variants)
    # A malformed duplicate must not disappear and leave a clean call usable.
    invalid_rsids.update(
        rsid for rsid, count in source_counts.items() if parsed_counts[rsid] != count
    )
    observations = [
        Observation(
            rsid=variant.rsid.lower(),
            genotype=variant.raw_genotype,
            chromosome=variant.chromosome,
            position=variant.position,
            genome_build=genome_build,
            orientation=orientation,
            coordinate_system="1-based",
            ploidy=(
                len(variant.raw_genotype)
                if variant.raw_genotype
                and re.fullmatch(r"[ACGTIDacgtid]+", variant.raw_genotype)
                else None
            ),
        )
        for variant in parsed.variants
    ]
    return IngestionResult(
        "23andme", observations, diagnostics, metadata, invalid_rsids
    )


def _call_status(genotype: str | None) -> ObservationStatus:
    if genotype in (None, "", "--"):
        return "no_call"
    assert genotype is not None
    if re.fullmatch(r"[ACGT?\-]+", genotype) and any(c in genotype for c in "?-"):
        return "partial"
    if not re.fullmatch(r"[ACGTID]+", genotype):
        return "invalid"
    if len(genotype) != 2 or any(c in genotype for c in "ID"):
        return "unsupported"
    return "usable"


def match_observation(
    ingestion: IngestionResult, requirements: VariantRequirements
) -> ObservationMatch:
    """Expose one canonical observation only after all compatibility checks pass."""
    requirements = VariantRequirements.model_validate(requirements.model_dump())

    def withhold(status: ObservationStatus, message: str) -> ObservationMatch:
        return ObservationMatch(status, [message])

    if ingestion.provider != "23andme":
        return withhold("unsupported", "Only the 23andMe representation is supported.")
    if requirements.rsid in ingestion.invalid_rsids:
        return withhold("invalid", "A row for this marker has invalid structure.")
    rows = []
    for observation in ingestion.observations:
        if observation.rsid != requirements.rsid:
            continue
        genotype = observation.genotype.upper() if observation.genotype else None
        if _call_status(genotype) == "usable":
            genotype = "".join(sorted(genotype or ""))
        rows.append(observation.model_copy(update={"genotype": genotype}))
    if not rows:
        return withhold("absent", "The required marker is absent from the file.")
    observation = rows[0]
    if any(row != observation for row in rows[1:]):
        return withhold("conflicting", "Duplicate rows disagree for this marker.")
    status = _call_status(observation.genotype)
    if status != "usable":
        return withhold(status, f"The raw genotype is {status.replace('_', ' ')}.")
    if observation.chromosome not in GRCH37_ACCESSIONS or observation.ploidy != 2:
        return withhold("unsupported", "Only diploid autosomal SNVs are supported.")
    if observation.genome_build is None or observation.orientation in (None, "unknown"):
        return withhold("unresolved", "Genome build or orientation is unresolved.")
    if observation.genome_build != "GRCh37":
        return withhold("unsupported", "Only Build 37 uploads are supported.")
    if any(
        getattr(observation, name) is None for name in ("position", "coordinate_system")
    ):
        return withhold("unresolved", "Required representation metadata is missing.")
    # Uploads do not supply RefSeq accessions. Resolve only the verified assembly.
    accession = GRCH37_ACCESSIONS[observation.chromosome]
    placement = next(
        (
            item
            for item in requirements.placements
            if item.genome_build == observation.genome_build
        ),
        None,
    )
    if (
        placement is None
        or observation.chromosome != placement.chromosome
        or observation.position != placement.position
        or accession != placement.sequence_accession
        or observation.sequence_accession not in (None, accession)
        or observation.orientation != requirements.orientation
        or observation.coordinate_system != requirements.coordinate_system
        or observation.ploidy != requirements.ploidy
        or not set(observation.genotype or "") <= set(requirements.alleles)
    ):
        return withhold(
            "incompatible", "The observation does not match rule requirements."
        )
    return ObservationMatch(
        "usable", [], observation.model_copy(update={"sequence_accession": accession})
    )
