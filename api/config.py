"""
hermes-webui-wrap — Configuration & Auto-Discovery
"""

import os
import sys
from pathlib import Path
from typing import Optional


class Config:
    """Global configuration for hermes-webui-wrap."""

    def __init__(self):
        self.AGENT_DIR = self._discover_agent_dir()
        self.PYTHON = self._discover_python()
        self.HOST = os.environ.get("HERMES_WEBUI_HOST", "127.0.0.1")
        self.PORT = int(os.environ.get("HERMES_WEBUI_PORT", "8787"))
        self.STATE_DIR = Path(os.environ.get(
            "HERMES_WEBUI_STATE_DIR",
            Path.home() / ".hermes" / "webui"
        ))
        self.DEFAULT_WORKSPACE = os.environ.get(
            "HERMES_WEBUI_DEFAULT_WORKSPACE",
            "./workspace"
        )
        self.PASSWORD = os.environ.get("HERMES_WEBUI_PASSWORD")
        self.DEBUG = os.environ.get("HERMES_WEBUI_DEBUG", "0") == "1"

        # Ensure state dir exists
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)

    def _discover_agent_dir(self) -> Optional[Path]:
        """Auto-detect Hermes Agent installation."""
        if os.environ.get("HERMES_WEBUI_AGENT_DIR"):
            p = Path(os.environ["HERMES_WEBUI_AGENT_DIR"])
            if p.exists():
                return p

        home = Path.home()
        candidates = [
            home / ".hermes" / "hermes-agent",
            home / ".hermes-agent",
            home / "hermes-agent",
            Path("/opt/hermes-agent"),
            Path("/usr/local/hermes-agent"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _discover_python(self) -> str:
        """Find Python executable for Hermes Agent."""
        if os.environ.get("HERMES_WEBUI_PYTHON"):
            return os.environ["HERMES_WEBUI_PYTHON"]
        for name in ["python3", "python"]:
            try:
                import subprocess
                r = subprocess.run([name, "--version"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return name
            except Exception:
                continue
        return sys.executable

    def __repr__(self):
        return (
            f"Config(agent={self.AGENT_DIR}, host={self.HOST}:{self.PORT}, "
            f"state={self.STATE_DIR}, workspace={self.DEFAULT_WORKSPACE})"
        )


# Global singleton config
config = Config()