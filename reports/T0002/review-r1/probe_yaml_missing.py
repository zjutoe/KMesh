"""Simulate missing PyYAML in a fresh process without changing installed packages."""
import importlib.abc
import importlib.metadata
from pathlib import Path
import sys
import types

version, command, report_path, baseline_path = sys.argv[1:]
assert "yaml" not in sys.modules


class BlockYaml(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "yaml" or fullname.startswith("yaml."):
            raise ModuleNotFoundError("review fixture: PyYAML unavailable", name="yaml")
        return None


real_version = importlib.metadata.version


def missing_yaml_version(name):
    if name == "PyYAML":
        raise importlib.metadata.PackageNotFoundError(name)
    return real_version(name)


sys.meta_path.insert(0, BlockYaml())
importlib.metadata.version = missing_yaml_version
if version == "baseline":
    module = types.ModuleType("kmesh._review_baseline_cli")
    module.__package__ = "kmesh"
    exec(compile(Path(baseline_path).read_bytes(), baseline_path, "exec"), module.__dict__)
    main = module.main
else:
    from kmesh.cli import main
argv = ["--help"] if command == "help" else ["doctor", "--out", report_path]
raise SystemExit(main(argv))
