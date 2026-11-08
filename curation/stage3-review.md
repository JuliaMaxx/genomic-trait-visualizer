# Stage 3: Manual Scientific Review

## 1. Purpose

Stage 2 defines the structure of scientific data and checks that fields and references are valid. **Stage 3 adds human review:** it records what was reviewed, the decision, the reviewer and the reason.

The main goal is to prevent an old approval from silently applying to changed information. Stage 3 does **not** publish a catalog, analyze uploaded DNA or prove that a scientific conclusion is correct.

The workflow uses the same `TraitDossier` format for manually written data and future pipeline-generated proposals.

## 2. What can be reviewed?

There are four separate review scopes:

| Scope | What is checked? |
| --- | --- |
| **Evidence** | Does an `EvidenceClaim` accurately describe its scientific source and location? |
| **Claim** | Is an `AssessedClaim` supported by that evidence, with appropriate scope and limitations? |
| **Model** | Are the interpretation requirements, rules and handling of unavailable data acceptable? |
| **Content** | Is an individual `ExplanationContent` accurate, clear and consistent with its supporting information? |

These are separate decisions. **An approved scientific claim does not automatically approve the interpretation model that uses it.** For Stage 3, the model's review target ID is the trait's `proposed_id` (for example, `alcohol_flush`).

Some explanations depend on the interpretation model, while others describe general research. Result-specific explanations and the kinds `mental_model`, `model_limit_summary` and `calculation_notes` always depend on the model. Other explanations can declare `model_dependent: true`. Reviewers must check this setting; the program cannot determine scientific meaning from text alone.

Content review also covers the trait's display fields: name, category, description and keywords. Changing one of these makes the existing **content** approvals outdated, without automatically invalidating evidence, claim or model approvals.

## 3. How the review workflow works

The command-line interface (CLI) supports these commands:

| Command | Purpose |
| --- | --- |
| `init` | Start a review workspace from a dossier |
| `validate` | Check the dossier's structure and publication completeness |
| `inspect` | Display an item, its supporting information and its fingerprint |
| `decide` | Approve, reject or request changes |
| `revise` | Save a correction as a new dossier revision |
| `status` | Show current approvals, problems and Stage 4 readiness |
| `history` | Show previous revisions and decisions |

Run the commands from the repository root, using the project's Python environment.

### Inspect the real rs671 research draft

The real rs671 dossier is **not automatically approved**. It can be initialized and inspected without recording any scientific approval:

```powershell
python -m backend.services.trait_curation.cli init curation/alcohol_flush/stage2-draft.json curation/reviews/alcohol_flush
python -m backend.services.trait_curation.cli validate curation/reviews/alcohol_flush
python -m backend.services.trait_curation.cli inspect curation/reviews/alcohol_flush evidence E1
python -m backend.services.trait_curation.cli inspect curation/reviews/alcohol_flush model alcohol_flush
python -m backend.services.trait_curation.cli status curation/reviews/alcohol_flush
```

Inspection displays the relevant source details, evidence locations, claims or rules. The original scientific source files remain in the Stage 1 source archive; they are **not copied** into the review workspace. Reviewers should consult those source files and the acquisition inventory when checking findings.

### Practice a decision with fictional data

Use the existing synthetic example to test the workflow without making real scientific approval claims:

```powershell
$synthetic = Get-Content curation/examples/synthetic-reviewed-catalog.json -Raw | ConvertFrom-Json
$synthetic.traits[0] | ConvertTo-Json -Depth 30 | Set-Content -Encoding utf8 curation/synthetic-review-input.json
python -m backend.services.trait_curation.cli init curation/synthetic-review-input.json curation/reviews/synthetic
$review = python -m backend.services.trait_curation.cli inspect curation/reviews/synthetic evidence synthetic-finding | ConvertFrom-Json
python -m backend.services.trait_curation.cli decide curation/reviews/synthetic evidence synthetic-finding approve --reviewer thesis-author --rationale "Fictional demonstration only." --revision $review.revision --fingerprint $review.fingerprint
```

