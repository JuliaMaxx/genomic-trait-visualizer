import pytest

from backend.services.parsers import parse_vcf


# --- VCF Header and Comment Handling ---
def test_skips_vcf_header_and_comments() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "##INFO=<ID=DP,Number=1,Type=Integer>",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "# This is a comment",
        "1	1000	rs123	A	G	.	.	.	GT	0/0",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 1
    assert result.variants[0].rsid == "rs123"
    assert result.errors == []


# --- Genotype Parsing (VCF encoding) ---
@pytest.mark.parametrize(
    "genotype_str,ref,alt,expected_genotype",
    [
        # Unphased
        ("0/0", "A", ["G"], "AA"),  # homozygous reference
        ("0/1", "A", ["G"], "AG"),  # heterozygous
        ("1/1", "A", ["G"], "GG"),  # homozygous alternate
        ("1/0", "A", ["G"], "GA"),  # reversed heterozygous (order preserved)
        # Phased
        ("0|0", "A", ["G"], "AA"),
        ("0|1", "A", ["G"], "AG"),
        ("1|1", "A", ["G"], "GG"),
        # Missing alleles
        ("./.", "A", ["G"], None),
        (".|.", "A", ["G"], None),
        ("./..", "A", ["G"], None),
        # Partial missing
        ("0/.", "A", ["G"], "A"),
        ("./1", "A", ["G"], "G"),
        # Multiple ALTs
        ("0/2", "A", ["G", "C"], "AC"),
        ("1/2", "A", ["G", "C"], "GC"),
        ("2/2", "A", ["G", "C"], "CC"),
        # Single allele (non-standard but should handle)
        ("0", "A", ["G"], "A"),
        ("1", "A", ["G"], "G"),
    ],
)
def test_vcf_genotype_parsing(
    genotype_str: str, ref: str, alt: list[str], expected_genotype: str | None
) -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        f"1	1000	rs123	{ref}	{','.join(alt)}	.	.	.	GT	{genotype_str}",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype == expected_genotype


# --- Chromosome Normalization ---
@pytest.mark.parametrize(
    "chrom_input,expected",
    [
        ("1", "1"),
        ("22", "22"),
        ("X", "X"),
        ("x", "X"),
        ("Y", "Y"),
        ("y", "Y"),
        ("MT", "MT"),
        ("mt", "MT"),
        ("M", "MT"),
        ("m", "MT"),
        ("chrX", "X"),
        ("CHR1", "1"),
    ],
)
def test_chromosome_normalization(chrom_input: str, expected: str) -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        f"{chrom_input}	1000	rs123	A	G	.	.	.	GT	0/0",
    ]
    result = parse_vcf(lines)

    assert result.variants[0].chromosome == expected


# --- rsID Handling ---
@pytest.mark.parametrize(
    "rsid_input,expect_error",
    [
        ("rs123", False),
        ("i4000001", False),
        (".", False),  # VCF placeholder
        ("rsABC", True),  # invalid
        ("R123", True),  # invalid
    ],
)
def test_rsid_validation(rsid_input: str, expect_error: bool) -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        f"1	1000	{rsid_input}	A	G	.	.	.	GT	0/0",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 1
    if expect_error:
        assert any("invalid rsid" in e for e in result.errors)
    else:
        assert not any("invalid rsid" in e for e in result.errors)


# --- Position Validation (HARD FAIL) ---
@pytest.mark.parametrize(
    "position_input,should_keep",
    [
        ("1000", True),
        ("1", True),
        ("999999999", True),
        ("0", True),
        ("-100", True),  # technically allowed even if unusual
        ("abc", False),  # invalid → drop
        ("1.5", False),  # float not allowed
    ],
)
def test_position_validation(position_input: str, should_keep: bool) -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        f"1	{position_input}	rs123	A	G	.	.	.	GT	0/0",
    ]
    result = parse_vcf(lines)

    if should_keep:
        assert len(result.variants) == 1
    else:
        assert len(result.variants) == 0


# --- Invalid Format (HARD FAIL) ---
def test_invalid_vcf_structure_dropped() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000",  # too few columns
        "1",  # just chromosome
        "1	1000	rs123	A	G	.	.	.",  # missing FORMAT and genotype
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 0
    assert len(result.errors) == 3


# --- Invalid Chromosome (HARD FAIL) ---
def test_invalid_chromosome_dropped() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "Z	1000	rs123	A	G	.	.	.	GT	0/0",
        "26	1000	rs124	A	G	.	.	.	GT	0/0",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 0
    assert len(result.errors) == 2


# --- Multiple ALT Alleles ---
def test_multiple_alt_alleles() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	rs123	A	G,C,T	.	.	.	GT	0/1",  # 0=A, 1=G
        "1	2000	rs124	A	G,C,T	.	.	.	GT	2/3",  # 2=C, 3=T
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 2
    assert result.variants[0].genotype == "AG"
    assert result.variants[1].genotype == "CT"


# --- No ALT (ALT == ".") ---
def test_no_alternate_allele() -> None:
    # no ALT, but genotype is 0/0 (REF/REF)
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	rs123	A	.	.	.	.	GT	0/0",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AA"


# --- Invalid Genotype (SOFT FAIL) ---
def test_invalid_genotype_soft_fail() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	rs123	A	G	.	.	.	GT	5/5",  # index out of range
        "1	2000	rs124	A	G	.	.	.	GT	ZZ",  # invalid characters
        "1	3000	rs125	A	G	.	.	.	GT	0/0",  # valid
    ]
    result = parse_vcf(lines)

    # All 3 rows should be kept
    assert len(result.variants) == 3
    # First two have None genotype
    assert result.variants[0].genotype is None
    assert result.variants[1].genotype is None
    assert result.variants[2].genotype == "AA"
    # Errors for first two
    assert len(result.errors) == 2


