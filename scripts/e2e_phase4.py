from __future__ import annotations

import os
import subprocess
import sys


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return p.stdout


def main() -> None:
    session = os.environ.get("MF_SESSION", "e2e_p4")
    os.environ.setdefault("M3_ENABLED", "true")
    goal = os.environ.get("MF_GOAL", "针对大模型/Agent的Memory综述：综合duckduckgo与arxiv近1个月Top10；自动规划")
    print("[E2E-Phase4] First run (learn workflow)...")
    p1 = subprocess.Popen([sys.executable, "-m", "memfuse.cli", "task", session, goal], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert p1.stdout is not None
    for line in p1.stdout:
        print(line, end="")
    p1.wait()
    print("[E2E-Phase4] Second run (reuse workflow if similar)...")
    p2 = subprocess.Popen([sys.executable, "-m", "memfuse.cli", "task", session, goal], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert p2.stdout is not None
    for line in p2.stdout:
        print(line, end="")
    p2.wait()
    print("[E2E-Phase4] DONE")


if __name__ == "__main__":
    main()
