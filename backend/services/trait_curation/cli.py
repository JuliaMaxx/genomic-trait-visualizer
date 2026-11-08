"""Run from the repository root: python -m backend.services.trait_curation.cli."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.models.curation import ReviewAction
from backend.services.trait_curation.validation import validate_review_readiness
from backend.services.trait_curation.workflow import (
    ReviewScope,
    get_snapshot,
    initialize_workspace,
    inspect_item,
    load_dossier,
    record_decision,
    revise_workspace,
    workspace_history,
    workspace_status,
    write_json_new,
)


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def _print_status(status: dict[str, Any]) -> None:
    ready = "yes" if status["ready_for_stage4"] else "no"
    print(f"Revision {status['revision']} | Ready for Stage 4: {ready}")
    for item in status["items"]:
        print(f"{item['scope']:8} {item['target_id']}: {item['state']}")
        if item["blocked_by"]:
            print(f"  Needs approval: {', '.join(item['blocked_by'])}")
    for error in status["structural_errors"]:
        print(f"Structure: {error}")
    stale = [
        decision for decision in status["decisions"] if decision["state"] == "stale"
    ]
    print(f"Stale historical decisions: {len(stale)}")
    for decision in stale:
        print(
            f"  {decision['scope']}:{decision['target_id']} "
            f"{decision['action']} at revision {decision['candidate_revision']} "
            f"({decision['decision_id']})"
        )
    print(
        "Readiness records human review; it does not publish or prove scientific truth."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline scientific dossier review")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a new workspace from a dossier")
    init.add_argument("dossier", type=Path)
    init.add_argument("workspace", type=Path)
    init.add_argument("--reason", default="Initial dossier imported for manual review.")

    validate = commands.add_parser("validate", help="Validate a dossier or workspace")
    validate.add_argument("path", type=Path)
    validate.add_argument(
        "--revision", type=int, help="Workspace revision (default: latest)"
    )

    inspect = commands.add_parser(
        "inspect", help="Display a dossier or a review target"
    )
    inspect.add_argument("workspace", type=Path)
    inspect.add_argument("scope", nargs="?", choices=list(ReviewScope))
    inspect.add_argument("target", nargs="?")
    inspect.add_argument("--revision", type=int)
    inspect.add_argument(
        "--output", type=Path, help="Write JSON to a new file for editing"
    )

    decide = commands.add_parser(
        "decide", help="Record a decision for inspected information"
    )
    decide.add_argument("workspace", type=Path)
    decide.add_argument("scope", choices=list(ReviewScope))
    decide.add_argument("target")
    decide.add_argument("action", choices=list(ReviewAction))
    decide.add_argument("--reviewer", required=True)
    decide.add_argument("--rationale", required=True)
    decide.add_argument("--revision", required=True, type=int)
    decide.add_argument("--fingerprint", required=True, help="SHA-256 shown by inspect")

    revise = commands.add_parser(
        "revise", help="Save a corrected dossier as the next revision"
    )
    revise.add_argument("workspace", type=Path)
    revise.add_argument("dossier", type=Path)
    revise.add_argument("--reason", required=True)

    status = commands.add_parser(
        "status", help="Show effective approvals and remaining work"
    )
    status.add_argument("workspace", type=Path)
    status.add_argument(
        "--json", action="store_true", help="Include full decision details"
    )

    history = commands.add_parser(
        "history", help="List preserved revisions and decisions"
    )
    history.add_argument("workspace", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            snapshot = initialize_workspace(
                args.workspace, load_dossier(args.dossier), args.reason
            )
            print(
                f"Initialized {args.workspace} at revision "
                f"{snapshot.dossier.candidate.revision}"
            )
        elif args.command == "validate":
            if not args.path.is_dir() and args.revision is not None:
                raise ValueError("--revision applies only to a workspace")
            dossier = (
                get_snapshot(args.path, args.revision).dossier
                if args.path.is_dir()
                else load_dossier(args.path)
            )
            _print_json(
                {
                    "valid_draft": True,
                    "readiness_structure_errors": validate_review_readiness(dossier),
                    "note": "Structure and references checked; no scientific approval.",
                }
            )
        elif args.command == "inspect":
            if (args.scope is None) != (args.target is None):
                raise ValueError(
                    "Supply both scope and target, or neither to inspect the dossier"
                )
            dossier = get_snapshot(args.workspace, args.revision).dossier
            output = (
                inspect_item(dossier, ReviewScope(args.scope), args.target)
                if args.scope
                else dossier.model_dump(mode="json")
            )
            if args.output:
                write_json_new(args.output, output)
                print(f"Wrote {args.output}")
            else:
                _print_json(output)
        elif args.command == "decide":
            dossier = get_snapshot(args.workspace).dossier
            inspected = inspect_item(dossier, ReviewScope(args.scope), args.target)
            # Show the complete payload/dependencies, even when the decision is refused.
            _print_json(inspected)
            decision = record_decision(
                args.workspace,
                ReviewScope(args.scope),
                args.target,
                ReviewAction(args.action),
                args.reviewer,
                args.rationale,
                args.revision,
                args.fingerprint,
            )
            _print_json({"recorded_decision": decision.model_dump(mode="json")})
        elif args.command == "revise":
            snapshot = revise_workspace(
                args.workspace, load_dossier(args.dossier), args.reason
            )
            print(
                f"Saved revision {snapshot.dossier.candidate.revision}: "
                f"{snapshot.reason}"
            )
        elif args.command == "status":
            status = workspace_status(args.workspace)
            if args.json:
                _print_json(status)
            else:
                _print_status(status)
        elif args.command == "history":
            _print_json(workspace_history(args.workspace))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
