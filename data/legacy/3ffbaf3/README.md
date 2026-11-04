# Legacy baseline and Stage 0 recovery

This is a **scientifically superseded, not independently validated** historical
baseline. It identifies software behavior, not an approved scientific release.
Scores, odds ratios, genotype interpretations, confidence percentages and advice
are not scientifically approved. Passing regression tests does not change that.

The scientific and architectural findings remain in
`docs/audits/01-pipeline-readiness.md` through `05-implementation-plan.md`.
Stage 0 preserves these findings and the old behavior; it does not correct the
biology or implement Stages 1–9. The active application still uses
`data/traits.json`, not this archive.

## Identity and contents

- Engine commit: `3ffbaf3c564a51e9db8f808b88c1842b1d2b4711`.
- Engine tree: `898692ae03a6066e0e631eaf21505244974315dc`.
- Catalog schema: `2.0`, in the existing `version` field.
- Exact working catalog SHA-256:
  `e696a027db45bce4ad799b190b0cb67e19d6658f85003f0fd0150e6bc1808582`.
- Git catalog blob: `1dc8864698140fad623274a369446e88d2970ad2`.
- Git catalog SHA-256:
  `6e1a7d7148417ba92c711b204f0c862667eae068b6a174f0b431b219c697a565`.

`manifest.json` records the commit, catalog identity, environment, dependency
snapshot, original runtime source hashes, contract artifact hashes, historical
case-set identity and recovery provenance. This detached historical inventory is
not a new published catalog schema or an approval manifest.

`traits.json` is the exact 57,474-byte starting working copy. Its CRLF line
endings differ from the 56,519-byte LF Git blob. Local `core.autocrlf=true`
explains the two byte hashes; the JSON and normalized text agree. The local
`.gitattributes` disables text conversion for this archived file, preserving its
bytes when committed and checked out. Other hashed baseline artifacts use LF.
The live `data/traits.json` was not rewritten.

`requirements.freeze.txt` records every installed Python distribution, including
pip. The environment was CPython **3.14.3**, MSC 64-bit AMD64, Windows 11 build
26200. Backend versions include FastAPI 0.135.1, Starlette 0.52.1, Pydantic
2.12.5, pydantic_core 2.41.5, python-multipart 0.0.22 and Uvicorn 0.41.0.
Test/tool versions include pytest 9.0.2 and Ruff 0.15.5. The installed
`pandas-stubs==3.0.0.260204` and `pip==26.0.1` supplement the original pinned
`requirements.txt`; the original requirements file remains unchanged.

Frontend identity is the original commit's `frontend/package-lock.json`, with
Node v24.14.1, npm 11.11.0 and installed TypeScript 5.9.3. No dependencies were
installed or updated during Stage 0. The mypy configuration targets Python 3.11;
that configuration is not evidence of a tested Python 3.11 runtime.

`historical-regressions.json` was captured before recovering the curation code.
Its 32 cases cover the 21 catalog-supported complete genotype combinations,
missing data for every trait, unmatched and no-call input, matched allele-order
reversal, last-row duplicate selection, and increased lactose confidence from an
unmatched secondary marker. It retains result labels, numeric outputs, rule
states, contribution labels and headlines. These are synthetic direct-service
inputs with deliberately unrelated coordinates, following existing test setup.
They do not establish provider, build or strand compatibility.

The pre-existing tests and expected outputs remain available at
`3ffbaf3c564a51e9db8f808b88c1842b1d2b4711:backend/tests`. They were preserved
without changes. Both those assertions and the captured cases are historical
software evidence, not independently sourced scientific expectations.

## Reproduction

From this Stage 0 repository root, using the existing environment:

```powershell
.\venv\Scripts\python.exe -B -m pytest backend/tests/unit/test_legacy_baseline.py -q -p no:cacheprovider -p no:cov
.\venv\Scripts\python.exe -B -m pytest backend/tests -q -p no:cacheprovider -p no:cov
```

The baseline tests verify archived byte hashes, normalized equality with the
active catalog, each original backend source hash, and all 32 fixed historical
outputs. Numeric comparisons allow only `1e-12` rounding differences. They never
regenerate expectations. When later stages intentionally replace runtime
behavior, run these checks against the historical commit rather than requiring
the revised engine to retain these results or fall back to legacy execution.

