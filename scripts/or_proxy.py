#!/usr/bin/env python3
"""Local OpenAI-compatible proxy: localhost -> OpenRouter or Groq (stdlib only; --upstream).

The benchmark accepts localhost endpoints only. This forwards chat completions to
OpenRouter, adds the key (read from a file, never logged), retries 429/5xx with
backoff (honours Retry-After), and caps concurrency. Request log: JSONL, no prompts, no key.
Usage: or_proxy.py --key-file F --port 8089 --log proxy.jsonl [--max-inflight 2] [--min-interval 3]
"""
import argparse, json, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

A = None
SEM = None
LOCK = threading.Lock()
LAST = [0.0]
TOK = []


def log(rec):
    with LOCK, open(A.log, "a") as f:
        f.write(json.dumps(rec) + "\n")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            req = json.loads(body)
            req.setdefault("temperature", 0)
            req.setdefault("max_tokens", A.max_tokens)
            req.update(json.loads(A.extra))
            body = json.dumps(req).encode()
            est = sum(len(m.get("content") or "") for m in req.get("messages", [])) // 3 + req["max_tokens"] // 4
        except ValueError:
            pass
        est = locals().get("est", 1000)
        status, data, tries = 599, b'{"error":"proxy failure"}', 0
        with SEM:
            for tries in range(1, A.max_tries + 1):
                while A.tpm:
                    with LOCK:
                        now = time.time()
                        TOK[:] = [(t, n) for t, n in TOK if now - t < 60]
                        used = sum(n for _, n in TOK)
                        if used + est <= A.tpm * 0.9 or not TOK:
                            TOK.append((now, est))
                            break
                    time.sleep(2)
                with LOCK:  # spacing between upstream calls
                    wait = LAST[0] + A.min_interval - time.time()
                    LAST[0] = max(time.time(), LAST[0]) + (A.min_interval if wait > 0 else 0)
                if wait > 0:
                    time.sleep(wait)
                r = urllib.request.Request(
                    A.upstream.rstrip("/") + "/chat/completions", data=body, method="POST",
                    headers={"Content-Type": "application/json", "User-Agent": "cdavc-night-run/1.0",
                             "Authorization": "Bearer " + open(A.key_file).read().strip()})
                t0 = time.time()
                try:
                    with urllib.request.urlopen(r, timeout=A.timeout) as resp:
                        status, data = resp.status, resp.read()
                        hdr = dict(resp.headers)
                except urllib.error.HTTPError as e:
                    status, data, hdr = e.code, e.read(), dict(e.headers)
                except Exception as e:
                    status, data, hdr = 599, json.dumps({"error": str(e)}).encode(), {}
                ok = status == 200
                if ok:
                    try:  # OpenRouter sometimes returns 200 with an error body
                        j = json.loads(data)
                        if "error" in j and "choices" not in j:
                            ok, status = False, int(j["error"].get("code", 502) or 502)
                    except ValueError:
                        ok, status = False, 502
                if ok and A.tpm:
                    try:
                        u = json.loads(data).get("usage", {}).get("total_tokens")
                        if u:
                            with LOCK:
                                TOK[-1:] = [(TOK[-1][0], u)] if TOK else []
                    except ValueError:
                        pass
                log({"t": time.time(), "try": tries, "status": status, "secs": round(time.time() - t0, 2),
                     "rl": {k: v for k, v in hdr.items() if k.lower().startswith(("x-ratelimit", "retry-after"))}})
                if ok or status not in (429, 500, 502, 503, 504, 599):
                    break
                ra = hdr.get("Retry-After") or hdr.get("retry-after")
                if status == 429 and ra and ra.replace(".", "").isdigit() and float(ra) > 300:
                    break  # daily cap: do not burn retries, report 429 to the harness
                time.sleep(min(float(ra), 120) if ra and ra.replace(".", "").isdigit() else min(5 * 2 ** tries, 120))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--key-file", required=True)
    p.add_argument("--upstream", default="https://openrouter.ai/api/v1")
    p.add_argument("--tpm", type=int, default=0, help="tokens/minute budget; 0 = no token pacing")
    p.add_argument("--extra", default="{}", help="JSON merged into every request body, e.g. reasoning_effort")
    p.add_argument("--port", type=int, default=8089)
    p.add_argument("--log", default="proxy.jsonl")
    p.add_argument("--max-inflight", type=int, default=2)
    p.add_argument("--min-interval", type=float, default=3.0)
    p.add_argument("--max-tries", type=int, default=6)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--timeout", type=float, default=300)
    A = p.parse_args()
    SEM = threading.Semaphore(A.max_inflight)
    ThreadingHTTPServer(("127.0.0.1", A.port), H).serve_forever()
