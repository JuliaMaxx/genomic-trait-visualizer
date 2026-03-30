import pytest

from backend.services.parsers.parser_23andme import (
    normalize_chromosome,
    normalize_genotype,
    parse_23andme,
)


@pytest.mark.parametrize(
    "lines,expected_count",
    [
        (["rs123\t1\t1000\tAA"], 1),
        (["rs123 1 1000 AA"], 1),
        (["# comment", "rs123\t1\t1000\tAA"], 1),
        ([""], 0),
        (["rs123\t1\t1000"], 0),  # missing genotype
        (["bad\tdata"], 0),
    ],
)
def test_basic_parsing(lines: list[str], expected_count: int) -> None:
    result = parse_23andme(lines)
    assert len(result.variants) == expected_count


@pytest.mark.parametrize(
    "genotype,expected",
    [
        ("AA", "AA"),
        ("ag", "AG"),
        ("--", None),
        ("", None),
        ("NA", None),
        ("ZZ", None),
    ],
)
def test_genotype_handling(genotype: str, expected: str | None) -> None:
    result = normalize_genotype(genotype)

    assert result == expected


@pytest.mark.parametrize(
    "chrom,expected",
    [
        ("1", "1"),
        ("X", "X"),
        ("Y", "Y"),
        ("M", "MT"),
        ("mt", "MT"),
    ],
)
def test_chromosome_normalization(chrom: str, expected: str) -> None:
    result = normalize_chromosome(chrom)

    assert result == expected


def test_invalid_chromosome() -> None:
    lines = ["rs123\t25\t1000\tAA"]
    result = parse_23andme(lines)

    assert len(result.variants) == 0


def test_invalid_position() -> None:
    lines = ["rs123\t1\tabc\tAA"]
    result = parse_23andme(lines)

    assert len(result.variants) == 0


def test_internal_ids() -> None:
    lines = ["i4000001\t1\t1000\tAA"]
    result = parse_23andme(lines)

    assert len(result.variants) == 1


def test_mixed_quality_input() -> None:
    lines = [
        "rs123\t1\t1000\tAA",
        "bad_line",
        "rs456\tX\t2000\tCC",
        "rs789\t25\t3000\tGG",
        "# comment",
    ]

    result = parse_23andme(lines)

    assert len(result.variants) == 2


def test_large_input() -> None:
    lines = [f"rs{i}\t1\t{i}\tAA" for i in range(5000)]
    result = parse_23andme(lines)

    assert len(result.variants) == 5000


def test_messy_spacing_and_case() -> None:
    lines = ["  rs123   x   1000   ag  "]
    result = parse_23andme(lines)

    assert result.variants[0].chromosome == "X"
    assert result.variants[0].genotype == "AG"


def test_duplicates_allowed() -> None:
    lines = [
        "rs123\t1\t1000\tAA",
        "rs123\t1\t1000\tAA",
    ]

    result = parse_23andme(lines)

    assert len(result.variants) == 2


def test_error_reporting() -> None:
    lines = [
        "rs123\t1\t1000\tAA",
        "bad_line",
        "rs456\t25\t2000\tGG",
    ]

    result = parse_23andme(lines)

    assert len(result.variants) == 1
    assert len(result.errors) >= 2


def test_error_messages_content() -> None:
    lines = ["bad_line"]

    result = parse_23andme(lines)

    assert len(result.errors) == 1
    assert "invalid format" in result.errors[0].lower()


def test_only_comments() -> None:
    lines = ["# comment", "# another"]

    result = parse_23andme(lines)

    assert result.variants == []
    assert result.errors == []


def test_negative_position() -> None:
    lines = ["rs123\t1\t-100\tAA"]
    result = parse_23andme(lines)

    assert result.variants[0].position == -100
