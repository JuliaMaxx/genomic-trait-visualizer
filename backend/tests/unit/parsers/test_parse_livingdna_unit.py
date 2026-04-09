import pytest

from backend.services.parsers import parse_livingdna


# --- Header / BOM / Comment handling ---
@pytest.mark.parametrize(
    "lines",
    [
        [
            "# LivingDNA raw data",
            "rsid\tchromosome\tposition\tallele1\tallele2",
            "rs123\t1\t1000\tA\tA",
        ],
        [
            "\ufeffrsid\tchromosome\tposition\tallele1\tallele2",
            "rs123\t1\t1000\tA\tA",
        ],
        [
            "\ufeffrs123\t1\t1000\tA\tA",
        ],
    ],
)
def test_skips_headers_and_strips_bom(lines: list[str]) -> None:
    result = parse_livingdna(lines)

    assert len(result.variants) == 1
    v = result.variants[0]

    assert v.rsid == "rs123"
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AA"


# --- Delimiter + layout flexibility (structure still valid) ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123\t1\t1000\tA\tG",
        "rs123 1 1000 A G",
        "rs123,1,1000,A,G",
        "rs123\t1,1000\tA\tG",  # mixed delimiters
    ],
)
def test_accepts_mixed_delimiters(line: str) -> None:
    result = parse_livingdna([line])

    assert len(result.variants) == 1
    v = result.variants[0]

    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AG"


# --- Structure validation (ONLY chrom + position can drop) ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123\tZ\t1000\tA\tA",  # invalid chromosome
        "rs123\t1\tpos\tA\tA",  # invalid position
    ],
)
def test_invalid_structure_dropped(line: str) -> None:
    result = parse_livingdna([line])

    assert len(result.variants) == 0
    assert len(result.errors) == 1


# --- Too few columns → invalid structure ---
def test_too_few_columns_dropped() -> None:
    result = parse_livingdna(["rs123\t1"])

    assert len(result.variants) == 0
    assert len(result.errors) == 1


# --- rsID soft-fail (MUST NOT drop) ---
def test_invalid_rsid_kept() -> None:
    result = parse_livingdna(["rsABC\t1\t1000\tA\tA"])

    assert len(result.variants) == 1
    assert len(result.errors) == 1
    assert "invalid rsid" in result.errors[0]


def test_rsid_dot_allowed() -> None:
    result = parse_livingdna([".\t1\t1000\tA\tA"])

    assert len(result.variants) == 1
    assert result.errors == []


# --- Genotype soft-fail (MUST NOT drop) ---
@pytest.mark.parametrize(
    "line",
    [
        "rs1\t1\t1000\tZ\tZ",
        "rs1\t1\t1000\tA\tZ",
    ],
)
def test_invalid_genotype_kept(line: str) -> None:
    result = parse_livingdna([line])

    assert len(result.variants) == 1
    v = result.variants[0]

    assert v.genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0]


# --- Missing genotype → None (no drop) ---
@pytest.mark.parametrize(
    "line",
    [
        "rs1\t1\t1000\t--\t--",
        "rs1\t1\t1000\t\t",
    ],
)
def test_missing_genotype_becomes_none(line: str) -> None:
    result = parse_livingdna([line])

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None


# --- Haploid handling (still valid genotype) ---
@pytest.mark.parametrize(
    "line,expected",
    [
        ("rs1\tY\t1000\tC\t--", "C"),
        ("rs1\tMT\t1000\tA\t--", "A"),
    ],
)
def test_haploid_supported(line: str, expected: str) -> None:
    result = parse_livingdna([line])

    assert len(result.variants) == 1
    assert result.variants[0].genotype == expected


# --- Chromosome normalization ---
@pytest.mark.parametrize(
    "chrom_input,expected",
    [
        ("1", "1"),
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
        ("X", "X"),
        ("Y", "Y"),
    ],
)
def test_chromosome_normalization(chrom_input: str, expected: str) -> None:
    result = parse_livingdna([f"rs123\t{chrom_input}\t1000\tA\tA"])

    assert result.variants[0].chromosome == expected


# --- Internal IDs preserved ---
def test_internal_ids_preserved() -> None:
    result = parse_livingdna(["i123456\t1\t1000\tA\tA"])

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "i123456"


# --- Duplicates preserved ---
def test_duplicates_preserved() -> None:
    lines = [
        "rs123\t1\t1000\tA\tA",
        "rs123\t1\t1000\tA\tA",
    ]

    result = parse_livingdna(lines)

    assert len(result.variants) == 2
    assert result.variants[0] == result.variants[1]


# --- Extra columns ignored (structure still valid) ---
def test_extra_columns_ignored() -> None:
    result = parse_livingdna(["rs123\t1\t1000\tA\tG\tEXTRA\tVALUE"])

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


# --- Whitespace robustness ---
def test_whitespace_handling() -> None:
    result = parse_livingdna(["  rs123\t1\t1000\tA\tA  "])

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs123"


# --- Case normalization ---
def test_lowercase_alleles_normalized() -> None:
    result = parse_livingdna(["rs123\t1\t1000\ta\tg"])

    assert result.variants[0].genotype == "AG"


# --- Error format contract ---
def test_error_formatting() -> None:
    result = parse_livingdna(["rs123\tZ\t1000\tA\tA"])

    assert len(result.errors) == 1
    assert result.errors[0].startswith("Line ")
    assert ":" in result.errors[0]


# --- Comment-only file → no variants, no errors ---
def test_parse__comment_only_file() -> None:
    lines = ["# comment", "# another comment"]
    result = parse_livingdna(lines)

    assert result.variants == []
    assert result.errors == []
