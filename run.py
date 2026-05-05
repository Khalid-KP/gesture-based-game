from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable


PROJECT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
RUNNER_PORT = 8080
GAME_URL = "https://poki.com/en/g/hill-climb-racing-lite"
RUNTIME_DIR = PROJECT_DIR / ".runtime"
STATE_FILE = RUNTIME_DIR / "gesture-state.json"
CONTROL_FILE = RUNTIME_DIR / "gesture-control.json"
FRAME_FILE = RUNTIME_DIR / "gesture-frame.jpg"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gesture Game launcher and cleaner")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--confidence", type=float, default=0.7)
    parser.add_argument("--smooth-frames", type=int, default=4)
    parser.add_argument("--allow-left-hand", action="store_true")
    parser.add_argument(
        "--preview",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Show webcam preview window (default: disabled for stable browser focus)",
    )
    parser.add_argument(
        "--ports",
        default=str(RUNNER_PORT),
        help="Comma-separated ports to free before restart (example: 8080,5000)",
    )
    parser.add_argument(
        "--runner-port",
        type=int,
        default=RUNNER_PORT,
        help="Preferred local runner port (default: 8080)",
    )
    parser.add_argument(
        "--kill-only",
        action="store_true",
        help="Only stop running processes/ports, do not start the game",
    )
    parser.add_argument(
        "--open",
        choices=("runner", "game", "both"),
        default="runner",
        help="Which page to open in browser: local runner, direct game, or both (default: runner)",
    )
    parser.add_argument(
        "--ui-mode",
        choices=("web", "legacy"),
        default="web",
        help="UI mode for launch flow (default: web)",
    )
    return parser.parse_args()


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        text=True,
        capture_output=True,
        check=check,
    )


def parse_ports(raw: str) -> list[int]:
    values: list[int] = []
    for part in re.split(r"[\s,]+", raw.strip()):
        if not part:
            continue
        if not part.isdigit():
            continue
        port = int(part)
        if 1 <= port <= 65535:
            values.append(port)
    return sorted(set(values))


def get_listening_pids_for_port(port: int) -> set[int]:
    result = run(["netstat", "-ano"])
    pids: set[int] = set()
    pattern = re.compile(rf"^\s*TCP\s+\S+:{port}\s+\S+\s+LISTENING\s+(\d+)\s*$")
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if match:
            pids.add(int(match.group(1)))
    return pids


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def get_python_listener_pids() -> set[int]:
    result = run(["netstat", "-ano"])
    pids: set[int] = set()
    pattern = re.compile(r"^\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$")
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        pid = int(match.group(2))
        info = run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
        row = info.stdout.strip().lower()
        if row.startswith("\"python.exe\"") or row.startswith("\"pythonw.exe\""):
            pids.add(pid)
    return pids


def kill_pid(pid: int) -> None:
    run(["taskkill", "/F", "/PID", str(pid)])


def kill_window_titles() -> None:
    run(["taskkill", "/F", "/FI", "WINDOWTITLE eq Gesture Web Runner Server*"])
    run(["taskkill", "/F", "/FI", "WINDOWTITLE eq Gesture Controller*"])


def kill_known_python_commands() -> None:
    # Scope kills to gesture project command lines to avoid stopping unrelated Python apps.
    self_pid = str(os.getpid())
    ps = (
        "$procs = Get-CimInstance Win32_Process | Where-Object "
        "{ ($_.Name -ieq 'python.exe' -or $_.Name -ieq 'pythonw.exe') "
        f"-and $_.ProcessId -ne {self_pid} "
        "-and ($_.CommandLine -match 'main\\.py' "
        "-or $_.CommandLine -match 'http\\.server\\s+8080') }; "
        "foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }"
    )
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])


def cleanup(ports: Iterable[int]) -> None:
    print("[0/4] Stopping existing runner/controller processes...")
    kill_window_titles()
    kill_known_python_commands()

    print("[0/4] Freeing requested ports...")
    for port in ports:
        for pid in get_listening_pids_for_port(port):
            kill_pid(pid)
    time.sleep(1)


def ensure_venv_python() -> None:
    if VENV_PYTHON.exists():
        return
    print('[ERROR] Virtual environment not found at ".venv\\Scripts\\python.exe".')
    print("Run setup first:")
    print("  python -m venv .venv")
    print("  .venv\\Scripts\\activate")
    print("  pip install -r requirements.txt")
    raise SystemExit(1)


def _default_state() -> dict[str, object]:
    return {
        "enabled": False,
        "raw_gesture": "NEUTRAL",
        "stable_gesture": "NEUTRAL",
        "handedness": "None",
        "updated_at": time.time(),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path, fallback: dict[str, object]) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(fallback)


