import pytest

from backend.services.dna_format_detector import detect_format


def load_lines(path: str) -> list[str]:
    """Load a file and return its lines."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


@pytest.mark.parametrize(
    "filename,format",
    [
        ("23andme_1.tsv", "23andme"),
        ("23andme_2.txt", "23andme"),
        ("ancestry.csv", "ancestry"),
        ("ftdna.csv", "ftdna"),
        ("gedmatch_1.csv", "gedmatch"),
        ("gedmatch_2.csv", "gedmatch"),
        ("gedmatch_3.csv", "gedmatch"),
        ("livingdna.csv", "livingdna"),
        ("myheritage.csv", "myheritage"),
        ("vcf.vcf", "vcf"),
    ],
)
def test_detect_format(filename: str, format: str) -> None:
    """Test DNA format detection for multiple sample files."""
    file_path: str = f"backend/tests/dna_samples/{format}/{filename}"
    lines: list[str] = load_lines(file_path)
    fmt: str = detect_format(lines)
    assert fmt == format


def test_empty_file() -> None:
    """Empty file should raise ValueError."""
    with pytest.raises(ValueError):
        detect_format([])


def test_unknown_format() -> None:
    """Random non-DNA lines should return 'unknown'."""
    lines: list[str] = ["random text", "not dna"]
    fmt: str = detect_format(lines)
    assert fmt == "unknown"
