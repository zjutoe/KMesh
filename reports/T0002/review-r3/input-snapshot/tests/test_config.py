"""Boundary tests for the model-structure config loader and CLI."""
from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from kmesh import cli
from kmesh.config import (
    ModelConfig,
    ConfigError,
    load_model_config,
    parse_model_config,
)

VALID_MODEL = {
    "hidden_size": 256,
    "patch_encoder_layers": 2,
    "core_layers": 6,
    "heads": 4,
    "ffn_size": 1024,
    "memory_slots_per_patch": 4,
    "workspace_tokens": 4,
    "max_clause_tokens": 48,
    "dropout": 0.1,
}


def _write_config(tmp_path: Path, body: str, name: str = "cfg.yaml") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _doc(model_lines: str) -> str:
    return f"schema_version: 1\nmodel:\n{model_lines}"


def _valid_body() -> str:
    lines = [f"  hidden_size: {VALID_MODEL['hidden_size']}",
             f"  patch_encoder_layers: {VALID_MODEL['patch_encoder_layers']}",
             f"  core_layers: {VALID_MODEL['core_layers']}",
             f"  heads: {VALID_MODEL['heads']}",
             f"  ffn_size: {VALID_MODEL['ffn_size']}",
             f"  memory_slots_per_patch: {VALID_MODEL['memory_slots_per_patch']}",
             f"  workspace_tokens: {VALID_MODEL['workspace_tokens']}",
             f"  max_clause_tokens: {VALID_MODEL['max_clause_tokens']}",
             f"  dropout: {VALID_MODEL['dropout']}"]
    return _doc("\n".join(lines))


# --- parse_model_config: valid inputs ---


def test_parse_example_values_gives_immutable_object():
    config = parse_model_config(dict(VALID_MODEL))
    assert config.hidden_size == 256 and config.dropout == 0.1
    assert config.as_dict() == VALID_MODEL
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.hidden_size = 128


def test_parse_rejects_different_example_sizes_are_legal():
    alt = dict(VALID_MODEL, hidden_size=128, heads=8)
    config = parse_model_config(alt)
    assert config.hidden_size == 128 and config.heads == 8


def test_parse_does_not_mutate_input_dict():
    original = dict(VALID_MODEL)
    snapshot = json.loads(json.dumps(original))
    parse_model_config(original)
    assert original == snapshot


def test_dropout_zero_is_legal_and_coerced_to_float():
    config = parse_model_config(dict(VALID_MODEL, dropout=0))
    assert config.dropout == 0.0 and isinstance(config.dropout, float)


# --- parse_model_config: invalid inputs ---


@pytest.mark.parametrize("field", ["hidden_size", "heads", "core_layers"])
@pytest.mark.parametrize("bad", [True, "256", 4.0, 0, -1])
def test_int_field_rejects_bool_string_float_and_nonpositive(field, bad):
    with pytest.raises(ConfigError, match=f"model\\.{field}"):
        parse_model_config(dict(VALID_MODEL, **{field: bad}))


@pytest.mark.parametrize("hidden,heads", [(256, 3), (6, 4)])
def test_hidden_size_must_be_divisible_by_heads(hidden, heads):
    with pytest.raises(ConfigError, match=r"model\.hidden_size: must be divisible by model\.heads"):
        parse_model_config(dict(VALID_MODEL, hidden_size=hidden, heads=heads))


@pytest.mark.parametrize("bad", [True, "0.1", -0.1, 1, float("nan"), float("inf")])
def test_dropout_rejects_bool_string_out_of_range_and_non_finite(bad):
    with pytest.raises(ConfigError, match=r"model\.dropout"):
        parse_model_config(dict(VALID_MODEL, dropout=bad))


def test_missing_field_is_reported():
    broken = dict(VALID_MODEL)
    del broken["heads"]
    with pytest.raises(ConfigError, match=r"model: missing required fields: heads"):
        parse_model_config(broken)


def test_unknown_field_is_reported():
    with pytest.raises(ConfigError, match=r"model: unknown fields: dropout_rate"):
        parse_model_config(dict(VALID_MODEL, dropout_rate=0.1))


def test_non_dict_model_and_non_string_keys_fail():
    with pytest.raises(ConfigError, match=r"model: expected a mapping"):
        parse_model_config([1, 2, 3])
    with pytest.raises(ConfigError, match=r"model: expected string field names"):
        parse_model_config({**VALID_MODEL, 1: "x"})  # extra int key is checked first


# --- load_model_config: strict YAML reading ---


