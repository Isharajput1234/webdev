from __future__ import annotations

from pathlib import Path
import os


def load_dotenv(base_dir: Path, filename: str = ".env") -> None:
    """
    Minimal .env loader (no dependency).
    - Loads KEY=VALUE lines into os.environ if the key is not already set.
    - Supports optional quotes and ignores comments/blank lines.
    """
    env_path = base_dir / filename
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or key in os.environ:
            continue

        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        os.environ[key] = value

