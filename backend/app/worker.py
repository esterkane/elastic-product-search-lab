from __future__ import annotations

import os
import time
from pathlib import Path


def main() -> None:
    ready_file = Path(os.getenv("WORKER_READY_FILE", "/tmp/worker-ready"))
    ready_file.write_text("ready\n", encoding="utf-8")
    interval = int(os.getenv("WORKER_IDLE_SECONDS", "30"))
    print("worker ready", flush=True)
    while True:
        time.sleep(interval)


if __name__ == "__main__":
    main()
