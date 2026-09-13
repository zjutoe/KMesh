# T0001 第 2 轮（needs_changes 返工）验证日志

执行：2026-09-13，Pi + `qwen3.8-coding:27b`。工作目录 `/home/mye/src/llm/KMesh`，分支 `T0001-bootstrap-doctor`，返工基线提交 `dcbdaa5`（Codex 第 1 轮冻结提交）。

返工范围（仅 R1–R3，与 Codex 要求对应）：

- R1：`src/kmesh/utils/environment.py` —— 读取 `torch.version.cuda` 包裹异常捕获，非 str/None 记 error 并置 `runtime_version=null`，保留 `torch_import_ok=true` 与其他可独立取得的信息；`is_available()` 要求严格 bool、`device_count()` 要求非 bool 的正整数，移除 `bool()`/`int()` 强制转换；探得无效值时按原契约清空 `available`/`device_count`/`devices` 并保留已取得 runtime。
- R2：`tests/test_doctor.py` —— help 回归 guard 改 patch `cli.collect_environment`（CLI 按名导入的真实调用位置）。
- R3：`README.md:53` —— 安装命令改为 `-e '.[dev]'`。
- 新增测试：`missing_torch_version_attribute`、`invalid_cuda_runtime_type`、`invalid_is_available_return`（×3）、`invalid_device_count`（×3）、`cli_broken_torch` 共 9 个用例；测试总数 16 → 25。

命令与结果（完整 stdout 存于本目录）：

```text
$ timeout 60s .venv/bin/python -c 'from pathlib import Path; import kmesh; ...assert p == Path("src/kmesh/__init__.py").resolve()'
   EXIT=0

$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout 120s .venv/bin/python -m pytest -q tests/test_doctor.py --basetemp $(pwd)/reports/T0001/pi-r2/pytest-tmp
25 passed in 0.17s   EXIT=0；pytest.stderr.txt 为空
   （basetemp 为本轮独占、执行前不存在的新路径，未与首轮/review-r1 证据目录共用）

R2 guard 有效性自校验（证明测试能拦截真实回归）：
  1. 临时在 src/kmesh/cli.py 的 _parse_args 注入一行 collect_environment()（模拟 help 路径回归），
     跑 `pytest -k test_help_does_not_call_collector`：`1 failed`（AssertionError: collector must not run for --help），
     即注入回归后测试如预期失败；
  2. `git checkout -- src/kmesh/cli.py` 恢复，`grep -c 'TEMP regression'` = 0，随后全量 25 passed。

$ .venv/bin/python -m kmesh.cli --help            EXIT=0
$ .venv/bin/kmesh --help                          EXIT=0
$ .venv/bin/python -m kmesh.cli doctor --help     EXIT=0

$ .venv/bin/python -m kmesh.cli doctor --out reports/T0001/pi-r2/environment-module.json    EXIT=0
$ .venv/bin/kmesh doctor --out reports/T0001/pi-r2/environment-console.json                 EXIT=0
$ CUDA_VISIBLE_DEVICES="" .venv/bin/python -m kmesh.cli doctor --out reports/T0001/pi-r2/environment-cpu.json   EXIT=0

交叉核对（标准库 json 读回，忽略 generated_at_utc）：
   两份真实报告 schema_version=1、errors=[]、稳定字段一致；module/console 状态为 ok/cpu_only，
   强制 CPU 报告 status=cpu_only、available=false、device_count=0、devices=[]。打印 PASS，EXIT=0

$ zsh -f -c "print -r -- '.[dev]'"     EXIT=0，stdout 原样输出 '.[dev]'（见 readme-zsh-quote.stdout.txt），
   确认 README 修正后的参数在 zsh 下原样传递

$ sha256sum reports/T0001/pi-r2/environment-*.json   → sha256.txt
99548c00be315c818d352667ce6860ff2c457a3af85db33b58fae4896b30c39a  reports/T0001/pi-r2/environment-module.json
7bdeef63ef40bd1f6bdc16c5733f6ce9b766b5d7027a81d7fee824f090d9b7e7  reports/T0001/pi-r2/environment-console.json
3201e6353648fdf12f2cd68104255eccc2607e3bfb98c8fdda8cb44e7ec30405  reports/T0001/pi-r2/environment-cpu.json

$ git diff --check   无输出，EXIT=0
```

未覆盖项说明：按 Codex 要求未重新创建 venv、未重复安装（本轮为文档修复）；未在 `review-r1/` 或首轮历史目录内重跑复现脚本；首轮与 review-r1 产物保持原样。失败/阻塞：无。
