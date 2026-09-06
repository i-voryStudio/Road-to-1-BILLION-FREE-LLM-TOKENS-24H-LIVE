#!/usr/bin/env python3
"""Ask each provider what your quota actually is, instead of reading it off a marketing page.

    python bench/measure_limits.py --date 2026-09-07

Most of our rows say UNKNOWN for tokens-per-day, and that understates the free tier badly: totalling
only what is published gave 1.2M tokens/day across ten providers, when a single one of them exposes 5M
through its own usage endpoint. UNKNOWN is honest, but it is not the same as unknowable — and where a
provider will tell you, asking beats guessing.

Two ways to ask, both cheap and neither of them scraping:

  1. A USAGE ENDPOINT. Some providers publish your remaining quota at a documented URL. One GET.
  2. RATE-LIMIT HEADERS. Most OpenAI-compatible endpoints return x-ratelimit-* on any normal call, so
     one tiny completion tells you the daily and per-minute ceilings and how much is left.

The rule OmniRoute states and we borrow: **response headers are read only through an explicit
per-provider mapping.** Generic header names are never assumed globally, because `x-ratelimit-remaining`
means requests at one provider and tokens at another, and mixing those up publishes a wrong number
with a confident face.

PACE YOURSELF. Measured the hard way on 2026-09-07: running this minutes after the daily radar tripped
Cerebras's 5-requests-per-minute ceiling, and the 403 came back with no rate-limit headers at all - which
reads exactly like a provider that publishes nothing. Run this on its own, not in a burst with anything
else, or you will measure your own impatience.

Nothing here is written to limits.json automatically. It prints what it found and you paste it in with
the date - a measurement still needs a human deciding it is the right measurement.
"""
import argparse, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import ALLOWED_HOSTS, ALLOWED_URL_PLACEHOLDERS

UA = "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"

# Explicit per-provider mapping. A header name is only trusted where it is listed here.
HEADER_MAP = {
    "groq": {"requests_per_day": "x-ratelimit-limit-requests",
             "requests_left": "x-ratelimit-remaining-requests",
             "tokens_per_minute": "x-ratelimit-limit-tokens",
             "tokens_left": "x-ratelimit-remaining-tokens"},
    "cerebras": {"requests_per_day": "x-ratelimit-limit-requests-day",
                 "requests_left": "x-ratelimit-remaining-requests-day",
                 "tokens_per_day": "x-ratelimit-limit-tokens-day",
                 "tokens_left": "x-ratelimit-remaining-tokens-day",
                 "requests_per_minute": "x-ratelimit-limit-requests-minute"},
    "openrouter": {"requests_left": "x-ratelimit-remaining"},
}

# Documented usage endpoints, one GET each.
USAGE_ENDPOINT = {
    "xkiro": "https://api.xkiro.com/v1/usage",
    "openrouter": "https://openrouter.ai/api/v1/key",
}


def get_json(url, key, timeout=45):
    if (urlparse(url).hostname or "") not in ALLOWED_HOSTS:
        return None, "host not in ALLOWED_HOSTS"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            return json.loads(f.read(400000).decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except Exception as e:
        return None, type(e).__name__


def probe_headers(url, key, model, extra_body, timeout=45):
    if (urlparse(url).hostname or "") not in ALLOWED_HOSTS:
        return None, "host not in ALLOWED_HOSTS"
    body = {"model": model, "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 8, "temperature": 0, **(extra_body or {})}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            f.read(20000)
            return {k.lower(): v for k, v in f.headers.items()}, None
    except urllib.error.HTTPError as e:
        # A 429 carries the limit headers too, and is in fact the most informative answer here.
        return {k.lower(): v for k, v in e.headers.items()}, "HTTP %s" % e.code
    except Exception as e:
        return None, type(e).__name__


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    a = ap.parse_args()

    provs = json.loads(Path(a.providers).read_text(encoding="utf-8"))["providers"]
    if a.only:
        want = {x.strip() for x in a.only.split(",")}
        provs = [p for p in provs if p["name"] in want]

    found = {}
    for p in provs:
        name = p["name"]
        key = os.environ.get(p["key_env"], "")
        if not key:
            print("%-12s no key set, skipped" % name)
            continue

        # 1. usage endpoint, where one is documented
        if name in USAGE_ENDPOINT:
            data, err = get_json(USAGE_ENDPOINT[name], key)
            if data:
                found.setdefault(name, {})["usage_endpoint"] = {"url": USAGE_ENDPOINT[name], "body": data}
                print("%-12s usage endpoint: %s" % (name, json.dumps(data)[:220]))
            else:
                print("%-12s usage endpoint failed: %s" % (name, err))

        # 2. rate-limit headers, only through the explicit mapping
        url = p["url"]
        for ph in set(__import__("re").findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url)):
            if ph not in ALLOWED_URL_PLACEHOLDERS:
                url = None
                break
            url = url.replace("{%s}" % ph, os.environ.get(ph, ""))
        if url and name in HEADER_MAP:
            m = p["models"][0]
            headers, err = probe_headers(url, key, m["id"], m.get("extra_body"),
                                         p.get("timeout_seconds", 45))
            if headers:
                got = {label: headers[h] for label, h in HEADER_MAP[name].items() if h in headers}
                if got:
                    found.setdefault(name, {})["headers"] = got
                    print("%-12s headers: %s%s" % (name, json.dumps(got),
                                                   "  (from %s)" % err if err else ""))
                else:
                    # Say WHY there were none. "no headers" and "we were blocked" look identical here
                    # and mean opposite things: measured on 2026-09-07, running the radar and this
                    # script minutes apart tripped Cerebras's 5-per-minute limit, and the 403 that came
                    # back carried no rate-limit headers at all. Reported as "no headers", that would
                    # have looked like the provider publishing nothing.
                    present = [h for h in headers if "ratelimit" in h or "rate-limit" in h]
                    why = ("blocked or refused: %s - not evidence that they publish nothing" % err
                           if err else "answered 200 but exposed no mapped headers")
                    print("%-12s %s%s" % (name, why,
                                          "; unmapped seen: %s" % present if present else ""))
            else:
                print("%-12s header probe failed: %s" % (name, err))
        time.sleep(p.get("pause_seconds", 2))

    print()
    if not found:
        print("Nothing new measured. That is a result too: it means these providers do not tell you.")
        return 0
    print("=== MEASURED %s - paste into bench/limits.json with this date ===" % a.date)
    print(json.dumps(found, indent=1)[:4000])
    print()
    print("Nothing was written automatically. A measurement still needs a human deciding it is the")
    print("right measurement, and limits.json wants the source and date beside every number.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
