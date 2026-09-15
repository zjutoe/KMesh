"""Round-2 development checks for R1-R3, with evidence in reports/T0002/pi-r2-dev1/.

Run from the repo root:
    .venv/bin/python reports/T0002/pi-r2-dev1/dev_checks.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PY = REPO / ".venv" / "bin" / "python"
DEV = Path(__file__).resolve().parent
RECORD: list[dict] = []


def record(check: str, detail: str) -> None:
    RECORD.append({"check": check, "detail": detail})
    print(f"[{check}] {detail}", flush=True)


def run(check: str, argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=cwd)
    tag = check.replace(" ", "-").lower()
    (DEV / f"{tag}.stdout").write_text(r.stdout)
    (DEV / f"{tag}.stderr").write_text(r.stderr)
    return r


def main() -> int:
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    checks: list[tuple[str, bool]] = []
    (DEV / "devtmp").mkdir(exist_ok=True)
    base = (REPO / "configs" / "model_e0.yaml").read_text(encoding="utf-8")

    # --- R1: yaml import blocked and PyYAML metadata reported missing in a
    # fresh subprocess, before anything from kmesh.cli is imported ---
    r1_script = (
        "import contextlib, importlib.metadata as md, io, json, sys\n"
        "from pathlib import Path\n"
        "sys.modules['yaml'] = None\n"
        "import kmesh.utils.environment as env\n"
        "def _version(name):\n"
        "    if name == 'PyYAML':\n"
        "        raise md.PackageNotFoundError(name)\n"
        "    return md.version(name)\n"
        "env.version = _version\n"
        "from kmesh import cli\n"
        "buf = io.StringIO()\n"
        "with contextlib.redirect_stdout(buf):\n"
        "    help_rc = cli.main(['--help'])\n"
        "doctor_rc = cli.main(['doctor', '--out', sys.argv[1]])\n"
        "report = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
        "print('help_rc', help_rc)\n"
        "print('doctor_rc', doctor_rc)\n"
        "print('status', report['status'])\n"
        "print('pyyaml', report['packages']['PyYAML'])\n"
        "print('help_ok', 'KMesh research toolkit' in buf.getvalue())\n"
    )
    out = DEV / "r1-doctor-report.json"
    if out.exists():
        out.unlink()
    r1 = run(
        "R1 pyyaml-missing",
        [str(PY), "-c", r1_script, str(out)],
        REPO,
    )
    r1_pass = (
        r1.returncode == 0
        and "help_rc 0" in r1.stdout
        and "doctor_rc 1" in r1.stdout
        and "status error" in r1.stdout
        and "pyyaml None" in r1.stdout
        and "help_ok True" in r1.stdout
        and "Traceback" not in r1.stderr
        and out.exists()
    )
    checks.append(("R1 help+doctor without PyYAML", r1_pass))
    record("R1", f"fresh subprocess, yaml blocked before kmesh import; exit={r1.returncode}; pass={r1_pass}")
    if not r1_pass:
        print("R1 FAILED\nSTDOUT:", r1.stdout, "\nSTDERR:", r1.stderr)

    # --- R2: the 5 construction-error bodies -> ConfigError (API) ---
    bodies = {
        "r2-int-nope": base.replace("  hidden_size: 256", "  hidden_size: !!int nope"),
        "r2-bool-nope": base.replace("  hidden_size: 256", "  hidden_size: !!bool nope"),
        "r2-bad-date": base.replace("  hidden_size: 256", "  hidden_size: 2026-99-99"),
        "r2-map-scalar": "schema_version: 1\nmodel: !!map nope\n",
        "r2-map-seq": "schema_version: 1\nmodel: !!map [a, b]\n",
    }
    for name, body in bodies.items():
        (DEV / "devtmp" / f"{name}.yaml").write_text(body)
    api_script = (
        f"from pathlib import Path\n"
        f"import sys\n"
        f"sys.path.insert(0, str(Path({str(REPO)!r}) / 'src'))\n"
        "from kmesh.config import ConfigError, load_model_config\n"
        f"out_dir = Path({str(DEV / 'devtmp')!r})\n"
        "for name in ('r2-int-nope', 'r2-bool-nope', 'r2-bad-date', 'r2-map-scalar', 'r2-map-seq'):\n"
        "    p = out_dir / (name + '.yaml')\n"
        "    try:\n"
        "        load_model_config(p)\n"
        "        print(name, 'UNCAUGHT')\n"
        "    except ConfigError as exc:\n"
        "        msg = str(exc)\n"
        "        print(name, 'CONFIGERROR path_ok=%s first_line=%s' % (str(p) in msg, msg.splitlines()[0][:100]))\n"
    )
    r2_api = run("R2 api", [str(PY), "-c", api_script], DEV)
    r2_api_pass = (
        r2_api.returncode == 0
        and all(f"{n} CONFIGERROR path_ok=True" in r2_api.stdout for n in bodies)
        and "UNCAUGHT" not in r2_api.stdout
        and "Traceback" not in r2_api.stderr
    )
    checks.append(("R2 API: 5 bodies -> ConfigError with path", r2_api_pass))
    record("R2-API", f"exit={r2_api.returncode}; pass={r2_api_pass}")
    if not r2_api_pass:
        print("R2-API FAILED\nSTDOUT:", r2_api.stdout, "\nSTDERR:", r2_api.stderr)

    # R2 CLI: rc=1, empty stdout, no traceback, path + invalid YAML reason
    r2_cli_pass = True
    for name, _body in bodies.items():
        cli_script = (
            "from kmesh.cli import main\n"
            f"raise SystemExit(main(['config', 'validate-model', '--config', {str(DEV / 'devtmp' / (name + '.yaml'))!r}]))\n"
        )
        r = run(f"R2 cli {name}", [str(PY), "-c", cli_script], REPO)
        ok = (
            r.returncode == 1
            and r.stdout == ""
            and "Traceback" not in r.stderr
            and "invalid YAML" in r.stderr
            and name in r.stderr
        )
        r2_cli_pass = r2_cli_pass and ok
        record(f"R2-CLI {name}", f"exit={r.returncode}; pass={ok}")
    checks.append(("R2 CLI: rc=1, empty stdout, no Traceback, path+reason", r2_cli_pass))

    # --- R3: overflow integers hit ConfigError before float() ---
    r3_script = (
        f"import sys\n"
        f"from pathlib import Path\n"
        f"sys.path.insert(0, str(Path({str(REPO)!r}) / 'src'))\n"
        "from kmesh.config import ConfigError, parse_model_config\n"
        "valid = {'hidden_size': 256, 'patch_encoder_layers': 2, 'core_layers': 6, 'heads': 4,\n"
        "         'ffn_size': 1024, 'memory_slots_per_patch': 4, 'workspace_tokens': 4,\n"
        "         'max_clause_tokens': 48, 'dropout': 0.1}\n"
        "for bad in (10**400, -(10**400)):\n"
        "    try:\n"
        "        parse_model_config({**valid, 'dropout': bad})\n"
        "        print(bad, 'UNCAUGHT')\n"
        "    except ConfigError as exc:\n"
        "        print(bad, 'CONFIGERROR first_line=', str(exc).splitlines()[0][:100])\n"
    )
    r3 = run("R3 overflow", [str(PY), "-c", r3_script], REPO)
    r3_pass = (
        r3.returncode == 0
        and r3.stdout.count("CONFIGERROR") == 2
        and "UNCAUGHT" not in r3.stdout
        and "model.dropout" in r3.stdout
        and "Traceback" not in r3.stderr
    )
    checks.append(("R3: 10**400 / -(10**400) -> ConfigError", r3_pass))
    record("R3", f"exit={r3.returncode}; pass={r3_pass}")
    if not r3_pass:
        print("R3 FAILED\nSTDOUT:", r3.stdout, "\nSTDERR:", r3.stderr)

    failed = [name for name, ok in checks if not ok]
    summary = {
        "started": started,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checks": [{"name": n, "passed": ok} for n, ok in checks],
        "recorded_commands": RECORD,
        "failed": failed,
        "result": "PASS" if not failed else "FAIL",
    }
    (DEV / "dev-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print()
    print(json.dumps({k: summary[k] for k in ("checks", "failed", "result")}, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
