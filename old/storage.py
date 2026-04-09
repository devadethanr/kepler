from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .paths import ensure_runtime_dirs

T = TypeVar("T", bound=BaseModel)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    ensure_runtime_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)


def load_model(path: Path, model_cls: type[T], default: T | None = None) -> T:
    if not path.exists():
        if default is not None:
            return default
        return model_cls()  # type: ignore[call-arg]
    with path.open("r", encoding="utf-8") as handle:
        return model_cls.model_validate_json(handle.read())


def dump_model(path: Path, model: BaseModel) -> None:
    ensure_runtime_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(model.model_dump_json(indent=2))
