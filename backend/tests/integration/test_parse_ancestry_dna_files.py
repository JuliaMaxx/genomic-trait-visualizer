from backend.services.parsers.parser_ancestry_dna import parse_ancestry_dna


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def test_parse_ancestry_edge_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ancestry/ancestry_edge.csv")
    result = parse_ancestry_dna(lines)

    # All rows structurally valid → all kept
    assert len(result.variants) == 6

    # One invalid genotype (--,--) → 1 error
    assert len(result.errors) == 1

    # Spot-check key behaviors
    assert result.variants[0].rsid == "."  # placeholder rsid allowed
    assert result.variants[1].rsid.startswith("i")  # internal id

    # Chromosome normalization
    assert result.variants[2].chromosome == "X"
    assert result.variants[3].chromosome == "Y"
    assert result.variants[4].chromosome == "MT"

    # Genotype handling
    assert result.variants[4].genotype == "ID"  # indel
    assert result.variants[5].genotype is None  # both alleles missing


def test_parse_ancestry_messy_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ancestry/ancestry_messy.txt")
    result = parse_ancestry_dna(lines)

    # All rows structurally valid → all kept
    assert len(result.variants) == 5

    # One invalid genotype (G,--) → still valid (haploid), so no error here
    # BUT: check if your parser treats it as valid → expected 0 errors
    assert len(result.errors) == 0

    # Check delimiter flexibility worked
    assert result.variants[0].genotype == "AA"  # whitespace split
    assert result.variants[1].genotype == "CC"  # tab split

    # Haploid case
    assert result.variants[2].genotype == "G"

    # Case normalization + extra columns ignored
    assert result.variants[3].genotype == "AG"

    # Lowercase normalization
    assert result.variants[4].genotype == "TT"


def test_parse_ancestry_valid_file() -> None:
    lines = load_lines("backend/tests/dna_samples/ancestry/ancestry_valid.csv")
    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 5
    assert result.errors == []

    # Spot-check correctness
    assert result.variants[0].genotype == "AA"
    assert result.variants[2].genotype == "AG"
    assert result.variants[-1].genotype == "TT"

    # Ensure chromosome consistency
    assert all(v.chromosome == "1" for v in result.variants)


def test_parse_ancestry_dna_broken_file() -> None:
    file_path = "backend/tests/dna_samples/ancestry/ancestry_broken.csv"
    lines = load_lines(file_path)

    result = parse_ancestry_dna(lines)

    assert len(result.variants) == 0


def test_parse_ancestry_dna_empty_file() -> None:
    result = parse_ancestry_dna([])

    assert result.variants == []
