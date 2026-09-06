#!/usr/bin/env python3
"""Run the four-probe battery against every free LLM endpoint you have a key for.

Reads bench/providers.json (endpoints, models, pacing) and bench/languages/<code>.json (the probes and
the pass conditions). Writes one JSON file with every raw answer, plus a mechanical score per model.

The probes are checked by code, not by a model: probe A has one correct pair of numbers, probe C is fed
to a JSON parser, probe B and D are counted character by character. Only probe D needs a judge, and that
is a separate step (judge.py), so this script alone gives you a reproducible number with no LLM in the loop.

    export GROQ_API_KEY=... CEREBRAS_API_KEY=...
    python bench/benchmark.py --out results.json                 # every provider you have a key for
    python bench/benchmark.py --out results.json --only groq,cerebras
    python bench/benchmark.py --out results.json --language en

Providers with no key set are skipped and listed at the end. Nothing here writes a key anywhere.
"""
import argparse, json, os, re, sys, threading, time, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import ALLOWED_HOSTS, ALLOWED_URL_PLACEHOLDERS  # single source of truth
UA = "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"
MAX_BODY = 8 * 1024 * 1024   # a chat completion that big is a fault, not an answer


# ---------------------------------------------------------------- checking

def count_any(text, chars):
    return sum(text.count(c) for c in chars) if chars else 0


SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{6,}|gsk_[A-Za-z0-9_\-]{6,}|nvapi-[A-Za-z0-9_\-]{6,}"
                    r"|AIza[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
                    r"|(?:Bearer|api[-_ ]?key|token)[\"'\s:=]+[A-Za-z0-9_\-]{12,})", re.I)
# A provider's error body can echo the key back, and it always describes the calling account, not the model.
# The trigger word is dropped along with the rest: keeping it would still publish the state of our own
# account, and the HTTP code already carries everything a reader of the results needs to know.
BALANCE = re.compile(r"[^\"}]{0,40}(balance|insufficient\s+funds|insufficient[_ ]quota|billing)[^\"}]{0,80}", re.I)


def redact(body):
    """Never let a key or the calling account state reach a published results file."""
    return BALANCE.sub("<account state redacted>", SECRET.sub("***", body))


# A thousands separator is a comma/dot/space between a digit and EXACTLY three more digits.
# "14,400" is one number; "14400,81600" is two, because 81600 has five digits, not three.
# Getting this wrong in either direction silently rewrites the score, so test_probes.py pins both cases.
THOUSANDS = re.compile(r"(?<=\d)[.,   ](?=\d{3}(?!\d))")


def numbers_in(text):
    """Every integer the text states, with thousands separators removed and list separators kept."""
    return [int(x) for x in re.findall(r"\d+", THOUSANDS.sub("", text))]


def check(probe, spec, text, lang):
    """Return (passed, note). Pure code, no model involved."""
    t = (text or "").strip()
    if not t:
        return False, "empty"
    kind = spec.get("kind")

    if kind == "arithmetic":
        # The whole difficulty is telling a list separator from a thousands separator: "14400, 81600"
        # is two numbers, "14,400" is one. numbers_in() settles it by grouping width, not by guessing.
        stated = numbers_in(t)
        missing = [n for n in spec["expect_numbers"] if n not in stated]
        return not missing, ("found all" if not missing else "missing %s" % missing) + " | stated=%s" % stated[:5]

    if kind in ("diacritics_rewrite", "constrained_rewrite"):
        d = count_any(t, lang.get("diacritics", ""))
        bad = count_any(t, lang.get("wrong_diacritics", ""))
        ok = (d >= spec.get("min_diacritics", 0)
              and bad == 0
              and all(w.lower() in t.lower() for w in spec.get("must_contain", []))
              and not any(w.lower() in t.lower() for w in spec.get("must_not_contain", []))
              and spec.get("min_chars", 0) <= len(t) <= spec.get("max_chars", 10 ** 6))
        return ok, "diacritics=%d wrong_diacritics=%d chars=%d" % (d, bad, len(t))

    if kind == "json_extraction":
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            return False, "no JSON object in the answer"
        try:
            j = json.loads(m.group(0))
        except Exception as e:
            return False, "invalid JSON: %s" % str(e)[:40]
        strings = set(spec.get("string_keys", []))
        for k, want in spec["expect"].items():
            got = j.get(k)
            if k in strings:
                if str(want).lower() not in str(got).lower():
                    return False, "key %s = %r, expected to contain %r" % (k, got, want)
            elif got != want:
                return False, "key %s = %r, expected %r" % (k, got, want)
        return True, "keys=%s" % sorted(j.keys())

    if kind == "paragraph":
        words = len(t.split())
        d = count_any(t, lang.get("diacritics", ""))
        bad = count_any(t, lang.get("wrong_diacritics", ""))
        markdown = bool(re.search(r"(^|\n)\s*([#\-*]|\d+\.)\s", t)) or "**" in t
        ok = (spec.get("min_words", 0) <= words <= spec.get("max_words", 10 ** 6)
              and d >= spec.get("min_diacritics", 0) and bad == 0 and not markdown)
        return ok, "words=%d diacritics=%d wrong_diacritics=%d markdown=%s" % (words, d, bad, markdown)

    return False, "unknown probe kind %r" % kind