_INVALID_CASES = [
    # duplicate key at model level (full valid document, one duplicated line)
    (_valid_body().replace("  dropout: 0.1", "  dropout: 0.1\n  dropout: 0.1"), "duplicate key"),
    # duplicate key at root level (full valid document, one duplicated line)
    (_valid_body() + "\nschema_version: 1\n", "duplicate key"),
    # plain merge key
    (_doc("  <<: {hidden_size: 256}\n  heads: 4"), "merge"),
    # multi-document
    (_valid_body() + "\n---\nrerun: false\n", "single document"),
    # unsupported tag (no execution side effects)
    (_doc("  hidden_size: !!python/tuple [1, 2]"), "python/tuple"),
    # invalid scalar constructions (PyYAML raises ValueError/KeyError, not YAMLError)
    (_valid_body().replace("  hidden_size: 256", "  hidden_size: !!int nope"), "invalid literal"),
    (_valid_body().replace("  hidden_size: 256", "  hidden_size: !!bool nope"), "'nope'"),
    (_valid_body().replace("  hidden_size: 256", "  hidden_size: 2026-99-99"), "month must be in"),
    # mapping-tagged non-mapping values
    ("schema_version: 1\nmodel: !!map nope\n", "expected a mapping node"),
    ("schema_version: 1\nmodel: !!map [a, b]\n", "expected a mapping node"),
    # syntax error
    (_doc("  hidden_size: [256"), "invalid YAML"),
    # empty file
    ("", "top-level document must be a mapping"),
    # non-mapping root
    ("- just\n- a\n- list\n", "top-level document must be a mapping"),
    # missing required root field
    ("schema_version: 1\n", "missing required top-level fields: model"),
    # unknown root-level key
    (_valid_body() + "\nrouter: {}\n", "unknown top-level fields: router"),
]


@pytest.mark.parametrize("body, reason", _INVALID_CASES)
def test_invalid_documents_are_rejected_for_the_labeled_reason(tmp_path, body, reason):
    # Each case must fail on the labeled rule (and message), not on an
    # earlier, unrelated YAML parse failure.
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError) as excinfo:
        load_model_config(path)
    message = str(excinfo.value)
    assert str(path) in message and reason in message


@pytest.mark.parametrize("version_text", ["2", "'1'", "true"])
def test_schema_version_rejects_wrong_value(tmp_path, version_text):
    # Full valid document with only the schema_version line changed.
    body = _valid_body().replace("schema_version: 1", f"schema_version: {version_text}")
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError) as excinfo:
        load_model_config(path)
    message = str(excinfo.value)
    assert str(path) in message
    assert "schema_version: expected the integer 1, got" in message


def test_scalar_anchor_and_alias_are_allowed(tmp_path):
    body = (
        "schema_version: 1\n"
        "model:\n"
        "  hidden_size: &size 256\n"
        "  patch_encoder_layers: 2\n"
        "  core_layers: 6\n"
        "  heads: 4\n"
        "  ffn_size: *size\n"
        "  memory_slots_per_patch: 4\n"
        "  workspace_tokens: 4\n"
        "  max_clause_tokens: 48\n"
        "  dropout: 0.1\n"
    )
    path = _write_config(tmp_path, body)
    config = load_model_config(path)
    assert config.hidden_size == 256 and config.ffn_size == 256


def test_load_error_messages_carry_source_path(tmp_path):
    path = _write_config(tmp_path, _valid_body())
    assert isinstance(load_model_config(path), ModelConfig)

    with pytest.raises(ConfigError, match=r"no_such_file"):
        load_model_config(tmp_path / "no_such_file.yaml")
    with pytest.raises(ConfigError, match=re.escape(str(tmp_path))):
        load_model_config(tmp_path)  # directory as file
    binary = tmp_path / "binary.yaml"
    binary.write_bytes(b"schema_version: 1\nmodel:\n  hidden_size: \xff\xfe\n")
    with pytest.raises(ConfigError, match=r"not valid UTF-8"):
        load_model_config(binary)


def test_full_experiment_document_is_not_accepted(tmp_path):
    # A complete §8.3-style experiment config has extra top-level keys and
    # must not be silently reduced to the model fragment.
    body = _valid_body() + "\nrouter:\n  enabled: true\n"
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError, match=r"unknown top-level fields: router"):
        load_model_config(path)


# --- CLI ---


def _read(stdout: str) -> dict:
    return json.loads(stdout)


def test_cli_valid_output_comes_from_loader(tmp_path, capsys):
    path = _write_config(tmp_path, _valid_body())
    assert cli.main(["config", "validate-model", "--config", str(path)]) == 0
    out = capsys.readouterr()
    payload = _read(out.out)
    assert out.err == ""
    assert payload == {
        "schema_version": 1,
        "validation_scope": "model_only",
        "model": load_model_config(path).as_dict(),
    }


def test_cli_invalid_field_exits_1_with_reason(tmp_path, capsys):
    path = _write_config(tmp_path, _valid_body().replace("heads: 4", "heads: 3"))
    assert cli.main(["config", "validate-model", "--config", str(path)]) == 1
    out = capsys.readouterr()
    assert out.out == ""
    assert str(path) in out.err and "model.hidden_size" in out.err
    assert "Traceback" not in out.err


