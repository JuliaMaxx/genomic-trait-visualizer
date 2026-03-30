import pytest

from backend.services.parsers.parser_ancestry_dna import parse_ancestry_dna


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


@pytest.mark.parametrize(
    "filename,expected_min",
    [
        ("ancestry_valid.csv", 3),
        ("ancestry_messy.txt", 3),
        ("ancestry_edge.csv", 4),
    ],
)
def test_parse_ancestry_dna_files(filename: str, expected_min: int) -> None:
    file_path = f"backend/tests/dna_samples/ancestry/{filename}"
    lines = load_lines(file_path)

    result = parse_ancestry_dna(lines)

    assert len(result.variants) >= expected_min


def test_parse_ancestry_dna_broken_file() -> None:
    file_path = "backend/tests/dna_samples/ancestry/ancestry_broken.csv"
    lines = load_lines(file_path)

    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 0


def test_parse_ancestry_dna_empty_file() -> None:
    result = parse_ancestry_dna([])

    assert result.variants == []