# ---------------------------------------------------------------- calling

class NoCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect that changes host.

    urllib keeps the Authorization header across a 302, so a provider (or anyone who can answer for one)
    could bounce the request to a server of their choosing and receive the API key. The host allowlist
    would be useless without this: it checks where we aim, this checks where we land.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).hostname != urlparse(req.full_url).hostname:
            raise urllib.error.URLError(
                "refused redirect to a different host (%s -> %s): the API key travels in the header"
                % (urlparse(req.full_url).hostname, urlparse(newurl).hostname))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(NoCrossHostRedirect)


def build_body(model, prompt, extra_body, max_tokens, generation, unsupported):
    """The exact JSON sent to a provider. Separated from call() so a test can inspect it without a network.

    Generation parameters are sent EXPLICITLY. Leaving them out means each provider applies its own
    default, the defaults differ between providers and change without notice, and two runs of the same
    battery are then not comparable - which quietly makes the whole ranking unreproducible. It is the
    first thing anyone technical will ask about, and they are right to.

    `unsupported` lists parameters a given provider rejects (some return 400 on a key they do not know).
    Those are dropped for that provider only, and the drop is recorded in the results so a reader can
    see which models were measured under exactly which settings.
    """
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    applied, dropped = {}, []
    for k, v in (generation or {}).items():
        if k in (unsupported or []):
            dropped.append(k)
        else:
            body[k] = v
            applied[k] = v
    body.update(extra_body or {})
    return body, applied, dropped


def call(url, key, model, prompt, extra_body, max_tokens, timeout, generation=None, unsupported=None):
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        # Belt and braces: gate_contributions.py blocks this in CI, and this blocks it at request time,
        # for anyone running a modified providers.json on their own machine.
        return {"http": 0, "seconds": 0.0, "text": "",
                "error": "refused: %r is not in ALLOWED_HOSTS. This sends a real API key in a header, "
                         "so destinations are declared in code." % host}
    body, applied, dropped = build_body(model, prompt, extra_body, max_tokens, generation, unsupported)
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if key:                       # keyless providers are called with no Authorization header at all
        headers["Authorization"] = "Bearer " + key
    started = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with OPENER.open(req, timeout=timeout) as f:
            # A broken or hostile endpoint can stream forever. Read a bounded amount and refuse the rest:
            # json.load(f) would happily consume the machine's memory.
            payload = f.read(MAX_BODY + 1)
        if len(payload) > MAX_BODY:
            return {"http": 0, "seconds": round(time.time() - started, 1), "text": "",
                    "error": "response larger than %d bytes, refused" % MAX_BODY}
        data = json.loads(payload.decode("utf-8", "replace"))
        msg = (data.get("choices") or [{}])[0].get("message", {}) if isinstance(data, dict) else {}
        text = msg.get("content") or ""
        if not text and isinstance(data, dict) and isinstance(data.get("result"), dict):
            text = data["result"].get("response", "")  # Cloudflare's non-OpenAI shape
        thought_out_loud = bool(re.search(r"<think>|<thought>", text))
        text = re.sub(r"<think>.*?</think>|<thought>.*?</thought>", "", text, flags=re.S).strip()
        return {"http": 200, "seconds": round(time.time() - started, 1), "text": text,
                "reasoning_field": bool(msg.get("reasoning") or msg.get("reasoning_content")),
                "thought_out_loud": thought_out_loud,
                "generation_applied": applied, "generation_dropped": dropped}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "seconds": round(time.time() - started, 1), "text": "",
                "error": redact(e.read().decode("utf-8", "replace"))[:200]}
    except Exception as e:
        return {"http": 0, "seconds": round(time.time() - started, 1), "text": "", "error": redact(str(e))[:160]}


