#!/usr/bin/env python3
"""Local-only HTTP interface for the AO3-to-EPUB Tcl pipeline."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import secrets
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
CONVERTER = ROOT / "backend" / "converter" / "into_epub.tcl"
TCLSH = os.environ.get("TCLSH", "tclsh")
MAX_REQUEST_BYTES = 4096
CONVERSION_TIMEOUT_SECONDS = 300
JOBS: dict[str, tuple[tempfile.TemporaryDirectory, Path, str]] = {}
JOBS_LOCK = threading.Lock()


def extract_work_id(raw_url: str) -> str:
    """Accept only AO3 work URLs, optionally including a chapter suffix."""
    parsed = urlparse(raw_url.strip())
    if parsed.scheme != "https" or parsed.hostname not in {
        "archiveofourown.org", "www.archiveofourown.org"
    }:
        raise ValueError("Please enter an HTTPS link from archiveofourown.org.")
    match = re.fullmatch(r"/works/(\d+)(?:/chapters/\d+)?/?", parsed.path)
    if not match:
        raise ValueError("That doesn't look like an AO3 work link. Expected /works/ followed by the work ID.")
    return match.group(1)


class Handler(BaseHTTPRequestHandler):
    server_version = "AO3EPUBLocal/0.1"

    def log_message(self, fmt: str, *args) -> None:
        print("[http] " + fmt % args)

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"))

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            target = FRONTEND / "index.html"
        elif self.path in ("/styles.css", "/app.js"):
            target = FRONTEND / self.path.lstrip("/")
        elif self.path == "/health":
            self._json(200, {"ok": True})
            return
        elif self.path.startswith("/download/"):
            self._download(self.path.rsplit("/", 1)[-1])
            return
        else:
            self._json(404, {"error": "Not found"})
            return

        if not target.is_file():
            self._json(404, {"error": "Frontend file not found"})
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)

    def do_POST(self) -> None:
        if self.path != "/api/convert":
            self._json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Invalid request length."})
            return
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json(413, {"error": "Request is empty or too large."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            work_id = extract_work_id(str(payload.get("url", "")))
        except (json.JSONDecodeError, AttributeError, ValueError) as exc:
            self._json(400, {"error": str(exc) or "Please provide a valid AO3 URL."})
            return

        tempdir = tempfile.TemporaryDirectory(prefix="ao3-epub-")
        output = Path(tempdir.name) / f"ao3-work-{work_id}.epub"
        command = [TCLSH, str(CONVERTER), work_id, str(output)]
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            tempdir.cleanup()
            self._json(504, {"error": "Conversion took too long and was stopped."})
            return
        except OSError as exc:
            tempdir.cleanup()
            self._json(500, {"error": f"Could not start Tcl. Check that Tcl is installed. Details: {exc}"})
            return

        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            tempdir.cleanup()
            detail = (completed.stderr or completed.stdout or "The conversion process failed.").strip()
            self._json(502, {"error": detail[-1800:]})
            return

        token = secrets.token_urlsafe(24)
        with JOBS_LOCK:
            JOBS[token] = (tempdir, output, output.name)
        self._json(200, {
            "ok": True,
            "message": "Your EPUB is ready.",
            "filename": output.name,
            "download_url": f"/download/{token}",
        })

    def _download(self, token: str) -> None:
        with JOBS_LOCK:
            job = JOBS.pop(token, None)
        if job is None:
            self._json(404, {"error": "This download has expired or was already used. Convert the work again."})
            return
        tempdir, path, filename = job
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/epub+zip")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(filename)}")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        finally:
            tempdir.cleanup()


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    # In Docker, bind inside the container; docker-compose exposes the host
    # port only on 127.0.0.1. Outside Docker, stay on loopback.
    if host not in ("127.0.0.1", "localhost") and not (host == "0.0.0.0" and os.environ.get("DOCKERIZED") == "1"):
        raise SystemExit("This personal-use MVP must bind to localhost only.")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"AO3 to EPUB is running at http://{host}:{port}")
    print("Press Ctrl+C to stop. The server is accessible only from this computer.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()
        with JOBS_LOCK:
            remaining = list(JOBS.values())
            JOBS.clear()
        for tempdir, _, _ in remaining:
            tempdir.cleanup()


if __name__ == "__main__":
    main()
