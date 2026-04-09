import pytest

from backend.services.parsers import parse_gedmatch


# --- Header / BOM / Comment handling ---
@pytest.mark.parametrize(
    "lines",
    [
        [
            "# GEDmatch raw data",
            "rsid,chromosome,position,allele1,allele2",
            "rs123,1,1000,A,A",
        ],
        [
            "\ufeffrsid,chromosome,position,allele1,allele2",
            "rs123,1,1000,A,A",
        ],
        [
            "\ufeffrs123,1,1000,A,A",
        ],
    ],
)
def test_skips_headers_and_strips_bom(lines: list[str]) -> None:
    result = parse_gedmatch(lines)

    assert len(result.variants) == 1
    v = result.variants[0]

    assert v.rsid == "rs123"
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AA"


# --- Delimiter flexibility (GEDmatch often messy) ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123,1,1000,A,G",
        "rs123 1 1000 A G",
        "rs123\t1\t1000\tA\tG",
        "rs123\t1,1000,A,G",  # mixed delimiters
    ],
)
def test_accepts_mixed_delimiters(line: str) -> None:
    result = parse_gedmatch([line])

    assert len(result.variants) == 1
    v = result.variants[0]

    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AG"


# --- Structure validation (ONLY chrom + position can drop) ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123,Z,1000,A,A",
        "rs123,1,pos,A,A",
    ],
)
def test_invalid_structure_dropped(line: str) -> None:
    result = parse_gedmatch([line])

    assert len(result.variants) == 0
    assert len(result.errors) == 1


# --- Too few columns ---
def test_too_few_columns_dropped() -> None:
    result = parse_gedmatch(["rs123,1"])

    assert len(result.variants) == 0
    assert len(result.errors) == 1


# --- rsID soft-fail ---
def test_invalid_rsid_kept() -> None:
    result = parse_gedmatch(["rsABC,1,1000,A,A"])

    assert len(result.variants) == 1
    assert len(result.errors) == 1
    assert "invalid rsid" in result.errors[0]


def test_rsid_dot_allowed() -> None:
    result = parse_gedmatch([".,1,1000,A,A"])

    assert len(result.variants) == 1
    assert result.errors == []


# --- Genotype soft-fail ---
@pytest.mark.parametrize(
    "line",
    [
        "rs1,1,1000,Z,Z",
        "rs1,1,1000,A,Z",
    ],
)
def test_invalid_genotype_kept(line: str) -> None:
    result = parse_gedmatch([line])

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0]


# --- Missing genotype handling ---
@pytest.mark.parametrize(
    "line",
    [
        "rs1,1,1000,--,--",
        "rs1,1,1000,,",
    ],
)
def test_missing_genotype_becomes_none(line: str) -> None:
    result = parse_gedmatch([line])

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None


# --- Haploid handling ---
@pytest.mark.parametrize(
    "line,expected",
    [
        ("rs1,Y,1000,C,--", "C"),
        ("rs1,MT,1000,A,--", "A"),
    ],
)
def test_haploid_supported(line: str, expected: str) -> None:
    result = parse_gedmatch([line])

    assert len(result.variants) == 1
    assert result.variants[0].genotype == expected


# --- Chromosome normalization (GEDmatch often numeric) ---
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
    result = parse_gedmatch([f"rs123,{chrom_input},1000,A,A"])

    assert result.variants[0].chromosome == expected


# --- Extra columns (VERY common in GEDmatch exports) ---
def test_extra_columns_ignored() -> None:
    result = parse_gedmatch(["rs123,1,1000,A,G,0.123,build37,EXTRA"])

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


# --- Empty trailing columns ---
def test_trailing_empty_columns() -> None:
    result = parse_gedmatch(["rs123,1,1000,A,G,,,"])

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


# --- Whitespace robustness ---
def test_whitespace_handling() -> None:
    result = parse_gedmatch(["  rs123,1,1000,A,A  "])

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs123"


# --- Case normalization ---
def test_lowercase_alleles_normalized() -> None:
    result = parse_gedmatch(["rs123,1,1000,a,g"])

    assert result.variants[0].genotype == "AG"


# --- Duplicates preserved ---
def test_duplicates_preserved() -> None:
    lines = [
        "rs123,1,1000,A,A",
        "rs123,1,1000,A,A",
    ]

    result = parse_gedmatch(lines)

    assert len(result.variants) == 2
    assert result.variants[0] == result.variants[1]


# --- Error format contract ---
def test_error_formatting() -> None:
    result = parse_gedmatch(["rs123,Z,1000,A,A"])

    assert len(result.errors) == 1
    assert result.errors[0].startswith("Line ")
    assert ":" in result.errors[0]


# --- Comment-only file ---
def test_parse_comment_only_file() -> None:
    result = parse_gedmatch(["# comment", "# another comment"])

    assert result.variants == []
    assert result.errors == []
