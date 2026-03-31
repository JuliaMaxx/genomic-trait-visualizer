import pytest

from backend.services.parsers.parser_myheritage import (
    normalize_genotype_from_alleles,
    normalize_genotype_token,
    normalize_myheritage_chromosome,
    parse_myheritage,
)


@pytest.mark.parametrize(
    "lines,expected_count",
    [
        (["rs123,1,1000,AA"], 1),
        (["rs123\t1\t1000\tAA"], 1),
        (["rs123 1 1000 AA"], 1),
        (["# comment", "rs123,1,1000,GG"], 1),
        ([""], 0),
        (["rs123,1,1000"], 0),
        (["bad,data"], 0),
    ],
)
def test_basic_parsing(lines: list[str], expected_count: int) -> None:
    """Test core MyHeritage parsing across delimiters and malformed rows."""
    result = parse_myheritage(lines)
    assert len(result.variants) == expected_count


def test_skips_column_header() -> None:
    """Test that standard MyHeritage header rows are skipped."""
    lines = [
        "# MyHeritage DNA raw data",
        "rsid,chromosome,position,genotype",
        "rs3094315,1,742429,AA",
    ]
    result = parse_myheritage(lines)
    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs3094315"
    assert result.variants[0].genotype == "AA"


def test_skips_allele_header() -> None:
    """Test that alternative allele-column headers are skipped."""
    lines = [
        "rsid,chromosome,position,allele1,allele2",
        "rs1,1,1000,A,G",
    ]
    result = parse_myheritage(lines)
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


def test_header_row_with_bom_is_skipped() -> None:
    """Test header detection works when UTF-8 BOM is present."""
    lines = [
        "\ufeffrsid,chromosome,position,genotype",
        "rs1,1,1,AA",
    ]
    result = parse_myheritage(lines)
    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs1"


def test_numeric_sex_chromosomes() -> None:
    """Test numeric chromosome code mapping for X/Y/MT."""
    lines = [
        "rs1,23,100,AA",
        "rs2,24,200,CC",
        "rs3,25,300,GG",
    ]
    result = parse_myheritage(lines)
    assert result.variants[0].chromosome == "X"
    assert result.variants[1].chromosome == "Y"
    assert result.variants[2].chromosome == "MT"


def test_dot_rsid_allowed() -> None:
    """Test placeholder '.' rsid is accepted."""
    result = parse_myheritage([".,1,1000,TT"])
    assert len(result.variants) == 1
    assert result.variants[0].rsid == "."


def test_internal_ids_allowed() -> None:
    """Test internal IDs prefixed with 'i' are accepted."""
    result = parse_myheritage(["i4000001,1,1000,GG"])
    assert len(result.variants) == 1


@pytest.mark.parametrize(
    "line",
    [
        "bad,1,1,AA",  # invalid rsid
        "rs1,26,1,AA",  # invalid chromosome
        "rs1,1,abc,AA",  # invalid position
    ],
)
def test_invalid_rsid_chromosome_or_position_yields_no_variants(line: str) -> None:
    """Test structural field validation rejects invalid rows before genotype parsing."""
    result = parse_myheritage([line])
    assert result.variants == []
    assert len(result.errors) == 1


def test_negative_position_is_allowed() -> None:
    """Test negative positions are preserved (no min-position validation)."""
    result = parse_myheritage(["rs1,1,-100,AA"])
    assert len(result.variants) == 1
    assert result.variants[0].position == -100


