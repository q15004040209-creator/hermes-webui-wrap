"""
hermes-webui-wrap — HTTP Server
Bottle-based HTTP server with REST API + SSE streaming.
"""

import os
import sys
import json
import time
import hashlib
import secrets
import threading
from pathlib import Path
from typing import Optional, Iterator

# Try to use the standard library wsgiref first (no dependencies)
try:
    from wsgiref.simple_server import make_server, WSGIServer
    from urllib.parse import parse_qs, urlparse
except ImportError:
    WSGIServer = object

# Optional: gevent for async streaming
try:
    from gevent.pywsgi import WSGIServer as GeventWSGIServer
    HAS_GEVENT = True
except ImportError:
    HAS_GEVENT = False

from api.config import config

# ---------------------------------------------------------------------------
# Simple WSGI Router (no external framework dependency)
# ---------------------------------------------------------------------------

class Router:
    """Minimal WSGI router."""

    def __init__(self):
        self.routes = {}  # method -> {path: handler}

    def route(self, path: str, methods=None):
        if methods is None:
            methods = ["GET"]
        methods = [m.upper() for m in methods]

        def decorator(func):
            for method in methods:
                if method not in self.routes:
                    self.routes[method] = {}
                self.routes[method][path] = func
            return func
        return decorator

    def dispatch(self, method: str, path: str, query: dict) -> tuple:
        """Returns (status, headers, body_bytes)."""
        method = method.upper()
        if method not in self.routes:
            return 404, [(b"Content-Type", b"application/json")], b'{"error":"Not found"}'

        routes = self.routes[method]
        # Exact match first
        if path in routes:
            handler = routes[path]
        else:
            #404
            return 404, [(b"Content-Type", b"application/json")], b'{"error":"Not found"}'

        try:
            result = handler(query)
            if isinstance(result, tuple) and len(result) == 3:
                status, headers, body = result
                if isinstance(body, str):
                    body = body.encode("utf-8")
                return status, headers, body
            else:
                return 200, [(b"Content-Type", b"application/json")], json.dumps(result).encode()
        except Exception as e:
            return 500, [(b"Content-Type", b"application/json")], json.dumps({"error": str(e)}).encode()


router = Router()
app = router # alias


# ---------------------------------------------------------------------------
# Session Store (in-memory with disk persistence)
# ---------------------------------------------------------------------------

