# T0001 验证命令原始日志（2026-09-13）

工作目录：`/home/mye/src/llm/KMesh`。每项独立执行，格式：命令 → EXIT（退出码）、耗时（秒）、关键输出。首次 pytest 运行失败（2 failed），复跑输出见下；失败日志与首轮结果一并保留。

```text
$ git rev-parse HEAD
69984c2e99ff73cbb43de9e1e440d2b8379a9fd7   (EXIT=0)

$ git status --short            # 执行前
?? docs/handoffs/T0001-bootstrap-doctor.md   (EXIT=0)

$ timeout 60s /opt/anaconda3/bin/python3 -c 'import sys, torch, numpy, yaml, pytest; from importlib.metadata import version; print(sys.executable, sys.version); print({n: version(n) for n in ("torch", "numpy", "PyYAML", "pytest", "pip", "setuptools", "wheel")})'
/opt/anaconda3/bin/python3 3.13.9 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 19:16:10) [GCC 11.2.0]
{'torch': '2.10.0+cu126', 'numpy': '2.3.5', 'PyYAML': '6.0.3', 'pytest': '8.4.2', 'pip': '25.3', 'setuptools': '80.9.0', 'wheel': '0.45.1'}
   (EXIT=0, <60s)

$ timeout 120s /opt/anaconda3/bin/python3 -m venv --system-site-packages .venv
   (EXIT=0, 3s)
  pyvenv.cfg: home=/opt/anaconda3/bin, include-system-site-packages=true, version=3.13.9

$ timeout 120s .venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e '.[dev]'
  Successfully installed kmesh-0.1.0
   (EXIT=0, 3s)

$ timeout 60s .venv/bin/python -c 'from pathlib import Path; import kmesh; p = Path(kmesh.__file__).resolve(); print(p); assert p == Path("src/kmesh/__init__.py").resolve()'
/home/mye/src/llm/KMesh/src/kmesh/__init__.py
   (EXIT=0)

$ timeout 60s .venv/bin/python -m kmesh.cli --help       # EXIT=0，打印用法
$ timeout 60s .venv/bin/kmesh --help                     # EXIT=0，同样用法
$ timeout 60s .venv/bin/python -m kmesh.cli doctor --help  # EXIT=0

$ timeout 60s .venv/bin/python -m kmesh.cli doctor --out reports/environment.json
kmesh doctor: status=ok; report written to reports/environment.json
   (EXIT=0, 2s)

$ timeout 60s .venv/bin/kmesh doctor --out reports/T0001/environment-console.json
kmesh doctor: status=ok; report written to reports/T0001/environment-console.json
   (EXIT=0, 2s)

$ CUDA_VISIBLE_DEVICES="" timeout 60s .venv/bin/python -m kmesh.cli doctor --out reports/T0001/environment-cpu.json
kmesh doctor: status=cpu_only (no CUDA device available in this process); report written to reports/T0001/environment-cpu.json
   (EXIT=0, 2s)

$ timeout 60s .venv/bin/python - <<'PY'  (交叉核对脚本，见交接文档)
PASS: reports readable, entrypoints agree, CPU fallback explicit
   (EXIT=0)

$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout 120s .venv/bin/python -m pytest -q tests/test_doctor.py   # 首轮（实现缺陷，未通过）
14 passed, 2 failed  (EXIT=1, 1s)
  FAIL test_cli_output_path_is_directory: 测试签名漏了 monkeypatch 参数（测试自身缺陷）
  FAIL test_arg_errors_exit_2_without_file: main([]) 触发 cli.py 中 argv[0] IndexError（实现缺陷）

  # 修复 src/kmesh/cli.py 空 argv 处理与测试签名后复跑：
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout 120s .venv/bin/python -m pytest -q tests/test_doctor.py
16 passed  (EXIT=0, 1s)
  （stderr 中 PytestWarning 为 pytest 清理 /tmp 内其他项目遗留临时目录失败，与本任务测试无关）

$ timeout 60s .venv/bin/python -m pip list --format=json > reports/T0001/installed-packages.json
   (EXIT=0)

$ timeout 60s .venv/bin/python -c 'import torch, numpy, yaml; print({m.__name__: m.__file__ for m in (torch, numpy, yaml)})'
{'torch': '/opt/anaconda3/lib/python3.13/site-packages/torch/__init__.py', 'numpy': '/opt/anaconda3/lib/python3.13/site-packages/numpy/__init__.py', 'yaml': '/opt/anaconda3/lib/python3.13/site-packages/yaml/__init__.py'}
   (EXIT=0)

$ sha256sum reports/environment.json reports/T0001/environment-console.json reports/T0001/environment-cpu.json reports/T0001/installed-packages.json
a0639fe3d530d68c13491ef85d61669021f0599b825649530b86b34afa212b91  reports/environment.json
8b1ce381c609f8b1a1a402275cf9666da5a5cf1e1836c7878f1dc60bdbfcc1b9  reports/T0001/environment-console.json
a8271ceb712cb807e7d2db1aeddac26f863aa254ff55d2243619d1d7f641683d  reports/T0001/environment-cpu.json
8300a47582adb207ca7cbb0dc425430ceaf4ddb5afcc6b1cd384efa090cfd841  reports/T0001/installed-packages.json
   (EXIT=0)

$ git diff --check
（无输出）   (EXIT=0)
```

附加检查（交接文档验证方法要求）：

- 用标准库 `json` 读回三份报告并核对 `schema_version=1`、`errors==[]`、两入口稳定字段一致（忽略 `generated_at_utc`）、强制 CPU 报告 `status=cpu_only`、`cuda.available=false`、`device_count=0`、`devices==[]`：PASS（上方交叉核对脚本，EXIT=0）。
- 本任务全部新增文本文件的末尾换行与尾随空白逐文件检查：无缺失换行、无行尾空白。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 生效，pytest 仅收集 `tests/test_doctor.py` 的 16 个用例；无因 GPU 缺失而 skip 的用例（合成 fixture 覆盖 CPU/GPU/错误路径）。
- 真实 doctor 环境含 1×NVIDIA GeForce RTX 3090（24 GB），故两份真实报告为 `status=ok`；`CUDA_VISIBLE_DEVICES=""` 子进程得到 `cpu_only`，符合契约。
