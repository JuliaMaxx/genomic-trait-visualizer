import re

from fastapi.logger import logger

from backend.models.schemas import ParseResult, Variant
from backend.services.parsers.chromosomes import VALID_CHROMOSOMES, normalize_chromosome

_MISSING_ALLELE = {"", "--", "NA", "N", ".", "0"}


def normalize_ancestry_chromosome(chrom: str) -> str:
    """Map AncestryDNA numeric sex/MT codes, then apply 23andMe-style normalization."""
    c = chrom.strip().upper()
    if c == "23":
        return "X"
    if c == "24":
        return "Y"
    if c == "25":
        return "MT"
    return normalize_chromosome(c)


def _is_missing_allele(allele: str) -> bool:
    return allele.strip().upper() in _MISSING_ALLELE


def normalize_genotype_from_ancestry_alleles(allele1: str, allele2: str) -> str | None:
    """
    Build a diploid or haploid genotype string from AncestryDNA ALLELE1/ALLELE2.
    """
    a1 = allele1.strip().upper()
    a2 = allele2.strip().upper()

    m1, m2 = _is_missing_allele(allele1), _is_missing_allele(allele2)

    if m1 and m2:
        return None
    if m1:
        if re.fullmatch(r"[ACGTID]", a2):
            return a2
        return None
    if m2:
        if re.fullmatch(r"[ACGTID]", a1):
            return a1
        return None

    combined = a1 + a2
    if re.fullmatch(r"[ACGTID]{2}", combined):
        return combined
    return None


def _is_valid_ancestry_rsid(rsid: str) -> bool:
    r = rsid.strip().lstrip("\ufeff")
    if r == ".":
        return True
    return bool(re.match(r"^(rs|i)\d+$", r, re.IGNORECASE))


def _split_line(line: str) -> list[str]:
    line = line.strip()
    if "\t" in line:
        return line.split("\t")
    if "," in line:
        return [p.strip() for p in line.split(",")]
    return re.split(r"\s+", line)


def _is_header_row(parts: list[str]) -> bool:
    if not parts:
        return False
    return parts[0].lstrip("\ufeff").strip().lower() == "rsid"


def parse_ancestry_dna(lines: list[str]) -> ParseResult:
    variants: list[Variant] = []
    errors: list[str] = []

    header_skipped = False

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        parts = _split_line(line)

        if not header_skipped and _is_header_row(parts):
            header_skipped = True
            continue

        if len(parts) < 5:
            msg = f"Line {line_number}: invalid format"
            logger.warning(msg)
            errors.append(msg)
            continue

        rsid, chrom, pos, allele1, allele2 = parts[:5]
        rsid = rsid.lstrip("\ufeff")

        if not _is_valid_ancestry_rsid(rsid):
            msg = f"Line {line_number}: invalid rsid"
            logger.warning(msg)
            errors.append(msg)
            continue

        chrom = normalize_ancestry_chromosome(chrom)

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

        genotype = normalize_genotype_from_ancestry_alleles(allele1, allele2)
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
