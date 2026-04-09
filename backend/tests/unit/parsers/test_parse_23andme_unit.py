import pytest

from backend.services.parsers import parse_23andme


# --- Header / BOM / Comment handling ---
def test_skips_headers_and_comments() -> None:
    lines = [
        "# comment line",
        "\ufeffrsid\tchromosome\tposition\tgenotype",
        "rs123\t1\t1000\tAA",
    ]
    result = parse_23andme(lines)

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs123"
    assert result.errors == []


# --- Delimiter variations ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123\t1\t1000\tAA",  # standard tab
        "rs123 1 1000 AA",  # spaces
        "rs123\t 1   1000\tAA",  # mixed tabs + spaces
    ],
)
def test_accepts_delimiter_variations(line: str) -> None:
    result = parse_23andme([line])

    assert len(result.variants) == 1
    v = result.variants[0]
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AA"


# --- Chromosome normalization ---
@pytest.mark.parametrize(
    "chrom_input,expected",
    [
        ("1", "1"),
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
    ],
)
def test_chromosome_normalization(chrom_input: str, expected: str) -> None:
    result = parse_23andme([f"rs123\t{chrom_input}\t1000\tAA"])
    assert result.variants[0].chromosome == expected


# --- rsid handling ---
@pytest.mark.parametrize(
    "rsid_input,expected_count",
    [
        ("rs123", 1),
        ("i4000001", 1),  # internal id
        (".", 1),  # VCF-compatible placeholder
        ("rsABC", 1),  # invalid but preserved
    ],
)
def test_rsid_validation(rsid_input: str, expected_count: int) -> None:
    result = parse_23andme([f"{rsid_input}\t1\t1000\tAA"])
    assert len(result.variants) == expected_count


# --- Position validation ---
@pytest.mark.parametrize(
    "position_input,keep_row",
    [
        ("1000", True),
        ("-100", True),  # negative allowed
        ("abc", False),  # invalid → drop
    ],
)
def test_position_validation(position_input: str, keep_row: bool) -> None:
    result = parse_23andme([f"rs123\t1\t{position_input}\tAA"])
    assert (len(result.variants) == 1) == keep_row
    if not keep_row:
        assert len(result.errors) == 1


# --- Genotype normalization / tolerance ---
@pytest.mark.parametrize(
    "genotype_input,expected_genotype,expect_error",
    [
        ("AA", "AA", False),
        ("ag", "AG", False),  # case normalization
        ("--", None, True),  # missing → None + error
        ("ZZ", None, True),  # invalid → None + error
        ("A", "A", False),  # haploid
        ("A-", "A", False),  # partial haploid
        (".", None, True),  # missing
    ],
)
def test_genotype_handling(
    genotype_input: str, expected_genotype: str | None, expect_error: bool
) -> None:
    result = parse_23andme([f"rs123\t1\t1000\t{genotype_input}"])
    v = result.variants[0]
    assert v.genotype == expected_genotype
    if expect_error:
        assert len(result.errors) == 1
    else:
        assert not result.errors


# --- Invalid rows produce errors but parser continues ---
def test_mixed_valid_and_invalid_rows() -> None:
    lines = [
        "rs123\t1\t1000\tAA",
        "bad_line",
        "rs456\t23\t2000\tCC",
        "# comment",
        "rs789\t25\t3000\tGG",
        "rs000\tbad\t1000\tAA",
    ]
    result = parse_23andme(lines)

    # Only valid structure rows are preserved
    assert len(result.variants) == 3
    # All invalid lines produce errors, comment is not an error
    assert len(result.errors) == 2


# --- Duplicates preserved ---
def test_duplicates_preserved() -> None:
    lines = [
        "rs123\t1\t1000\tAA",
        "rs123\t1\t1000\tAA",
    ]
    result = parse_23andme(lines)
    assert len(result.variants) == 2
    assert result.variants[0] == result.variants[1]


# --- Extra columns ignored ---
def test_extra_columns_are_ignored() -> None:
    lines = ["rs123\t1\t1000\tAA\tEXTRA\tANOTHER"]
    result = parse_23andme(lines)
    v = result.variants[0]
    assert v.rsid == "rs123"
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AA"
