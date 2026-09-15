"""Strict, read-only loading of the model-structure fragment.

This module validates only the ``model`` block of an experiment config
(research plan §8.3). It never imports torch, never constructs a model
and never fills in defaults: every field is required and typed exactly.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "ConfigError",
    "ModelConfig",
    "load_model_config",
    "parse_model_config",
]

CONFIG_SCHEMA_VERSION = 1

_INT_FIELDS = (
    "hidden_size",
    "patch_encoder_layers",
    "core_layers",
    "heads",
    "ffn_size",
    "memory_slots_per_patch",
    "workspace_tokens",
    "max_clause_tokens",
)


class ConfigError(ValueError):
    """Raised when a config file cannot be read, parsed or validated.

    The message always carries the source path (for file-level failures)
    or the field path, plus the concrete reason.
    """


@dataclass(frozen=True)
class ModelConfig:
    """Immutable, fully validated ``model`` block (plan §8.3)."""

    hidden_size: int
    patch_encoder_layers: int
    core_layers: int
    heads: int
    ffn_size: int
    memory_slots_per_patch: int
    workspace_tokens: int
    max_clause_tokens: int
    dropout: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_model_config(value: object) -> ModelConfig:
    """Validate the inner ``model`` mapping and build a ``ModelConfig``.

    ``value`` must be the mapping under the ``model`` key, not the whole
    YAML document. The input is never mutated; failures raise
    ``ConfigError`` with the offending field path.
    """
    if not isinstance(value, dict):
        raise ConfigError(f"model: expected a mapping of model fields, got {type(value).__name__}")
    for key in value:
        if not isinstance(key, str):
            raise ConfigError(f"model: expected string field names, got {type(key).__name__}")
    missing = [name for name in _INT_FIELDS + ("dropout",) if name not in value]
    if missing:
        raise ConfigError(f"model: missing required fields: {', '.join(missing)}")
    unknown = [key for key in value if key not in _INT_FIELDS and key != "dropout"]
    if unknown:
        raise ConfigError(f"model: unknown fields: {', '.join(sorted(unknown))}")

    ints: dict[str, int] = {}
    for name in _INT_FIELDS:
        raw = value[name]
        if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
            raise ConfigError(f"model.{name}: expected a positive integer, got {raw!r}")
        ints[name] = raw
    if ints["hidden_size"] % ints["heads"] != 0:
        raise ConfigError("model.hidden_size: must be divisible by model.heads")

    raw_dropout = value["dropout"]
    if isinstance(raw_dropout, bool) or not isinstance(raw_dropout, (int, float)):
        raise ConfigError(f"model.dropout: expected a number in [0, 1), got {raw_dropout!r}")
    dropout = float(raw_dropout)
    if not math.isfinite(dropout) or not 0.0 <= dropout < 1.0:
        raise ConfigError(f"model.dropout: must be finite and in [0, 1), got {raw_dropout!r}")

    return ModelConfig(dropout=dropout, **ints)


class _StrictModelLoader(yaml.SafeLoader):
    """SafeLoader subclass that rejects duplicate keys, non-string keys and merge keys.

    Only this class is affected; the global SafeLoader is untouched.
    """


def _construct_no_duplicate_mapping(self: yaml.SafeLoader, node: yaml.Node, deep: bool = False) -> dict:
    seen: set[str] = set()
    for key_node, _value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ConfigError(f"mapping at line {node.start_mark.line + 1}: merge tag is not supported")
        key = self.construct_object(key_node, deep=deep)
        if key == "<<":
            raise ConfigError(f"mapping at line {node.start_mark.line + 1}: merge key '<<' is not supported")
        if not isinstance(key, str):
            raise ConfigError(
                f"mapping at line {node.start_mark.line + 1}: expected a string key, got {type(key).__name__}"
            )
        if key in seen:
            raise ConfigError(f"mapping at line {node.start_mark.line + 1}: duplicate key {key!r}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(self, node, deep)


_StrictModelLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_no_duplicate_mapping
)


def load_model_config(path: str | Path) -> ModelConfig:
    """Read and validate a config file; return the validated ``model`` block.

    Accepts a full-structure experiment fragment whose top-level keys are
    exactly ``schema_version`` (integer 1) and ``model``. Any read,
    decode, YAML or field validation failure raises ``ConfigError``
    carrying the source path and the concrete reason.
    """
    source = str(path)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        reason = "file is not valid UTF-8" if isinstance(exc, UnicodeDecodeError) else "cannot read file"
        raise ConfigError(f"{source}: {reason}: {exc}") from exc

    try:
        document = yaml.load(text, Loader=_StrictModelLoader)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{source}: invalid YAML: {exc}") from exc
    except ConfigError as exc:
        # Raised by the strict loader (duplicate/merge/non-string keys);
        # attach the source path here like for every other failure.
        raise ConfigError(f"{source}: {exc}") from exc

    if not isinstance(document, dict):
        raise ConfigError(f"{source}: top-level document must be a mapping, got {type(document).__name__}")
    keys = set(document)
    required = {"schema_version", "model"}
    missing = sorted(required - keys)
    if missing:
        raise ConfigError(f"{source}: missing required top-level fields: {', '.join(missing)}")
    unknown = sorted(keys - required)
    if unknown:
        raise ConfigError(f"{source}: unknown top-level fields: {', '.join(unknown)}")

    version = document["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != CONFIG_SCHEMA_VERSION:
        raise ConfigError(f"{source}: schema_version: expected the integer {CONFIG_SCHEMA_VERSION}, got {version!r}")

    try:
        return parse_model_config(document["model"])
    except ConfigError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
