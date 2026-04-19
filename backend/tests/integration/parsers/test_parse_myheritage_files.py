from backend.services.parsers import parse_myheritage


def to_alleles(genotype: str | None) -> list[str] | None:
    if genotype is None:
        return None
    return [allele for allele in genotype]


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def test_parse_myheritage_edge_file() -> None:
    lines = load_lines("backend/tests/dna_samples/myheritage/myheritage_edge.csv")
    result = parse_myheritage(lines)

    # All rows structurally valid → all kept
    assert len(result.variants) == 6

    # One invalid genotype (--,--) → 1 error
    assert len(result.errors) == 1

    # Spot-check key behaviors
    assert result.variants[0].rsid == "."
    assert result.variants[3].genotype == ["C"]  # haploid
    assert result.variants[4].genotype == ["I", "D"]  # indel
    assert result.variants[5].genotype is None  # missing alleles


def test_parse_myheritage_messy_file() -> None:
    lines = load_lines("backend/tests/dna_samples/myheritage/myheritage_messy.txt")
    result = parse_myheritage(lines)

    assert len(result.variants) == 5
    assert len(result.errors) == 2

    # Check normalization worked
    assert result.variants[0].genotype == ["A", "A"]

    # Check invalid genotype preserved as None
    assert any(v.genotype is None for v in result.variants)

    # Ensure bad line was dropped (not silently kept)
    assert all(v.rsid != "bad" for v in result.variants)


def test_parse_myheritage_valid_file() -> None:
    lines = load_lines("backend/tests/dna_samples/myheritage/myheritage_valid.csv")
    result = parse_myheritage(lines)

    assert len(result.variants) == 4
    assert result.errors == []

    # Spot-check correctness
    assert result.variants[0].genotype == ["A", "A"]
    assert result.variants[-1].chromosome == "7"


def test_parse_myheritage_broken_file() -> None:
    file_path = "backend/tests/dna_samples/myheritage/myheritage_broken.csv"
    lines = load_lines(file_path)

    result = parse_myheritage(lines)

    assert len(result.variants) == 0


def test_parse_myheritage_empty_file() -> None:
    result = parse_myheritage([])

    assert result.variants == []
