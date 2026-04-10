import re

from fastapi.logger import logger

from backend.models import ParseResult, Variant
from backend.services.parsers.common import (
    VALID_CHROMOSOMES,
    is_standard_rsid,
    normalize_chromosome,
    normalize_genotype,
)


def _parse_vcf_genotype(genotype_str: str, ref: str, alt_list: list[str]) -> str | None:
    """
    Parse VCF genotype string into normalized alleles.

    VCF Genotype Format:
    - 0/0: homozygous reference (REF/REF)
    - 0/1: heterozygous (REF/ALT[0])
    - 1/1: homozygous alternate (ALT[0]/ALT[0])
    - 0|1: phased (same as above, we treat / and | the same)
    - ./.: missing (both alleles missing)
    - .|.: phased missing
    - ./..: etc (any combination with . is missing)

    Args:
        genotype_str: The genotype string (e.g., "0/1", "1|1", "./.")
        ref: Reference allele
        alt_list: List of alternate alleles

    Returns:
        Normalized genotype string (e.g., "AC") or None if missing/invalid
    """
    # Normalize the genotype string
    # Replace phasing character | with / for uniform processing
    normalized = genotype_str.strip().replace("|", "/")

    # Handle missing genotypes
    if normalized in (".", ".", "./."):
        return None

    # Split on / to get individual alleles
    try:
        parts = normalized.split("/")
    except Exception:
        return None

    alleles: list[str] = []

    for part in parts:
        part = part.strip()

        # . means missing allele
        if part == ".":
            continue

        try:
            idx = int(part)
        except ValueError:
            # Invalid allele index
            return None

        # 0 = REF
        if idx == 0:
            alleles.append(ref)
        # 1, 2, 3... = ALT[0], ALT[1], ALT[2]...
        elif 1 <= idx < len(alt_list) + 1:
            alleles.append(alt_list[idx - 1])
        else:
            # Index out of range
            return None

    # If no valid alleles remain, return None
    if not alleles:
        return None

    # Use the common normalize_genotype to standardize (uppercase, etc)
    return normalize_genotype(genotype="".join(alleles))


def parse_vcf(lines: list[str]) -> ParseResult:
    """
    Parse a VCF (Variant Call Format) file into the common Variant schema.

    Supports:
    - VCFv4.0, VCFv4.1, VCFv4.2+
    - Standard VCF structure with CHROM/POS/ID/REF/ALT/QUAL/FILTER/INFO/FORMAT
    - Single or multiple samples
    - Phased and unphased genotypes
    - All VCF encoding (0=REF, 1+=ALT)

    Returns:
        ParseResult with variants and errors
    """
    variants: list[Variant] = []
    errors: list[str] = []

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip any lines starting with # (metadata, headers, comments)
        if line.startswith("#"):
            continue

        # At this point, we expect data lines
        # Split on tabs (VCF is tab-delimited by specification)
        parts = line.split("\t")  # trust VCF

        # Handle mixed delimiter inside columns (e.g. "1000,rs123") ---
        if len(parts) < 10:
            parts = [p for p in re.split(r"[,\t\s]+", line) if p]

        # VCF requires at least: CHROM POS ID REF ALT QUAL FILTER INFO FORMAT [sample]
        if len(parts) < 10:
            msg = f"Line {line_number}: invalid format"
            logger.warning(msg)
            errors.append(msg)
            continue

        # Extract fields
        chrom_raw = parts[0]
        pos_raw = parts[1]
        rsid = parts[2]
        ref = parts[3]
        alt_raw = parts[4]
        # QUAL, FILTER, INFO at parts[5:8]
        # FORMAT at parts[8]

        # ===== STRUCTURE VALIDATION (HARD FAIL) =====

        # Normalize and validate chromosome
        chrom = normalize_chromosome(chrom_raw)
        if chrom not in VALID_CHROMOSOMES:
            msg = f"Line {line_number}: invalid chromosome"
            logger.warning(msg)
            errors.append(msg)
            continue

        # Parse and validate position
        try:
            position = int(pos_raw)
        except ValueError:
            msg = f"Line {line_number}: invalid position"
            logger.warning(msg)
            errors.append(msg)
            continue

        # ===== DATA EXTRACTION (SOFT FAIL) =====

        # rsID validation (soft fail)
        rsid = rsid.lstrip("\ufeff")
        if not is_standard_rsid(rsid):
            msg = f"Line {line_number}: invalid rsid"
            logger.warning(msg)
            errors.append(msg)

        # Parse ALT field (comma-separated list of alternates)
        # Can be "." for no alternate
        alt_alleles: list[str] = []
        if alt_raw and alt_raw != ".":
            alt_alleles = [a.strip() for a in alt_raw.split(",") if a.strip()]

        # Parse genotype (soft fail)
        # Extract GT from GT:PL or similar format
        # (just take the first colon-separated part)
        format_field = parts[8]
        sample_field = parts[9]

        genotype = None

        try:
            format_keys = format_field.split(":")
            sample_values = sample_field.split(":")

            # Enforce matching structure
            if len(format_keys) != len(sample_values):
                raise ValueError("FORMAT/sample mismatch")

            if "GT" not in format_keys:
                raise ValueError("GT not present")

            gt_index = format_keys.index("GT")
            genotype_part = sample_values[gt_index]

            genotype = _parse_vcf_genotype(genotype_part, ref, alt_alleles)

            if genotype is None:
                raise ValueError("invalid genotype")

        except Exception:
            msg = f"Line {line_number}: invalid genotype"
            logger.warning(msg)
            errors.append(msg)

        # ===== ADD VARIANT =====
        variants.append(
            Variant(
                rsid=rsid,
                chromosome=chrom,
                position=position,
                genotype=genotype,
            )
        )

    return ParseResult(variants=variants, errors=errors)
