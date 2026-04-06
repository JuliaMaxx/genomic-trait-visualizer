# 🧬 DNA Parser Contract (Developer Guide)

## 1. 🧱 Core Principle

> **Preserve data whenever structure is valid. Reject only when structure is broken.**

* **Keep the row** if it has valid structure (`chromosome`, `position`)
* **Drop the row** only if structure is invalid
* **rsid and genotype are NOT structural fields**
* **Genotype may be `None`**, but the variant should still be included

---

## 2. 📦 Output Contract (Non-Negotiable)

Every parser MUST return:

```python
ParseResult(
    variants: list[Variant],
    errors: list[str]
)
```

### `Variant` schema:

```python
Variant(
    rsid: str,
    chromosome: str,
    position: int,
    genotype: str | None
)
```

---

## 3. 🔁 Row Processing Rules

For each input line:

### 3.1 Skip Non-Data Lines

Skip:

* Empty lines
* Comment lines (`# ...`)
* Header row (must be detected dynamically)

---

### 3.2 Line Splitting

Use:

```python
parts = split_line(line)
```

Supports:

* CSV
* TSV
* Whitespace-delimited

---

### 3.3 Structure Validation (Hard Fail → Drop Row)

A row is **invalid and must be dropped** if:

#### ❌ Too few columns

```python
len(parts) < 4
```

#### ❌ Invalid chromosome

```python
normalize_chromosome(chrom) not in VALID_CHROMOSOMES
```

#### ❌ Invalid position

```python
int(position) fails
```

👉 For each failure:

* Log warning
* Append error
* `continue` (DO NOT add variant)

---

## 4. 🧬 rsID Handling (Soft Fail → Keep Row)

rsID is **informational, not structural**.

### 4.1 Validation

Use:

```python
is_standard_rsid(rsid)
```

### 4.2 Behavior

If rsid is invalid:

* ✅ Keep the variant
* ⚠️ Append error:

```python
"Line X: invalid rsid"
```

* ⚠️ Log warning

```python
logger.warning(msg)
```

---

## 5. 🧬 Genotype Handling (Soft Fail → Keep Row)

Genotype is **optional and tolerant**.

### 5.1 Supported Formats

#### Single column:

```
rsid, chrom, pos, genotype
```

#### Split alleles:

```
rsid, chrom, pos, allele1, allele2
```

### 5.2 Normalization

Always use:

```python
normalize_genotype(...)
```

### 5.3 Invalid Genotype

If normalization returns `None`:

* ✅ Keep the variant
* ⚠️ Append error:

```python
"Line X: invalid genotype"
```

---

## 6. 🧠 Normalization Rules

### 6.1 Chromosome

Use:

```python
chrom = normalize_chromosome(chrom)
```

Must match:

```python
VALID_CHROMOSOMES
```

---

### 6.2 rsID

Use:

```python
is_standard_rsid(rsid)
```

Rules:

* Used for **validation only**, not for dropping rows
* `"."` is considered valid (VCF compatibility)
* Strip BOM if present:

```python
rsid.lstrip("\ufeff")
```

---

### 6.3 Position

* Must be an integer
* No float / string tolerance

---

### 6.4 Genotype

Handled centrally via:

```python
normalize_genotype(...)
```

Parser MUST NOT implement genotype logic itself.

---

## 7. ⚠️ Error Handling Rules

### 7.1 Format

All errors MUST follow:

```
Line {line_number}: {reason}
```

Examples:

* `Line 10: invalid rsid`
* `Line 22: invalid chromosome`
* `Line 5: invalid genotype`

---

### 7.2 Logging

All **all errors MUST be logged and added to errors**:

```python
logger.warning(msg)
```

```python
errors.append(msg)
```

---

## 8. 🏗️ Parser Implementation Rules

### 8.1 Required Imports

```python
from fastapi.logger import logger
from backend.models.schemas import ParseResult, Variant
from backend.services.parsers.common import (
    VALID_CHROMOSOMES,
    normalize_chromosome,
    split_line,
    is_standard_rsid,
    normalize_genotype,
)
```

---

### 8.2 Function Signature

```python
def parse_<provider>(lines: list[str]) -> ParseResult:
```

---

### 8.3 Required Behavior

* Iterate with `enumerate(lines, start=1)`
* Strip lines before processing
* Use shared helpers (NO duplication)
* Append errors, never raise

---

## 9. 🧪 Testing Contract (Critical)

Each parser MUST satisfy:

### 9.1 Structural Tests

* Invalid rows (bad chrom/position) are dropped
* Valid rows are preserved regardless of rsid/genotype

### 9.2 rsID Tests

* Invalid rsid → error
* Variant still included

### 9.3 Genotype Tests

* Invalid genotype → `None`
* Variant still included

### 9.4 Mixed Quality Input

* Parser continues despite errors
* Errors collected, not raised

---

## 10. 🚫 Anti-Patterns (Strictly Forbidden)

❌ Dropping rows due to invalid rsid
❌ Dropping rows due to invalid genotype
❌ Raising exceptions for bad data
❌ Re-implementing normalization logic
❌ Silent failures (no error reporting)

---

## 11. ✅ Minimal Reference Flow

```python
for line_number, raw_line in enumerate(lines, start=1):
    # skip empty/comment
    # split line
    # skip header

    # validate structure (drop only if chrom/pos invalid)

    # validate rsid (log, but DO NOT drop)

    # normalize genotype (keep even if None)

    # append Variant
```
