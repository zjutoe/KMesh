"""Strict, read-only loading of the model-structure fragment.

This module validates only the ``model`` block of an experiment config
(research plan §8.3). It never imports torch, never constructs a model
and never fills in defaults: every field is required and typed exactly.

The PyYAML import is deferred into ``_load_strict_yaml`` so that
``kmesh.config`` (and therefore ``kmesh.cli`` ``--help`` and ``doctor``)
stays importable when the package is absent.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
    if isinstance(raw_dropout, int) and raw_dropout != 0:
        # The only valid integer in [0, 1) is 0; reject every other int
        # before float(), where values past 2**1023 would raise OverflowError.
        raise ConfigError(f"model.dropout: must be finite and in [0, 1), got {raw_dropout!r}")
    dropout = float(raw_dropout)
    if not math.isfinite(dropout) or not 0.0 <= dropout < 1.0:
        raise ConfigError(f"model.dropout: must be finite and in [0, 1), got {raw_dropout!r}")

    return ModelConfig(dropout=dropout, **ints)


def _load_strict_yaml(text: str) -> Any:
    """Parse a single-document, strict YAML mapping from ``text``.

    The PyYAML import and every YAML-specific conversion live here so the
    rest of the module (and ``kmesh.cli --help`` / ``doctor``) works when
    the package is missing. Rejections are raised as ``ConfigError`` with
    the concrete reason:

    * duplicate keys, non-string keys and merge keys/tag (loader below)
    * ``yaml.YAMLError`` for scan/parse/constructor errors and unsupported
      node-type/tag mismatches (e.g. a mapping tag on a scalar)
    * ``KeyError``/``ValueError``/``TypeError`` raised deep inside
      ``yaml.load`` by broken constructors (e.g. ``!!int nope``,
      ``!!bool nope``, ``2026-99-99``) instead of ``yaml.YAMLError``

    Only errors from these explicitly listed boundaries are converted;
    unrelated programming errors are never swallowed.
    """
    import yaml

    def construct_no_duplicate_mapping(
        loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False
    ) -> dict:
        if not isinstance(node, yaml.MappingNode):
            # Mapping tag on a non-mapping node: let the safe constructor
            # raise its own ConstructorError(YAMLError) with node details.
            return yaml.SafeLoader.construct_mapping(loader, node, deep)
        seen: set[str] = set()
        for key_node, _value_node in node.value:
            if key_node.tag in ("tag:yaml.org,2002:merge",):
                raise ConfigError(
                    f"mapping at line {node.start_mark.line + 1}: merge tag is not supported"
                )
            key = loader.construct_object(key_node, deep=deep)
            if key == "<<":
                raise ConfigError(
                    f"mapping at line {node.start_mark.line + 1}: merge key '<<' is not supported"
                )
            if not isinstance(key, str):
                raise ConfigError(
                    f"mapping at line {node.start_mark.line + 1}: expected a string key, "
                    f"got {type(key).__name__}"
                )
            if key in seen:
                raise ConfigError(
                    f"mapping at line {node.start_mark.line + 1}: duplicate key {key!r}"
                )
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    class StrictModelLoader(yaml.SafeLoader):  # local: never touches the global safe loader
        pass

    StrictModelLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_no_duplicate_mapping
    )

    try:
        return yaml.load(text, Loader=StrictModelLoader)
    except ConfigError as exc:
        # Raised by the strict loader above; re-raised so load_model_config
        # attaches the source path exactly like for every other failure.
        raise
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {exc}") from exc
    except (KeyError, TypeError, ValueError) as exc:
        # Broken constructor values; PyYAML raises these outside
        # YAMLError. They only occur during single-document construction.
        raise ConfigError(f"invalid YAML: {exc}") from exc
    except (IndexError, AttributeError, OverflowError) as exc:
        # PyYAML 6.0.3 built-in constructors with proven escape paths that
        # do not go through YAMLError: empty !!int/!!float (IndexError on
        # value[0]), unmatched !!timestamp (AttributeError on groupdict of
        # the failed regex match), and sexagesimal float base conversion
        # (OverflowError when the base-60 value exceeds float range).
        raise ConfigError(f"invalid YAML: {exc}") from exc


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
        document = _load_strict_yaml(text)
    except ConfigError as exc:
        # All YAML-level failures (strict loader and invalid YAML) surface
        # with the source path attached here.
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
