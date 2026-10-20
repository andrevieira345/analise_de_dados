import json
import time
from pathlib import Path

import requests


API_KEY = "w7IiUkBZqpzEACRemhuhS4JqzbmI3s0FzFc0fHrd"
URL = "https://api.nasa.gov/neo/rest/v1/neo/browse"
RAW_DIR = Path("data/raw")


def fetch_all(start=0, end=5):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for page in range(start, end):
        path = RAW_DIR / f"page_{page:04d}.json"

        if path.exists():                      # already downloaded -> skip
            continue

        for attempt in range(3):               # retry up to 3 times
            try:
                r = requests.get(URL, params={"api_key": API_KEY, "page": page}, timeout=30)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                rate_limited = (
                    isinstance(e, requests.HTTPError) and e.response.status_code == 429
                )
                wait = 3600 if rate_limited else 10
                print(f"page {page} failed ({e}), waiting {wait}s")
                time.sleep(wait)
        else:                                  # all 3 attempts failed
            print(f"giving up on page {page}")
            continue

        path.write_text(json.dumps(r.json()))

        remaining = int(r.headers.get("X-RateLimit-Remaining", 9999))
        print(f"page {page}/{end - 1} saved, {remaining} requests left")

        if remaining < 50:
            print("near the limit, sleeping 1 hour")
            time.sleep(3600)

        time.sleep(0.5)


if __name__ == "__main__":
    fetch_all(0, 3150)        # test first; then fetch_all(0, 3135)