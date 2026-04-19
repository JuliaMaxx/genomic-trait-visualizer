from backend.services.parsers import parse_ftdna


def to_alleles(genotype: str | None) -> list[str] | None:
    if genotype is None:
        return None
    return [allele for allele in genotype]


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def test_parse_ftdna_edge_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ftdna/ftdna_edge.csv")
    result = parse_ftdna(lines)

    # All rows structurally valid → all kept
    assert len(result.variants) == 6

    # One invalid genotype (-- or ZZ) → 1 error
    assert len(result.errors) == 1

    # Spot-check behaviors
    assert result.variants[0].rsid == "."  # placeholder allowed
    assert result.variants[1].rsid.startswith("i")  # internal id

    # Chromosome normalization
    assert result.variants[2].chromosome == "X"
    assert result.variants[3].chromosome == "Y"
    assert result.variants[4].chromosome == "MT"

    # Genotype handling
    assert result.variants[4].genotype == ["I", "D"]  # indel
    assert result.variants[5].genotype is None  # invalid/missing


def test_parse_ftdna_messy_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ftdna/ftdna_messy.txt")
    result = parse_ftdna(lines)

    # All rows structurally valid → all kept
    assert len(result.variants) == 6

    # No invalid genotypes here
    assert len(result.errors) == 0

    # Mixed delimiters + formats
    assert result.variants[0].genotype == ["A", "A"]  # whitespace
    assert result.variants[1].genotype == ["C", "C"]  # tab
    assert result.variants[2].genotype == ["G", "G"]  # combined format

    # Haploid
    assert result.variants[3].genotype == ["A"]

    # Case normalization + extra columns
    assert result.variants[4].genotype == ["A", "G"]

    # Lowercase normalization
    assert result.variants[5].genotype == ["T", "T"]


def test_parse_ftdna_valid_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ftdna/ftdna_valid.csv")
    result = parse_ftdna(lines)

    assert len(result.variants) == 5
    assert result.errors == []

    # Spot-check correctness
    assert result.variants[0].genotype == ["A", "A"]
    assert result.variants[2].genotype == ["A", "G"]
    assert result.variants[-1].genotype == ["T", "T"]

    # Ensure chromosome consistency
    assert all(v.chromosome == "1" for v in result.variants)


def test_parse_ftdna_broken_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ftdna/ftdna_broken.csv")
    result = parse_ftdna(lines)

    # All rows structurally invalid → all dropped
    assert len(result.variants) == 0


def test_parse_ftdna_empty_file() -> None:
    result = parse_ftdna([])

    assert result.variants == []
