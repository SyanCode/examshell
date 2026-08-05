"""Browser-based terminal front-end for examshell.

Spawns `python3 -m examshell` inside a real pty per connection and bridges
it to a browser terminal (xterm.js) over a WebSocket, so the exam can be
run from a web page instead of a local shell. Full-screen editors (nano,
vim...) work too, since the pty forwards raw terminal escape sequences.

Intended for local/trusted use: anyone who can reach this server can run
the exam shell (and whichever $EDITOR it launches) as this process's user.
Do not expose it on an untrusted network.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import http.server
import json
import os
import pty
import struct
import subprocess
import sys
import termios
import threading
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
INDEX_TEMPLATE = WEB_DIR / "index.html"


class PtySession:
    def __init__(self, cmd: list, cwd: str):
        self.master_fd, slave_fd = pty.openpty()
        env = {**os.environ, "TERM": "xterm-256color"}
        env.setdefault("EDITOR", "nano")
        self.proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)

    def resize(self, cols: int, rows: int) -> None:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        try:
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass

    def write(self, data: bytes) -> None:
        try:
            os.write(self.master_fd, data)
        except OSError:
            pass

    def close(self) -> None:
        try:
            self.proc.terminate()
        except ProcessLookupError:
            pass
        try:
            os.close(self.master_fd)
        except OSError:
            pass


async def handle_connection(websocket) -> None:
    session = PtySession([sys.executable, "-u", "-m", "examshell"], cwd=str(ROOT))
    loop = asyncio.get_running_loop()
    output_queue: asyncio.Queue = asyncio.Queue()

    def on_readable() -> None:
        try:
            data = os.read(session.master_fd, 65536)
        except OSError:
            data = b""
        output_queue.put_nowait(data)
        if not data:
            loop.remove_reader(session.master_fd)

    loop.add_reader(session.master_fd, on_readable)

    async def pump_output() -> None:
        while True:
            data = await output_queue.get()
            if not data:
                break
            await websocket.send(data.decode(errors="replace"))

    pump_task = asyncio.create_task(pump_output())
    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
            except ValueError:
                continue
            kind = msg.get("type")
            if kind == "input":
                session.write(msg.get("data", "").encode())
            elif kind == "resize":
                session.resize(int(msg.get("cols", 80)), int(msg.get("rows", 24)))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        pump_task.cancel()
        try:
            loop.remove_reader(session.master_fd)
        except (KeyError, ValueError, OSError):
            pass
        session.close()


class _StaticHandler(http.server.SimpleHTTPRequestHandler):
    ws_port = 8765

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            body = INDEX_TEMPLATE.read_text().replace("__WS_PORT__", str(self.ws_port))
            encoded = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return
        super().do_GET()

    def log_message(self, fmt, *args) -> None:  # quieter default logging
        pass


def run_http_server(http_port: int, ws_port: int) -> http.server.ThreadingHTTPServer:
    handler = type("Handler", (_StaticHandler,), {"ws_port": ws_port})
    server = http.server.ThreadingHTTPServer(("0.0.0.0", http_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def run_ws_server(ws_port: int) -> None:
    async with websockets.serve(handle_connection, "0.0.0.0", ws_port):
        await asyncio.Future()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run examshell as a browser terminal.")
    parser.add_argument("--http-port", type=int, default=8000)
    parser.add_argument("--ws-port", type=int, default=8765)
    args = parser.parse_args(argv)

    run_http_server(args.http_port, args.ws_port)
    print(f"examshell web running: open http://localhost:{args.http_port} in your browser")
    print(f"(terminal bridge on ws://localhost:{args.ws_port})")
    try:
        asyncio.run(run_ws_server(args.ws_port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