To reproduce independently after the application evolves, create a separate
checkout of the exact original engine and copy only the historical artifacts
and baseline test into it. The following commands are instructions, not actions
performed by Stage 0:

```powershell
# Run at the Stage 0 checkout root; keep this checkout available as the source.
$stageZeroRoot = (Get-Location).Path
git worktree add --detach ../legacy-reproduction 3ffbaf3c564a51e9db8f808b88c1842b1d2b4711
Set-Location ../legacy-reproduction
New-Item -ItemType Directory -Path data/legacy -Force | Out-Null
Copy-Item -LiteralPath "$stageZeroRoot/data/legacy/3ffbaf3" -Destination data/legacy -Recurse
Copy-Item -LiteralPath "$stageZeroRoot/backend/tests/unit/test_legacy_baseline.py" -Destination backend/tests/unit

# Install CPython 3.14.3 (64-bit) first; verify that exact patch version.
py -3.14 -m venv venv
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip install -r data/legacy/3ffbaf3/requirements.freeze.txt
.\venv\Scripts\python.exe -B -m pytest backend/tests -q -p no:cacheprovider -p no:cov
.\venv\Scripts\python.exe -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The original suite has 381 tests; the copied baseline file adds 34. Recovery
tests require the Stage 0 checkout and are not part of the original engine.
The archived catalog can be restored byte-for-byte in this separate checkout
with `Copy-Item data/legacy/3ffbaf3/traits.json data/traits.json` if exact CRLF
bytes are needed. Ordinary LF/CRLF checkouts produce the same parsed catalog.
The loader uses a fixed path and process caches; start a fresh process for each
reproduction. No runtime release selection was added.

The original routes include `POST /analyze/` for multipart uploads,
`POST /traits/{trait_id}/evaluate` for detail, and `GET /traits/`,
`GET /traits/{trait_id}`, `GET /rsids/`, `GET /rsids/{rsid}` and `GET /search/`.
For example, in a second terminal, send a repository test fixture:

```powershell
curl.exe -F "file=@backend/tests/dna_samples/23andme/23andme_valid.txt" http://127.0.0.1:8000/analyze/
```

To reproduce the original frontend in that checkout, use Node/npm versions above
and run `npm.cmd ci` then `npm.cmd run dev` from `frontend/`. No frontend assets
or contracts were changed. The lockfile identifies dependencies; the baseline
does not vendor Python wheels, npm packages or the operating system. Recreating
the environment requires access to those distributions. Other platforms are
not independently verified.

The legacy evaluator remains unchanged: a matched genotype score is multiplied
by `ln(odds_ratio)` when present (otherwise by 1), multiplied by rule weight,
then divided by all trait rule weights. Scores at least 0.25 yield `likely`, at
most -0.25 yield `unlikely`; other scores yield `inconclusive`. No matched rules
means an unavailable score. Confidence remains observed weighted coverage times
the capped mean absolute matched signal with the existing evidence multiplier.
This describes the implementation and supplies no scientific justification.

## Recovered foundations and adaptations

All objects were inspected and verified as blobs in containing snapshot tree
`0196dd10dd0868fd3df5fc9052db68fccfa6a40e` before restoration:

| Recovered file | Original Git blob |
| --- | --- |
| `backend/models/curation.py` | `97988ab2b6be9a44cfee6da8f763ed44f66dbf0e` |
| `backend/services/trait_curation/validation.py` | `0ae64817b0ce485236a5afe081cf8afb8e0fc0a2` |
| `backend/tests/unit/test_curation_models.py` | `1a7b3a2518fce5a578faf8d3ec7af7935dcfa658` |

The recovered models retain source, claim and extraction classifications,
source bibliography and locations, evidence proposals, candidate revisions,
assessments, review decisions and structured findings. Existing `TraitCategory`
and `EvidenceLevel` aliases from `backend.models.common` replace duplicated
literals with identical allowed values. Module documentation explicitly limits
the meaning of historical status fields. The reference validator is restored
without behavioral changes.

Tests import internal types directly from `backend.models.curation`. The obsolete
`/traits/{trait_id}/detail` assumption is replaced with assertions for the current
GET catalog and POST evaluation routes, HTTP methods and response models.
Existing assertions remain, with additional independent invalid-field checks,
timezone checks for all timestamp fields, location/provenance serialization,
all three reference kinds, mixed findings, revision preservation and defaults.
Typed constructors use enum members; intentionally invalid inputs still pass
through Pydantic validation. Route inspection narrows to FastAPI's `APIRoute`.

Intentionally not restored: old `schemas.py`, historical package exports,
routes, catalog service implementations or unrelated snapshot files. Public
package exports and the runtime import graph stay unchanged. New records are
available only by direct internal import; nothing activates them at startup.

## Limitations retained for later stages

- Recovered models keep Pydantic's original unknown-field ignoring behavior.
  Source passages/locations and many scientific fields remain optional. A
  structurally valid proposal need not contain adequate evidence.
- `validated`, `approved`, `reviewed` and `approve` are retained historical
  vocabulary. No record created here grants scientific approval, publication
  eligibility or runtime authority. Extraction confidence is not predictive
  confidence. The default rubric string identifies no implemented review rubric.
- Review decisions lack subject/dependency hashes, approval scopes and immutable
  snapshots. Assessments are not bound to exact scientific revisions. These
  types need later extension; they are not a completed review workflow.
- Reference validation checks existence only, over every supplied claim. It
  does not detect duplicate IDs, enforce candidate membership, prove source
  fidelity, validate mappings or change statuses. Empty findings do not mean
  scientific validity. Finding timestamps are current UTC, so whole serialized
  reports are not byte-deterministic even though check order/results are.
- The existing catalog retains the documented eye/bitter direction problems,
  lactose orientation and reachability problems, unsupported numerical origins,
  confidence limitations and bibliographic discrepancies. Input and privacy
  issues identified by the audits also remain. No scientific corrections,
  pipeline, review CLI, successor schemas, publication gates or evaluator
  refactor belong to Stage 0.

## Review inventory and validation

New files are the three recovered files, `backend/tests/unit/test_legacy_baseline.py`
and this directory's `.gitattributes`, `README.md`, `manifest.json`,
`requirements.freeze.txt`, `historical-regressions.json` and archived `traits.json`.
No pre-existing tracked file is modified by this implementation. The user's
pre-existing `.gitignore` edit (ignoring `docs/`), all audit reports and unrelated
files are preserved. This report lives under `data/legacy/` so it is not hidden
by that ignore rule.

Contract checks must be read-only. Do not run `npm run api:check` for this purpose:
its exporter rewrites tracked OpenAPI. Compare `app.openapi()` in memory with
`frontend/openapi.json`, then run the installed generator's `--check` directly:

```powershell
# Repository root
.\venv\Scripts\python.exe -B -m ruff check --no-cache backend
.\venv\Scripts\python.exe -B -c "import json; from pathlib import Path; from backend.main import app; assert app.openapi() == json.loads(Path('frontend/openapi.json').read_text(encoding='utf-8'))"