# --- Mixed Valid and Invalid Rows ---
def test_mixed_valid_invalid_rows() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	rs123	A	G	.	.	.	GT	0/0",
        "1	bad	rs124	A	G	.	.	.	GT	0/1",  # bad position
        "Z	2000	rs125	A	G	.	.	.	GT	0/1",  # bad chromosome
        "1	3000	rsABC	A	G	.	.	.	GT	0/1",  # bad rsid
        "1	4000	rs126	A	G	.	.	.	GT	./.",  # missing genotype
    ]
    result = parse_vcf(lines)

    # 3 valid structure rows kept
    assert len(result.variants) == 3
    # 4 errors: bad position, bad chromosome, bad rsid, missing genotype
    assert len(result.errors) == 4


# --- Empty Lines and Comments ---
def test_empty_lines_and_inline_comments() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "",
        "# inline comment",
        "1	1000	rs123	A	G	.	.	.	GT	0/0",
        "",
        "1	2000	.	A	G	.	.	.	GT	0/1",
        "",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 2
    assert result.variants[0].rsid == "rs123"
    assert result.variants[1].rsid == "."
    assert result.errors == []


# --- Extra Columns Ignored ---
def test_extra_columns_ignored() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT sample1 sample2 sample3",
        (
            "1 1000 rs123 A G 100 PASS DP=50 GT:PL "
            "0/0:0,10,100 0/1:50,0,50 1/1:100,100,0"
        ),
    ]
    result = parse_vcf(lines)

    # Should use only sample1 (column 9)
    assert len(result.variants) == 1
    assert result.variants[0].genotype == "AA"


# --- Phased vs Unphased Equivalence ---
def test_phased_unphased_treated_same() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	rs123	A	G	.	.	.	GT	0|1",
        "1	2000	rs124	A	G	.	.	.	GT	0/1",
    ]
    result = parse_vcf(lines)

    # Both should produce the same genotype
    assert result.variants[0].genotype == "AG"
    assert result.variants[1].genotype == "AG"


# --- BOM Handling ---
def test_bom_in_rsid() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	\ufeffrs123	A	G	.	.	.	GT	0/0",  # BOM in rsid
    ]
    result = parse_vcf(lines)

    assert result.variants[0].rsid == "rs123"


# --- Contract: Valid Structure Always Kept ---
def test_valid_structure_always_kept() -> None:
    """Valid structure rows should be kept even with soft failures."""
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
        "1	1000	rs123	A	G	.	.	.	GT	0/0",  # valid
        "1	2000	rsINVALID	A	G	.	.	.	GT	0/1",  # bad rsid (soft fail)
        "1	3000	.	A	G	.	.	.	GT	./.",  # missing genotype (soft fail)
    ]
    result = parse_vcf(lines)

    # All 3 should be kept
    assert len(result.variants) == 3


# --- Contract: Empty File ---
def test_empty_file() -> None:
    result = parse_vcf([])
    assert result.variants == []
    assert result.errors == []


# --- Contract: Only Headers ---
def test_only_headers() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "##INFO=<ID=DP,Number=1,Type=Integer>",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample1",
    ]
    result = parse_vcf(lines)
    assert result.variants == []
    assert result.errors == []


# --- Contract: Missing Genotype Field ---
def test_missing_gt_field() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1",
        "1\t1000\trs123\tA\tG\t.\t.\t.\tDP:AD\t10:5,5",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert any("invalid genotype" in e for e in result.errors)


# --- Contract: FORMAT Field Mismatch ---
def test_format_sample_mismatch() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1",
        "1\t1000\trs123\tA\tG\t.\t.\t.\tGT:DP\t0/1",
    ]
    result = parse_vcf(lines)

    assert len(result.variants) == 1
    assert result.variants[0].genotype is None
    assert any("invalid genotype" in e for e in result.errors)


# --- Contract: ALT == "." with Non-REF Genotype ---
def test_alt_dot_with_nonzero_gt() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1",
        "1\t1000\trs123\tA\t.\t.\t.\t.\tGT\t1/1",
    ]
    result = parse_vcf(lines)

    assert result.variants[0].genotype is None
    assert any("invalid genotype" in e for e in result.errors)


# --- Contract: ALT Index Out of Range ---
def test_alt_index_out_of_range() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1",
        "1\t1000\trs123\tA\tG,C\t.\t.\t.\tGT\t2/3",
    ]
    result = parse_vcf(lines)

    assert result.variants[0].genotype is None
    assert any("invalid genotype" in e for e in result.errors)


# --- Contract: Mixed Delimiters ---
def test_mixed_delimiters_supported() -> None:
    lines = [
        "#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT sample1",
        "1\t1000,rs123\tA\tG\t.\t.\t.\tGT\t0/0",
    ]
    result = parse_vcf(lines)
    assert len(result.variants) == 1


# --- Contract: Uses First Sample Only ---
def test_uses_first_sample_only() -> None:
    lines = [
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ts1\ts2",
        "1\t1000\trs123\tA\tG\t.\t.\t.\tGT\t0/0\t1/1",
    ]
    result = parse_vcf(lines)

    assert result.variants[0].genotype == "AA"
