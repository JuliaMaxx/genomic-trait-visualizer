import re

from fastapi.logger import logger

from backend.models.schemas import ParseResult, Variant
from backend.services.parsers.chromosomes import VALID_CHROMOSOMES, normalize_chromosome

_MISSING_ALLELE = {"", "--", "NA", "N", ".", "0"}
_ALLELE_RE = re.compile(r"^[ACGTID]$")


def normalize_myheritage_chromosome(chrom: str) -> str:
    """
    MyHeritage can sometimes encode sex/MT chromosomes as numeric codes.
    Map those to the same values used across the app.
    """
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


def _split_line(line: str) -> list[str]:
    """
    Split a line from a raw MyHeritage export.

    Supports tab, comma, and whitespace-delimited exports.
    """
    s = line.strip()
    if "\t" in s:
        return s.split("\t")
    if "," in s:
        return [p.strip() for p in s.split(",")]
    return re.split(r"\s+", s)


def _is_header_row(parts: list[str]) -> bool:
    if not parts:
        return False
    return parts[0].lstrip("\ufeff").strip().lower() == "rsid"


def _is_valid_myheritage_rsid(rsid: str) -> bool:
    r = rsid.strip().lstrip("\ufeff")
    if r == ".":
        return True
    return bool(re.match(r"^(rs|i)\d+$", r, re.IGNORECASE))


def normalize_genotype_token(token: str) -> str | None:
    """
    Normalize a MyHeritage genotype token (already combined, e.g. "AA" or "ID").
    """
    t = token.strip().upper()
    if t in _MISSING_ALLELE:
        return None

    # SNP genotype: e.g. AA, AG, CC
    if re.fullmatch(r"[ACGT]{2}", t):
        return t

    # Indel genotype: e.g. ID, DI, II, DD
    if re.fullmatch(r"[ID]{2}", t):
        return t

    # Some exports may provide haploid/half-calls (single allele).
    if _ALLELE_RE.fullmatch(t):
        return t

    return None


def normalize_genotype_from_alleles(allele1: str, allele2: str) -> str | None:
    """
    Normalize a genotype from separate allele columns.
    """
    a1 = allele1.strip().upper()
    a2 = allele2.strip().upper()

    m1, m2 = _is_missing_allele(a1), _is_missing_allele(a2)
    if m1 and m2:
        return None

    if m1:
        return a2 if _ALLELE_RE.fullmatch(a2) else None
    if m2:
        return a1 if _ALLELE_RE.fullmatch(a1) else None

    combined = a1 + a2
    if re.fullmatch(r"[ACGT]{2}", combined):
        return combined
    if re.fullmatch(r"[ID]{2}", combined):
        return combined

    # Mixed allele sets are unexpected (e.g. A with I/D); treat as invalid.
    return None


def parse_myheritage(lines: list[str]) -> ParseResult:
    """
    Parse a MyHeritage raw DNA export into the common Variant schema.

    Supports multiple common layouts:
    - rsid,chromosome,position,genotype
    - rsid,chromosome,position,allele1,allele2
    - tab/CSV/whitespace-delimited variants
    """
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

        if len(parts) < 4:
            msg = f"Line {line_number}: invalid format"
            logger.warning(msg)
            errors.append(msg)
            continue

        rsid, chrom, pos = parts[0], parts[1], parts[2]
        rsid = rsid.lstrip("\ufeff")

        if not _is_valid_myheritage_rsid(rsid):
            msg = f"Line {line_number}: invalid rsid"
            logger.warning(msg)
            errors.append(msg)
            continue

        chrom_norm = normalize_myheritage_chromosome(chrom)
        if chrom_norm not in VALID_CHROMOSOMES:
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

        genotype: str | None
        # If the export has separate allele columns, combine them.
        if len(parts) >= 5:
            allele1, allele2 = parts[3], parts[4]

            allele1_u = allele1.strip().upper()
            allele2_u = allele2.strip().upper()
            if (_ALLELE_RE.fullmatch(allele1_u) or _is_missing_allele(allele1_u)) and (
                _ALLELE_RE.fullmatch(allele2_u) or _is_missing_allele(allele2_u)
            ):
                genotype = normalize_genotype_from_alleles(allele1, allele2)
            else:
                genotype = normalize_genotype_token(parts[3])
        else:
            genotype = normalize_genotype_token(parts[3])

        if genotype is None:
            errors.append(f"Line {line_number}: invalid genotype")

        variants.append(
            Variant(
                rsid=rsid,
                chromosome=chrom_norm,
                position=position,
                genotype=genotype,
            )
        )

    return ParseResult(variants=variants, errors=errors)
