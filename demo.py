#!/usr/bin/env python3
"""
hermes-webui-wrap — Demo Script
Shows how to use the Hermes Web UI API programmatically.
Requires the server to be running (python start.py).

Usage:
    python demo.py
"""

import os
import sys
import json
import time
import argparse
from typing import Optional

try:
    import requests
except ImportError:
    print("requests not installed. Install with: pip install requests")
    sys.exit(1)


BASE_URL = "http://{host}:{port}".format(
    host=os.environ.get("HERMES_WEBUI_HOST", "127.0.0.1"),
    port=os.environ.get("HERMES_WEBUI_PORT", "8787"),
)


def wait_for_server(timeout: int = 10) -> bool:
    """Wait for the server to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    return False


def demo_health_check():
    """Check if the server is running."""
    print("\n=== 1. Health Check ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    except requests.ConnectionError:
        print(f"ERROR: Server not reachable at {BASE_URL}")
        print("Start the server first: python start.py")
        return False
    return True


def demo_list_sessions():
    """List all sessions."""
    print("\n=== 2. List Sessions ===")
    resp = requests.get(f"{BASE_URL}/api/sessions", timeout=5)
    data = resp.json()
    print(f"Sessions ({data.get('total', 0)}):")
    for session in data.get("sessions", [])[:5]:
        print(f"  - [{session['id']}] {session.get('title', 'Untitled')}")
    return data


def demo_create_session(title: str = "Demo Session via API"):
    """Create a new session."""
    print(f"\n=== 3. Create Session: '{title}' ===")
    resp = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": title},
        timeout=5
    )
    data = resp.json()
    print(f"Created: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data.get("id")


def demo_send_message(session_id: str, message: str):
    """Send a message and stream the response."""
    print(f"\n=== 4. Send Message to session [{session_id}] ===")
    print(f"User: {message}")

    # Streaming request
    print("Agent: ", end="", flush=True)
    full_response = ""
    resp = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": message, "session_id": session_id},
        stream=True,
        timeout=60
    )

    for line in resp.iter_lines():
        if line:
            try:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("token", "")
                print(token, end="", flush=True)
                full_response += token
            except json.JSONDecodeError:
                continue

    print()  # newline after streaming
    return full_response


def demo_get_session(session_id: str):
    """Get details of a specific session."""
    print(f"\n=== 5. Get Session [{session_id}] Details ===")
    resp = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
    data = resp.json()
    print(f"Title: {data.get('title')}")
    print(f"Messages: {len(data.get('messages', []))}")
    print(f"Created: {data.get('created_at')}")
    return data


def demo_delete_session(session_id: str):
    """Delete a session."""
    print(f"\n=== 6. Delete Session [{session_id}] ===")
    resp = requests.delete(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Deleted successfully")
    return resp.status_code == 200


def demo_workspace_list(path: str = "/"):
    """List files in workspace."""
    print(f"\n=== 7. Workspace List [{path}] ===")
    resp = requests.get(
        f"{BASE_URL}/api/workspace/ls",
        params={"path": path},
        timeout=5
    )
    data = resp.json()
    print(f"Files ({data.get('count', 0)}):")
    for f in data.get("files", [])[:10]:
        print(f"  {'[DIR] ' if f['is_dir'] else ''}{f['name']}")
    return data


def main():
    parser = argparse.ArgumentParser(description="hermes-webui-wrap API Demo")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8787, help="Server port")
    parser.add_argument("--skip-wait", action="store_true", help="Skip server wait")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = f"http://{args.host}:{args.port}"

    print(f"[demo] Targeting {BASE_URL}")

    if not args.skip_wait:
        print("[demo] Waiting for server...")
        if not wait_for_server(timeout=15):
            print("[demo] ERROR: Server not available.")
            sys.exit(1)

    # Run all demos
    if not demo_health_check():
        sys.exit(1)

    sessions = demo_list_sessions()
    session_id = demo_create_session()

    if session_id:
        demo_send_message(session_id, "Hello! Can you introduce yourself?")
        demo_get_session(session_id)
        demo_delete_session(session_id)

    demo_workspace_list()

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()