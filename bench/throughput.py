#!/usr/bin/env python3
"""Measure how many tokens a provider ACTUALLY delivers in a minute, instead of reading its ceiling.

    python bench/throughput.py --date 2026-09-07 --only cerebras,groq

A published ceiling is what a provider allows. This measures what one arrives at: real requests, in
parallel, for a fixed window, counting the output tokens that came back. Nobody else on this shelf
publishes that, because it costs quota to find out.

THE BUDGET IS THE POINT, and it is enforced three ways at once, because a throughput test is a
quota-burning machine by construction and this one runs against somebody's free tier:

  1. A WALL CLOCK. The window is short - 30 seconds by default. Long enough for a rate, short enough
     that a mistake costs little.
  2. A TOKEN CEILING. It stops at 25,000 output tokens per provider whatever the clock says. Alibaba's
     entire free grant is 1,000,000 tokens for 90 days; a careless test would eat a fifth of it.
  3. THEIR OWN RATE LIMIT. Concurrency never exceeds the requests-per-minute they publish. Aiming
     above a documented ceiling is not measurement, it is abuse, and it gets the account closed.

And it stops on the first 429. A rate limit reached is itself the answer - it says the ceiling is real
and where it sits - so there is no reason to keep pushing into it.

WHAT THE NUMBER MEANS, exactly, and it is two different things depending on how the window ended:

  - THEIR LIMIT STOPPED US. Then what arrived before the refusal is the whole minute's allowance, and
    that is the number. Not scaled. Cerebras returned 1,580 tokens in 1.3 seconds and then refused:
    the truth is 1,580 a minute, and the first version of this file printed 72,871.
  - THE WINDOW ENDED WITHOUT A REFUSAL. Then the rate is what arrived, scaled to sixty seconds - and
    only if the window lasted at least ten of them. Under that, no rate is reported at all.

Either way it is a FLOOR, not a ceiling: more concurrency, a closer region or a bigger machine would
raise it. It is the one number on this list that nobody has to take on trust.
"""
import argparse, json, os, queue, sys, threading, time, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import ALLOWED_HOSTS, ALLOWED_URL_PLACEHOLDERS
from http_safe import open_url

UA = "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"

# A prompt that makes a model write, without asking it to think. Reasoning models spend their whole
# budget in a <think> block and return an empty message, which would read as zero throughput when the
# provider was in fact working hard.
PROMPT = ("Write a plain description of how a bicycle works, for a curious ten-year-old. "
          "Around 300 words. No lists, no headings, just prose.")

WINDOW_SECONDS = 30
TOKEN_BUDGET = 25000
MAX_CONCURRENCY = 8
MAX_TOKENS_PER_CALL = 700


def resolve_url(url):
    for ph in set(__import__("re").findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url)):
        if ph not in ALLOWED_URL_PLACEHOLDERS:
            return None
        url = url.replace("{%s}" % ph, os.environ.get(ph, ""))
    return url


def one_call(url, key, model, extra_body, timeout):
    """(output_tokens, status, seconds, why). Counts tokens the provider reported where it can."""
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": MAX_TOKENS_PER_CALL, "temperature": 0.7, **(extra_body or {})}
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if key:
        headers["Authorization"] = "Bearer " + key
    started = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with open_url(req, timeout) as f:
            data = json.loads(f.read(400000).decode("utf-8", "replace"))
        usage = data.get("usage") or {}
        out = usage.get("completion_tokens")
        if out is None:
            # No usage block: count words and be explicit that it is an estimate, not their number.
            msg = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            out = int(len(msg.split()) * 1.3)
        return out, 200, round(time.time() - started, 2), ""
    except urllib.error.HTTPError as e:
        # The provider's own error text often names the calling account state - "your balance is
        # insufficient" - and that is a fact about the caller, not about them. The publication gate refuses
        # it, correctly. What a reader needs is what the ENDPOINT did, so the body is replaced by a
        # description of the behaviour and the status code is kept as the evidence.
        why = {402: "payment required: this endpoint will not serve an account with no credit",
               401: "the credential was rejected (401)",
               403: "the request was refused (403)",
               429: "rate limit",
               500: "provider error",
               502: "bad gateway",
               503: "no capacity behind the endpoint"}.get(e.code, "HTTP %s" % e.code)
        return 0, e.code, round(time.time() - started, 2), why
    except Exception as e:
        return 0, 0, round(time.time() - started, 2), type(e).__name__


