"""Command line interface for KMesh.

Only ``doctor --out PATH`` is implemented. Importing this module must not
import torch or probe the environment; ``--help`` never collects anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .utils.environment import collect_environment

_KNOWN_SUBCOMMANDS = {"doctor"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kmesh", description="KMesh research toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser(
        "doctor", help="collect a read-only JSON environment report"
    )
    doctor.add_argument(
        "--out", required=True, help="path of the JSON report to write"
    )
    return parser


def _write_report(report: dict[str, object], out: Path) -> None:
    if out.is_dir():
        raise IsADirectoryError(f"output path is a directory: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    if not argv or (
        argv[0] not in _KNOWN_SUBCOMMANDS and argv[0] not in ("--help", "-h")
    ):
        cmd = argv[0] if argv else "<none>"
        print(
            f"kmesh: missing or unknown subcommand {cmd!r}; "
            f"expected one of: {', '.join(sorted(_KNOWN_SUBCOMMANDS))}",
            file=sys.stderr,
        )
        return 2
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 0 for --help and 2 for argument errors; convert to a
        # return value so callers can rely on the int contract.
        code = exc.code if isinstance(exc.code, int) else 2
        return 0 if code == 0 else 2

    if args.command != "doctor":
        print("kmesh: missing subcommand; expected 'doctor'", file=sys.stderr)
        return 2

    report = collect_environment()
    out = Path(args.out)
    try:
        _write_report(report, out)
    except OSError as exc:
        print(f"kmesh doctor: failed to write report to {out}: {exc}", file=sys.stderr)
        return 1
    except (TypeError, ValueError) as exc:
        print(f"kmesh doctor: report serialization failed: {exc!r}", file=sys.stderr)
        return 1

    status = report["status"]
    if status == "error":
        reasons = "; ".join(report["errors"]) if report["errors"] else "unknown"
        print(f"kmesh doctor: status=error ({reasons}) report saved to {out}",
              file=sys.stderr)
        return 1
    if status == "cpu_only":
        print(
            "kmesh doctor: status=cpu_only (no CUDA device available in this "
            f"process); report written to {out}"
        )
    else:
        print(f"kmesh doctor: status=ok; report written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
