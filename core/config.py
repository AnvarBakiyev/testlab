"""
core/config.py -- Project config loader with env-path override.

base_path priority (highest first):
  1. Env var  TESTLAB_BASE_{PROJECT_ID_UPPER}  e.g. TESTLAB_BASE_PERSONAL_AGI
  2. Env var  TESTLAB_BASE  (global fallback)
  3. Value in project.json  (local dev default, never relied on in CI)

This means project.json can ship with a sensible default for local dev,
but CI / other machines override via env without touching the file.
"""
import json
import os
from pathlib import Path

TESTLAB_ROOT = Path(__file__).parent.parent


def load_projects() -> dict:
    """Return {project_id: resolved_config} for all registered projects."""
    registry_path = TESTLAB_ROOT / "projects.json"
    registry = json.loads(registry_path.read_text())
    result = {}
    for entry in registry["projects"]:
        cfg_path = TESTLAB_ROOT / entry["config"]
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            result[cfg["id"]] = _resolve(cfg)
    return result


def load_project(project_id: str) -> dict | None:
    return load_projects().get(project_id)


def _resolve(cfg: dict) -> dict:
    """Apply env-var overrides to mutable fields."""
    project_id = cfg["id"]
    env_key_specific = f"TESTLAB_BASE_{project_id.upper()}"
    env_key_global = "TESTLAB_BASE"

    override = os.environ.get(env_key_specific) or os.environ.get(env_key_global)
    if override:
        cfg = {**cfg, "base_path": override}

    # Warn if path looks like it belongs to a specific user's machine
    base = cfg.get("base_path", "")
    if base.startswith("/Users/") and not override:
        import warnings
        warnings.warn(
            f"[testlab] base_path '{base}' is user-specific. "
            f"Set env var {env_key_specific} or {env_key_global} for portability.",
            stacklevel=3,
        )

    return cfg
