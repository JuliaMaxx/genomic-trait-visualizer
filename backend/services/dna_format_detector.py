import re

# -----------------------------
# Provider signatures
# -----------------------------
SignatureDict = dict[str, dict[str, object]]

SIGNATURES: SignatureDict = {
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
    "vcf": {
        "comments": ["##fileformat=vcf"],
        "headers": [{"#chrom"}],
        "min_columns": 8,
    },
}


# -----------------------------
# Detect format function
# -----------------------------
def detect_format(lines: list[str]) -> str:
    """
    Detect DNA file format.
    Supports: 23andMe, AncestryDNA, MyHeritage, FTDNA, LivingDNA, GEDmatch, VCF
    """
    if not lines:
        raise ValueError("Empty file")

    # Normalize
    stripped: list[str] = [line.strip() for line in lines if line.strip()]
    comments: list[str] = [line.lower() for line in stripped if line.startswith("#")]
    data_lines: list[str] = [line for line in stripped if not line.startswith("#")]

    # 1. Check VCF separately first (very distinct)
    for line in stripped[:20]:
        if line.lower().startswith("##fileformat=vcf") or line.lower().startswith(
            "#chrom"
        ):
            return "vcf"

    comment_blob: str = " ".join(comments)

    # 2. Check comments
    for provider, sig in SIGNATURES.items():
        comment_keys: list[str] = sig.get("comments", [])  # type: ignore
        if any(k.lower() in comment_blob for k in comment_keys):
            return provider

    # 3. Check headers
    if data_lines:
        first_line: str = data_lines[0]
        delimiter: str | None = (
            "\t" if "\t" in first_line else ("," if "," in first_line else None)
        )

        def split_line(line: str) -> list[str]:
            return line.split(delimiter) if delimiter else line.split()

        header_parts: set[str] = set(p.lower() for p in split_line(first_line))

        for provider, sig in SIGNATURES.items():
            headers_list: list[set[str]] = sig.get("headers", [])  # type: ignore
            for required_header in headers_list:
                if required_header.issubset(header_parts):
                    return provider

    # 4. Row pattern fallback (rsid detection)
    sample_rows: list[str] = data_lines[:5]
    parsed_rows: list[list[str]] = [split_line(row) for row in sample_rows if row]

    def looks_like_rsid(value: str) -> bool:
        return bool(re.match(r"rs\d+", value.lower()))

    rsid_like: int = sum(1 for row in parsed_rows if row and looks_like_rsid(row[0]))
    if rsid_like >= 3:
        # Column-count based differentiation
        lengths: list[int] = [len(row) for row in parsed_rows]
        for provider, sig in SIGNATURES.items():
            min_cols: int = sig.get("min_columns", 0)  # type: ignore
            if all(length >= min_cols for length in lengths):
                return provider

    # 5. Fallback
    return "unknown"