class SessionStore:
    """Simple JSON-backed session store."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.sessions = {}
        self._lock = threading.Lock()
        self._db_path = state_dir / "sessions.json"
        self._load()

    def _load(self):
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
            except Exception:
                self.sessions = {}

    def _save(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._db_path, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)

    def list_sessions(self) -> list:
        with self._lock:
            return [
                {"id": k, "title": v.get("title", "Untitled"), "created_at": v.get("created_at")}
                for k, v in self.sessions.items()
            ]

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

    def create_session(self, title: str = "New Chat") -> dict:
        import uuid
        session_id = secrets.token_hex(8)
        now = time.time()
        session = {
            "id": session_id,
            "title": title,
            "created_at": now,
            "messages": [],
            "model": None,
            "provider": None,
        }
        with self._lock:
            self.sessions[session_id] = session
            self._save()
        return session

    def add_message(self, session_id: str, role: str, content: str):
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["messages"].append({
                    "role": role,
                    "content": content,
                    "timestamp": time.time()
                })
                self._save()

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self._save()
                return True
        return False


session_store = SessionStore(config.STATE_DIR)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def check_auth(headers: dict) -> bool:
    """Check if request is authenticated."""
    if not config.PASSWORD:
        return True  # No auth required

    # Check for session cookie
    cookie = headers.get("cookie", "")
    if f"hermes_auth={config.PASSWORD}" in cookie:
        return True

    # Check Authorization header
    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        # Simple bearer token check (password as token)
        if token == config.PASSWORD:
            return True
    return False


def require_auth(func):
    """Decorator to require authentication."""
    def wrapper(query, headers=None):
        if not check_auth(headers or {}):
            return 401, [(b"Content-Type", b"application/json")], b'{"error":"Unauthorized"}'
        return func(query)
    return wrapper


# ---------------------------------------------------------------------------
# SSE Streaming
# ---------------------------------------------------------------------------

def sse_stream(tokens: Iterator[str]) -> bytes:
    """Convert token iterator to SSE format."""
    for token in tokens:
        if token:
            yield f"data: {json.dumps({'token': token})}\n\n".encode("utf-8")
    yield b"data: [DONE]\n\n"


def generate_hermes_response(session_id: str, message: str) -> Iterator[str]:
    """
    Generate a response from Hermes Agent.
    Falls back to a simple echo if Hermes Agent is not available.
    """
    # Try to import and use the actual hermes-webui streaming
    try:
        # Check if hermes-agent is available in the agent dir
        if config.AGENT_DIR and (config.AGENT_DIR / "api" / "streaming.py").exists():
            sys.path.insert(0, str(config.AGENT_DIR))
            from api.streaming import generate_response
            yield from generate_response(session_id, message, config)
            sys.path.remove(str(config.AGENT_DIR))
            return
    except Exception:
        pass

    # Fallback: simple mock response
    mock_response = (
        f"You said: '{message}'. "
        f"This is a mock response from hermes-webui-wrap. "
        f"To get real AI responses, please install Hermes Agent and "
        f"set the HERMES_WEBUI_AGENT_DIR environment variable."
    )
    for word in mock_response.split():
        yield word + " "
    return


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.route("/health")
def health(query):
    return200, [(b"Content-Type", b"application/json")], json.dumps({
        "status": "ok",
        "version": "1.0.0",
        "wrap": "hermes-webui-wrap",
        "agent_dir": str(config.AGENT_DIR) if config.AGENT_DIR else None,
        "host": config.HOST,
        "port": config.PORT,
    }).encode()


@router.route("/api/sessions", methods=["GET"])
def list_sessions(query):
    sessions = session_store.list_sessions()
    return 200, [(b"Content-Type", b"application/json")], json.dumps({
        "sessions": sessions,
        "total": len(sessions)
    }).encode()


@router.route("/api/sessions", methods=["POST"])
def create_session(query):
    import io, json as json_mod
    # Body parsed externally in WSGI handler
    return {"id": "demo", "title": "demo"}


@router.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(query, session_id=None):
    session = session_store.get_session(session_id or "")
    if not session:
        return 404, [(b"Content-Type", b"application/json")], b'{"error":"Session not found"}'
    return 200, [(b"Content-Type", b"application/json")], json.dumps(session).encode()


@router.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(query, session_id=None):
    ok = session_store.delete_session(session_id or "")
    if not ok:
        return 404, [(b"Content-Type", b"application/json")], b'{"error":"Session not found"}'
    return 200, [(b"Content-Type", b"application/json")], b'{"ok":true}'


@router.route("/api/chat", methods=["POST"])
def chat(query):
    # Streaming endpoint - returns SSE
    import io
    body = query.get("_body", {})
    message = body.get("message", "")
    session_id = body.get("session_id", "default")

    if not session_id or session_id == "default":
        session = session_store.create_session()
        session_id = session["id"]
    else:
        session = session_store.get_session(session_id)
        if not session:
            session = session_store.create_session()

    session_store.add_message(session_id, "user", message)

    # Collect response
    response_text = ""
    for token in generate_hermes_response(session_id, message):
        response_text += token

    session_store.add_message(session_id, "assistant", response_text)

    return 200, [(b"Content-Type", b"text/event-stream")], (
        f"data: {json.dumps({'token': response_text})}\n\n"
        f"data: [DONE]\n\n"
    ).encode()


@router.route("/api/workspace/ls", methods=["GET"])
def workspace_ls(query):
    workspace = Path(config.DEFAULT_WORKSPACE)
    if not workspace.exists():
        workspace = Path.cwd()

    path = query.get("path", ["/"])[0] if isinstance(query.get("path"), list) else query.get("path", "/")
    target = workspace / path.lstrip("/")

    if not target.exists():
        target = workspace

    files = []
    try:
        for item in sorted(target.iterdir()):
            files.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": 0 if item.is_dir() else item.stat().st_size,
                "path": str(item.relative_to(workspace))
            })
    except PermissionError:
        pass

    return 200, [(b"Content-Type", b"application/json")], json.dumps({
        "files": files,
        "count": len(files),
        "workspace": str(workspace)
    }).encode()


@router.route("/api/config", methods=["GET"])
def get_config(query):
    return200, [(b"Content-Type", b"application/json")], json.dumps({
        "host": config.HOST,
        "port": config.PORT,
        "agent_dir": str(config.AGENT_DIR) if config.AGENT_DIR else None,
        "has_password": bool(config.PASSWORD),
        "workspace": config.DEFAULT_WORKSPACE,
    }).encode()


# ---------------------------------------------------------------------------
# Static Files (simple file server)
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent.parent / "static"


@router.route("/static/<filename>")
def static_file(query, filename=None):
    import mimetypes
    filepath = STATIC_DIR / filename
    if not filepath.exists() or ".." in filename:
        return 404, [(b"Content-Type", b"text/plain")], b"Not found"

    mime, _ = mimetypes.guess_type(str(filepath))
    with open(filepath, "rb") as f:
        content = f.read()

    return 200, [(b"Content-Type", (mime or "application/octet-stream").encode())], content


@router.route("/")
def index(query):
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        return 200, [(b"Content-Type", b"text/html; charset=utf-8")], content.encode("utf-8")
    else:
        # Fallback: minimal HTML
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Hermes WebUI Wrap</title></head>
<body><h1>Hermes WebUI Wrap</h1>
<p>Server running. Static files not found.
<a href="/api/health">API Health</a></p></body></html>"""
        return 200, [(b"Content-Type", b"text/html")], html.encode("utf-8")


