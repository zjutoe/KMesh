"""Read-only environment collection for the ``kmesh doctor`` command.

Collects Python, platform, dependency metadata and PyTorch CUDA probe
results into a JSON-serializable dict. This module must not write files,
print, install packages, or import torch at import time.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version

_REQUIRED_PACKAGES = ("torch", "numpy", "PyYAML")
_OPTIONAL_PACKAGES = ("pytest", "pip", "setuptools")


def _read_packages(errors: list[str]) -> dict[str, str | None]:
    packages: dict[str, str | None] = {}
    for name in (*_REQUIRED_PACKAGES, *_OPTIONAL_PACKAGES):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
            if name in _REQUIRED_PACKAGES:
                errors.append(f"required package metadata not found: {name}")
        except Exception as exc:
            packages[name] = None
            errors.append(f"failed to read installation metadata for {name}: {exc!r}")
    return packages


class _CudaInfo:
    def __init__(self) -> None:
        self.runtime_version: str | None = None
        self.available: bool | None = None
        self.device_count: int | None = None
        self.devices: list[dict[str, object]] = []


def _probe_cuda(torch, cuda: _CudaInfo, errors: list[str]) -> None:
    try:
        raw_available = torch.cuda.is_available()
    except Exception as exc:
        cuda.available = None
        cuda.device_count = None
        cuda.devices = []
        errors.append(f"torch.cuda.is_available() raised: {exc!r}")
        return
    if not isinstance(raw_available, bool):
        cuda.available = None
        cuda.device_count = None
        cuda.devices = []
        errors.append(
            f"torch.cuda.is_available() returned {raw_available!r}, expected bool"
        )
        return
    cuda.available = raw_available
    if cuda.available is not True:
        if cuda.available is False:
            cuda.device_count = 0
            cuda.devices = []
        return
    try:
        count = torch.cuda.device_count()
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError(f"CUDA reported available but device_count={count!r}")
        devices: list[dict[str, object]] = []
        for index in range(count):
            props = torch.cuda.get_device_properties(index)
            name = getattr(props, "name", None)
            total = getattr(props, "total_memory", None)
            if not isinstance(name, str) or not name:
                raise ValueError(f"device {index} property 'name' is missing or not a string")
            if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
                raise ValueError(f"device {index} property 'total_memory' is not a positive integer")
            devices.append(
                {"index": index, "name": name, "total_memory_bytes": total}
            )
        cuda.device_count = count
        cuda.devices = devices
    except Exception as exc:
        # Do not treat a partially enumerated device list as a successful probe.
        cuda.available = None
        cuda.device_count = None
        cuda.devices = []
        errors.append(f"CUDA device enumeration failed: {exc!r}")


def collect_environment() -> dict[str, object]:
    """Collect a read-only, JSON-serializable environment report.

    ``status`` is ``error`` when any probe or metadata read failed,
    ``ok`` when CUDA is available, and ``cpu_only`` when torch imports
    cleanly but no CUDA device is available in this process.
    """
    errors: list[str] = []
    packages = _read_packages(errors)

    cuda = _CudaInfo()
    torch_import_ok = False
    try:
        import torch
    except Exception as exc:
        cuda.available = None
        cuda.device_count = None
        cuda.devices = []
        errors.append(f"torch import failed: {exc!r}")
    else:
        torch_import_ok = True
        try:
            runtime_raw = torch.version.cuda
        except Exception as exc:
            runtime = None
            errors.append(f"reading torch.version.cuda failed: {exc!r}")
        else:
            if runtime_raw is not None and not isinstance(runtime_raw, str):
                runtime = None
                errors.append(
                    f"torch.version.cuda={runtime_raw!r}, expected string or None"
                )
            else:
                runtime = runtime_raw
        cuda.runtime_version = runtime
        _probe_cuda(torch, cuda, errors)

    if errors:
        status = "error"
    elif cuda.available is True:
        status = "ok"
    elif cuda.available is False:
        status = "cpu_only"
    else:
        status = "error"

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "torch_import_ok": torch_import_ok,
        "cuda": {
            "runtime_version": cuda.runtime_version,
            "available": cuda.available,
            "device_count": cuda.device_count,
            "devices": cuda.devices,
        },
        "status": status,
        "errors": errors,
    }
