from __future__ import annotations

import json
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8877"))
ROOT = Path(__file__).resolve().parent
APP_VERSION = "0.8.7"
APP_NAME = "WARtool"


class WarToolHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if urlsplit(self.path).path == "/__wartool_health":
            payload = json.dumps({"ok": True, "app": APP_NAME, "version": APP_VERSION, "port": PORT}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()


def main() -> int:
    os.chdir(ROOT)
    try:
        server = ThreadingHTTPServer((HOST, PORT), WarToolHandler)
    except OSError as error:
        print()
        print(f"WARtool could not bind to http://localhost:{PORT}")
        print("That port is already occupied. Close the other local-server window first.")
        print(f"Technical detail: {error}")
        print()
        return 1

    url = f"http://localhost:{PORT}"
    print()
    print(f"WARtool v{APP_VERSION} running at {url}")
    print(f"Health check: {url}/__wartool_health")
    print("This dedicated port is intentionally different from PaxDex (8767).")
    print("Keep this window open. Press CTRL+C to stop.")
    print()
    if os.environ.get("WARTOOL_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping WARtool.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
