from __future__ import annotations

import os
import subprocess
import sys


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return p.stdout


def main() -> None:
    session = os.environ.get("MF_SESSION", "e2e_p3")
    goal = os.environ.get("MF_GOAL", "综述大模型/Agent Memory：综合duckduckgo与arxiv近1个月Top10，自动规划")
    print("[E2E-Phase3] Running orchestrated task once...")
    out = run([sys.executable, "-m", "memfuse.cli", "task", session, goal])
    print(out)
    print("[E2E-Phase3] DONE")


if __name__ == "__main__":
    main()
