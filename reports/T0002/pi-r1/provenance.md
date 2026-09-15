# T0002 第 1 轮（Pi）溯源

- **实际基线**：`git rev-parse HEAD` = `2c15f6a6db71ab2839643276f43eee05cab99f15`（任务分支 `T0002-model-config`，自 master 同点分出；本任务改动执行时为工作树变更，未提交）。
- **执行前 `git status --short`**（2026-09-13）：

  ```text
   M README.md
   M docs/implementation_status.md
   M src/kmesh/cli.py
  ?? configs/
  ?? docs/handoffs/T0002-model-config.md
  ?? reports/T0002/
  ?? src/kmesh/config.py
  ?? tests/test_config.py
  ```
- **源码预检**（契约给出的只读命令，原样执行，EXIT=0）：

  ```text
  /home/mye/src/llm/KMesh/.venv/bin/python
  {'kmesh': '0.1.0', 'PyYAML': '6.0.3', 'pytest': '8.4.2'}
  /opt/anaconda3/lib/python3.13/site-packages/yaml/__init__.py
  ```
- **配置样例核对**：`configs/model_e0.yaml` 逐字来自研究计划 §8.3 `e0_v2` 的 model 区块；驱动内 `source.count("heads: 4") == 1` 预检通过。
- **使用工具与模型**：Pi + `qwen3.8-coding-27b`（本地 Ollama；会话环境 `PI_MODEL=qwen3.8-coding:27b-q8_0-64k`、`PI_BASE_URL=http://127.0.0.1:11434/v1`、`PI_REASONING_LEVEL=off`）。未换模型。
- **驱动**：`reports/T0002/run_checks.py` 为交接文档“验证方法”小节的契约驱动，逐字保存（`python` 从文档 fenced 代码块提取后写入；未做任何修改）。契约首轮命令 `.venv/bin/python reports/T0002/run_checks.py reports/T0002/pi-r1` 原样执行：**EXIT=0**，十个子检查退出码全部符合预期（module-help、config-help、model-help、module-valid、console-valid = 0；invalid-model = 1；missing-argument = 2；tests、doctor-regression、diff-check = 0），末尾输出 `PASS: T0002 verification completed`；`doctor-cpu.json` 为 `status=cpu_only`、`errors=[]`（`CUDA_VISIBLE_DEVICES=""`）。驱动自身 stdout/stderr/退出码保存为 `driver.stdout`/`driver.stderr`（空）/`driver.exit`。
- **SHA-256**：配置样例、实现/测试文件、驱动与本轮全部验证产物见 `sha256.txt`。成功 JSON 由 CLI stdout 产生（`module-valid.stdout`、`console-valid.stdout`），未手工补填。
- **卫生检查**：全部本任务新文件以单个 `\n` 结尾（`tail -c1` 逐一核对）；`tests/`、`src/`、`configs/`、`README.md`、`pyproject.toml` 无尾随空白；README 与状态文档的本地相对链接全部解析到已存在文件；驱动 `diff-check` 对已跟踪文件 `git diff --check` 通过。
- **更正记录**：本轮初我先自己写了一版更长的驱动并跑出过一份 `pi-r1` 产物；核对交接文档后发现契约本就规定了精确驱动，遂把驱动替换为与文档逐字一致的契约版本（提取后未改动）、整体删除旧 `pi-r1` 目录、用契约首轮命令重跑并留下本套产物。旧产物不保留；Pi 执行记录中已同步更正。除该驱动替换外，产品代码与测试未因此变更（替换前后的产品代码完全相同）。
- **未做**：数据、模型、训练或正式实验命令均 `not_run`；合成测试无随机采样，seed=N/A。