def test_invalid_genotype_token_adds_error_and_keeps_variant() -> None:
    """Test invalid genotype tokens are recorded with genotype=None."""
    result = parse_myheritage(["rs1,1,1000,ZZ"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0].lower()


def test_missing_genotype_token_adds_error_and_keeps_variant() -> None:
    """Test missing genotype tokens produce errors and None genotype."""
    result = parse_myheritage(["rs1,1,1000,--"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1


def test_case_normalization_is_applied_to_genotype_token() -> None:
    """Test lowercase genotype tokens are normalized to uppercase."""
    result = parse_myheritage(["rs1,1,1,ag"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


def test_indel_genotype_token_is_supported() -> None:
    """Test indel genotype tokens (e.g. ID) are accepted."""
    result = parse_myheritage(["rs1,1,1,ID"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "ID"


def test_allele_columns_are_combined_when_present() -> None:
    """Test five-column allele format is combined into genotype."""
    result = parse_myheritage(["rs1,1,1000,A,G"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


def test_haploid_style_allele_rows_are_supported() -> None:
    """Test one-sided allele calls in five-column format produce haploid genotype."""
    result = parse_myheritage(["rs1,Y,1000,C,--"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "C"


def test_both_missing_alleles_yield_none_genotype() -> None:
    """Test both-missing allele rows result in genotype=None with an error."""
    result = parse_myheritage(["rs1,1,1000,--,--"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0].lower()


def test_five_column_fallback_uses_genotype_token_when_alleles_invalid() -> None:
    """Test falls back to column 4 token if allele columns are not allele-like."""
    # parts[3] is valid combined genotype, parts[4] is junk; parser should keep AA.
    result = parse_myheritage(["rs1,1,1000,AA,junk"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AA"


def test_extra_columns_are_ignored() -> None:
    """Test extra trailing columns do not break parsing."""
    result = parse_myheritage(["rs1,1,1000,AA,extra,columns"])
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AA"


def test_sample_file_line_count() -> None:
    """Test the MyHeritage sample fixture yields expected variants."""
    path = "backend/tests/dna_samples/myheritage/myheritage.csv"
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    result = parse_myheritage(lines)
    assert len(result.variants) == 14


@pytest.mark.parametrize(
    "chrom,expected",
    [
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
        ("M", "MT"),
        ("mt", "MT"),
    ],
)
def test_chromosome_normalization(chrom: str, expected: str) -> None:
    """Test normalization and mapping of MyHeritage chromosome values."""
    assert normalize_myheritage_chromosome(chrom) == expected


@pytest.mark.parametrize(
    "token,expected",
    [
        ("AA", "AA"),
        ("ag", "AG"),
        ("ID", "ID"),
        ("i", "I"),
        ("--", None),
        ("", None),
        ("NA", None),
        ("ZZ", None),
    ],
)
def test_genotype_token_normalization(token: str, expected: str | None) -> None:
    """Test genotype-token helper for MyHeritage 4-column exports."""
    assert normalize_genotype_token(token) == expected


@pytest.mark.parametrize(
    "a1,a2,expected",
    [
        ("A", "A", "AA"),
        ("a", "g", "AG"),
        ("I", "D", "ID"),
        ("G", "--", "G"),
        ("--", "C", "C"),
        ("--", "--", None),
        ("A", "I", None),
        ("ZZ", "A", None),
    ],
)
def test_genotype_from_alleles(a1: str, a2: str, expected: str | None) -> None:
    """Test genotype assembly helper for five-column allele exports."""
    assert normalize_genotype_from_alleles(a1, a2) == expected


def test_mixed_delimiters_in_file() -> None:
    """Test parser handles mixed delimiters in a file."""
    lines = [
        "rs1,1,1000,AA",
        "rs2\t1\t1001\tGG",
        "rs3 1 1002 CC",
    ]
    result = parse_myheritage(lines)
    assert len(result.variants) == 3


def test_whitespace_is_stripped() -> None:
    """Test whitespace is stripped from the input."""
    result = parse_myheritage(["  rs1 , 1 , 1000 , AA  "])
    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs1"


def test_duplicate_rsids_are_handled() -> None:
    """Test duplicate rsids are handled."""
    lines = [
        "rs1,1,1000,AA",
        "rs1,1,1000,GG",
    ]
    result = parse_myheritage(lines)
    assert len(result.variants) == 2


@pytest.mark.parametrize("chrom", ["0", "XY", "chr1", ""])
def test_invalid_chromosome_formats(chrom: str) -> None:
    """Test invalid chromosome formats are rejected."""
    result = parse_myheritage([f"rs1,{chrom},1000,AA"])
    assert result.variants == []
    assert len(result.errors) == 1


def test_zero_position() -> None:
    """Test zero position is allowed."""
    result = parse_myheritage(["rs1,1,0,AA"])
    assert len(result.variants) == 1


@pytest.mark.parametrize(
    "geno,expected",
    [
        ("A", "A"),  # valid haploid
        ("AAA", None),  # invalid
        ("AAGG", None),  # invalid
    ],
)
def test_genotype_lengths(geno: str, expected: str | None) -> None:
    """Test genotype lengths are validated."""
    result = parse_myheritage([f"rs1,1,1000,{geno}"])
    assert result.variants[0].genotype == expected


def test_partially_invalid_genotype() -> None:
    """Test non-ACGT characters mixed with valid ones are rejected."""
    result = parse_myheritage(["rs1,1,1000,AZ"])
    assert result.variants[0].genotype is None


def test_blank_lines_are_ignored() -> None:
    """Test completely empty / whitespace-only lines are ignored."""
    result = parse_myheritage(["   ", "\t", "\n"])
    assert len(result.variants) == 0


def test_variant_order_is_preserved() -> None:
    """Test variant order is preserved."""
    lines = [
        "rs1,1,1000,AA",
        "rs2,1,1001,GG",
    ]
    result = parse_myheritage(lines)
    assert [v.rsid for v in result.variants] == ["rs1", "rs2"]


def test_multiple_errors_are_collected() -> None:
    """Test multiple errors are collected."""
    lines = [
        "bad,1,1,AA",
        "rs1,1,abc,AA",
    ]
    result = parse_myheritage(lines)
    assert len(result.errors) == 2


def test_partial_failure_policy() -> None:
    """Test invalid genotype -> variant kept, error recorded."""
    result = parse_myheritage(["rs1,1,1000,ZZ"])
    assert len(result.variants) == 1
    assert len(result.errors) == 1
    assert result.variants[0].genotype is None
    assert result.errors[0] == "Line 1: invalid genotype"


def test_valid_chromosome_formats() -> None:
    """Test valid chromosome formats are accepted."""
    result = parse_myheritage(["rs1,1,1000,AA"])
    assert len(result.variants) == 1
    assert len(result.variants) == 1