def measure(prov, limits, window, budget):
    name = prov["name"]
    url = resolve_url(prov["url"])
    if not url or (urlparse(url).hostname or "") not in ALLOWED_HOSTS:
        return {"provider": name, "skipped": "host not in ALLOWED_HOSTS"}
    needs_key = bool(prov.get("key_env"))
    key = os.environ.get(prov["key_env"], "") if needs_key else ""
    if needs_key and not key:
        return {"provider": name, "skipped": "no key in this environment"}

    entry = (limits.get("providers") or {}).get(name) or {}
    am = entry.get("all_models") or {}
    rpm = am.get("rpm")
    # Never more requests in flight than their own published per-minute allowance. With 1 request a
    # minute allowed, this test is one request - and that is the honest answer for that provider.
    conc = max(1, min(MAX_CONCURRENCY, rpm if rpm else MAX_CONCURRENCY))
    model = prov["models"][0]["id"]
    extra = prov["models"][0].get("extra_body")
    timeout = prov.get("timeout_seconds", 90)

    results, lock = [], threading.Lock()
    stop = threading.Event()
    started = time.time()

    # A run that fails fast must not turn into a hammer. Measured on 2026-09-07: a provider returning
    # an instant 400 produced 461 requests in 31 seconds, because every worker simply looped. That is
    # not a measurement, it is a small denial-of-service against somebody who is giving us capacity
    # for free, and it is how an account gets closed. Consecutive failures stop the whole run.
    fails = {"n": 0, "last": ""}

    def worker():
        while not stop.is_set():
            out, code, secs, why = one_call(url, key, model, extra, timeout)
            with lock:
                results.append({"tokens": out, "http": code, "seconds": secs, "why": why})
                if code == 200:
                    fails["n"] = 0
                else:
                    fails["n"] += 1
                    fails["last"] = "HTTP %s %s" % (code, why)
                total = sum(r["tokens"] for r in results)
                if (code == 429 or fails["n"] >= 5 or total >= budget
                        or (time.time() - started) >= window):
                    stop.set()
            if code != 200 and not stop.is_set():
                time.sleep(2)          # never retry a failure at full speed

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(conc)]
    for t in threads:
        t.start()
    deadline = started + window + timeout
    while any(t.is_alive() for t in threads) and time.time() < deadline:
        if time.time() - started >= window:
            stop.set()
        time.sleep(0.25)
    stop.set()
    for t in threads:
        t.join(timeout=5)

    elapsed = max(0.001, time.time() - started)
    ok = [r for r in results if r["http"] == 200]
    tokens = sum(r["tokens"] for r in ok)
    limited = [r for r in results if r["http"] == 429]

    # THE RATE, and the one place this program could lie loudly.
    #
    # If a per-minute limit stopped us, then what arrived before the 429 IS the minute's allowance,
    # and dividing it by the seconds it took would be an extrapolation from noise. Cerebras returned
    # 1,580 tokens in 1.3 seconds and then refused: 1,580 a minute is the truth, 72,871 is arithmetic.
    # The first version of this file printed 72,871.
    #
    # If the window ran to the end without a refusal, the rate is real - but only if the window was
    # long enough to be one. Under ten seconds we report the tokens and no rate at all.
    if limited:
        rate = tokens
        basis = ("their per-minute limit stopped us, so this is the whole minute's allowance, "
                 "not a rate scaled up from %.1f seconds" % elapsed)
    elif elapsed >= 10:
        rate = int(tokens / elapsed * 60)
        basis = "delivered over %.0f seconds without a refusal, scaled to a minute" % elapsed
    else:
        rate = None
        basis = ("window too short to state a rate - %.1f seconds is noise, not throughput" % elapsed)

    return {
        "provider": name, "model": model, "concurrency": conc,
        "seconds": round(elapsed, 1),
        "requests_ok": len(ok), "requests_rate_limited": len(limited),
        "requests_failed": len(results) - len(ok) - len(limited),
        "output_tokens": tokens,
        "tokens_per_minute_measured": rate,
        "rate_basis": basis,
        "first_error": fails["last"] or None,
        "stopped_because": ("rate limit reached" if limited
                            else "five failures in a row: " + fails["last"] if fails["n"] >= 5
                            else "token budget spent" if tokens >= budget
                            else "window ended"),
        "note": "A floor, not a ceiling: more concurrency or a closer region would raise it.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="data/throughput.jsonl")
    ap.add_argument("--window", type=int, default=WINDOW_SECONDS)
    ap.add_argument("--budget", type=int, default=TOKEN_BUDGET)
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    ap.add_argument("--limits", default=str(HERE / "limits.json"))
    a = ap.parse_args()

    provs = json.loads(Path(a.providers).read_text(encoding="utf-8"))["providers"]
    limits = json.loads(Path(a.limits).read_text(encoding="utf-8"))
    if a.only:
        want = {x.strip() for x in a.only.split(",")}
        provs = [p for p in provs if p["name"] in want]

    print("window %ds, budget %s output tokens per provider, concurrency capped by their own RPM"
          % (a.window, "{:,}".format(a.budget)))
    print()
    rows = []
    for p in provs:
        r = measure(p, limits, a.window, a.budget)
        r["date"] = a.date
        rows.append(r)
        if r.get("skipped"):
            print("  %-12s skipped: %s" % (r["provider"], r["skipped"]))
        else:
            rate = r["tokens_per_minute_measured"]
            print("  %-12s %9s tokens/min   %s ok, %s limited, %ss, conc %d  (%s)"
                  % (r["provider"], "{:,}".format(rate) if rate is not None else "no rate",
                     r["requests_ok"], r["requests_rate_limited"], r["seconds"],
                     r["concurrency"], r["stopped_because"]))
        time.sleep(2)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    total = sum(r.get("tokens_per_minute_measured") or 0 for r in rows)
    print()
    print("measured total: %s tokens per minute across %d providers"
          % ("{:,}".format(total),
             sum(1 for r in rows if r.get("tokens_per_minute_measured") is not None)))
    print("appended %d rows to %s" % (len(rows), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
