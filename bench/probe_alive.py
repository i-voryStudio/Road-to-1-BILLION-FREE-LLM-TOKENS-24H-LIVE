#!/usr/bin/env python3
"""Ask every endpoint whether it is alive today. One tiny call each, appended to a dated history.

    export GROQ_API_KEY=... CEREBRAS_API_KEY=...
    python bench/probe_alive.py --date 2026-09-06

Writes one line per model per day to data/uptime.jsonl. That file is the whole point of the word LIVE
in this repo's name: without it, a "free API list" is a photograph of one afternoon, and every list in
this space eventually becomes exactly that.

WHAT IT COSTS: one call per model with `max_tokens: 64`. Across every provider we track that is a few
dozen tiny requests a day - far below any free tier, and deliberately so. A radar that eats the quota
it is measuring is not a radar.

Why 64 and not 5: measured on 2026-09-06, a 5-token budget made 14 of 33 endpoints report `empty`,
because a reasoning model spends its allowance thinking before it writes anything. That is a fact
about our probe, not about the provider, and a radar whose own settings manufacture outages is worse
than no radar. 64 tokens is enough for a short answer to survive a little thinking.

WHAT IT RECORDS, and the distinction matters more than the count:

    alive        200 with text in it
    empty        200 with NOTHING in it. Usually a reasoning model with no thinking switch, and it
                 costs you quota while looking like success. Not the same as alive.
    rate_limited 429 - the endpoint works, you are just out of quota for now
    overloaded   503 - their problem, not yours, and it may well pass
    down         anything else, including timeouts
    no_key       we hold no key, so we know nothing. NOT counted as down.

`no_key` is the honest one. A provider we cannot test is not a provider that is broken, and folding
those together would let our own missing credentials look like somebody else's outage.
"""
import argparse, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import ALLOWED_HOSTS, ALLOWED_URL_PLACEHOLDERS
from http_safe import open_url

UA = "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"
PROMPT = "Say OK."


def probe(url, key, model, extra_body, timeout=45):
    if (urlparse(url).hostname or "") not in ALLOWED_HOSTS:
        return "down", 0, 0.0, "host not in ALLOWED_HOSTS"
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 64, "temperature": 0, **(extra_body or {})}
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    # A keyless endpoint gets NO Authorization header at all. Sending "Bearer " with nothing after it
    # is not the same request a reader would make, and the answer to a different request is not
    # evidence about this one.
    if key:
        headers["Authorization"] = "Bearer " + key
    started = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with open_url(req, timeout) as f:
            data = json.loads(f.read(200000).decode("utf-8", "replace"))
        msg = (data.get("choices") or [{}])[0].get("message", {}) if isinstance(data, dict) else {}
        text = (msg.get("content") or "").strip()
        if not text and isinstance(data, dict) and isinstance(data.get("result"), dict):
            text = (data["result"].get("response") or "").strip()
        secs = round(time.time() - started, 2)
        return ("alive" if text else "empty"), 200, secs, ""
    except urllib.error.HTTPError as e:
        secs = round(time.time() - started, 2)
        # 402 is not an outage. The endpoint answered; what ran out is the money or the free
        # allowance on the calling account, and calling that "down" would blame the provider for our
        # empty pocket - and would start the 14-day death clock on a healthy endpoint.
        # "They are down" and "they refused the caller" are different facts and only one of them belongs to
        # the provider. 401/403 is the key or the caller's IP; 451 is a legal block on the caller's region; 406 is a bot
        # wall. Recording any of those as `down` starts a 14-day death clock on a healthy endpoint and
        # ends in a public, dated, false death notice - which for a list whose whole claim is honesty
        # is the worst thing it can print. `blocked` is neither up nor down: it is a fact about the caller.
        state = {429: "rate_limited", 503: "overloaded", 402: "payment_required",
                 401: "blocked", 403: "blocked", 406: "blocked", 451: "blocked"}.get(e.code, "down")
        return state, e.code, secs, ""
    except Exception as e:
        return "down", 0, round(time.time() - started, 2), type(e).__name__


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD, passed in so a run is reproducible")
    ap.add_argument("--out", default="data/uptime.jsonl")
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()

    provs = json.loads(Path(a.providers).read_text(encoding="utf-8"))["providers"]
    if a.only:
        want = {x.strip() for x in a.only.split(",")}
        provs = [p for p in provs if p["name"] in want]

    lines, counts = [], {}
    for p in provs:
        needs_key = bool(p.get("key_env"))
        key = os.environ.get(p["key_env"], "") if needs_key else ""
        url = p["url"]
        skip = ""
        for ph in set(__import__("re").findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url)):
            if ph not in ALLOWED_URL_PLACEHOLDERS:
                skip = "url interpolates an undeclared variable"
            url = url.replace("{%s}" % ph, os.environ.get(ph, ""))
        for m in p["models"]:
            if (needs_key and not key) or skip:
                state, code, secs, note = "no_key", None, None, skip or "no key set in this environment"
            else:
                state, code, secs, note = probe(url, key, m["id"], m.get("extra_body"),
                                                p.get("timeout_seconds", 45))
                time.sleep(p.get("pause_seconds", 2))
            counts[state] = counts.get(state, 0) + 1
            lines.append({"date": a.date, "provider": p["name"], "model": m["id"],
                          "state": state, "http": code, "seconds": secs, "note": note})
            print("  %-12s %-46s %-13s %s%s"
                  % (p["name"], m["id"][:46], state,
                     "%.2fs" % secs if secs is not None else "-",
                     "  " + note if note else ""), flush=True)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Append: the history IS the product. Rewriting it would erase the only thing that makes a
    # 14-day rule possible, and a file that only ever holds today is a photograph, not a radar.
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for row in lines:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\n%s: %s" % (a.date, ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items()))))
    tested = sum(v for k, v in counts.items() if k != "no_key")
    if tested:
        print("of the %d actually tested: %d alive (%.0f%%)"
              % (tested, counts.get("alive", 0), 100.0 * counts.get("alive", 0) / tested))
    print("appended %d rows to %s" % (len(lines), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
