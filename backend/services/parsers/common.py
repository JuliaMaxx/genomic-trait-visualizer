import re

VALID_CHROMOSOMES = {str(i) for i in range(1, 23)} | {"X", "Y", "MT", "M"}

MISSING_ALLELE = {"", "--", "NA", "N", ".", "0"}


def normalize_chromosome(chrom: str) -> str:
    chrom = chrom.strip().upper().replace("CHR", "")
    if chrom == "M":
        return "MT"
    # Map provider codes 23,24,25 → X,Y,MT
    if chrom == "23":
        return "X"
    if chrom == "24":
        return "Y"
    if chrom == "25":
        return "MT"
    return chrom


def _is_missing_allele(allele: str) -> bool:
    return allele.strip().upper() in MISSING_ALLELE


def is_standard_rsid(rsid: str) -> bool:
    r = rsid.strip().lstrip("\ufeff")
    if r == ".":
        return True
    return bool(re.match(r"^(rs|i)\d+$", r, re.IGNORECASE))


def split_line(line: str) -> list[str]:
    # Split on ANY delimiter: tabs, commas, or whitespace
    return [p for p in re.split(r"[,\t\s]+", line.strip()) if p]


_VALID_ALLELE_RE = re.compile(r"^[ACGTID]$")
_VALID_GENOTYPE_RE = re.compile(r"^[ACGTID]{1,2}$")


def normalize_genotype(
    genotype: str | None = None,
    allele1: str | None = None,
    allele2: str | None = None,
) -> str | None:
    """
    Universal genotype normalizer.

    Supports:
    - Single string genotype (e.g. "AG", "A", "DD")
    - Split alleles (Ancestry-style: allele1 + allele2)

    Future-proof:
    - Can easily extend to N alleles or phased data later

    Rules:
    - Preserve valid data whenever possible
    - Drop missing alleles
    - Return None only if nothing valid remains
    """

    alleles: list[str] = []

    # ---- Case 1: Split alleles (Ancestry, VCF-style fields, etc.)
    if allele1 is not None or allele2 is not None:
        for raw in (allele1, allele2):
            if raw is None:
                continue

            a = raw.strip().upper()

            if _is_missing_allele(a):
                continue

            if not _VALID_ALLELE_RE.fullmatch(a):
                return None
            alleles.append(a)

        # if both missing → None
        if not alleles:
            return None

        return "".join(alleles)

    # ---- Case 2: Single genotype string
    if genotype is None:
        return None

    g = genotype.strip().upper()

    if _is_missing_allele(g):
        return None

    # Fast path: already clean
    if _VALID_GENOTYPE_RE.fullmatch(g):
        return g

    # Fallback: extract valid alleles
    for char in g:
        if not _is_missing_allele(char) and _VALID_ALLELE_RE.fullmatch(char):
            alleles.append(char)

    if not alleles:
        return None

    return "".join(alleles)
