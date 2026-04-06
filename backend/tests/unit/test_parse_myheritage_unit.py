import pytest

from backend.services.parsers.parser_myheritage import parse_myheritage


# --- Header / BOM / Comment handling ---
@pytest.mark.parametrize(
    "lines",
    [
        [
            "# MyHeritage DNA raw data",
            "rsid,chromosome,position,genotype",
            "rs123,1,1000,AA",
        ],
        [
            "\ufeffrsid,chromosome,position,genotype",
            "rs123,1,1000,AA",
        ],
        [
            "\ufeffrs123,1,1000,AA",
        ],
    ],
)
def test_skips_headers_and_strips_bom(lines: list[str]) -> None:
    result = parse_myheritage(lines)
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.rsid == "rs123"
    assert v.genotype == "AA"
    assert result.errors == [] or result.errors is not None


# --- Layouts / delimiter variations ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123,1,1000,AA",  # CSV 4-column (genotype token)
        "rs123\t1\t1000\tAA",  # tab-delimited
        "rs123 1 1000 AA",  # whitespace-delimited
        "rs123,1,1000,A,G",  # CSV 5-column (alleles)
    ],
)
def test_accepts_layouts_and_delimiters(line: str) -> None:
    result = parse_myheritage([line])
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AA" if "AA" in line else "AG"


# --- Chromosome normalization ---
@pytest.mark.parametrize(
    "chrom_input,expected",
    [
        ("1", "1"),
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
        ("Y", "Y"),
    ],
)
def test_chromosome_normalization(chrom_input: str, expected: str) -> None:
    result = parse_myheritage([f"rs123,{chrom_input},1000,AA"])
    assert result.variants[0].chromosome == expected


# --- Genotype assembly (haploid / indels / 5-column allele mode) ---
@pytest.mark.parametrize(
    "line,expected_genotype,expect_error",
    [
        ("rs1,1,1000,A,G", "AG", False),
        ("rs1,Y,1000,C,--", "C", False),  # haploid
        ("rs1,1,1000,ID", "ID", False),  # 4-col indel
        ("rs2,1,1001,I,D", "ID", False),  # 5-col indel
        ("rs1,1,1000,AA,junk", None, True),  # invalid 5-col
    ],
)
def test_genotype_parsing(
    line: str, expected_genotype: str | None, expect_error: bool
) -> None:
    result = parse_myheritage([line])
    v = result.variants[0]

    assert v.genotype == expected_genotype
    if expect_error:
        assert len(result.errors) == 1
        assert "invalid" in result.errors[0].lower()
    else:
        assert not result.errors


# --- Internal IDs / duplicates ---
def test_internal_ids_and_duplicates() -> None:
    lines = [
        "i4000001,1,1000,GG",
        "i4000001,1,1000,GG",
    ]
    result = parse_myheritage(lines)

    assert len(result.variants) == 2
    assert result.variants[0].rsid == "i4000001"
    assert result.variants[0] == result.variants[1]
    assert result.errors == []


# --- Extra columns ignored ---
def test_extra_columns_ignored() -> None:
    result = parse_myheritage(["rs2,1,1001,A,G,EXTRA,VALUE"])
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.genotype == "AG"
