from typing import Callable, TypedDict

import pytest

from backend.models.schemas import ParseResult
from backend.services.parsers.parser_23andme import parse_23andme
from backend.services.parsers.parser_ancestry import parse_ancestry
from backend.services.parsers.parser_myheritage import parse_myheritage

ParserFn = Callable[[list[str]], ParseResult]


class ParserCase(TypedDict):
    name: str
    parser: ParserFn
    valid_line: str
    invalid_format_line: str
    invalid_genotype_line: str
    missing_genotype_line: str
    haploid_line: str
    rsid_dot_line: str
    invalid_rsid_line: str
    invalid_chrom_line: str
    invalid_position_line: str
    mixed_delimiter_line: str
    header_line: str


PARSERS: list[ParserCase] = [
    {
        "name": "23andme",
        "parser": parse_23andme,
        "valid_line": "rs123 1 1000 AA",
        "invalid_format_line": "rs123 1",
        "invalid_genotype_line": "rs123 1 1000 ZZ",
        "missing_genotype_line": "rs123 1 1000 --",
        "haploid_line": "rs123 1 1000 A",
        "rsid_dot_line": ". 1 1000 AA",
        "invalid_rsid_line": "rsABC 1 1000 AA",
        "invalid_chrom_line": "rs123 Z 1000 AA",
        "invalid_position_line": "rs123 1 pos AA",
        "mixed_delimiter_line": "rs123\t1,1000 AA",
        "header_line": "rsid chromosome position genotype",
    },
    {
        "name": "ancestry",
        "parser": parse_ancestry,
        "valid_line": "rs123,1,1000,A,A",
        "invalid_format_line": "rs123,1",
        "invalid_genotype_line": "rs123,1,1000,Z,Z",
        "missing_genotype_line": "rs123,1,1000,--,--",
        "haploid_line": "rs123,1,1000,A,--",
        "rsid_dot_line": ".,1,1000,A,A",
        "invalid_rsid_line": "rsABC,1,1000,A,A",
        "invalid_chrom_line": "rs123,Z,1000,A,A",
        "invalid_position_line": "rs123,1,pos,A,A",
        "mixed_delimiter_line": "rs123\t1,1000,A,A",
        "header_line": "rsid,chromosome,position,allele1,allele2",
    },
    {
        "name": "myheritage",
        "parser": parse_myheritage,
        "valid_line": "rs123 1 1000 AA",
        "invalid_format_line": "rs123 1",
        "invalid_genotype_line": "rs123 1 1000 ZZ",
        "missing_genotype_line": "rs123 1 1000 --",
        "haploid_line": "rs123 1 1000 A",
        "rsid_dot_line": ". 1 1000 AA",
        "invalid_rsid_line": "rsABC 1 1000 AA",
        "invalid_chrom_line": "rs123 Z 1000 AA",
        "invalid_position_line": "rs123 1 pos AA",
        "mixed_delimiter_line": "rs123\t1,1000 AA",
        "header_line": "rsid chromosome position genotype",
    },
]


# ----------------------------
# Helpers
# ----------------------------


def assert_error_format(errors: list[str]) -> None:
    for e in errors:
        assert e.startswith("Line ")
        assert ":" in e


# ----------------------------
# Output Contract
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_returns_parse_result_shape(case: ParserCase) -> None:
    result = case["parser"]([case["valid_line"]])

    assert isinstance(result.variants, list)
    assert isinstance(result.errors, list)


# ----------------------------
# Structural Rules (HARD FAIL)
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_invalid_structure_dropped(case: ParserCase) -> None:
    result = case["parser"](
        [
            case["invalid_format_line"],
            case["invalid_chrom_line"],
            case["invalid_position_line"],
        ]
    )

    assert len(result.variants) == 0
    assert len(result.errors) == 3
    assert_error_format(result.errors)


# ----------------------------
# Valid Structure Always Kept
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_valid_structure_always_kept(case: ParserCase) -> None:
    result = case["parser"](
        [
            case["valid_line"],
            case["invalid_rsid_line"],  # soft fail
            case["invalid_genotype_line"],  # soft fail
        ]
    )

    # ALL should be kept
    assert len(result.variants) == 3


# ----------------------------
# rsID (SOFT FAIL)
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_invalid_rsid_kept_with_error(case: ParserCase) -> None:
    result = case["parser"]([case["invalid_rsid_line"]])

    assert len(result.variants) == 1
    assert len(result.errors) == 1
    assert "invalid rsid" in result.errors[0]


@pytest.mark.parametrize("case", PARSERS)
def test_rsid_dot_allowed(case: ParserCase) -> None:
    result = case["parser"]([case["rsid_dot_line"]])

    assert len(result.variants) == 1
    assert len(result.errors) == 0


# ----------------------------
# Genotype (SOFT FAIL)
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_invalid_genotype_kept(case: ParserCase) -> None:
    result = case["parser"]([case["invalid_genotype_line"]])

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert len(result.errors) == 1
    assert "invalid genotype" in result.errors[0]


@pytest.mark.parametrize("case", PARSERS)
def test_missing_genotype_becomes_none(case: ParserCase) -> None:
    result = case["parser"]([case["missing_genotype_line"]])

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None


@pytest.mark.parametrize("case", PARSERS)
def test_haploid_supported(case: ParserCase) -> None:
    result = case["parser"]([case["haploid_line"]])

    assert len(result.variants) == 1
    assert result.variants[0].genotype is not None


# ----------------------------
# Parsing Behavior
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_mixed_delimiters_supported(case: ParserCase) -> None:
    result = case["parser"]([case["mixed_delimiter_line"]])

    assert len(result.variants) == 1


@pytest.mark.parametrize("case", PARSERS)
def test_header_skipped(case: ParserCase) -> None:
    result = case["parser"](
        [
            case["header_line"],
            case["valid_line"],
        ]
    )

    assert len(result.variants) == 1


@pytest.mark.parametrize("case", PARSERS)
def test_comments_and_empty_lines_ignored(case: ParserCase) -> None:
    result = case["parser"](
        [
            "",
            "# comment",
            case["valid_line"],
        ]
    )

    assert len(result.variants) == 1


# ----------------------------
# Mixed Quality Input
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_mixed_quality_input(case: ParserCase) -> None:
    result = case["parser"](
        [
            case["valid_line"],  # keep
            case["invalid_format_line"],  # drop
            case["invalid_genotype_line"],  # keep
            case["invalid_chrom_line"],  # drop
        ]
    )

    assert len(result.variants) == 2
    assert len(result.errors) >= 2


# ----------------------------
# Line Number Accuracy
# ----------------------------


@pytest.mark.parametrize("case", PARSERS)
def test_error_contains_correct_line_number(case: ParserCase) -> None:
    result = case["parser"](
        [
            case["valid_line"],
            case["invalid_chrom_line"],  # line 2
        ]
    )

    assert "Line 2" in result.errors[0]
