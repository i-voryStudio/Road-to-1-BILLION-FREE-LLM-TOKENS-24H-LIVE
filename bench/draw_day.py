#!/usr/bin/env python3
"""Draw from a provider for an hour at its own published pace, and record what actually arrived.

    python bench/draw_day.py --date 2026-09-07 --only alibaba,hetzner,mistral
    python bench/draw_day.py --date 2026-09-07 --dry-run

`throughput.py` answers "how much comes back in thirty seconds of pushing". This answers a different
question, in the unit the target is written in: how many output tokens a provider hands over across
an HOUR of ordinary, paced use. A burst says the ceiling is real. An hour says whether it holds - and
on 2026-09-07 one provider gave 66,197 tokens a minute on the first burst and 1,446 on the second,
minutes later, so the two readings are not the same fact.

HOW IT DRAWS. One model per provider, the first in providers.json. `max_tokens` 700 and the same prose
prompt as the burst meter. The pace is the provider's own figure:

    requests per minute = the published rpm, or 12 a minute where nothing is published,
                          and never above 120 whatever the page says

read from limits.json: `all_models.rpm` for most providers, the highest per-model `rpm` under `models`
for the ones that publish a table. Their own limit is the bound: a provider that publishes 600 a
minute is measured at 120, the safety ceiling, not at a number we made up. Never more than two
requests in flight. This is a metronome, not a hammer. Launching at or under their own figure is the
difference between measuring a free tier and abusing one, and every provider runs in its own thread
so the whole draw takes one hour, not eighteen.

WHAT STOPS IT, and every reason is written into the row as `stopped_because`:

    - the wall clock (`--minutes`, 60 by default)
    - a hard cap of 250,000 output tokens per provider per run, whatever the clock says. `--cap` can
      lower it freely. It can raise it, to at most 1,000,000, only together with the flag
      `--i-know-this-spends-quota`: a bigger draw is a bigger bite out of somebody's free tier, and
      the person taking it has to say so on the command line.
    - 401, 402 or 403 on two consecutive calls: the account, not the provider, is the problem
    - HTTP 429 on every call for five consecutive minutes. A single 429 costs a 30-second pause and is
      counted, because a limit reached once is a data point and a limit held for five minutes is the
      answer.
    - ten provider-side 5xx in a row, or twenty failures of any kind in a row
    - Ctrl-C. The rows drawn so far are still written, with the interruption as the reason.

WHAT THE ROW SAYS. `output_tokens_drawn` is what their `usage` block reported. Where a provider sends
no usage block at all, the count is words x 1.3 and the row carries `tokens_estimated: true`: an
estimate is not their number and must not be read as one. `tokens_per_hour_drawn` is stated in two
cases and no other:

    - the run lasted at least twenty minutes, or
    - the token cap ended it after at least five minutes and fifty successful requests. A cap
      reached quickly is a well-measured HIGH rate, not noise: the provider handed over a quarter
      of a million tokens and the clock says how fast. Under five minutes or fifty requests the same
      stop is too few samples to scale, and the figure stays null.

Under either floor it is null and `tokens_per_hour_basis` says why. Either way it is a FLOOR at our
pace, the caller's region and one key. It is not their ceiling. `gate_contributions.py` reads
data/drawn.jsonl against exactly these rules, through the functions below, so a row that this
program could not have written does not reach the front page.

No provider error body is ever written. Their error text describes the calling account, which is a fact
about the caller and not about them, so the status code is kept as the evidence and the body is replaced by a
sentence describing what the endpoint did. Every request goes through `open_url` from http_safe, so
a redirect to another host is refused before the key can travel there.
"""
import argparse, json, os, sys, threading, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import ALLOWED_HOSTS
from http_safe import open_url
from throughput import PROMPT, resolve_url   # one prompt and one placeholder rule for both meters

UA = "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"