def test_cli_io_errors_exit_1_without_fake_report(tmp_path, capsys):
    for target in (tmp_path / "missing.yaml", tmp_path):
        assert cli.main(["config", "validate-model", "--config", str(target)]) == 1
        out = capsys.readouterr()
        assert out.out == "" and str(target) in out.err


def test_help_does_not_call_loader_or_collector(monkeypatch, capsys):
    def boom():
        raise AssertionError("loader/collector must not run for --help")

    # Patch the call sites the CLI module actually invokes by name.
    monkeypatch.setattr(cli, "load_model_config", boom)
    monkeypatch.setattr(cli, "collect_environment", boom)
    assert cli.main(["--help"]) == 0
    assert cli.main(["config", "--help"]) == 0
    assert cli.main(["config", "validate-model", "--help"]) == 0
    out = capsys.readouterr().out
    assert "validate-model" in out and "--config" in out


def test_config_argument_errors_exit_2(capsys):
    for argv in (["config"], ["config", "validate-model"], ["config", "bogus"], ["bogus"]):
        assert cli.main(argv) == 2
        assert "Traceback" not in capsys.readouterr().err


def test_config_validation_does_not_import_torch(tmp_path):
    path = _write_config(tmp_path, _valid_body())
    probe = (
        "import sys; from kmesh.cli import main; rc = main(['config', 'validate-model', "
        f"'--config', {str(path)!r}]); print('TORCH_' + ('loaded' if 'torch' in sys.modules else 'absent')); "
        "raise SystemExit(rc)"
    )
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0
    assert "TORCH_absent" in result.stdout


# --- Round-2 regressions (R1-R3) ---


def _validate_model_probe(path: str) -> str:
    return (
        "from kmesh.cli import main\n"
        f"raise SystemExit(main(['config', 'validate-model', '--config', {str(path)!r}]))\n"
    )


@pytest.mark.parametrize(
    "body",
    [
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!int nope"),
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!bool nope"),
        _valid_body().replace("  hidden_size: 256", "  hidden_size: 2026-99-99"),
        "schema_version: 1\nmodel: !!map nope\n",
        "schema_version: 1\nmodel: !!map [a, b]\n",
    ],
)
def test_cli_yaml_construction_errors_exit_1_without_traceback(tmp_path, body):
    path = _write_config(tmp_path, body)
    result = subprocess.run(
        [sys.executable, "-c", _validate_model_probe(path)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert str(path) in result.stderr and "invalid YAML" in result.stderr


def test_help_and_doctor_run_when_pyyaml_is_missing(tmp_path):
    """R1: fresh subprocess with the yaml import blocked and the PyYAML
    distribution reported as missing, before anything from kmesh.cli.
    """
    out = tmp_path / "doctor-report.json"
    script = (
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
    result = subprocess.run(
        [sys.executable, "-c", script, str(out)], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert "help_rc 0" in result.stdout
    assert "doctor_rc 1" in result.stdout
    assert "status error" in result.stdout
    assert "pyyaml None" in result.stdout
    assert "help_ok True" in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("bad", [10**400, -(10**400)])
def test_dropout_rejects_ints_too_large_for_float_conversion(bad):
    with pytest.raises(ConfigError, match=r"model\.dropout: must be finite and in"):
        parse_model_config(dict(VALID_MODEL, dropout=bad))


def test_cli_dropout_overflow_exits_1_with_reason(tmp_path):
    path = _write_config(tmp_path, _valid_body().replace("dropout: 0.1", f"dropout: {10**400}"))
    result = subprocess.run(
        [sys.executable, "-c", _validate_model_probe(path)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert str(path) in result.stderr and "model.dropout" in result.stderr


@pytest.mark.parametrize(
    "body",
    [
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!int ''"),
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!float ''"),
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!timestamp nope"),
        _valid_body().replace("  dropout: 0.1", '  dropout: !!float "' + "0:" * 200 + '0"'),
    ],
)
def test_builtin_constructor_faults_raise_config_error(tmp_path, body):
    # PyYAML 6.0.3 built-in constructors raise non-YAMLError exceptions on
    # these inputs (IndexError on empty !!int/!!float, AttributeError on an
    # unmatched !!timestamp, OverflowError on a sexagesimal float whose
    # base-60 base overflows float range); load_model_config must convert
    # them to ConfigError instead of letting them escape.
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_model_config(path)


@pytest.mark.parametrize(
    "body",
    [
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!int ''"),
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!float ''"),
        _valid_body().replace("  hidden_size: 256", "  hidden_size: !!timestamp nope"),
        _valid_body().replace("  dropout: 0.1", '  dropout: !!float "' + "0:" * 200 + '0"'),
    ],
)
def test_cli_builtin_constructor_faults_exit_1_without_traceback(tmp_path, body):
    path = _write_config(tmp_path, body)
    result = subprocess.run(
        [sys.executable, "-c", _validate_model_probe(path)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert str(path) in result.stderr
    assert "invalid YAML" in result.stderr
