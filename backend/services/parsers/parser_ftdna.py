from fastapi.logger import logger

from backend.models.schemas import ParseResult, Variant
from backend.services.parsers.common import (
    VALID_CHROMOSOMES,
    is_standard_rsid,
    normalize_chromosome,
    normalize_genotype,
    split_line,
)


def _is_header_row(parts: list[str]) -> bool:
    if not parts:
        return False

    normalized = [part.lstrip("\ufeff").strip().lower() for part in parts]
    if "rsid" not in normalized:
        return False

    return any(
        header in normalized
        for header in ("result", "call", "genotype", "allele1", "allele2")
    )


def parse_ftdna(lines: list[str]) -> ParseResult:
    """
    Parse a FamilyTreeDNA raw DNA export into the common Variant schema.

    FTDNA raw export files are usually CSV with columns like:
    - RSID,Chromosome,Position,Result

    This parser also tolerates:
    - tab/CSV/whitespace-delimited input
    - optional header rows
    - optional split-allele layouts where allele1 and allele2 are present
    - extra trailing columns beyond the first four
    """
    variants: list[Variant] = []
    errors: list[str] = []
    header_skipped = False

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = split_line(line)

        if not header_skipped and _is_header_row(parts):
            header_skipped = True
            continue

        if len(parts) < 3:
            msg = f"Line {line_number}: invalid format"
            logger.warning(msg)
            errors.append(msg)
            continue

        rsid, chrom, pos = parts[0], parts[1], parts[2]
        rsid = rsid.lstrip("\ufeff")

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

        if not is_standard_rsid(rsid):
            msg = f"Line {line_number}: invalid rsid"
            logger.warning(msg)
            errors.append(msg)

        if len(parts) >= 5:
            allele1, allele2 = parts[3], parts[4]
            genotype = normalize_genotype(allele1=allele1, allele2=allele2)
        elif len(parts) >= 4:
            genotype = normalize_genotype(genotype=parts[3])
        else:
            genotype = None

        if genotype is None:
            msg = f"Line {line_number}: invalid genotype"
            logger.warning(msg)
            errors.append(msg)

        variants.append(
            Variant(
                rsid=rsid,
                chromosome=chrom,
                position=position,
                genotype=genotype,
            )
        )

    return ParseResult(variants=variants, errors=errors)
