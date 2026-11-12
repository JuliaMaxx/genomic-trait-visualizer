# Stage 6 — DNA ingestion and compatibility matching

## 1. Goal

My application already parses several DNA file formats. In Stage 6, I wanted to check **whether a parsed DNA observation can safely be used with a reviewed interpretation rule**.

Finding the right rsID is not enough. The genotype also needs to agree with the rule's genomic location, reference genome version, strand, and allowed alleles. If important information is missing or contradictory, the application should explain why the observation cannot be used instead of guessing.

I added two functions in `backend/services/dna_service.py`:

- `ingest_dna(lines)` reads a supported file and preserves its observations and problems.
- `match_observation(ingestion, requirements)` checks one required marker against a rule's requirements.

This is an **offline validation step**. Connecting it to the application's API is part of Stage 7.

## 2. What is supported

I started with a limited, documented subset of **23andMe raw DNA text files**:

- Four tab-separated columns: `rsid`, `chromosome`, `position`, `genotype`.
- Explicit **GRCh37 (Build 37)** and **plus/forward strand** metadata in the file.
- Positions counted from 1 (*1-based coordinates*).
- Two-letter A/C/G/T genotypes (*diploid single-nucleotide variants*) on chromosomes 1–22.

A *genome build* identifies the version of the reference genome used for positions. *Strand orientation* identifies which DNA strand the reported allele letters refer to. Both must be known before comparing an upload with a rule.

The program does **not** assume a genome build or strand just because the file identifies itself as 23andMe. Other file formats can still use the existing parsers, but they are not yet verified for this stricter matching workflow.

## 3. How it works

### Reading the DNA file

`ingest_dna()` checks the file format and metadata, then reuses my existing `parse_23andme()` parser. It returns the observations along with any parsing problems.

I added one optional field to the shared `Variant` model: `raw_genotype`. The 23andMe parser now preserves the original text alongside its normal normalized genotype. This matters because a tolerant parser might extract `AA` from an incomplete value such as `AA?`. Stage 6 checks the **original** text, so an incomplete call cannot silently become valid.

The function also keeps duplicate rows. If a malformed row has the same marker ID as a valid row, the malformed record cannot simply disappear and leave that marker looking reliable. An unrelated malformed row does not prevent other markers from being used.

### Checking compatibility with a rule

`match_observation()` looks for the rule's rsID and checks the available records. It treats `AG` and `GA` as the same complete genotype, but it never removes unexpected characters or invents missing alleles.

For a potentially usable observation, it checks:

- **Location:** chromosome and position.
- **Reference:** genome build, coordinate convention, and versioned chromosome sequence accession.
- **Representation:** strand orientation, diploid ploidy, and allowed alleles.
- **Consistency:** no conflicting duplicate records or missing essential metadata.

The chromosome sequence accession is obtained from a fixed GRCh37 reference mapping, **not copied from the rule to make the observation appear compatible**. The code does not convert genome builds or reverse-complement alleles.

The result has a status, a diagnostic explanation, and an observation **only when the status is `usable`**.

| Status | Meaning |
|---|---|
| `usable` | The observation meets the rule's requirements. |
| `absent` | The required marker is not present. |
| `no_call` | The marker is present, but no genotype was reported (`--`). |
| `partial` | The genotype is incomplete (`AA?`). |
| `invalid` | The genotype contains invalid characters (`ZZ`). |
| `conflicting` | Multiple rows for the marker disagree. |
| `unresolved` | Required metadata is missing or contradictory. |
| `incompatible` | The observation disagrees with the rule's representation. |
| `unsupported` | The input is outside the supported subset, such as a haploid call. |

For every result other than `usable`, the returned observation is `None`. The existing Stage 4 `evaluate()` function then reports an unavailable result rather than calculating an allele count.

## 4. A small example

Consider this **fictional** 23andMe row in a file with explicit Build 37 and plus-strand metadata:

```text
rs12345678    1    101    GA
```

