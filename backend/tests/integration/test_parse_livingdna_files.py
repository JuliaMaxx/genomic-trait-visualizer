from backend.services.parsers.parser_livingdna import parse_livingdna


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def test_parse_livingdna_edge_file() -> None:
    lines = load_lines("backend/tests/dna_samples/livingdna/livingdna_edge.txt")
    result = parse_livingdna(lines)

    # All structurally valid → all kept
    assert len(result.variants) == 6

    # Two invalid genotypes  → 2 errors
    assert len(result.errors) == 2

    # Spot checks
    assert result.variants[0].rsid == "."  # missing rsid allowed
    assert result.variants[2].genotype == "C"  # haploid
    assert result.variants[3].genotype == "ID"  # indel normalization
    assert result.variants[4].genotype is None  # missing genotype


def test_parse_livingdna_messy_file() -> None:
    lines = load_lines("backend/tests/dna_samples/livingdna/livingdna_messy.txt")
    result = parse_livingdna(lines)

    assert len(result.variants) == 6
    assert len(result.errors) == 2

    # normalization
    assert result.variants[0].genotype == "AA"

    # invalid genotype handled
    assert any(v.genotype is None for v in result.variants)

    # ensure garbage line dropped
    assert all(v.rsid != "bad" for v in result.variants)


def test_parse_livingdna_valid_file() -> None:
    lines = load_lines("backend/tests/dna_samples/livingdna/livingdna_valid.txt")
    result = parse_livingdna(lines)

    assert len(result.variants) == 4
    assert result.errors == []

    # correctness
    assert result.variants[0].genotype == "AA"
    assert result.variants[-1].chromosome == "7"


def test_parse_livingdna_broken_file() -> None:
    lines = load_lines("backend/tests/dna_samples/livingdna/livingdna_broken.txt")
    result = parse_livingdna(lines)

    assert len(result.variants) == 0


def test_parse_livingdna_empty_file() -> None:
    result = parse_livingdna([])

    assert result.variants == []