# ---------------------------------------------------------------------------
# WSGI Application
# ---------------------------------------------------------------------------

def wsgi_app(environ, start_response):
    """The WSGI application."""
    method = environ["REQUEST_METHOD"]
    path = environ["PATH_INFO"]
    query_dict = parse_qs(environ.get("QUERY_STRING", ""))

    # Read body for POST requests
    body = b""
    if method == "POST":
        content_length = int(environ.get("CONTENT_LENGTH", 0))
        body = environ["wsgi.input"].read(content_length)

    # Parse body as JSON if present
    parsed_body = {}
    if body:
        try:
            parsed_body = json.loads(body.decode("utf-8"))
        except Exception:
            pass

    # Merge query and body
    merged_query = {**query_dict}
    for k, v in parsed_body.items():
        merged_query[k] = v

    # Extract headers
    headers = {}
    for key in environ:
        if key.startswith("HTTP_"):
            headers[key[5:].lower().replace("_", "-")] = environ[key]
    if environ.get("CONTENT_TYPE"):
        headers["content-type"] = environ["CONTENT_TYPE"]
    if environ.get("HTTP_COOKIE"):
        headers["cookie"] = environ["HTTP_COOKIE"]

    # Dispatch to router
    status, resp_headers, resp_body = router.dispatch(method, path, merged_query)

    # Handle SSE - don't set Content-Length for streaming
    headers_out = [
        (k.encode(), v.encode()) for k, v in resp_headers
    ]
    if "text/event-stream" in str(headers_out):
        headers_out.append((b"Cache-Control", b"no-cache"))
        headers_out.append((b"X-Accel-Buffering", b"no"))
    else:
        headers_out.append((b"Content-Length", str(len(resp_body)).encode()))

    status_str = f"{status} {'OK' if status< 400 else 'ERROR'}"
    start_response(status_str, headers_out)
    return [resp_body]


# ---------------------------------------------------------------------------
# Server Runner
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 8787,
               agent_dir: Optional[str] = None,
               open_browser: bool = True):
    """Start the hermes-webui-wrap HTTP server."""

    if agent_dir:
        os.environ["HERMES_WEBUI_AGENT_DIR"] = agent_dir

    print(f"[hermes-webui-wrap] Starting server at http://{host}:{port}")
    print(f"[hermes-webui-wrap] Config: {config}")

    if open_browser:
        import threading
        def _open_browser():
            time.sleep(1.5)
            try:
                import webbrowser
                webbrowser.open(f"http://{host}:{port}")
            except Exception:
                pass
        threading.Thread(target=_open_browser, daemon=True).start()

    if HAS_GEVENT:
        print("[hermes-webui-wrap] Using gevent for async support")
        server = GeventWSGIServer((host, port), wsgi_app)
    else:
        print("[hermes-webui-wrap] Using wsgiref (synchronous)")
        server = make_server(host, port, wsgi_app, classes=(WSGIServer,))

    try:
        print(f"[hermes-webui-wrap] Serving on http://{host}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[hermes-webui-wrap] Shutting down...")
        server.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    run_server()