import pytest

from backend.services.parsers.parser_ancestry_dna import (
    normalize_ancestry_chromosome,
    normalize_genotype_from_ancestry_alleles,
    parse_ancestry_dna,
)


@pytest.mark.parametrize(
    "lines,expected_count",
    [
        (["rs123,1,1000,A,A"], 1),
        (["rs123\t1\t1000\tA\tA"], 1),
        (["# comment", "rs123,1,1000,G,G"], 1),
        ([""], 0),
        (["rs123,1,1000,A"], 0),
        (["bad,data"], 0),
    ],
)
def test_basic_parsing(lines: list[str], expected_count: int) -> None:
    """Test core AncestryDNA row parsing across common delimiters."""
    result = parse_ancestry_dna(lines)
    assert len(result.variants) == expected_count


def test_skips_column_header() -> None:
    """Test that the header row (rsid, chromosome, ...) is skipped."""
    lines = [
        "# AncestryDNA raw data",
        "rsid,chromosome,position,allele1,allele2",
        "rs3094315,1,742429,A,A",
    ]
    result = parse_ancestry_dna(lines)
    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs3094315"
    assert result.variants[0].genotype == "AA"


def test_numeric_sex_chromosomes() -> None:
    """Test numeric sex/MT chromosome code mapping (23/24/25)."""
    lines = [
        "rs1,23,100,A,A",
        "rs2,24,200,C,C",
        "rs3,25,300,G,G",
    ]
    result = parse_ancestry_dna(lines)
    assert result.variants[0].chromosome == "X"
    assert result.variants[1].chromosome == "Y"
    assert result.variants[2].chromosome == "MT"


def test_heterozygous_order_preserved() -> None:
    """Test genotype ordering for heterozygous allele1/allele2."""
    lines = ["rs1,1,1,A,G"]
    result = parse_ancestry_dna(lines)
    assert result.variants[0].genotype == "AG"


def test_haploid_style_one_missing_allele() -> None:
    """Test haploid-style rows where one allele is missing."""
    lines = ["rs1,Y,1,C,--"]
    result = parse_ancestry_dna(lines)
    assert result.variants[0].genotype == "C"


def test_indel_alleles() -> None:
    """Test indel allele calls encoded as I/D."""
    lines = ["rs1,1,1,I,D"]
    result = parse_ancestry_dna(lines)
    assert result.variants[0].genotype == "ID"


def test_dot_rsid_allowed() -> None:
    """Test AncestryDNA placeholder rsid '.' is accepted."""
    lines = [".,1,1000,T,T"]
    result = parse_ancestry_dna(lines)
    assert len(result.variants) == 1
    assert result.variants[0].rsid == "."


def test_internal_ids() -> None:
    """Test internal IDs prefixed with 'i' are accepted as rsid."""
    lines = ["i4000001,1,1000,G,G"]
    result = parse_ancestry_dna(lines)
    assert len(result.variants) == 1


def test_sample_file_line_count() -> None:
    """Test that the sample fixture yields the expected number of variants."""
    path = "backend/tests/dna_samples/ancestry/ancestry.csv"
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    result = parse_ancestry_dna(lines)
    assert len(result.variants) == 14


def test_invalid_genotype_adds_error_and_keeps_variant() -> None:
    """Test invalid allele values add errors and yield genotype=None."""
    # Z is not a valid allele token for AncestryDNA, so genotype normalization fails.
    lines = ["rs1,1,1,Z,A"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0].lower()


def test_both_alleles_missing_yields_none_genotype() -> None:
    """Test rows with both alleles missing produce genotype=None."""
    lines = ["rs1,1,1,--,--"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0].lower()