The `decide` command requires the exact revision and fingerprint shown by `inspect`. Other evidence, claims, the model and explanations still need their own decisions before the dossier can be ready.

To correct a dossier, export a copy, edit it in the IDE and save a new revision:

```powershell
python -m backend.services.trait_curation.cli inspect curation/reviews/synthetic --output curation/synthetic-correction.json
# Edit the exported file before continuing.
python -m backend.services.trait_curation.cli revise curation/reviews/synthetic curation/synthetic-correction.json --reason "Clarify the fictional explanation."
python -m backend.services.trait_curation.cli status curation/reviews/synthetic
python -m backend.services.trait_curation.cli history curation/reviews/synthetic
```

The corrected copy must keep the existing candidate ID, trait ID and current revision number. The workflow assigns the next revision number automatically.

## 4. Revisions, fingerprints and outdated approvals

A review workspace contains numbered dossier snapshots and a decision log:

```text
review-workspace/
  revisions/
    0001.json
    0002.json
  decisions.jsonl
```

A **revision** is a saved version of the dossier. Corrections create a new snapshot rather than overwriting earlier versions. `decisions.jsonl` preserves decisions, reviewer identifiers, reasons and timestamps.

A **fingerprint** is a SHA-256 hash of the reviewed item and its relevant dependencies. The program calculates it from validated JSON in a consistent format. If that information changes, its fingerprint changes and the previous decision no longer applies to the new content.

For example:

| Change | What happens to previous approvals? |
| --- | --- |
| Evidence or source-record information changes | Evidence and dependent claims, model and content become **stale** |
| Interpretation rule or counted allele changes | Model and model-dependent content become **stale**; unchanged scientific claims remain approved |
| One explanation's wording changes | Only that explanation becomes **stale** |
| Trait display name, category, description or keywords change | Content approvals become **stale** |
| A dependency is rejected without changing its content | Dependent approvals become **blocked**, not stale |
| Only JSON formatting or unrelated workflow metadata changes | Relevant approvals remain valid |

**Stale** means the decision's fingerprint no longer matches the current information. **Blocked** means an approval still matches, but a required supporting item is not effectively approved. **Pending** means no decision has been recorded. A matching rejection or request for changes also prevents effective approval.

The latest decision for a matching fingerprint applies. If exactly the same previously reviewed content is restored, its earlier decision can apply again, unless a later decision for that same fingerprint replaces it.

## 5. When is a dossier ready for Stage 4?

Readiness requires **both**:

1. A structurally complete dossier that passes the shared Stage 2 checks.
2. Effective approval of every current evidence finding, assessed claim, interpretation and explanation, including items not referenced by other records.

Stage 3 determines approval from recorded decisions, **not** from fields such as `status: "approved"` or `reviewed: true` in the dossier. It does not change those fields or build a published catalog.

`ready_for_stage4` means the dossier can proceed to the next stage. It does **not** mean it has already been published.

## 6. Limitations and next steps

- The CLI records a reviewer identifier but does not verify the person's identity. A recorded decision is not proof of scientific correctness.
- The workspace is local and is not tamper-proof. Use one writing process per workspace, preserve backups and avoid manually editing snapshots or the decision log.
- Fingerprints cover the stored source records, **not the bytes of external source documents**. Changes to a source document must be reflected in the dossier; Stage 1 separately retains document checksums.
- Stage 3 reviews the whole dossier. Selecting a smaller set of records, creating the final published format, testing expected genotype cases and approving an immutable release are tasks for **Stage 4**.
- The active v2 application and the original rs671 research dossier are unchanged.

## 7. Tests

Stage 3 uses fictional review decisions and temporary workspaces to test revision history, stale approvals, independent dependencies, CLI commands and publication readiness. The real rs671 dossier is only used for unapproved inspection examples.

Run the focused tests with:

```powershell
python -B -m pytest backend/tests/unit/test_stage3_workflow.py -q
```

**Main design decision:** separate scientific review into four scopes and bind decisions to exact data fingerprints. This makes corrections traceable and prevents an approval from silently covering changed scientific information.
