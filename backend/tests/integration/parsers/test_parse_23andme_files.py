from backend.services.parsers import parse_23andme


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def test_parse_23andme_valid_file() -> None:
    lines = load_lines("backend/tests/dna_samples/23andme/23andme_valid.txt")
    result = parse_23andme(lines)

    assert len(result.variants) == 3
    assert result.errors == []

    # Spot-check
    assert result.variants[0].genotype == "AA"
    assert result.variants[-1].chromosome == "1"


def test_parse_23andme_edge_file() -> None:
    lines = load_lines("backend/tests/dna_samples/23andme/23andme_edge.txt")
    result = parse_23andme(lines)

    # All are structurally valid
    assert len(result.variants) == 6

    assert len(result.errors) == 1

    # Spot-check
    assert result.variants[0].genotype == "A"  # haploid
    assert result.variants[1].rsid == "."  # missing rsid allowed
    assert result.variants[2].genotype is None  # missing genotype
    assert result.variants[4].genotype == "ID"  # indel normalization


def test_parse_23andme_messy_file() -> None:
    lines = load_lines("backend/tests/dna_samples/23andme/23andme_messy.txt")
    result = parse_23andme(lines)

    assert len(result.variants) == 5
    assert len(result.errors) == 2

    # normalization
    assert result.variants[0].genotype == "AA"

    # invalid genotype handled
    assert any(v.genotype is None for v in result.variants)

    # garbage line dropped
    assert all(v.rsid != "bad" for v in result.variants)


def test_parse_23andme_broken_file() -> None:
    lines = load_lines("backend/tests/dna_samples/23andme/23andme_broken.txt")
    result = parse_23andme(lines)

    # All structurally invalid → drop
    assert len(result.variants) == 0
    assert len(result.errors) == 5


def test_parse_23andme_empty_file() -> None:
    result = parse_23andme([])

    assert result.variants == []
    assert result.errors == []
