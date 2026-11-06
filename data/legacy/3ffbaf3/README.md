# Stage 0 — Recovery and Legacy Baseline

## Overview

Before starting the semi-automatic curation pipeline, I wanted to preserve the current implementation and recover some curation code from earlier development.

The goal of this stage was to:

- Recover previously written curation models and validators.
- Save the original trait catalog and its analysis results.
- Make it possible to reproduce the old behavior after future refactors.
- Keep the existing application working without changes.

**Note:** The original catalog contains scientific and scoring issues identified during the audits. This archive is only for preserving the old implementation, not for validating its scientific correctness.

## 1. Recovered code

I recovered three files from an earlier Git snapshot:

| File                                            | Purpose                                                                            |
| ----------------------------------------------- | ---------------------------------------------------------------------------------- |
| `backend/models/curation.py`                    | Models for scientific sources, extracted claims, assessments, and review decisions |
| `backend/services/trait_curation/validation.py` | Basic validation of references between curation records                            |
| `backend/tests/unit/test_curation_models.py`    | Tests for the recovered models and validation                                      |

Some imports and outdated tests were adjusted to work with the current codebase.

I did not restore the old schemas, routes, or services because they could conflict with the current implementation.

The recovered curation models are not yet used by the application. They will be extended in later stages.

## 2. Legacy catalog backup

The original `data/traits.json` has been saved in:

`data/legacy/3ffbaf3/traits.json`

This preserves the manually created catalog before changing its structure or scientific interpretation.

**Original version:**

- Commit: `3ffbaf3c564a51e9db8f808b88c1842b1d2b4711`
- Catalog schema: `2.0`
- SHA-256: `e696a027db45bce4ad799b190b0cb67e19d6658f85003f0fd0150e6bc1808582`

The exact file hashes, Git references, and environment information are stored in `manifest.json`.

The archived file preserves its original bytes. The Git version has different line endings, but the JSON content is equivalent.

The active `data/traits.json` was not modified.

## 3. Archived files

The `data/legacy/3ffbaf3/` directory contains:

| File                          | Purpose                                                   |
| ----------------------------- | --------------------------------------------------------- |
| `traits.json`                 | Copy of the original trait catalog                        |
| `manifest.json`               | Original commit, file hashes, and environment information |
| `requirements.freeze.txt`     | Installed Python package versions                         |
| `historical-regressions.json` | Original analysis outputs for 32 synthetic cases          |
| `.gitattributes`              | Preserves the archived file's line endings                |
| `README.md`                   | This documentation                                        |

The original frontend dependency versions are preserved in the Git commit's `package-lock.json`.

## 4. Historical regression cases

I saved 32 synthetic test cases showing how the original analysis engine behaves.

They cover:

- All supported genotype combinations for the five existing traits.
- Missing and unmatched genotypes.
- Genotype allele order.
- Duplicate variants.
- The original confidence calculation behavior.

These cases are useful for checking how future changes affect the results.

**Important:** The expected results come from the original implementation. They are not independently verified scientific expectations.

The new analysis engine is allowed to produce different results when the scientific logic is corrected.

## 5. Running the tests

Normal tests verify the archived catalog, dependency snapshot and regression hashes,
catalog version, scientific status and 32 unique case IDs. They do not call the
evaluator or compare the live catalog with the archive. Pytest still loads the
backend package normally during collection.

```powershell
.\venv\Scripts\python.exe -B -m pytest backend/tests/unit/test_legacy_baseline.py -q
.\venv\Scripts\python.exe -B -m pytest backend/tests -q
```

The 32 replay cases are skipped unless `WHOAMI_LEGACY_REPLAY=1`. To replay them,
use a separate original-engine checkout with the recorded CPython **3.14.3**
environment (Windows 11 AMD64 was tested):

```powershell
# Start at the development checkout root.
$sourceRoot = (Get-Location).Path
git worktree add --detach ../legacy-reproduction 3ffbaf3c564a51e9db8f808b88c1842b1d2b4711
$legacyRoot = (Resolve-Path ../legacy-reproduction).Path
New-Item -ItemType Directory -Path "$legacyRoot/data/legacy" -Force | Out-Null
Copy-Item -LiteralPath "$sourceRoot/data/legacy/3ffbaf3" -Destination "$legacyRoot/data/legacy" -Recurse
Copy-Item -LiteralPath "$sourceRoot/backend/tests/unit/test_legacy_baseline.py" -Destination "$legacyRoot/backend/tests/unit"
Set-Location $legacyRoot
Copy-Item -LiteralPath data/legacy/3ffbaf3/traits.json -Destination data/traits.json
py -3.14 -m venv venv
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip install -r data/legacy/3ffbaf3/requirements.freeze.txt
$env:WHOAMI_LEGACY_REPLAY = "1"
try {
    .\venv\Scripts\python.exe -B -m pytest backend/tests/unit/test_legacy_baseline.py -q
} finally {
    Remove-Item Env:\WHOAMI_LEGACY_REPLAY
}
```

Check that the selected Python is exactly 3.14.3. Replay verifies the original Git
commit, unchanged tracked backend files (excluding the copied baseline test), the
catalog's equivalence to the original Git blob, and the imported code's location.
Additional archive files and the baseline test are allowed, including a staged
baseline test. Opting into replay on the wrong checkout or with modified backend
files fails. All original expected outputs and the `1e-12` numerical tolerance remain.

The frontend lockfile path in the manifest refers to the original commit; use its
recorded Node/npm versions and `npm ci` if reproducing the frontend.
Dependencies and the Git commit must remain obtainable; package distributions and
the OS are not bundled. These checks preserve software history, not scientific truth.

## 6. Validation results

After Stage 0:

- 444 backend tests passed.
- Ruff, Black, isort, and mypy checks passed.
- TypeScript and ESLint checks passed.
- OpenAPI and generated TypeScript contracts were unchanged.
- The original trait catalog and analysis logic were unchanged.

No existing application functionality was modified.

## 7. Known limitations

Stage 0 only recovered and preserved the existing implementation.

The following problems still need to be addressed:

- Some genotype interpretations and allele mappings are incorrect.
- The existing scoring and confidence calculations are not scientifically justified.
- Genotype parsing and matching need stricter validation.
- The recovered curation models do not yet support complete scientific provenance, approval tracking, or versioned publishing.
- The application still loads the original `traits.json` directly.

These issues are covered in the audit reports and will be addressed during later stages.

## Summary

Stage 0 is complete.

The original catalog and its results are preserved, the previous curation code has been recovered, and the existing application still works.

The next step is to prepare a scientifically reviewed reference trait that can be used to design and test the new curation workflow.