MINUTES = 60
TOKEN_CAP = 250000              # per provider per run, whatever the clock says
TOKEN_CAP_MAX = 1000000         # the most --cap may ask for, and only with --i-know-this-spends-quota
MAX_PACE_RPM = 120              # a safety ceiling over the published figure, never a pace of our own
DEFAULT_RPM = 12                # one request every five seconds where nothing is published
MAX_IN_FLIGHT = 2
MAX_TOKENS_PER_CALL = 700
BACKOFF_429_SECONDS = 30
PERSIST_429_SECONDS = 300       # five minutes of nothing but 429 is the answer
AUTH_STOP_STREAK = 2
SERVER_ERROR_STOP_STREAK = 10
ANY_FAILURE_STOP_STREAK = 20
MIN_MINUTES_FOR_RATE = 20       # a rate needs this much clock...
CAP_STOP_MIN_MINUTES = 5        # ...unless the cap stopped the run, after at least this much clock
CAP_STOP_MIN_REQUESTS = 50      # ...and at least this many successful requests
CAP_STOP_PREFIX = "token cap reached: "     # the stop the gate recognises by its first words

# The same sentences the burst meter uses. What the ENDPOINT did, never what its body said about the caller.
BEHAVIOUR = {402: "payment required: this endpoint will not serve an account with no credit",
             401: "the credential was rejected (401)",
             403: "the request was refused (403)",
             429: "rate limit",
             500: "provider error",
             502: "bad gateway",
             503: "no capacity behind the endpoint"}

ROW_FIELDS = ("provider", "model", "date", "started_utc", "minutes_planned", "minutes_run",
              "pace_rpm", "pace_basis", "requests_ok", "requests_429", "requests_failed",
              "first_error", "output_tokens_drawn", "tokens_estimated", "tokens_per_hour_drawn",
              "tokens_per_hour_basis", "stopped_because", "note")


def label(code, why):
    """'HTTP 402 payment required: ...' from a status code, or the exception's class name."""
    if not code:
        return why or "no response"
    return "HTTP %d %s" % (code, BEHAVIOUR[code]) if code in BEHAVIOUR else "HTTP %d" % code


