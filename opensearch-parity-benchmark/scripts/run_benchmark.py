from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    run(root, [sys.executable, "scripts/ingest.py"])
    run(root, [sys.executable, "scripts/evaluate.py"])
    return 0


def run(cwd: Path, command: list[str]) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
