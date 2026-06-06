#!/usr/bin/env python3
"""
hermes-webui-wrap — Launcher
Automatically discovers Hermes Agent and starts the Web UI server.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def auto_discover_hermes_agent() -> Path | None:
    """Auto-detect Hermes Agent installation directory."""
    # Check HERMES_WEBUI_AGENT_DIR env var first
    if os.environ.get("HERMES_WEBUI_AGENT_DIR"):
        p = Path(os.environ["HERMES_WEBUI_AGENT_DIR"])
        if p.exists():
            return p

    # Check common locations
    home = Path.home()
    candidates = [
        home / ".hermes" / "hermes-agent",
        home / "hermes-agent",
        Path("/opt/hermes-agent"),
        Path("/usr/local/hermes-agent"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Try to find via `which hermes-agent` or PATH scan
    try:
        result = subprocess.run(
            ["hermes-agent", "--version"],
            capture_output=True, text=True, timeout=5
        )
        # If it ran, agent is in PATH — find its location
        for p in [home / ".hermes" / "hermes-agent"]:
            if p.exists():
                return p
    except (OSError, subprocess.TimeoutExpired):
        pass

    return None


def find_python_executable() -> str:
    """Find the Python executable to use for the agent."""
    if os.environ.get("HERMES_WEBUI_PYTHON"):
        return os.environ["HERMES_WEBUI_PYTHON"]

    # Prefer python3, fallback to python
    for name in ["python3", "python"]:
        try:
            result = subprocess.run(
                [name, "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return name
        except OSError:
            continue
    return sys.executable


def main():
    parser = argparse.ArgumentParser(
        description="hermes-webui-wrap — Start Hermes Web UI server"
    )
    parser.add_argument(
        "--host", default=os.environ.get("HERMES_WEBUI_HOST", "127.0.0.1"),
        help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("HERMES_WEBUI_PORT", "8787")),
        help="Port (default: 8787)"
    )
    parser.add_argument(
        "--hermes-dir",
        default=os.environ.get("HERMES_WEBUI_AGENT_DIR"),
        help="Hermes Agent directory (auto-detected if not provided)"
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("HERMES_WEBUI_PYTHON"),
        help="Python executable for Hermes Agent"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't open browser on startup"
    )
    args = parser.parse_args()

    # Auto-detect Hermes Agent
    agent_dir = args.hermes_dir
    if not agent_dir:
        discovered = auto_discover_hermes_agent()
        if discovered:
            agent_dir = str(discovered)
            print(f"[hermes-webui-wrap] Discovered Hermes Agent at: {agent_dir}")
        else:
            print("[hermes-webui-wrap] WARNING: Hermes Agent not found.")
            print("  Set HERMES_WEBUI_AGENT_DIR or --hermes-dir to specify its location.")
            print("  The Web UI will start but the agent may not be functional.")

    # Set env vars for the server
    if agent_dir:
        os.environ["HERMES_WEBUI_AGENT_DIR"] = agent_dir
    os.environ["HERMES_WEBUI_HOST"] = args.host
    os.environ["HERMES_WEBUI_PORT"] = str(args.port)

    # Import and start the server
    try:
        from api.server import run_server
        run_server(
            host=args.host,
            port=args.port,
            agent_dir=agent_dir,
            open_browser=not args.no_browser
        )
    except ImportError as e:
        print(f"[hermes-webui-wrap] Error: Could not import server module: {e}")
        print("  Make sure you are in the hermes-webui-wrap directory.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[hermes-webui-wrap] Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()