def run_provider(prov, lang, rows, lock, repeat, repeat_paragraph):
    generation = lang.get("generation") or {}
    unsupported = prov.get("unsupported_params") or []
    url = prov["url"]
    key = os.environ[prov["key_env"]] if prov.get("key_env") else ""
    # Only declared placeholders may be substituted. Without this, a contributed URL such as
    # https://evil.example/{OPENROUTER_API_KEY}/ would put a second key straight into the request path.
    for placeholder in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url):
        if placeholder not in ALLOWED_URL_PLACEHOLDERS:
            raise ValueError("provider %r interpolates {%s} into its URL; only %s is allowed"
                             % (prov["name"], placeholder, ", ".join(sorted(ALLOWED_URL_PLACEHOLDERS))))
        value = os.environ.get(placeholder, "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value or ""):
            raise ValueError("environment variable %s is empty or has an unexpected shape" % placeholder)
        url = url.replace("{%s}" % placeholder, value)
    timeout = prov.get("timeout_seconds", 120)
    for model in prov["models"]:
        for name, spec in lang["probes"].items():
            max_tokens = model.get("max_tokens", spec.get("max_tokens", 1200))
            # Every probe runs more than once. A single call cannot tell a model that fails from a model
            # that had one bad moment, and publishing one number per model implies a confidence we would
            # not have earned. The paragraph probe can be given a higher count of its own, since it is
            # the only one a jury also scores.
            tries = repeat_paragraph if spec["kind"] == "paragraph" else repeat
            attempts = []
            for i in range(tries):
                r = call(url, key, model["id"], spec["prompt"], model.get("extra_body"), max_tokens,
                         timeout, generation, unsupported)
                if r["http"] == 200:
                    ok, note = check(name, spec, r["text"], lang)
                else:
                    ok, note = False, "HTTP %s: %s" % (r["http"], r.get("error", "")[:90])
                attempts.append({"passed": ok, "note": note, "http": r["http"], "seconds": r["seconds"],
                                 "reasoning_field": r.get("reasoning_field"),
                                 "thought_out_loud": r.get("thought_out_loud"),
                                 "generation_applied": r.get("generation_applied"),
                                 "generation_dropped": r.get("generation_dropped"),
                                 "text": r.get("text", "")[:2500 if spec["kind"] == "paragraph" else 400]})
                if i + 1 < tries:
                    time.sleep(prov.get("pause_seconds", 2))
            wins = sum(1 for a in attempts if a["passed"])
            passed = wins * 2 > tries    # majority; a tie counts as a failure
            # Report the attempt that decided the verdict, so text and note match the pass/fail.
            best = next((a for a in attempts if a["passed"] == passed), attempts[0])
            row = {"provider": prov["name"], "model": model["id"], "probe": name, "kind": spec["kind"],
                   "passed": passed, "note": best["note"], "http": best["http"],
                   "seconds": round(sum(a["seconds"] for a in attempts) / len(attempts), 1),
                   "attempts": tries, "attempts_passed": wins,
                   "reasoning_field": best["reasoning_field"], "thought_out_loud": best["thought_out_loud"],
                   "generation_applied": best.get("generation_applied"),
                   "generation_dropped": best.get("generation_dropped"),
                   "text": best["text"],
                   "all_texts": [a["text"] for a in attempts] if tries > 1 else None}
            with lock:
                rows.append(row)
                extra = "" if tries == 1 else " [%d/%d]" % (wins, tries)
                print("%-12s %-46s %s %-4s %6.1fs  %s%s"
                      % (prov["name"], model["id"], name, "OK" if passed else "FAIL",
                         row["seconds"], best["note"][:60], extra), flush=True)
            time.sleep(prov.get("pause_seconds", 2))


# ---------------------------------------------------------------- main

def recheck(results_path, lang, out_path):
    """Re-run the checkers over saved answers. No network, no keys, no cost.

    The answers are stored, so a fix to check() does not need the battery run again - and it must not,
    because re-running would score different answers. Use this whenever a checker changes: it is the
    difference between correcting a score and quietly replacing the measurement.
    """
    data = json.loads(Path(results_path).read_text(encoding="utf-8"))
    changed = []
    for row in data["rows"]:
        # Redaction rules can tighten too, and a results file written under the old ones is still on disk.
        row["note"] = redact(row["note"])
        if row.get("text"):
            row["text"] = redact(row["text"])
        if row["http"] != 200:
            continue
        spec = lang["probes"].get(row["probe"])
        if not spec:
            continue
        was = row["passed"]
        # Re-score every attempt, not just the one that was reported. attempts_passed feeds the score
        # RANGE in rank.py, so leaving it stale would publish a corrected verdict with an uncorrected
        # spread beside it - two numbers about the same model that disagree.
        texts = row.get("all_texts") or [row.get("text", "")]
        verdicts = [check(row["probe"], spec, t, lang) for t in texts if t is not None]
        wins = sum(1 for ok, _ in verdicts if ok)
        now = wins * 2 > len(verdicts) if verdicts else False
        note = next((n for ok, n in verdicts if ok == now), verdicts[0][1] if verdicts else "empty")
        if now != was:
            changed.append((row["provider"], row["model"], row["probe"], was, now, row.get("text", "")[:60]))
        row["passed"], row["note"] = now, note
        row["attempts"], row["attempts_passed"] = len(verdicts), wins
    data["rechecked"] = True
    Path(out_path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
    print("re-checked %d rows against the current checkers, %d verdicts changed"
          % (len(data["rows"]), len(changed)))
    for provider, model, probe, was, now, text in changed:
        print("  %-12s %-42s %s  %s -> %s   %r"
              % (provider, model[:42], probe, "PASS" if was else "FAIL", "PASS" if now else "FAIL", text))
    print("wrote %s" % out_path)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="where to write the raw results JSON")
    ap.add_argument("--recheck", metavar="RESULTS",
                    help="re-score a saved results file with the current checkers and exit. Makes no API "
                         "calls: use it after fixing a checker, so the scores are corrected rather than "
                         "the measurement silently replaced by a new run.")
    ap.add_argument("--language", default="ro", help="probe set from bench/languages/ (default: ro)")
    ap.add_argument("--only", default="", help="comma-separated provider names, e.g. groq,cerebras")
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    ap.add_argument("--repeat", type=int, default=3, metavar="N",
                    help="run EVERY probe N times and take the majority verdict (default: 3). One call "
                         "cannot separate a model that fails from a model that had a bad moment, and the "
                         "spread between runs is published rather than hidden.")
    ap.add_argument("--repeat-paragraph", type=int, default=None, metavar="N",
                    help="a different count for the paragraph probe only (default: same as --repeat)")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z]{2,8}", a.language or ""):
        print("refusing language code %r: expected two to eight lowercase letters" % a.language)
        return 2
    lang = json.loads((HERE / "languages" / (a.language + ".json")).read_text(encoding="utf-8"))
    if a.recheck:
        return recheck(a.recheck, lang, a.out)

    all_providers = json.loads(Path(a.providers).read_text(encoding="utf-8"))["providers"]
    if a.only:
        wanted = {x.strip() for x in a.only.split(",")}
        all_providers = [p for p in all_providers if p["name"] in wanted]

    live = [p for p in all_providers if not p.get("key_env") or os.environ.get(p["key_env"])]
    skipped = [(p["name"], p["key_env"], p.get("signup", "")) for p in all_providers
               if p.get("key_env") and not os.environ.get(p["key_env"])]
    if not live:
        print("No API keys found in the environment. Set at least one, e.g.:\n  export GROQ_API_KEY=...")
        for name, env, signup in skipped:
            print("  %-12s %-22s %s" % (name, env, signup))
        return 1

    gen = lang.get("generation") or {}
    repeat_par = a.repeat_paragraph if a.repeat_paragraph is not None else a.repeat
    print("language: %s | probes: %s | every probe run %dx, paragraph %dx"
          % (lang["language"], ", ".join(lang["probes"]), a.repeat, repeat_par))
    print("generation: %s"
          % (", ".join("%s=%s" % kv for kv in sorted(gen.items())) if gen
             else "NONE SET - every provider will use its own default and results will NOT be reproducible"))
    print("providers: %s\n" % ", ".join("%s(%d)" % (p["name"], len(p["models"])) for p in live))

    rows, lock, threads = [], threading.Lock(), []
    for p in live:
        t = threading.Thread(target=run_provider,
                             args=(p, lang, rows, lock, a.repeat, repeat_par), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    per = {}
    for r in rows:
        k = (r["provider"], r["model"])
        d = per.setdefault(k, {"passed": 0, "seconds": [], "http": []})
        d["passed"] += 1 if r["passed"] else 0
        d["seconds"].append(r["seconds"])
        d["http"].append(r["http"])

    Path(a.out).write_text(json.dumps({
        "language": lang["code"], "probe_count": len(lang["probes"]),
        "generation": lang.get("generation") or {},
        "attempts_per_probe": a.repeat, "paragraph_attempts": repeat_par, "rows": rows,
        "mechanical_score": [{"provider": k[0], "model": k[1], "passed": v["passed"],
                              "of": len(lang["probes"]),
                              "avg_seconds": round(sum(v["seconds"]) / len(v["seconds"]), 1),
                              "http": v["http"]}
                             for k, v in per.items()],
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print("\n=== MECHANICAL SCORE (probes passed) ===")
    for k, v in sorted(per.items(), key=lambda kv: (-kv[1]["passed"], sum(kv[1]["seconds"]))):
        print("  %d/%d  %6.1fs avg  %-12s %-46s http=%s"
              % (v["passed"], len(lang["probes"]), sum(v["seconds"]) / len(v["seconds"]), k[0], k[1],
                 ",".join(str(h) for h in v["http"])))
    if skipped:
        print("\nskipped, no key set:")
        for name, env, signup in skipped:
            print("  %-12s %-22s %s" % (name, env, signup))
    print("\nwrote %s (%d rows)" % (a.out, len(rows)))
    print("Next: judge the paragraphs with  python bench/judge.py %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
