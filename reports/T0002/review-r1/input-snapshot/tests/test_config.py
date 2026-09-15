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


@pytest.mark.parametrize(
    "body",
    [
        # duplicate key at model level, even with identical values
        _doc("  heads: 4\n  heads: 4"),
        # duplicate key at root level
        "schema_version: 1\nschema_version: 1\nmodel:\nhidden_size: 256\n"
        + "\n".join(f"  {k}: {v}" for k, v in list(VALID_MODEL.items())),
        # plain merge key
        _doc("  <<: {hidden_size: 256}\n  heads: 4"),
        # multi-document
        _valid_body() + "\n---\nrerun: false\n",
        # unsupported tag (no execution side effects)
        _doc("  hidden_size: !!python/tuple [1, 2]"),
        # syntax error
        _doc("  hidden_size: [256"),
        # empty file
        "",
        # non-mapping root
        "- just\n- a\n- list\n",
        # wrong / missing / extra root fields
        "schema_version: 1\n",
        "schema_version: 2\nmodel:\nhidden_size: 256\n",
        "schema_version: '1'\nmodel:\nhidden_size: 256\n",
        "schema_version: true\nmodel:\nhidden_size: 256\n",
        "schema_version: 1\nmodel:\nhidden_size: 256\nrouter: {}\n",
    ],
)
def test_invalid_yaml_documents_are_rejected(tmp_path, body):
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError, match=f"{re.escape(str(path))}"):
        load_model_config(path)


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