def test_whitespace_delimited_row_is_parsed() -> None:
    """Test rows split on whitespace when tabs/commas are absent."""
    lines = ["rs1 1 1000 A G"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


def test_leading_whitespace_comment_is_skipped() -> None:
    """Test comments with leading whitespace are skipped."""
    lines = ["   # comment", "rs1,1,1,A,A"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs1"


def test_extra_columns_are_ignored() -> None:
    """Test extra trailing columns don't break parsing."""
    lines = ["rs1,1,1,A,A,EXTRA,COLUMNS"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AA"


@pytest.mark.parametrize(
    "line",
    [
        "bad,1,1,A,A",  # invalid rsid
        "rs1,26,1,A,A",  # invalid chromosome
        "rs1,1,abc,A,A",  # invalid position
    ],
)
def test_invalid_rsid_chromosome_or_position_yields_no_variants(line: str) -> None:
    """Test invalid rsid/chromosome/position results in zero variants."""
    result = parse_ancestry_dna([line])
    assert result.variants == []
    assert len(result.errors) == 1


def test_case_normalization_is_applied_to_alleles() -> None:
    """Test allele case is normalized before genotype assembly."""
    lines = ["rs1,1,1,a,g"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AG"


def test_negative_position_is_allowed() -> None:
    """Test negative positions are accepted (no min-position validation)."""
    lines = ["rs1,1,-100,A,A"]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].position == -100


def test_header_row_with_bom_is_skipped() -> None:
    """Test header detection works when the first cell includes UTF-8 BOM."""
    # Some exports can prefix the first header cell with a UTF-8 BOM.
    lines = [
        "\ufeffrsid,chromosome,position,allele1,allele2",
        "rs1,1,1,A,A",
    ]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs1"


@pytest.mark.parametrize(
    "chrom,expected",
    [
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
        ("X", "X"),
        ("M", "MT"),
    ],
)
def test_chromosome_normalization(chrom: str, expected: str) -> None:
    """Test mapping and normalization of AncestryDNA chromosome codes."""
    assert normalize_ancestry_chromosome(chrom) == expected


@pytest.mark.parametrize(
    "a1,a2,expected",
    [
        ("A", "A", "AA"),
        ("a", "g", "AG"),
        ("--", "--", None),
        ("G", "--", "G"),
        ("--", "C", "C"),
        ("I", "D", "ID"),
    ],
)
def test_genotype_from_alleles(a1: str, a2: str, expected: str | None) -> None:
    """Test genotype assembly from ALLELE1/ALLELE2 helper."""
    assert normalize_genotype_from_ancestry_alleles(a1, a2) == expected


def test_duplicate_rsid_handling() -> None:
    """Test duplicate rsid handling."""
    lines = [
        "rs1,1,100,A,A",
        "rs1,1,100,G,G",
    ]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 2


def test_garbage_line_is_skipped() -> None:
    """Test garbage line is skipped."""
    lines = ["this is not even remotely valid"]
    result = parse_ancestry_dna(lines)

    assert result.variants == []
    assert len(result.errors) == 1


def test_mixed_valid_and_invalid_rows() -> None:
    """Test mixed valid and invalid rows."""
    lines = [
        "rs1,1,1,A,A",
        "bad,data",
        "rs2,1,2,G,G",
    ]
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 2
    assert len(result.errors) == 1


@pytest.mark.parametrize(
    "chrom,expected",
    [
        (" x ", "X"),
        ("y", "Y"),
        ("mt", "MT"),
    ],
)
def test_chromosome_normalization_edge_cases(chrom: str, expected: str) -> None:
    """Test chromosome normalization edge cases."""
    assert normalize_ancestry_chromosome(chrom) == expected


@pytest.mark.parametrize(
    "a1,a2",
    [
        ("1", "A"),
        ("*", "G"),
        ("A", "???"),
    ],
)
def test_invalid_alleles(a1: str, a2: str) -> None:
    """Test invalid alleles."""
    result = parse_ancestry_dna([f"rs1,1,1,{a1},{a2}"])
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1


@pytest.mark.parametrize(
    "pos",
    ["0", "999999999999"],
)
def test_position_edge_cases(pos: str) -> None:
    """Test position edge cases."""
    result = parse_ancestry_dna([f"rs1,1,{pos},A,A"])
    assert len(result.variants) == 1


def test_only_whitespace_lines() -> None:
    """Test only whitespace lines."""
    lines = ["   ", "\t", "\n"]
    result = parse_ancestry_dna(lines)
    assert result.variants == []


def test_large_input_does_not_crash() -> None:
    """Test large input does not crash."""
    lines = ["rs1,1,1,A,A"] * 10000
    result = parse_ancestry_dna(lines)
    assert len(result.variants) == 10000


def test_partial_vs_full_failure_behavior() -> None:
    """Test partial vs full failure behavior."""
    # genotype failure → keep
    r1 = parse_ancestry_dna(["rs1,1,1,Z,Z"])
    assert len(r1.variants) == 1

    # structural failure → drop
    r2 = parse_ancestry_dna(["bad,1,1,A,A"])
    assert len(r2.variants) == 0
