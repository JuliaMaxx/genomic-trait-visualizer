import re

from fastapi.logger import logger

from backend.models.schemas import ParseResult, Variant
from backend.services.parsers.chromosomes import VALID_CHROMOSOMES, normalize_chromosome


def normalize_genotype(genotype: str) -> str | None:
    genotype = genotype.strip().upper()

    if genotype in {"--", "", "NA"}:
        return None

    # Ensure only valid DNA letters
    if not re.fullmatch(r"[ACGT]{1,2}", genotype):
        return None

    return genotype


def parse_23andme(lines: list[str]) -> ParseResult:
    variants: list[Variant] = []
    errors: list[str] = []

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        parts = re.split(r"\s+", line)

        if len(parts) < 4:
            msg = f"Line {line_number}: invalid format"
            logger.warning(msg)
            errors.append(msg)
            continue

        rsid, chrom, pos, genotype = parts[:4]

        if not rsid.startswith(("rs", "i")):
            msg = f"Line {line_number}: invalid rsid"
            logger.warning(msg)
            errors.append(msg)
            continue

        chrom = normalize_chromosome(chrom)

        if chrom not in VALID_CHROMOSOMES:
            msg = f"Line {line_number}: invalid chromosome"
            logger.warning(msg)
            errors.append(msg)
            continue

        try:
            position = int(pos)
        except ValueError:
            msg = f"Line {line_number}: invalid position"
            logger.warning(msg)
            errors.append(msg)
            continue

        genotype = normalize_genotype(genotype)
        if genotype is None:
            errors.append(f"Line {line_number}: invalid genotype")

        variants.append(
            Variant(
                rsid=rsid,
                chromosome=chrom,
                position=position,
                genotype=genotype,
            )
        )

    return ParseResult(variants=variants, errors=errors)
