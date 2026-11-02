"""
Tiny stdlib HTTP helper for the CC5 bridge on THIS machine, any port.

The bridge only answers when the Host header is 127.0.0.1:<its own port>, so a
client must use the same port the bridge listens on (CC5_BRIDGE_PORT, default
5101). Run it on the machine where CC5 runs (over ssh for another machine):

    python scripts/cc5_http.py --port 5111 --path /health
    python scripts/cc5_http.py --port 5111 --method POST --path /avatar/list --json "{}"
    python scripts/cc5_http.py --port 5101 --path /ui/windows --out D:/tmp/windows.json

Prints the reply body. Exit code 0 for HTTP 2xx, 1 for other HTTP codes,
3 when the bridge cannot be reached.
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time

DEFAULT_PORT = 5101


def valid_port(text: str) -> int:
    """argparse type: an integer port 1024-65535."""
    try:
        port = int(text)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"not an integer port: {text!r}") from err
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port {port} is outside 1024-65535")
    return port


def build_request(method: str, path: str, body_text: str | None) -> tuple[str, str, bytes | None]:
    """Validate method, path and JSON body. Returns (METHOD, path, encoded body or None)."""
    method = method.upper()
    if method not in ("GET", "POST"):
        raise ValueError(f"method must be GET or POST, got {method!r}")
    if not path.startswith("/"):
        raise ValueError(f"path must start with '/', got {path!r}")
    if body_text is None:
        return method, path, (b"{}" if method == "POST" else None)
    json.loads(body_text)  # raises ValueError for bad JSON
    return method, path, body_text.encode("utf-8")


def call(port: int, method: str, path: str, body: bytes | None, timeout: float) -> tuple[int, bytes]:
    """Send one request to 127.0.0.1:<port>. Host header is 127.0.0.1:<port> (http.client default)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=body, headers=headers)
        reply = conn.getresponse()
        return reply.status, reply.read()
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call the CC5 bridge on this machine.")
    parser.add_argument("--port", type=valid_port, default=DEFAULT_PORT)
    parser.add_argument("--method", default="GET")
    parser.add_argument("--path", default="/health")
    parser.add_argument("--json", dest="body", default=None, help="JSON body (POST)")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--out", default=None, help="also write the body to this file")
    parser.add_argument("--time", action="store_true", help="print seconds taken to stderr")
    args = parser.parse_args(argv)

    try:
        method, path, body = build_request(args.method, args.path, args.body)
    except ValueError as err:
        print(f"cc5_http: {err}", file=sys.stderr)
        return 2
    started = time.monotonic()
    try:
        status, data = call(args.port, method, path, body, args.timeout)
    except OSError as err:
        print(f"cc5_http: cannot reach 127.0.0.1:{args.port}: {err}", file=sys.stderr)
        return 3
    if args.time:
        print(f"cc5_http: {status} in {time.monotonic() - started:.2f} s", file=sys.stderr)
    if args.out:
        with open(args.out, "wb") as handle:
            handle.write(data)
    sys.stdout.write(data.decode("utf-8", errors="replace") + "\n")
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
