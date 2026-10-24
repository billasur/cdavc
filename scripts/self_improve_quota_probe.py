"""Minimal Groq quota probe for a supervised self-improvement run.

Run ONLY after spend approval: this makes one chat completion with
max_tokens=1 (a handful of tokens) to learn whether the daily TPD window has
room. Prints the HTTP status and rate-limit headers; never prints the key.

Usage:
    CDAVC_API_KEY_FILE=/path/to/key python3 scripts/self_improve_quota_probe.py [model]
"""

from __future__ import annotations

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def main() -> int:
    key_file = os.environ.get("CDAVC_API_KEY_FILE")
    if not key_file:
        print("CDAVC_API_KEY_FILE is not set", file=sys.stderr)
        return 2
    key = open(key_file).read().strip()
    model = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-oss-20b"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }).encode()
    req = Request("https://api.groq.com/openai/v1/chat/completions", data=payload,
                  headers={"Content-Type": "application/json",
                           "Authorization": f"Bearer {key}",
                           "User-Agent": "cdavc-self-improve/1.0"}, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            print("status:", resp.status)
            for h, v in resp.headers.items():
                if "ratelimit" in h.lower():
                    print(f"{h}: {v}")
            print("QUOTA OK: a completion succeeded; daily window has room.")
            return 0
    except HTTPError as exc:
        print("status:", exc.code)
        for h, v in exc.headers.items():
            if "ratelimit" in h.lower() or h.lower() == "retry-after":
                print(f"{h}: {v}")
        body = exc.read().decode()[:300]
        print("error body (truncated):", body)
        if exc.code == 429:
            print("QUOTA BLOCKED: do not start the run; retry after the window resets.")
            return 1
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
