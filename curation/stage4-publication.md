# Stage 4 — Catalog publication

**Status:** The publication workflow is implemented and has been tested with fictional data. The real rs671 dossier has not received the required scientific approvals and has not been published.

## 1. Goal

Stage 3 introduced a workflow for reviewing evidence, claims, interpretation rules and explanation text. Stage 4 uses those decisions to create a publishable trait catalog. Before a release is approved, the system checks that the review is complete and that the compiled trait produces the expected results for predefined test cases.

I kept the research data separate from the published data:

- `TraitDossier` contains the research material, supporting information and review-related fields.
- `TraitCatalog` (schema `3.1`) contains only the information needed to describe and interpret a published trait: its basic details, sources, evidence, claims, interpretation rules and explanations.

Review notes, extraction information and decision history are not included in `catalog.json`. They remain available in the review workspace and saved release inputs.

## 2. Requirements before building

A release is built from the latest dossier revision in a Stage 3 workspace. Stage 4 checks the recorded decisions, rather than trusting status labels written directly into the JSON.

For the current implementation, **every item in the dossier must have a valid approval**, including evidence that might not be used in the final catalog. This avoids adding a separate feature for selecting individual records. If an item is rejected, it must be removed in a new dossier revision; the earlier version remains in the review history.

Publication also requires a name, category, description and general explanation. For an allele-count interpretation, the genotype table must be complete, with result summaries for zero, one and two copies of the counted allele, plus an unavailable result.

Stage 4 uses the new compact schema `3.1`, rather than the earlier full-dossier schema `3.0`. The existing v2 application catalog, API, parsers, trait engine and frontend have not been changed by this stage.

## 3. Building a reproducible candidate

The `build` command validates the dossier and reviews, then creates the release files. For identical saved inputs and the same release ID, it produces identical file contents. To make that possible, JSON output uses a consistent format and compilation does not add the current time, random values or local workspace paths.

The build also saves a copy of the inputs, including the relevant dossier revisions, review decisions and expected test cases. This makes it possible to see what information was used to create a release.

If a source acquisition inventory is available, Stage 4 records information about the source documents used by the published trait, including their IDs and previously recorded SHA-256 hashes. It does **not** download the documents or check whether they scientifically support the claims. That remains part of the research and review process.

## 4. Checking interpretation results

Stage 4 includes an offline `evaluate()` function. It receives one compiled trait and one observation; it does not read an uploaded DNA file or depend on any particular DNA provider.

Two interpretation types are supported:

- **Allele count:** The evaluator checks the variant identifier, genome build, position, orientation and other required representation fields. If the input is compatible, it uses the reviewed genotype table to count the specified allele. If information is missing or incompatible, it returns an unavailable result instead of guessing.
- **Educational:** The evaluator returns the reviewed educational explanation without calculating a genotype result.

The expected results are stored separately in JSON files. The verifier compares the evaluator's actual outputs with those expected results. Missing required cases or incorrect results prevent a candidate from being built.

For rs671, `stage4-expected-cases.json` checks GG, AG, GA and AA for both GRCh37 and GRCh38, as well as cases with missing or incompatible information. Duplicate observations are marked as deferred because the current evaluator accepts only one observation at a time. These tests check genotype handling and software rules; **they do not establish a person's likelihood of experiencing alcohol flushing**.

## 5. Preview, approval and publication

The release process has five steps:

1. **Build:** Create and check the candidate files.
2. **Preview:** Display the compiled information and the results of the expected cases.
3. **Approve:** Record a reviewer, reason and the SHA-256 fingerprint of the exact candidate manifest.
4. **Publish:** Copy the approved files to the release directory without compiling them again.
5. **Verify:** Check the published files for changes and rerun the relevant consistency checks.

The fingerprint is used to ensure that approval refers to the same version of the files that is published. If the dossier revision or its effective review decisions change, a new build and approval are required.

A release contains:

| File                | Purpose                                                               |
| ------------------- | --------------------------------------------------------------------- |
| `catalog.json`      | Published trait data and interpretation rules                         |
| `inputs.json`       | Saved inputs, review decisions, cases and source-document information |
| `verification.json` | Actual and expected results for the test cases                        |
| `preview.md`        | Readable summary for the reviewer                                     |
| `manifest.json`     | Release details and hashes of candidate files                         |
| `approval.json`     | Final reviewer decision tied to the manifest                          |
| `checksums.json`    | Hashes used to check the published files                              |

Preview and approval also confirm that `catalog.json` matches the reviewed dossier. Publication does not rebuild the catalog and refuses to overwrite an existing release. The verification command can check a saved release without the original review workspace.

## 6. Example: publishing fictional data

The following PowerShell commands demonstrate the process from the repository root. **They use a synthetic dossier and fictional review decisions, not scientific approvals.** Use new workspace, candidate and release names if these paths already exist.

```powershell
$python = '.\venv\Scripts\python.exe'
$cli = 'backend.services.trait_curation.cli'
$workspace = 'curation/reviews/synthetic-stage4-practice'
$candidate = 'curation/candidates/synthetic-stage4-practice'

& $python -m $cli init curation/examples/synthetic-stage4-dossier.json $workspace
$targets = (& $python -m $cli status $workspace --json | ConvertFrom-Json).items
foreach ($target in $targets) {
    $item = & $python -m $cli inspect $workspace $target.scope $target.target_id | ConvertFrom-Json
    & $python -m $cli decide $workspace $target.scope $target.target_id approve --reviewer synthetic-demo --rationale 'Fictional software demonstration.' --revision $item.revision --fingerprint $item.fingerprint
}

& $python -m $cli status $workspace
& $python -m $cli build $workspace $candidate --release-id synthetic-practice-v1 --cases curation/examples/synthetic-stage4-cases.json
& $python -m $cli preview $candidate
```

After checking the preview, copy the displayed `Manifest SHA-256` value into `$fingerprint`:

```powershell
$fingerprint = '<paste the manifest SHA-256>'
& $python -m $cli approve-release $candidate $workspace --reviewer synthetic-demo --rationale 'Reviewed the fictional preview and case results.' --fingerprint $fingerprint
& $python -m $cli publish $candidate $workspace --releases data/releases
& $python -m $cli verify-release data/releases/synthetic-practice-v1
```

An existing example can be checked without building anything:

```powershell
& $python -m $cli verify-release data/releases/synthetic-stage4-demo-v1
```

## 7. Testing and limitations

The Stage 4 tests cover incomplete reviews, invalid published data, repeatable builds, expected interpretation results, changes to saved decisions, approval of exact files, publication without recompilation and detection of modified releases. The Stage 2 and Stage 3 tests continue to check the earlier authoring and review behavior.

From the repository root, the backend checks can be run with:

```powershell
& $python -B -m pytest backend/tests -q -p no:cacheprovider -p no:cov
& $python -B -m ruff check --no-cache backend
& $python -B -m mypy --config-file mypy.ini backend
```

There are important limits:

- Passing software tests does not mean that scientific claims or expected cases are scientifically correct. The real rs671 dossier still needs human review.
- SHA-256 hashes detect changes to release files, but someone with full filesystem access could change the files and their hashes together. Reviewer identities are not authenticated.
- The evaluator currently works with one explicit observation, not uploaded files or provider-specific formats.
- Verification uses the current evaluator and preview renderer. If those change later, an older release may fail verification even if its files have not changed. The saved fictional release is retained to help detect such compatibility changes.
