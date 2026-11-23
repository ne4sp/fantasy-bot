import msvcrt
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


def build_environment() -> dict[str, str]:
    debug_key = dotenv_values(ROOT / ".env").get("DEBUG_KEY")
    if not debug_key:
        raise RuntimeError("DEBUG_KEY is not configured in .env")

    env = os.environ.copy()
    env["MAIN_KEY"] = debug_key
    env["GROUP_ID"] = "0"
    env["H2H_ANNOUNCE"] = "0"
    return env


def start_bot(env: dict[str, str]) -> subprocess.Popen[bytes]:
    print("Starting debug bot...", flush=True)
    return subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "main.py")],
        cwd=ROOT,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def stop_bot(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    process.send_signal(signal.CTRL_BREAK_EVENT)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    env = build_environment()
    process = start_bot(env)
    print("Press Ctrl+R to restart; Ctrl+C to stop.", flush=True)

    try:
        while process.poll() is None:
            if msvcrt.kbhit() and msvcrt.getwch() == "\x12":
                print("\nRestarting debug bot...", flush=True)
                stop_bot(process)
                process = start_bot(env)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping debug bot...", flush=True)
    finally:
        stop_bot(process)

    return process.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