Suppose a reviewed rule expects this rsID on chromosome 1 at position 101, with alleles A/G on the same reference build and strand. Matching returns `usable` and a standardized genotype of `AG`, while the original `GA` is preserved in the ingested data.

If the row contains `AA?` instead, the result is `partial`. If two rows report `AA` and `GG`, the result is `conflicting`. If the build is unknown, the result is `unresolved`. None of these is passed through as a usable observation.

The marker ID, position, and calls in this example are fictional; they are not scientific findings.

## 5. Why I chose this design

I kept **file ingestion** separate from **matching against a rule** because a DNA file can be read successfully even when a particular marker cannot be interpreted.

I also reused the existing parser instead of replacing it or changing normalization for every provider. Only the original genotype text needed to be preserved; the stricter checks belong in the matching step.

Starting with one verified 23andMe subset keeps the implementation understandable and testable. Other providers and genome representations can be added later after their conventions have been checked.

## 6. How to try it

From the project root, this example reads the fictional fixture and matches it against **manually constructed test requirements**:

```python
from pathlib import Path

from backend.models.interpretation import VariantRequirements
from backend.services.dna_service import ingest_dna, match_observation

lines = Path(
    "backend/tests/dna_samples/stage6/23andme_build37.txt"
).read_text(encoding="utf-8").splitlines()

requirements = VariantRequirements(
    rsid="rs12345678",
    placements=[{
        "genome_build": "GRCh37",
        "chromosome": "1",
        "position": 101,
        "sequence_accession": "NC_000001.10",
    }],
    orientation="forward_genomic",
    coordinate_system="1-based",
    ploidy=2,
    alleles=["A", "G"],
)

result = match_observation(ingest_dna(lines), requirements)
print(result.status)  # usable
```

These requirements demonstrate software compatibility only. They do **not** approve a scientific rule. The tests also use a fictional Stage 4 published trait to check that a usable match can reach the existing offline evaluator.

## 7. Testing

The Stage 6 tests use fictional data. They cover valid and equivalent genotypes, raw-value preservation, missing and malformed calls, conflicting duplicates, metadata problems, incompatible representations, and withholding unsafe observations. Existing parser and Stage 4 tests check that earlier functionality still works.

From the repository root in PowerShell:

```powershell
$python = '.\venv\Scripts\python.exe'

# Stage 6 tests
& $python -B -m pytest backend/tests/unit/test_stage6_dna_matching.py -q -p no:cacheprovider -p no:cov

# Full backend suite
& $python -B -m pytest backend/tests -q -p no:cacheprovider -p no:cov

# Code quality
& $python -B -m ruff check --no-cache backend
& $python -B -m mypy --config-file mypy.ini backend
& $python -B -m black --check backend
```

**Recorded verification (12 November 2026):** 59 Stage 6 tests passed; the full backend suite reported 789 passed and 32 skipped. Ruff, mypy, and Black passed. These are results from the implementation review, not claims of a fresh run of the commands above.

## 8. Limitations and next steps

Stage 6 does not yet verify other providers, GRCh38 uploads, sex or mitochondrial chromosomes, insertions/deletions, haploid or phased calls, strand conversion, genome-build conversion, or missing-genotype inference. File-header metadata is read, not independently authenticated.

The functions do **not** calculate trait probabilities, confidence scores, or medical conclusions. A compatible genotype is not proof that a scientific interpretation is valid; that depends on the separate review and publication workflow.

The existing public DNA upload and analysis routes still follow their earlier processing path. **Stage 7** will connect approved trait releases and these compatibility checks to FastAPI. Frontend presentation and thesis evaluation are addressed in later stages.

## References

- [23andMe — reference genome and strand](https://support.23andme.org/hc/en-us/articles/42965348688279-Which-Reference-Genome-and-Strand-Does-23andMe-Use)
- [23andMe — raw data guide](https://int.customercare.23andme.com/hc/en-us/articles/215983947)
- [NCBI — GRCh37 reference assembly](https://www.ncbi.nlm.nih.gov/grc/human/data?asm=GRCh37)
