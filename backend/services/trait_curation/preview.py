"""Markdown assembled only from the compiled catalog and verification report."""

import json
import re
from typing import Any

from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import TraitCatalog

_TEXT_ENTITIES = str.maketrans({char: f"&#{ord(char)};" for char in "\\`*_[]<>&#|~"})


def _plain_text(text: str) -> str:
    """Encode prose once; Markdown displays entities as their original characters."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        # Encoding the first character also prevents lists and indented code.
        if line and (line[0] in " \t-+=" or line[0].isdigit()):
            lines.append(f"&#{ord(line[0])};{line[1:].translate(_TEXT_ENTITIES)}")
        else:
            lines.append(line.translate(_TEXT_ENTITIES))
    return "\n".join(lines)


def _format_metadata(value: object) -> str:
    """Display strings or Unicode JSON as literal text, including nested strings."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return _plain_text(text)


def _inline_json(value: object) -> str:
    """Keep serialized input literal even when its strings contain backticks."""
    text = json.dumps(value, sort_keys=True)
    longest_run = max((len(run) for run in re.findall(r"`+", text)), default=0)
    delimiter = "`" * (longest_run + 1)
    return f"{delimiter}{text}{delimiter}"


def render_preview(catalog: TraitCatalog, verification: dict[str, Any]) -> str:
    trait = catalog.traits[0]
    lines = [
        f"# Publication preview: {_plain_text(trait.name)}",
        "",
        f"Trait: `{trait.id}` | Category: {trait.category}",
        "",
        _plain_text(trait.description),
        "",
        "## Scientific claims",
        "",
    ]
    for claim in trait.claims:
        lines.extend(
            [
                f"### {_plain_text(claim.claim_id)}",
                "",
                _plain_text(claim.statement),
                "",
                f"Scope: {_plain_text(claim.scope)}",
                "",
                f"Evidence: {_plain_text(', '.join(claim.evidence_ids))}",
                "",
                *[f"- {_plain_text(limit)}" for limit in claim.limitations],
                "",
            ]
        )
    lines.extend(["## Sources and evidence locations", ""])
    for source in trait.sources:
        lines.extend(
            [f"### {_plain_text(source.source_id)}: {_plain_text(source.name)}", ""]
        )
        for key, value in source.model_dump(mode="json", exclude_none=True).items():
            if key not in {"source_id", "name"}:
                lines.append(f"- {key}: {_format_metadata(value)}")
        lines.append("")
        for finding in trait.evidence:
            if source.source_id not in finding.source_ids:
                continue
            lines.extend(
                [
                    f"**{_plain_text(finding.evidence_id)}**: "
                    f"{_plain_text(finding.statement)}",
                    "",
                ]
            )
            for key, value in finding.model_dump(
                mode="json",
                exclude_none=True,
                exclude={"evidence_id", "statement", "source_ids"},
            ).items():
                value_text = json.dumps(value, ensure_ascii=False)
                # Preserve the fixed enum label used in frozen previews;
                # all free text, including quoted scalars, must be escaped.
                if key != "claim_type":
                    value_text = _plain_text(value_text)
                lines.append(f"- {key}: {value_text}")
            lines.append("")
    model = trait.interpretation
    lines.extend(
        [
            "## Interpretation",
            "",
            f"Strategy: `{model.strategy}`",
            "",
            f"Supporting claims: {_plain_text(', '.join(model.claim_ids))}",
            "",
        ]
    )
    if isinstance(model, AlleleCountInterpretation):
        lines.extend(
            [
                f"Counted allele: `{model.counted_allele}`",
                "",
                "Required representation:",
                "",
                "```json",
                json.dumps(
                    model.requirements.model_dump(), indent=2, ensure_ascii=False
                ),
                "```",
                "",
                "| Genotype | Copies |",
                "| --- | --- |",
                *[f"| {rule.genotype} | {rule.copies} |" for rule in model.rules],
                "",
                f"Missing/incompatible input policy: `{model.unavailable_policy}`.",
                "",
            ]
        )
    lines.extend(["## Reviewed explanations", ""])
    for content in trait.explanations:
        target = content.result_key if content.result_key is not None else "general"
        lines.extend(
            [
                f"### {_plain_text(content.content_id)} ({content.kind}; {target})",
                "",
                *([_plain_text(content.title), ""] if content.title else []),
                _plain_text(content.body),
                "",
                f"Claims: {_plain_text(', '.join(content.claim_ids))}",
                "",
            ]
        )
    lines.extend(
        [
            "## Independent verification",
            "",
            f"Case set: {_plain_text(verification['case_set_id'])} "
            f"({verification['kind']})",
            "",
            _plain_text(verification["basis"]),
            "",
            "Required cases: " + ("PASS" if verification["passed"] else "FAIL"),
            "",
        ]
    )
    for case in verification["cases"]:
        lines.extend(
            [
                f"- **{_plain_text(case['case_id'])}**: {case['state']}. "
                f"{_plain_text(case['rationale'])}"
            ]
        )
        if "actual" in case:
            lines.extend(
                [
                    f"  Input: {_inline_json(case['observation'])}.",
                    f"  Expected: {_inline_json(case['expected'])}.",
                    f"  Actual: {_inline_json(case['actual'])}.",
                    "  Explanation IDs: "
                    f"{_plain_text(', '.join(case['content_ids']))}.",
                ]
            )
    return "\n".join(lines) + "\n"
