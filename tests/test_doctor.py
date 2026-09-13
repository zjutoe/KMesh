"""Boundary tests for ``kmesh doctor``: collector, CLI entries, exit codes.

All torch behaviour is simulated with synthetic stubs and metadata is
monkeypatched, so the suite runs without a real GPU and without reading
any experimental data.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import types
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

import kmesh
import kmesh.cli as cli
from kmesh.utils import environment

REPO_ROOT = Path(__file__).resolve().parent.parent

FAKE_VERSIONS = {
    "torch": "2.10.0+cu126",
    "numpy": "2.3.5",
    "PyYAML": "6.0.3",
    "pytest": "8.4.2",
    "pip": "25.3",
    "setuptools": "80.9.0",
}


def _patch_metadata(monkeypatch, missing=(), broken=()):
    def fake_version(name):
        if name in broken:
            raise RuntimeError(f"simulated metadata failure for {name}")
        if name in missing:
            raise PackageNotFoundError(name)
        return FAKE_VERSIONS[name]

    monkeypatch.setattr(environment, "version", fake_version)


def _torch_stub(cuda_obj):
    module = types.ModuleType("torch")
    module.version = types.SimpleNamespace(cuda="12.6")
    module.cuda = cuda_obj
    return module


def _cpu_cuda():
    return types.SimpleNamespace(
        is_available=lambda: False,
        device_count=lambda: 0,
        get_device_properties=None,
    )


def _gpu_cuda(count=1, name="Fake GPU", total_memory=25769803776):
    return types.SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: count,
        get_device_properties=lambda i: types.SimpleNamespace(
            name=name, total_memory=total_memory
        ),
    )


# --- collect_environment: CPU and GPU shapes ---


def test_cpu_report_fields_and_status(monkeypatch):
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(_cpu_cuda()))
    report = environment.collect_environment()
    assert report["schema_version"] == 1
    assert report["generated_at_utc"].endswith("+00:00")
    assert report["python_executable"] == sys.executable
    assert report["python_version"] == platform.python_version()
    assert report["packages"] == FAKE_VERSIONS
    assert report["torch_import_ok"] is True
    assert report["cuda"] == {
        "runtime_version": "12.6",
        "available": False,
        "device_count": 0,
        "devices": [],
    }
    assert report["status"] == "cpu_only"
    assert report["errors"] == []
    json.dumps(report)  # must stay JSON-serializable


def test_single_gpu_report_fields(monkeypatch):
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(_gpu_cuda()))
    report = environment.collect_environment()
    assert report["torch_import_ok"] is True
    assert report["cuda"]["runtime_version"] == "12.6"
    assert report["cuda"]["available"] is True
    assert report["cuda"]["device_count"] == 1
    devices = report["cuda"]["devices"]
    assert len(devices) == 1
    assert devices[0]["index"] == 0
    assert devices[0]["name"] == "Fake GPU"
    assert isinstance(devices[0]["total_memory_bytes"], int)
    assert devices[0]["total_memory_bytes"] > 0
    assert report["status"] == "ok"
    assert report["errors"] == []


# --- collect_environment: failure semantics ---


def test_missing_required_dependency_is_error(monkeypatch):
    _patch_metadata(monkeypatch, missing=("numpy",))
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(_cpu_cuda()))
    report = environment.collect_environment()
    assert report["packages"]["numpy"] is None
    assert report["status"] == "error"
    assert any("numpy" in err for err in report["errors"])


def test_missing_tool_metadata_is_null_without_error(monkeypatch):
    _patch_metadata(monkeypatch, missing=("pytest", "pip", "setuptools"))
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(_cpu_cuda()))
    report = environment.collect_environment()
    assert report["packages"]["pytest"] is None
    assert report["packages"]["pip"] is None
    assert report["packages"]["setuptools"] is None
    assert report["status"] == "cpu_only"
    assert report["errors"] == []


def test_unexpected_metadata_exception_is_error(monkeypatch):
    _patch_metadata(monkeypatch, broken=("pip",))
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(_cpu_cuda()))
    report = environment.collect_environment()
    assert report["packages"]["pip"] is None
    assert report["status"] == "error"
    assert any("pip" in err for err in report["errors"])


def test_torch_import_failure(monkeypatch):
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", None)  # makes `import torch` raise
    report = environment.collect_environment()
    assert report["torch_import_ok"] is False
    assert report["cuda"]["runtime_version"] is None
    assert report["cuda"]["available"] is None
    assert report["cuda"]["device_count"] is None
    assert report["cuda"]["devices"] == []
    assert report["status"] == "error"
    assert any("torch" in err for err in report["errors"])


def test_cuda_query_exception_is_error(monkeypatch):
    bad_cuda = types.SimpleNamespace(
        is_available=lambda: (_ for _ in ()).throw(RuntimeError("probe failed")),
        device_count=None,
        get_device_properties=None,
    )
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(bad_cuda))
    report = environment.collect_environment()
    assert report["torch_import_ok"] is True
    assert report["cuda"]["runtime_version"] == "12.6"
    assert report["cuda"]["available"] is None
    assert report["cuda"]["device_count"] is None
    assert report["cuda"]["devices"] == []
    assert report["status"] == "error"
    assert report["errors"]


def test_available_true_but_count_zero_is_error(monkeypatch):
    inconsistent = types.SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: 0,
        get_device_properties=None,
    )
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(inconsistent))
    report = environment.collect_environment()
    assert report["cuda"]["available"] is None
    assert report["cuda"]["device_count"] is None
    assert report["cuda"]["devices"] == []
    assert report["status"] == "error"
    assert report["errors"]


def test_device_properties_exception_is_error(monkeypatch):
    bad_props = types.SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: 1,
        get_device_properties=lambda i: (_ for _ in ()).throw(RuntimeError("props")),
    )
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(bad_props))
    report = environment.collect_environment()
    # No partial enumeration may be reported as a successful probe.
    assert report["cuda"]["available"] is None
    assert report["cuda"]["device_count"] is None
    assert report["cuda"]["devices"] == []
    assert report["status"] == "error"


# --- lazy import of torch ---


def test_importing_package_and_cli_does_not_load_torch():
    code = (
        "import sys\n"
        "assert 'torch' not in sys.modules, 'torch must not be preloaded'\n"
        "import kmesh, kmesh.cli\n"
        "rc = kmesh.cli.main(['--help'])\n"
        "assert rc == 0\n"
        "assert 'torch' not in sys.modules, 'help must not import torch'\n"
        "print('NO_TORCH_OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "NO_TORCH_OK" in result.stdout


def test_help_does_not_call_collector(monkeypatch, capsys):
    def boom():
        raise AssertionError("collector must not run for --help")

    monkeypatch.setattr(environment, "collect_environment", boom)
    assert cli.main(["--help"]) == 0
    assert cli.main(["doctor", "--help"]) == 0
    out = capsys.readouterr().out
    assert "doctor" in out and "--out" in out


# --- CLI end-to-end with the real collector + synthetic deps ---


def _run_doctor(monkeypatch, torch_stub, out_path):
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", torch_stub)
    return cli.main(["doctor", "--out", str(out_path)])


def _read(out_path):
    return json.loads(Path(out_path).read_text(encoding="utf-8"))


def test_cli_cpu_and_nested_dir(monkeypatch, tmp_path):
    out = tmp_path / "a" / "b" / "report.json"  # nested dirs must be created
    rc = _run_doctor(monkeypatch, _torch_stub(_cpu_cuda()), out)
    assert rc == 0
    report = _read(out)
    assert report["status"] == "cpu_only"
    assert report["cuda"]["available"] is False
    assert report["cuda"]["device_count"] == 0
    assert report["cuda"]["devices"] == []
    assert text_ends_with_newline(out)


def test_cli_gpu(monkeypatch, tmp_path):
    out = tmp_path / "report.json"
    rc = _run_doctor(monkeypatch, _torch_stub(_gpu_cuda()), out)
    assert rc == 0
    report = _read(out)
    assert report["status"] == "ok"
    assert report["cuda"]["device_count"] == 1
    assert report["cuda"]["devices"][0]["total_memory_bytes"] > 0


def test_cli_error_writes_report_and_exits_1(monkeypatch, tmp_path, capsys):
    inconsistent = types.SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: 0,
        get_device_properties=None,
    )
    out = tmp_path / "report.json"
    rc = _run_doctor(monkeypatch, _torch_stub(inconsistent), out)
    assert rc == 1
    report = _read(out)  # diagnostic report must still be saved
    assert report["status"] == "error"
    assert report["errors"]
    assert "error" in capsys.readouterr().err


def test_cli_output_path_is_directory(monkeypatch, tmp_path, capsys):
    _patch_metadata(monkeypatch)
    monkeypatch.setitem(sys.modules, "torch", _torch_stub(_cpu_cuda()))
    existing_dir = tmp_path / "adir"
    existing_dir.mkdir()
    rc = cli.main(["doctor", "--out", str(existing_dir)])
    assert rc != 0
    err = capsys.readouterr().err
    assert str(existing_dir) in err
    assert existing_dir.is_dir()


def test_arg_errors_exit_2_without_file(tmp_path):
    out = tmp_path / "report.json"
    for argv in ([], ["train"], ["doctor"], ["doctor", "--out"], ["doctor", str(out), "--wrong"]):
        assert cli.main(argv) == 2, f"argv={argv}"
    assert not out.exists()


def text_ends_with_newline(path):
    return path.read_bytes().endswith(b"\n")
