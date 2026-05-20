import os
import time

from app.config import settings


def main() -> None:
    interval_seconds = int(os.getenv("WORKER_TICK_SECONDS", "30"))
    print(f"GrooveGraph worker started for {settings.service_name}.", flush=True)

    while True:
        print("GrooveGraph worker heartbeat.", flush=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
