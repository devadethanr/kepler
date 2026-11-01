from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, model_validator


class Profile(BaseModel):
    model: str
    model_path: Path
    endpoint: str
    gpu_uuid: str
    gguf_sha256: str

    @model_validator(mode="after")
    def local_only(self):
        url = urlsplit(self.endpoint)
        if (
            url.scheme != "http"
            or url.hostname != "127.0.0.1"
            or not url.port
            or url.username
            or url.password
            or url.path not in ("", "/v1")
        ):
            raise ValueError("Research model endpoints must be explicit local HTTP services")
        return self


class Settings(BaseModel):
    llama_binary: Path
    llama_sha256: str
    codex_binary: Path
    codex_sha256: str
    browser_binary: Path
    browser_sha256: str
    browser_skill: Path
    browser_skill_sha256: str
    chrome_binary: Path = Path("/usr/bin/google-chrome")
    state_root: Path = Field(default_factory=lambda: Path.home() / ".local/state/kepler-rooms")
    artifact_root: Path
    workspace_target: str = "Kepler"
    browser_domains: list[str] = Field(default_factory=list)
    profiles: dict[str, Profile]
    context_tokens: int = 32768
    output_tokens: int = 512
    model_calls: int = 24
    tool_calls: int = 24
    room_seconds: int = 1200
    lease_seconds: int = 45
    max_messages: int = 12

    @model_validator(mode="after")
    def pinned_limits(self):
        if (
            set(self.profiles) != {"analyst", "skeptic"}
            or len({p.model for p in self.profiles.values()}) != 2
            or len({p.endpoint for p in self.profiles.values()}) != 2
            or not 10 <= self.lease_seconds <= 120
            or self.context_tokens != 32768
            or self.output_tokens != 512
            or not 1 <= self.model_calls <= 24
            or not 1 <= self.tool_calls <= 24
            or not 30 <= self.room_seconds <= 1200
            or not 2 <= self.max_messages <= 24
        ):
            raise ValueError("Invalid pinned research configuration or room ceilings")
        return self


def load_settings() -> Settings:
    filename = os.environ.get("KEPLER_RESEARCH_CONFIG")
    if not filename:
        raise RuntimeError("Set KEPLER_RESEARCH_CONFIG to an explicit local runtime configuration")
    return Settings.model_validate(json.loads(Path(filename).read_text()))
