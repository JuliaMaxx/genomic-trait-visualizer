import pytest

from backend.services.parsers.parser_23andme import parse_23andme


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


@pytest.mark.parametrize(
    "filename,expected_min",
    [
        ("23andme_valid.txt", 3),
        ("23andme_messy.txt", 3),
        ("23andme_edge.txt", 4),
    ],
)
def test_parse_23andme_files(filename: str, expected_min: int) -> None:
    file_path = f"backend/tests/dna_samples/23andme/{filename}"
    lines = load_lines(file_path)

    result = parse_23andme(lines)

    assert len(result.variants) >= expected_min


def test_parse_23andme_broken_file() -> None:
    file_path = "backend/tests/dna_samples/23andme/23andme_broken.txt"
    lines = load_lines(file_path)

    result = parse_23andme(lines)
    print(result)
    assert len(result.variants) == 0


def test_parse_23andme_empty_file() -> None:
    result = parse_23andme([])

    assert result.variants == []
