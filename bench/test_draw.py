#!/usr/bin/env python3
"""Tests for the hour-long draw meter. No network, no keys, no real provider.

A fake provider runs on the loopback address in a thread and answers the OpenAI shape from four
doors: one with a `usage` block, one without, one that only ever says 429, and one that reports a
hundred thousand tokens a call so the cap can be watched closing. Everything the meter promises is
pinned here in both directions where a direction exists: the pace must never be exceeded, the
estimate flag must be true for the door without usage and false for the one with it, every stop must
carry its documented reason, and no provider error body may reach a row.

    python bench/test_draw.py
"""
import contextlib, io, json, os, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw_day as D
from gate_contributions import ALLOWED_HOSTS

# What the specification says a row holds. Kept HERE, apart from draw_day.ROW_FIELDS, so a field
# quietly dropped from the meter is caught rather than agreed with.
SPEC_FIELDS = {"provider", "model", "date", "started_utc", "minutes_planned", "minutes_run",
               "pace_rpm", "pace_basis", "requests_ok", "requests_429", "requests_failed",
               "first_error", "output_tokens_drawn", "tokens_estimated", "tokens_per_hour_drawn",
               "stopped_because", "note"}

# A phrase planted in every fake error body. If it ever shows up in a row, the meter copied a
# provider's error text, which is where a provider describes the calling account.
POISON = "PROVIDER-ERROR-BODY-MUST-NOT-BE-COPIED"
FAKE_KEY = "test-key"           # short on purpose: the publication gate hunts for real-looking ones

