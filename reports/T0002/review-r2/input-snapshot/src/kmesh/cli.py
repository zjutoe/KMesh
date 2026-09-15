"""Command line interface for KMesh.

Subcommands: ``doctor --out PATH`` (read-only environment report) and
``config validate-model --config PATH`` (model-fragment validation).
Importing this module must not import torch or probe the environment, and
``--help`` never collects or loads anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_model_config
from .utils.environment import collect_environment

_KNOWN_SUBCOMMANDS = {"doctor", "config"}


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
    config = subparsers.add_parser(
        "config", help="validate KMesh configuration fragments"
    )
    config_subparsers = config.add_subparsers(dest="config_command", required=True)
    validate_model = config_subparsers.add_parser(
        "validate-model", help="validate the model section of a config file"
    )
    validate_model.add_argument(
        "--config", required=True, help="path to a config file with schema_version 1"
    )
    return parser


def _write_report(report: dict[str, object], out: Path) -> None:
    if out.is_dir():
        raise IsADirectoryError(f"output path is a directory: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def _doctor(args: argparse.Namespace) -> int:
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


def _validate_model(config_path: str) -> int:
    try:
        model = load_model_config(config_path)
    except ConfigError as exc:
        print(f"config validate-model: {exc}", file=sys.stderr)
        return 1
    payload = {
        "schema_version": 1,
        "validation_scope": "model_only",
        "model": model.as_dict(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code (0 ok, 1 error, 2 arg error)."""
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

    if args.command == "doctor":
        return _doctor(args)
    if args.command == "config":
        if args.config_command == "validate-model":
            return _validate_model(args.config)
        print("kmesh: missing config subcommand; expected 'validate-model'",
              file=sys.stderr)
        return 2
    return 2  # unreachable: argparse enforces the subcommand choices


if __name__ == "__main__":
    raise SystemExit(main())