def human_seconds(seconds):
    if seconds >= 60 and seconds % 60 == 0:
        m = int(seconds // 60)
        return "%d minute%s" % (m, "" if m == 1 else "s")
    return "%g seconds" % seconds


def pace_for(entry, max_pace=MAX_PACE_RPM):
    """(requests per minute, how we got there) from one provider's limits.json entry.

    Two shapes exist in that file: `all_models.rpm` for a provider with one figure, and a per-model
    table under `models` for the ones that publish one. The table is read as its highest rpm, because
    that is the most any single model there is allowed - we draw one model. Their figure is the pace;
    `max_pace` is a safety ceiling above it, not a pace of our own.
    """
    entry = entry or {}
    published = None
    am = entry.get("all_models") or {}
    if isinstance(am.get("rpm"), (int, float)) and am["rpm"] > 0:
        published = int(am["rpm"])
    else:
        table = entry.get("models") or {}
        rpms = [m.get("rpm") for m in table.values() if isinstance(m, dict)]
        rpms = [int(r) for r in rpms if isinstance(r, (int, float)) and r > 0]
        if rpms:
            published = max(rpms)
    if published is None:
        return DEFAULT_RPM, "default %d, nothing published" % DEFAULT_RPM
    if published > max_pace:
        return max_pace, "published rpm %d, capped at %d" % (published, max_pace)
    return published, "published rpm %d" % published


def rate_allowed(minutes_run, requests_ok=0, cap_reached=False):
    """May a run of this shape state an hourly rate? Twenty minutes of clock, or the token cap
    reached after five minutes and fifty successful requests. The gate applies this same predicate
    to every row in data/drawn.jsonl."""
    if minutes_run >= MIN_MINUTES_FOR_RATE:
        return True
    return bool(cap_reached) and minutes_run >= CAP_STOP_MIN_MINUTES and requests_ok >= CAP_STOP_MIN_REQUESTS


def hourly(tokens, minutes_run, requests_ok=0, cap_reached=False):
    """(tokens per hour or None, the sentence that says why)."""
    if minutes_run <= 0:
        return None, "no hourly figure: the run had no length"
    if rate_allowed(minutes_run, requests_ok, cap_reached):
        if minutes_run >= MIN_MINUTES_FOR_RATE:
            return int(tokens / minutes_run * 60), "scaled from %.1f minutes of drawing" % minutes_run
        return int(tokens / minutes_run * 60), ("scaled from %.1f minutes of drawing: the token cap ended "
                                                "the run after %d successful requests, which is a measured "
                                                "high rate, not noise" % (minutes_run, requests_ok))
    if cap_reached:
        return None, ("no hourly figure: the token cap ended the run at %.1f minutes and %d successful "
                      "requests, under the %d-minute and %d-request floor for a cap stop; too few samples "
                      "to scale" % (minutes_run, requests_ok, CAP_STOP_MIN_MINUTES, CAP_STOP_MIN_REQUESTS))
    return None, ("no hourly figure: %.1f minutes is under the %d-minute floor, and an hour scaled up "
                  "from that would be arithmetic, not measurement" % (minutes_run, MIN_MINUTES_FOR_RATE))


def plan_for(prov, limits, allowed_hosts=None, max_pace=MAX_PACE_RPM):
    """What a run WOULD do for this provider, decided before any request: the dry run prints this
    and the real run follows it. Returns {"skipped": why} where there is nothing to draw."""
    allowed = ALLOWED_HOSTS if allowed_hosts is None else allowed_hosts
    name = prov["name"]
    url = resolve_url(prov["url"])
    if not url or (urlparse(url).hostname or "") not in allowed:
        return {"provider": name, "skipped": "host not in ALLOWED_HOSTS"}
    needs_key = bool(prov.get("key_env"))
    key = os.environ.get(prov["key_env"], "") if needs_key else ""
    if needs_key and not key:
        return {"provider": name, "skipped": "no key in this environment"}
    entry = (limits.get("providers") or {}).get(name) or {}
    rpm, basis = pace_for(entry, max_pace)
    return {"provider": name, "url": url, "key": key, "host": urlparse(url).hostname,
            "model": prov["models"][0]["id"], "extra_body": prov["models"][0].get("extra_body"),
            "timeout": prov.get("timeout_seconds", 90), "pace_rpm": rpm, "pace_basis": basis,
            "credential": ("env " + prov["key_env"]) if needs_key else "none, keyless endpoint"}


def one_call(url, key, model, extra_body, timeout):
    """(output_tokens, status, seconds, why, estimated). Their count where they send one."""
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": MAX_TOKENS_PER_CALL, "temperature": 0.7, **(extra_body or {})}
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if key:   # a keyless endpoint gets no Authorization header at all
        headers["Authorization"] = "Bearer " + key
    started = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with open_url(req, timeout) as f:
            data = json.loads(f.read(400000).decode("utf-8", "replace"))
        secs = round(time.time() - started, 2)
        usage = data.get("usage") if isinstance(data, dict) else None
        out = usage.get("completion_tokens") if isinstance(usage, dict) else None
        if isinstance(out, (int, float)) and not isinstance(out, bool):
            return int(out), 200, secs, "", False
        # No usage block: count words and say so. The burst meter forgot to say so; this one does not.
        msg = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return int(len(msg.split()) * 1.3), 200, secs, "", True
    except urllib.error.HTTPError as e:
        # The body is dropped here and never stored: it is where "your balance is insufficient" lives.
        return 0, e.code, round(time.time() - started, 2), BEHAVIOUR.get(e.code, "HTTP %s" % e.code), False
    except Exception as e:
        return 0, 0, round(time.time() - started, 2), type(e).__name__, False


def draw(prov, limits, minutes=MINUTES, cap=TOKEN_CAP, *, date=None, halt=None, log=print,
         allowed_hosts=None, seconds=None, max_pace=MAX_PACE_RPM,
         backoff_seconds=BACKOFF_429_SECONDS, persist_seconds=PERSIST_429_SECONDS):
    """Draw from one provider and return its row.

    The keyword arguments after `log` exist for the test, which runs this against a server on the
    loopback address for a few seconds. The command line never sets them: `allowed_hosts` widens the
    allowlist for that one call without touching the gate, `seconds` replaces the minutes, `max_pace`
    lets a fast fake prove the metronome, and the two 429 timings shrink so a five-minute rule can be
    watched in half a second.
    """
    plan = plan_for(prov, limits, allowed_hosts, max_pace)
    if plan.get("skipped"):
        return plan
    name, url, key, model = plan["provider"], plan["url"], plan["key"], plan["model"]
    extra, timeout, rpm = plan["extra_body"], plan["timeout"], plan["pace_rpm"]
    interval = 60.0 / rpm
    window = float(seconds) if seconds is not None else minutes * 60.0

    s = {"ok": 0, "r429": 0, "failed": 0, "tokens": 0, "estimated": False, "first_error": "",
         "streak_auth": 0, "streak_5xx": 0, "streak_fail": 0, "since_429": None, "hold_until": 0.0,
         "stop": None}
    lock = threading.Lock()
    started_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.monotonic()

    def finish(out, code, why, estimated):
        """Fold one answer into the state and decide, under the lock, whether it ends the run."""
        now = time.monotonic()
        with lock:
            if code == 200:
                s["ok"] += 1
                s["tokens"] += out
                s["estimated"] = s["estimated"] or estimated
                s["streak_auth"] = s["streak_5xx"] = s["streak_fail"] = 0
                s["since_429"] = None
            elif code == 429:
                s["r429"] += 1
                s["streak_auth"] = s["streak_5xx"] = 0
                if s["since_429"] is None:
                    s["since_429"] = now
                s["hold_until"] = now + backoff_seconds
            else:
                s["failed"] += 1
                s["streak_fail"] += 1
                s["streak_auth"] = s["streak_auth"] + 1 if code in (401, 402, 403) else 0
                s["streak_5xx"] = s["streak_5xx"] + 1 if 500 <= code < 600 else 0
                s["since_429"] = None
            if code != 200 and not s["first_error"]:
                s["first_error"] = label(code, why)
            if s["stop"] is not None:
                return
            if s["tokens"] >= cap:
                s["stop"] = "%s%s output tokens" % (CAP_STOP_PREFIX, "{:,}".format(cap))
            elif s["streak_auth"] >= AUTH_STOP_STREAK:
                s["stop"] = "%s on two consecutive calls" % label(code, why)
            elif s["streak_5xx"] >= SERVER_ERROR_STOP_STREAK:
                s["stop"] = "ten provider-side errors in a row, the last %s" % label(code, why)
            elif s["streak_fail"] >= ANY_FAILURE_STOP_STREAK:
                s["stop"] = "twenty failures in a row, the last %s" % label(code, why)
            elif s["since_429"] is not None and now - s["since_429"] >= persist_seconds:
                s["stop"] = ("rate limited: HTTP 429 on every call for %s, their limit is holding"
                             % human_seconds(persist_seconds))

    def worker():
        out, code, _secs, why, estimated = one_call(url, key, model, extra, timeout)
        finish(out, code, why, estimated)

    threads, next_at, reported = [], t0, 0
    while True:
        now = time.monotonic()
        with lock:
            stop, hold_until, tokens = s["stop"], s["hold_until"], s["tokens"]
        if stop:
            break
        if now - t0 >= window:
            with lock:
                s["stop"] = "window ended: %s planned" % human_seconds(window)
            break
        if halt is not None and halt.is_set():
            with lock:
                s["stop"] = "interrupted from the keyboard after %.1f minutes" % ((now - t0) / 60)
            break
        minute = int((now - t0) // 60)
        if minute > reported:
            reported = minute
            with lock:
                log("  %-12s minute %2d: %s output tokens drawn, %d ok, %d limited, %d failed"
                    % (name, minute, "{:,}".format(tokens), s["ok"], s["r429"], s["failed"]))
        threads = [t for t in threads if t.is_alive()]
        launch_at = max(next_at, hold_until)
        if now >= launch_at and len(threads) < MAX_IN_FLIGHT:
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
            next_at = now + interval     # a strict gap: never more than rpm launches in any minute
        else:
            time.sleep(min(0.05, launch_at - now) if now < launch_at else 0.02)

    for t in threads:                    # an answer still on its way is still tokens we drew
        t.join(timeout=timeout + 5)
    elapsed_min = (time.monotonic() - t0) / 60
    cap_reached = (s["stop"] or "").startswith(CAP_STOP_PREFIX)
    rate, rate_basis = hourly(s["tokens"], elapsed_min, s["ok"], cap_reached)
    return {
        "provider": name, "model": model, "date": date, "started_utc": started_utc,
        "minutes_planned": round(window / 60, 3), "minutes_run": round(elapsed_min, 2),
        "pace_rpm": rpm, "pace_basis": plan["pace_basis"],
        "requests_ok": s["ok"], "requests_429": s["r429"], "requests_failed": s["failed"],
        "first_error": s["first_error"] or None,
        "output_tokens_drawn": s["tokens"], "tokens_estimated": s["estimated"],
        "tokens_per_hour_drawn": rate, "tokens_per_hour_basis": rate_basis,
        "stopped_because": s["stop"],
        "note": ("Drawn at %d requests a minute, at most %d in flight, one model, one key. A floor at "
                 "our pace, not their ceiling." % (rpm, MAX_IN_FLIGHT)),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD, passed in so a run is reproducible")
    ap.add_argument("--only", default="")
    ap.add_argument("--minutes", type=int, default=MINUTES)
    ap.add_argument("--cap", type=int, default=TOKEN_CAP,
                    help="output tokens per provider per run; lower it freely, raise it to at most %d "
                         "only with --i-know-this-spends-quota" % TOKEN_CAP_MAX)
    ap.add_argument("--i-know-this-spends-quota", action="store_true",
                    help="required to raise --cap above %d: a bigger draw is a bigger bite out of "
                         "somebody's free tier" % TOKEN_CAP)
    ap.add_argument("--out", default="data/drawn.jsonl")
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    ap.add_argument("--limits", default=str(HERE / "limits.json"))
    ap.add_argument("--dry-run", action="store_true", help="print the plan and send nothing")
    a = ap.parse_args(argv)
    if a.minutes <= 0:
        ap.error("--minutes must be positive")
    if not 0 < a.cap <= TOKEN_CAP_MAX:
        ap.error("--cap must be between 1 and %d" % TOKEN_CAP_MAX)
    if a.cap > TOKEN_CAP and not a.i_know_this_spends_quota:
        ap.error("--cap %d is above the default %d; raising it spends somebody's free quota, so say so "
                 "with --i-know-this-spends-quota" % (a.cap, TOKEN_CAP))

    provs = json.loads(Path(a.providers).read_text(encoding="utf-8"))["providers"]
    limits = json.loads(Path(a.limits).read_text(encoding="utf-8"))
    if a.only:
        want = {x.strip() for x in a.only.split(",")}
        provs = [p for p in provs if p["name"] in want]

    print("drawing for %d minutes per provider at the published rpm (%d where none is published, never "
          "above %d), at most %d in flight, %d tokens a call, cap %s output tokens per provider"
          % (a.minutes, DEFAULT_RPM, MAX_PACE_RPM, MAX_IN_FLIGHT, MAX_TOKENS_PER_CALL,
             "{:,}".format(a.cap)))
    print()

    if a.dry_run:
        for p in provs:
            plan = plan_for(p, limits)
            if plan.get("skipped"):
                print("  %-12s skipped: %s" % (plan["provider"], plan["skipped"]))
            else:
                print("  %-12s %2d/min (%s)  %s  credential: %s  host: %s"
                      % (plan["provider"], plan["pace_rpm"], plan["pace_basis"], plan["model"],
                         plan["credential"], plan["host"]))
        print()
        print("dry run: no request was sent, nothing was written")
        return 0

    halt, plock, rows = threading.Event(), threading.Lock(), {}

    def run(p):
        r = draw(p, limits, a.minutes, a.cap, date=a.date, halt=halt)
        with plock:
            rows[p["name"]] = r
            if r.get("skipped"):
                print("  %-12s skipped: %s" % (r["provider"], r["skipped"]))
            else:
                rate = r["tokens_per_hour_drawn"]
                print("  %-12s %10s tokens/hour   %s tokens in %.1f min, %d ok, %d limited, %d failed"
                      "  (%s)%s"
                      % (r["provider"], "{:,}".format(rate) if rate is not None else "no rate",
                         "{:,}".format(r["output_tokens_drawn"]), r["minutes_run"], r["requests_ok"],
                         r["requests_429"], r["requests_failed"], r["stopped_because"],
                         "  [estimated: no usage block]" if r["tokens_estimated"] else ""))

    threads = [threading.Thread(target=run, args=(p,), daemon=True) for p in provs]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.5)
    except KeyboardInterrupt:
        halt.set()
        print("\ninterrupted: waiting for the requests in flight, then writing what was drawn")
        for t in threads:
            t.join(timeout=200)

    written = [rows[p["name"]] for p in provs if p["name"] in rows and not rows[p["name"]].get("skipped")]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for r in written:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print()
    print("drawn total: %s output tokens across %d providers, %d with an hourly figure"
          % ("{:,}".format(sum(r["output_tokens_drawn"] for r in written)), len(written),
             sum(1 for r in written if r["tokens_per_hour_drawn"] is not None)))
    print("appended %d rows to %s" % (len(written), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