HITS, INFLIGHT, PEAK, AUTH = {}, {"n": 0}, {"n": 0}, {}
LOCK = threading.Lock()


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):   # keep the test output ours
        pass

    def do_POST(self):
        door = self.path.split("/v1/")[0]
        with LOCK:
            HITS.setdefault(door, []).append(time.monotonic())
            AUTH.setdefault(door, set()).add(self.headers.get("Authorization"))
            INFLIGHT["n"] += 1
            PEAK["n"] = max(PEAK["n"], INFLIGHT["n"])
        try:
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if door == "/slow":
                time.sleep(0.3)
            if door == "/limited":
                return self.answer(429, {"error": {"message": POISON}})
            if door == "/auth":
                return self.answer(402, {"error": {"message": POISON}})
            if door == "/down":
                return self.answer(503, {"error": {"message": POISON}})
            words = "one two three four five six seven eight nine ten"
            body = {"choices": [{"message": {"role": "assistant", "content": words}}]}
            if door in ("/usage", "/slow"):
                body["usage"] = {"prompt_tokens": 40, "completion_tokens": 50}
            elif door == "/big":
                body["usage"] = {"prompt_tokens": 40, "completion_tokens": 100000}
            self.answer(200, body)
        finally:
            with LOCK:
                INFLIGHT["n"] -= 1

    def answer(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def provider(port, door, keyed=True):
    p = {"name": "fake" + door.strip("/"), "url": "http://127.0.0.1:%d%s/v1/chat/completions" % (port, door),
         "timeout_seconds": 10, "models": [{"id": "fake-model"}]}
    if keyed:
        p["key_env"] = "DRAW_TEST_KEY"
    else:
        p["auth"] = "none"
    return p


def limits(rpm):
    return {"providers": {"fake%s" % d: {"all_models": {"rpm": rpm}}
                          for d in ("usage", "nousage", "limited", "big", "auth", "down", "slow")}}


FAST = dict(allowed_hosts=ALLOWED_HOSTS | {"127.0.0.1"}, max_pace=600, backoff_seconds=0.05,
            persist_seconds=0.5, log=lambda *a: None, date="2026-01-01")


def main():
    fails = []

    def check(ok, what, why=""):
        print("%s %s%s" % ("ok  " if ok else "FAIL", what, ("  -> " + why) if (why and not ok) else ""))
        if not ok:
            fails.append(what)

    # --- pure pieces: the pace and the hourly rule -------------------------------------------
    check(D.pace_for({"all_models": {"rpm": 5}}) == (5, "published rpm 5"), "pace: all_models.rpm is read")
    check(D.pace_for({"models": {"a": {"rpm": 30}, "b": {"rpm": 15}, "c": {}}}) == (30, "published rpm 30"),
          "pace: per-model table read as its highest rpm")
    check(D.pace_for({"all_models": {"rpm": 300}}) == (30, "published rpm 300, capped at 30"),
          "pace: a published 300 is capped at 30")
    check(D.pace_for({"all_models": {"rpd": 1000, "tpd": 5000000}}) == (12, "default 12, nothing published"),
          "pace: nothing published means 12 a minute, one request every five seconds")
    check(D.pace_for({"all_models": {"rpm": None}, "models": {"a": {"rpm": None}}})[0] == 12,
          "pace: null rpm in both shapes is not a figure")
    check(D.pace_for(None)[0] == 12, "pace: a provider missing from limits.json gets the default")
    check(D.hourly(1000, 30) == (2000, "scaled from 30.0 minutes of drawing"), "hourly: 1,000 in 30 min is 2,000 an hour")
    r, why = D.hourly(1000, 19.9)
    check(r is None and "under the 20-minute floor" in why, "hourly: 19.9 minutes gives no rate, with the reason")

    # --- the fake provider -------------------------------------------------------------------
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["DRAW_TEST_KEY"] = FAKE_KEY
    try:
        # Host discipline: without the widened allowlist the loopback address is refused, and the
        # server sees nothing.
        row = D.draw(provider(port, "/usage"), limits(600), seconds=1, log=lambda *a: None)
        check(row.get("skipped") == "host not in ALLOWED_HOSTS" and "/usage" not in HITS,
              "a host outside ALLOWED_HOSTS is refused before any request", json.dumps(row))
        del os.environ["DRAW_TEST_KEY"]
        row = D.draw(provider(port, "/usage"), limits(600), seconds=1, **FAST)
        check(row.get("skipped") == "no key in this environment" and "/usage" not in HITS,
              "a provider whose key is not set is skipped, not called", json.dumps(row))
        os.environ["DRAW_TEST_KEY"] = FAKE_KEY

        # The dry run sends nothing: against the fake, and against the repo's own providers file,
        # where with no key in the environment it can only plan the keyless endpoints.
        with tempfile.TemporaryDirectory() as tmp:
            pj, lj = Path(tmp) / "providers.json", Path(tmp) / "limits.json"
            pj.write_text(json.dumps({"providers": [provider(port, "/usage")]}), encoding="utf-8")
            lj.write_text(json.dumps(limits(600)), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = D.main(["--date", "2026-01-01", "--dry-run", "--providers", str(pj), "--limits", str(lj)])
        check(rc == 0 and not HITS and "dry run: no request was sent" in out.getvalue(),
              "--dry-run exits 0 and sends no request", "hits: %s" % sorted(HITS))
        real = json.loads((Path(__file__).resolve().parent / "providers.json").read_text(encoding="utf-8"))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = D.main(["--date", "2026-01-01", "--dry-run"])
        lines = [l for l in out.getvalue().splitlines() if l.startswith("  ")]
        check(rc == 0 and len(lines) == len(real["providers"])
              and all(("skipped: " in l) or ("/min (" in l) for l in lines),
              "--dry-run on the repo's providers prints one plan or one skip per provider",
              "%d lines for %d providers" % (len(lines), len(real["providers"])))

        # The metronome: 600 a minute asked for, one launch every 0.1 s, at most two in flight.
        row = D.draw(provider(port, "/usage"), limits(600), seconds=3, **FAST)
        t = HITS.get("/usage", [])
        k = 10                                             # 600 rpm is 10 requests a second
        gaps_ok = all(t[i + k] - t[i] >= 1.0 - 0.05 for i in range(len(t) - k))
        check(len(t) >= 15 and gaps_ok and len(t) <= 600 * 3 / 60 + 2,
              "pace: any one-second window on the server holds at most rpm/60 requests",
              "%d requests, gaps ok %s" % (len(t), gaps_ok))
        check(row["requests_ok"] == len(t) and row["output_tokens_drawn"] == 50 * len(t),
              "usage block: their completion_tokens are what is counted")
        check(row["tokens_estimated"] is False, "usage block: tokens_estimated is false")
        check(row["stopped_because"] == "window ended: 3 seconds planned", "the clock stop names the window",
              row["stopped_because"])
        check(row["tokens_per_hour_drawn"] is None and "under the 20-minute floor" in row["tokens_per_hour_basis"],
              "under twenty minutes the hourly figure is null, with the reason in the row")
        check(AUTH.get("/usage") == {"Bearer " + FAKE_KEY}, "a keyed provider gets exactly one Bearer header")
        check(row["first_error"] is None and row["requests_failed"] == 0 and row["requests_429"] == 0,
              "a clean run records no error")
        check(set(row) == set(D.ROW_FIELDS) and SPEC_FIELDS <= set(row),
              "the row carries every field of the specification, and nothing undeclared",
              "missing %s, extra %s" % (SPEC_FIELDS - set(row), set(row) - set(D.ROW_FIELDS)))
        check(all(row[f] is not None for f in SPEC_FIELDS - {"first_error", "tokens_per_hour_drawn"}),
              "no field is left unset on a clean row")

        # At most two in flight, even when the provider is slower than the metronome.
        PEAK["n"] = 0
        row = D.draw(provider(port, "/slow", keyed=False), limits(600), seconds=1.5, **FAST)
        check(PEAK["n"] <= 2 and len(HITS.get("/slow", [])) >= 4,
              "never more than two requests in flight against a slow endpoint",
              "peak %d, %d requests" % (PEAK["n"], len(HITS.get("/slow", []))))
        check(AUTH.get("/slow") == {None}, "a keyless endpoint gets no Authorization header at all")

        # No usage block: words x 1.3, and the row says it is an estimate.
        row = D.draw(provider(port, "/nousage"), limits(600), seconds=1, **FAST)
        n = len(HITS.get("/nousage", []))
        check(row["tokens_estimated"] is True and row["output_tokens_drawn"] == 13 * n and n >= 5,
              "no usage block: words x 1.3 and tokens_estimated true",
              "%d requests, %s tokens, flag %s" % (n, row["output_tokens_drawn"], row["tokens_estimated"]))

        # 429 on every call: backed off, counted, and stopped once it has held for the window.
        t0 = time.monotonic()
        row = D.draw(provider(port, "/limited"), limits(600), seconds=10, **FAST)
        took = time.monotonic() - t0
        check(row["stopped_because"].startswith("rate limited: HTTP 429 on every call for 0.5 seconds"),
              "a 429 that persists stops the run with the documented reason", row["stopped_because"])
        check(took < 5 and row["requests_429"] >= 2 and row["requests_ok"] == 0 and row["requests_failed"] == 0,
              "429s are counted as limited, not as failures, and the clock did not have to run out",
              "%.1fs, %d limited" % (took, row["requests_429"]))
        check(row["first_error"] == "HTTP 429 rate limit", "first_error is the behaviour sentence, not their text",
              row["first_error"])
        check(POISON not in json.dumps(row), "no provider error body reaches the row")
        check(row["output_tokens_drawn"] == 0 and row["tokens_estimated"] is False,
              "nothing drawn under a 429 wall, and nothing estimated")

        # The cap: 100,000 tokens a call closes 250,000 in three calls, whatever the clock says.
        row = D.draw(provider(port, "/big"), limits(600), seconds=30, **FAST)
        check(row["stopped_because"] == "token cap reached: 250,000 output tokens",
              "the 250,000 cap stops the run with its reason", row["stopped_because"])
        check(row["output_tokens_drawn"] >= 250000 and row["requests_ok"] <= 3 + D.MAX_IN_FLIGHT,
              "the cap closes within the requests in flight",
              "%d ok, %d tokens" % (row["requests_ok"], row["output_tokens_drawn"]))
        check(D.TOKEN_CAP == 250000, "the cap is 250,000 output tokens per provider per run")

        # 402 twice in a row: the calling account's credit, not their outage, and it must not be hammered.
        row = D.draw(provider(port, "/auth"), limits(600), seconds=10, **FAST)
        check(row["stopped_because"] == ("HTTP 402 payment required: this endpoint will not serve an account "
                                         "with no credit on two consecutive calls")
              and row["requests_failed"] == 2 and len(HITS.get("/auth", [])) == 2,
              "402 on two consecutive calls stops the run after exactly two requests",
              "%s, %d requests" % (row["stopped_because"], len(HITS.get("/auth", []))))
        check(POISON not in json.dumps(row), "no 402 body reaches the row either")

        # Ten 5xx in a row.
        row = D.draw(provider(port, "/down"), limits(600), seconds=10, **FAST)
        check(row["stopped_because"] == "ten provider-side errors in a row, the last HTTP 503 no capacity behind the endpoint"
              and row["requests_failed"] == 10,
              "ten provider-side errors in a row stop the run", "%s, %d failed" % (row["stopped_because"], row["requests_failed"]))
    finally:
        srv.shutdown()
        srv.server_close()
        os.environ.pop("DRAW_TEST_KEY", None)

    # --- and nobody may quietly go back to the unprotected call ------------------------------
    src = (Path(__file__).resolve().parent / "draw_day.py").read_text(encoding="utf-8")
    check("urllib.request.urlopen(" not in src, "draw_day.py does not call urlopen directly",
          "found urllib.request.urlopen - use open_url from http_safe")
    check("open_url(" in src, "draw_day.py goes through open_url")

    print()
    print("%d failures" % len(fails))
    for f in fails:
        print("  " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
