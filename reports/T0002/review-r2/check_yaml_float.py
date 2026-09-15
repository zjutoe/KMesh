"""One additional input-boundary probe from the SafeConstructor source review."""
import json
from pathlib import Path
import subprocess
import sys

from kmesh.config import ConfigError, load_model_config

root = Path.cwd()
run = root / "reports/T0002/review-r2/yaml-float"
run.mkdir(exist_ok=False)
source = (root / "configs/model_e0.yaml").read_text()
scalar = "0:" * 200 + "0"
path = run / "sexagesimal.yaml"
path.write_text(source.replace("dropout: 0.1", f"dropout: !!float '{scalar}'"))
try:
    value = load_model_config(path)
except Exception as exc:
    api = dict(exception=type(exc).__name__, message=str(exc), controlled=isinstance(exc, ConfigError))
else:
    api = dict(exception=None, value=value.as_dict(), controlled=False)
argv = [sys.executable, "-m", "kmesh.cli", "config", "validate-model", "--config", str(path)]
p = subprocess.run(argv, capture_output=True, timeout=60, cwd=root)
(run / "cli.stdout").write_bytes(p.stdout)
(run / "cli.stderr").write_bytes(p.stderr)
result = dict(argv=argv, scalar_characters=len(scalar), api=api, exit_code=p.returncode,
              stdout_empty=not p.stdout, traceback=b"Traceback" in p.stderr)
(run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
passed = api["controlled"] and p.returncode == 1 and not p.stdout and not result["traceback"]
print(json.dumps(result, indent=2))
raise SystemExit(0 if passed else 1)
