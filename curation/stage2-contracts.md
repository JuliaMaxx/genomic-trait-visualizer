# Stage 2: data models and validation

Stage 2 gives whoami a consistent way to store scientific information before
the application uses it. Pydantic models are Python classes that check the
structure and relationships of this data.

This stage does not extract information automatically, review the science,
analyse uploaded DNA or publish a catalog. It defines the data structures
needed for later steps.

## From a source to an explanation

The models are separate because they describe different things:

- `EvidenceSource` identifies a publication or database record.
- `EvidenceClaim` records what that source reports. Each finding has one source
  and an `EvidenceLocation`, such as a page, table or database field.
- `AssessedClaim` records what the application proposes to say based on one or
  more findings, including the claim's scope and limitations.

A reported finding is not automatically an approved conclusion. Approval of an
assessed claim requires a recorded review and a reason. The models check that
this information is present; they cannot judge whether the reasoning is correct.

A fictional educational example shows the flow:

> Fictional source → finding: “The outcome varied with exposure” →
> assessed claim: “Exposure context matters when explaining this finding” →
> educational strategy and an explanation, without a personal prediction.

Records refer to each other by IDs. This makes the information traceable:
someone can follow an explanation back through its supporting claims and
findings to the original sources.

## Research drafts and explanation text

`TraitDossier` keeps the research for one trait together. It can start with
just a candidate identifying the proposed trait. Sources, findings, claims,
an interpretation and explanations can be added as the work progresses.
A draft can be incomplete, but its existing records and references must be valid.

`ExplanationContent` stores text, its purpose and the claims supporting it.
It covers descriptions, simple and technical explanations, result summaries
and tooltips. The same model can hold manually written text or text drafted
automatically in the future.

Review of the wording is recorded separately from approval of its supporting
claims. An approved claim does not automatically make every explanation of it
suitable for users.

## Two interpretation strategies

Different topics need different ways of using scientific information:

- **`allele_count`** describes a table for counting a chosen allele, such as A,
  at one DNA marker. It requires a complete pair of alleles and explicit
  information about the marker's location, reference genome version and DNA
  strand. Counts must agree with the genotype. `AG` and `GA` describe the same
  unordered pair, so duplicate or conflicting rows are rejected. The contract says
  to withhold a result for missing or incompatible input.
- **`educational`** describes information supported by claims without genotype
  rules or a personalized result.

The validators check these definitions; they do not apply them to uploaded DNA.
Another strategy can be added later if a trait needs it.

## Drafts and the published catalog contract

Validation rejects unexpected fields, missing references, duplicate record IDs
and rules that disagree with their input requirements.

The staged `TraitCatalog` is stricter than a draft. Each entry needs an approved
candidate, sources, findings, approved assessed claims, an interpretation and
reviewed explanation text. It requires schema version `3.0`, which identifies
the data format, and rejects other versions.

A source finding may retain its older `pending` label because its status is
separate from assessed-claim approval. This does not mean the finding has been
scientifically verified. Findings marked `rejected` or `needs_review` block
the catalog, even when no claim references them.

Result text must match the strategy, use a supported result label and reference
a claim used by the interpretation. Competing texts of the same type for the
same result are rejected. Educational explanations cannot target a result.

Passing validation means the structure and required review labels are consistent.
It does not prove scientific correctness, verify that a review took place or
authorize publication.

## Examples and the existing application

- The [rs671 draft](alcohol_flush/stage2-draft.json) represents the mapping and
  functional subset of the Stage 1 research. It has no scores and remains
  unapproved. It passes draft validation but fails the published contract.
- The [synthetic catalog](examples/synthetic-reviewed-catalog.json) demonstrates
  educational content without genotype rules. Its source, finding and approvals
  are fictional test data. Tests also use a fictional marker for approved
  allele-count examples. None of these approvals are real scientific approvals.

The application still uses the existing v2 catalog and models. The new
`TraitCatalog` is kept in `backend/models/published_catalog.py` until migration,
so Stage 2 does not change application behaviour.

The Stage 2 checks are covered by the contract and curation tests:

```powershell
.\venv\Scripts\python.exe -B -m pytest backend/tests/unit/test_stage2_contracts.py backend/tests/unit/test_curation_models.py -q
```