def build_runner_handler(
    web_dir: Path, state_file: Path, control_file: Path, frame_file: Path
) -> type[SimpleHTTPRequestHandler]:
    class RunnerHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_dir), **kwargs)

        def do_GET(self) -> None:
            if self.path == "/api/state":
                payload = _read_json(state_file, _default_state())
                body = json.dumps(payload).encode("utf-8")
                try:
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                return
            if self.path.startswith("/api/frame"):
                if not frame_file.exists():
                    # Frame is expected to be unavailable during startup. Return empty quickly.
                    self.send_response(HTTPStatus.NO_CONTENT)
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return
                body = frame_file.read_bytes()
                try:
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                return
            return super().do_GET()

        def do_POST(self) -> None:
            if self.path != "/api/control":
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
                return
            enabled = bool(payload.get("enabled", False))
            _write_json(control_file, {"enabled": enabled, "updated_at": time.time()})
            state = _read_json(state_file, _default_state())
            state["enabled"] = enabled
            body = json.dumps(state).encode("utf-8")
            try:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

    return RunnerHandler


def start_runner(
    state_file: Path, control_file: Path, frame_file: Path, preferred_port: int
) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    handler = build_runner_handler(PROJECT_DIR / "web", state_file, control_file, frame_file)

    class ReusableThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = True

    if not _port_available(preferred_port):
        raise RuntimeError(
            f"Port {preferred_port} is still busy after cleanup. "
            "Free that port first, then run again."
        )

    runner_url = f"http://localhost:{preferred_port}"
    print(f"[1/4] Starting local web runner at {runner_url} ...")

    server = ReusableThreadingHTTPServer(("127.0.0.1", preferred_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, preferred_port


def run_self_check(camera_index: int) -> None:
    print("[2/4] Running gesture controller self-check...")
    result = run(
        [
            str(VENV_PYTHON),
            "main.py",
            "--self-check",
            "--camera-index",
            str(camera_index),
        ]
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        print("\n[ERROR] Self-check failed. Fix the reported issue, then try again.")
        raise SystemExit(result.returncode)


def run_controller(
    args: argparse.Namespace, state_file: Path, control_file: Path, frame_file: Path
) -> int:
    use_preview = args.preview if args.ui_mode == "legacy" else False
    if use_preview:
        print("[3/4] Starting gesture controller with webcam preview...")
        print("      Keep the game tab focused after preview appears.")
    else:
        print("[3/4] Starting gesture controller in no-window mode...")
        print("      This keeps browser focus stable for key sync.")
    print("      Stop with Ctrl+C in this terminal.\n")

    cmd = [
        str(VENV_PYTHON),
        "main.py",
        "--camera-index",
        str(args.camera_index),
        "--confidence",
        str(args.confidence),
        "--smooth-frames",
        str(args.smooth_frames),
    ]
    if not use_preview:
        cmd.append("--no-window")
    if args.allow_left_hand:
        cmd.append("--allow-left-hand")
    cmd.extend(
        [
            "--status-file",
            str(state_file),
            "--control-file",
            str(control_file),
            "--frame-file",
            str(frame_file),
        ]
    )

    try:
        process = subprocess.run(cmd, cwd=PROJECT_DIR)
    except KeyboardInterrupt:
        print("\n[4/4] Stopped by user.")
        return 130
    print("\n[4/4] Gesture controller exited.")
    return process.returncode


def open_pages(open_target: str, runner_url: str) -> None:
    if open_target in {"runner", "both"}:
        webbrowser.open(runner_url)
    if open_target in {"game", "both"}:
        webbrowser.open(GAME_URL)


def main() -> None:
    args = parse_args()
    preferred_port = args.runner_port if 1 <= args.runner_port <= 65535 else RUNNER_PORT
    requested_ports = parse_ports(args.ports)
    ports = sorted(set(requested_ports + [preferred_port])) if requested_ports else [preferred_port]

    ensure_venv_python()
    cleanup(ports)

    if args.kill_only:
        print("Cleanup complete. Exiting because --kill-only was provided.")
        raise SystemExit(0)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(STATE_FILE, _default_state())
    _write_json(CONTROL_FILE, {"enabled": True, "updated_at": time.time()})

    runner, runner_thread, runner_port = start_runner(
        STATE_FILE, CONTROL_FILE, FRAME_FILE, preferred_port
    )
    runner_url = f"http://localhost:{runner_port}"
    time.sleep(1)
    if args.ui_mode == "web" and args.preview:
        print("[INFO] --preview is ignored in --ui-mode web to keep single-page focus stable.")
    open_pages(args.open, runner_url)
    time.sleep(2)
    try:
        run_self_check(args.camera_index)
    except KeyboardInterrupt:
        print("\n[2/4] Self-check interrupted by user.")
        raise SystemExit(130)

    exit_code = 0
    try:
        exit_code = run_controller(args, STATE_FILE, CONTROL_FILE, FRAME_FILE)
    except KeyboardInterrupt:
        print("\n[4/4] Launcher interrupted by user.")
        exit_code = 130
    finally:
        runner.shutdown()
        runner.server_close()
        runner_thread.join(timeout=3)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