# frontend/
node node_modules/typescript/bin/tsc --noEmit --incremental false
node node_modules/eslint/bin/eslint.js . --no-cache
node node_modules/openapi-typescript/bin/cli.js openapi.json -o src/types/generated-api.ts --check
```

Validation on 2026-11-04:

- Before recovery: all 381 existing backend tests passed, and in-memory OpenAPI
  equalled the tracked snapshot.
- After recovery: **444 backend tests passed** (381 existing, 29 recovered/adapted
  curation checks, and 34 baseline checks including the 32 historical cases).
- Ruff over `backend`, Black/isort checks on all four added Python files,
  mypy on those four files, TypeScript, ESLint and generated TypeScript `--check`
  passed.
- In-memory OpenAPI still exactly equals `frontend/openapi.json`. Both tracked
  API artifact byte hashes match the initial manifest. No artifacts were
  regenerated and no unexpected API differences were found.
- The live catalog, all five audits and the user's existing `.gitignore` edit
  have exactly their starting SHA-256 values. All 27 original backend Python
  source hashes match the recorded engine. The recovered validator is
  byte-identical to its original blob.
- Git attribute filtering preserves the archived catalog bytes; `git diff
  --check` passed. No pre-existing tracked files were changed by Stage 0.

**Stage 0 acceptance criteria are satisfied.** Recovery and reference checks are
tested, existing functionality and contracts are preserved, the exact historical
catalog and engine/environment identities are recoverable, and scientific
limitations are explicit. The documented later-stage incompatibilities remain
deliberately unresolved. No changes were committed. A fresh dependency install,
browser session and cross-platform reproduction were not performed.
