#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SuiteResult:
    suite: str
    ok: bool
    details: dict[str, Any]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def run_roundtrip(args: argparse.Namespace) -> SuiteResult:
    # Placeholder: sidecar invocation + HOS upload goes here.
    return SuiteResult(
        suite="roundtrip",
        ok=True,
        details={"note": "skeleton only", "corpus": args.corpus},
    )


def run_mutation_hook(args: argparse.Namespace) -> SuiteResult:
    # Placeholder: drive `hcp/document/applyMutations` and validate emitted scene graph RPCs.
    return SuiteResult(
        suite="mutation-hook",
        ok=True,
        details={"note": "skeleton only", "seed": args.seed, "mutations": args.mutations},
    )


def run_drc(args: argparse.Namespace) -> SuiteResult:
    # Placeholder: sidecar-specific DRC invocation + normalization + golden comparison.
    return SuiteResult(
        suite="drc",
        ok=True,
        details={"note": "skeleton only", "corpus": args.corpus, "goldens": args.goldens},
    )


def run_simulation_stability(args: argparse.Namespace) -> SuiteResult:
    # Placeholder: simulation dispatcher integration + tolerance comparison.
    return SuiteResult(
        suite="simulation-stability",
        ok=True,
        details={"note": "skeleton only", "corpus": args.corpus, "goldens": args.goldens},
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="run_suite.py")
    sub = parser.add_subparsers(dest="suite", required=True)

    p1 = sub.add_parser("roundtrip")
    p1.add_argument("--corpus", required=True)
    p1.add_argument("--out", default="out/regression/roundtrip.json")
    p1.set_defaults(_fn=run_roundtrip)

    p2 = sub.add_parser("mutation-hook")
    p2.add_argument("--seed", required=True)
    p2.add_argument("--mutations", type=int, default=100)
    p2.add_argument("--out", default="out/regression/mutation_hook.json")
    p2.set_defaults(_fn=run_mutation_hook)

    p3 = sub.add_parser("drc")
    p3.add_argument("--corpus", required=True)
    p3.add_argument("--goldens", required=True)
    p3.add_argument("--out", default="out/regression/drc.json")
    p3.set_defaults(_fn=run_drc)

    p4 = sub.add_parser("simulation-stability")
    p4.add_argument("--corpus", required=True)
    p4.add_argument("--goldens", required=True)
    p4.add_argument("--out", default="out/regression/simulation_stability.json")
    p4.set_defaults(_fn=run_simulation_stability)

    args = parser.parse_args()
    result: SuiteResult = args._fn(args)

    _write_json(Path(args.out), asdict(result))
    if not result.ok:
        print(json.dumps(asdict(result), indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

