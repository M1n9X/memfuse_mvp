from __future__ import annotations

import os
import subprocess
import sys


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return p.stdout


def main() -> None:
    session = os.environ.get("MF_SESSION", "e2e_p3")
    print("[E2E-Phase3] Running orchestrated task once...")
    out = run([sys.executable, "-m", "memfuse.cli", "task", session, "Analyze the sample.txt content and summarize key topics" ])
    print(out)
    print("[E2E-Phase3] DONE")


if __name__ == "__main__":
    main()
