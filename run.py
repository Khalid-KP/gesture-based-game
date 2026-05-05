from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Iterable


PROJECT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
RUNNER_PORT = 8080
RUNNER_URL = f"http://localhost:{RUNNER_PORT}"
GAME_URL = "https://poki.com/en/g/hill-climb-racing-lite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gesture Game launcher and cleaner")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--confidence", type=float, default=0.7)
    parser.add_argument("--smooth-frames", type=int, default=4)
    parser.add_argument("--allow-left-hand", action="store_true")
    parser.add_argument(
        "--preview",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show webcam preview window (default: enabled)",
    )
    parser.add_argument(
        "--ports",
        default=str(RUNNER_PORT),
        help="Comma-separated ports to free before restart (example: 8080,5000)",
    )
    parser.add_argument(
        "--kill-only",
        action="store_true",
        help="Only stop running processes/ports, do not start the game",
    )
    parser.add_argument(
        "--open",
        choices=("runner", "game", "both"),
        default="both",
        help="Which page to open in browser: local runner, direct game, or both",
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
    ps = (
        "$procs = Get-CimInstance Win32_Process | Where-Object "
        "{ ($_.Name -ieq 'python.exe' -or $_.Name -ieq 'pythonw.exe') "
        "-and ($_.CommandLine -match 'main\\.py' -or $_.CommandLine -match 'http\\.server\\s+8080') }; "
        "foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }"
    )
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])


def cleanup(ports: Iterable[int]) -> None:
    print("[0/4] Stopping existing runner/controller processes...")
    kill_window_titles()
    kill_known_python_commands()

    print("[0/4] Killing all listening Python ports...")
    for pid in get_python_listener_pids():
        kill_pid(pid)

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


def start_runner() -> subprocess.Popen[str]:
    print(f"[1/4] Starting local web runner at {RUNNER_URL} ...")
    return subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "http.server",
            str(RUNNER_PORT),
            "--directory",
            "web",
        ],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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


def run_controller(args: argparse.Namespace) -> int:
    if args.preview:
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
    if not args.preview:
        cmd.append("--no-window")
    if args.allow_left_hand:
        cmd.append("--allow-left-hand")

    process = subprocess.run(cmd, cwd=PROJECT_DIR)
    print("\n[4/4] Gesture controller exited.")
    return process.returncode


def open_pages(open_target: str) -> None:
    if open_target in {"runner", "both"}:
        webbrowser.open(RUNNER_URL)
    if open_target in {"game", "both"}:
        webbrowser.open(GAME_URL)


def main() -> None:
    args = parse_args()
    ports = parse_ports(args.ports) or [RUNNER_PORT]

    ensure_venv_python()
    cleanup(ports)

    if args.kill_only:
        print("Cleanup complete. Exiting because --kill-only was provided.")
        raise SystemExit(0)

    runner = start_runner()
    time.sleep(1)
    open_pages(args.open)
    time.sleep(2)
    run_self_check(args.camera_index)

    exit_code = 0
    try:
        exit_code = run_controller(args)
    finally:
        if runner.poll() is None:
            runner.terminate()
            try:
                runner.wait(timeout=3)
            except subprocess.TimeoutExpired:
                runner.kill()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
