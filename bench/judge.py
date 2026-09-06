#!/usr/bin/env python3
"""Score the paragraph probe with a blind jury of several judges.

The other three probes are decided by code. The paragraph is not: whether a text reads like a person
wrote it cannot be counted, so it gets judged. Four things keep that honest:

  1. BLIND. Paragraphs are stripped of the model that produced them and shuffled under IDs (P01, P02,
     ...) with a fixed seed, so no judge learns whose text it is scoring and the shuffle is reproducible.
  2. SEPARATE LENSES. Each lens is a separate call with its own question. A single "rate this 0-10"
     collapses three different failures into one number and hides all of them.
  3. MORE THAN ONE JUDGE, FROM MORE THAN ONE FAMILY. A model scoring its own family is a conflict of
     interest that no prompt wording fixes. Judges are declared in bench/judges.json with their family,
     and gate_contributions.py refuses a jury drawn from a single family.
  4. THE DISAGREEMENT IS PUBLISHED. bench/agreement.py measures how much the judges agree and writes it
     out. A confident average that hides a split jury is worse than an honest range.

    python bench/judge.py results.json --export judged/          # anonymised paragraphs + exact prompts
    python bench/judge.py results.json --api --out jury.json     # run every api judge in judges.json
    python bench/judge.py results.json --api --only glm          # just one of them

The export path is the important one: it means you never have to trust our jury. It hands you the
corpus and the prompts, and you can re-judge the lot with anything you like.
"""
import argparse, json, os, random, re, sys, time, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import ALLOWED_HOSTS
SEED = 20260905  # fixed so anyone re-running gets the same P-numbers from the same input

GRID = """Score 0 to 10, where 0 means the text fails completely on this lens and 10 means it could not
be improved on it. Judge ONLY this lens, ignore everything else about the text. Answer with a JSON object
{"score": <integer 0-10>, "reason": "<one sentence, quoting the words from the text that decided it>"}
and nothing else."""


def load_paragraphs(results_path):
    data = json.loads(Path(results_path).read_text(encoding="utf-8"))
    out = []
    for row in data["rows"]:
        if row["kind"] != "paragraph" or not row["passed"]:
            continue  # a paragraph that failed the mechanical check is not sent to the jury
        text = (row.get("text") or "").strip()
        if text:
            out.append({"provider": row["provider"], "model": row["model"], "text": text})
    return data.get("language", "?"), out


def anonymise(paragraphs):
    order = list(range(len(paragraphs)))
    random.Random(SEED).shuffle(order)
    key, anon = {}, []
    for position, original in enumerate(order, start=1):
        pid = "P%02d" % position
        p = paragraphs[original]
        key[pid] = "%s | %s" % (p["provider"], p["model"])
        anon.append({"id": pid, "text": p["text"]})
    return key, anon


def call_judge(judge, key, prompt, timeout=180):
    """A judge receives an API key in a header, exactly like a benchmarked provider, so it goes through
    the same host allowlist. A jury entry is not a safer thing than a provider entry."""
    url = judge["url"]
    if (urlparse(url).hostname or "") not in ALLOWED_HOSTS:
        return None, "refused: %s is not in ALLOWED_HOSTS" % urlparse(url).hostname
    body = {"model": judge["model"], "messages": [{"role": "user", "content": prompt}],
            "max_tokens": judge.get("max_tokens", 500), "temperature": 0,
            **(judge.get("extra_body") or {})}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key,
               "User-Agent": "free-llm-benchmark/1.0"}
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as f:
            data = json.load(f)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None, "judge did not return JSON: %r" % text[:60]
        try:
            parsed = json.loads(m.group(0))
            score, reason, fallback = parsed.get("score"), str(parsed.get("reason", "")), False
        except json.JSONDecodeError:
            # The score is a number and the reason is free text, so a judge quoting the paragraph
            # inside its reason breaks the JSON without making the score any less valid. Measured:
            # 3 of 69 GLM calls failed this way, always on an unescaped quote in the reason.
            # Recover the score, keep the reason as raw text, and MARK it so nobody mistakes a
            # salvaged verdict for a clean one.
            sm = re.search(r'"score"\s*:\s*(\d{1,2})', m.group(0))
            if not sm:
                return None, "unparseable answer: %s" % m.group(0)[:70]
            score, fallback = int(sm.group(1)), True
            rm = re.search(r'"reason"\s*:\s*"(.*)', m.group(0), re.S)
            reason = (rm.group(1) if rm else "")[:300]
        if not isinstance(score, (int, float)) or not 0 <= score <= 10:
            return None, "judge returned score=%r" % score
        out = {"score": score, "reason": reason[:300]}
        if fallback:
            out["parse_fallback"] = True
        return out, None
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except Exception as e:
        return None, str(e)[:120]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="the JSON written by benchmark.py")
    ap.add_argument("--export", metavar="DIR", help="write anonymised paragraphs and prompts, judge them yourself")
    ap.add_argument("--api", action="store_true", help="run every api judge in bench/judges.json")
    ap.add_argument("--only", default="", help="comma-separated judge names")
    ap.add_argument("--judges", default=str(HERE / "judges.json"))
    ap.add_argument("--out", default="jury.json")
    ap.add_argument("--language", default=None, help="language pack for the lens questions (default: from results)")
    a = ap.parse_args()

    lang_code, paragraphs = load_paragraphs(a.results)
    code = a.language or lang_code
    # `lang_code` comes out of the results file, which may have been sent by a stranger. Pathlib replaces
    # the base when a segment is absolute, so an unchecked value picks which file this script reads - and
    # its contents end up in judge-prompts.md, which gets published, or sent to a judge in --api mode.
    if not re.fullmatch(r"[a-z]{2,8}", code or ""):
        print("refusing language code %r: expected two to eight lowercase letters" % code)
        return 2
    lang = json.loads((HERE / "languages" / (code + ".json")).read_text(encoding="utf-8"))
    lenses = lang["jury"]
    key, anon = anonymise(paragraphs)
    print("%d paragraphs passed the mechanical check and go to the jury, on %d lenses"
          % (len(anon), len(lenses)))

    if a.export:
        d = Path(a.export)
        d.mkdir(parents=True, exist_ok=True)
        (d / "paragraphs-anonymised.md").write_text(
            "\n\n".join("## %s\n\n%s" % (p["id"], p["text"]) for p in anon) + "\n",
            encoding="utf-8", newline="\n")
        (d / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n",
                                    encoding="utf-8", newline="\n")
        (d / "judge-prompts.md").write_text(
            "# The exact prompt given to each judge\n\nOne call per lens per paragraph, per judge.\n\n"
            + "\n\n".join("## Lens: %s\n\n```\n%s\n\n%s\n\n---\n<paragraph>\n---\n```" % (name, q, GRID)
                          for name, q in lenses.items()) + "\n",
            encoding="utf-8", newline="\n")
        print("wrote %s/paragraphs-anonymised.md, key.json and judge-prompts.md" % d)
        print("Judge them with any model you like, then feed the scores back as jury.json.")
        return 0

    if not a.api:
        print("Nothing to do: pass --export or --api.")
        return 1

    all_judges = json.loads(Path(a.judges).read_text(encoding="utf-8"))["judges"]
    wanted = {x.strip() for x in a.only.split(",") if x.strip()}
    judges = [j for j in all_judges if j.get("via") == "api" and (not wanted or j["name"] in wanted)]
    live = [j for j in judges if os.environ.get(j.get("key_env", ""))]
    missing = [j for j in judges if not os.environ.get(j.get("key_env", ""))]
    if not live:
        print("No api judge has its key set. Needed: %s"
              % ", ".join(j.get("key_env", "?") for j in judges))
        return 1
    print("judges: %s" % ", ".join("%s (%s)" % (j["name"], j["family"]) for j in live))
    for j in missing:
        print("  skipped %s: %s not set" % (j["name"], j["key_env"]))

    verdicts, failures = [], 0
    for judge in live:
        api_key = os.environ[judge["key_env"]]
        for lens_name, question in lenses.items():
            for p in anon:
                prompt = "%s\n\n%s\n\n---\n%s\n---" % (question, GRID, p["text"])
                got, err = call_judge(judge, api_key, prompt)
                if got is None:
                    failures += 1
                    print("  %-7s %s %-22s FAILED: %s" % (judge["name"], p["id"], lens_name, err), flush=True)
                else:
                    verdicts.append({"id": p["id"], "lens": lens_name, "judge": judge["name"], **got})
                    print("  %-7s %s %-22s %2s  %s"
                          % (judge["name"], p["id"], lens_name, got["score"], got["reason"][:60]), flush=True)
                time.sleep(judge.get("pause_seconds", 1))

    Path(a.out).write_text(json.dumps({
        "judges": [{k: v for k, v in j.items() if k != "key_env"} for j in live],
        "seed": SEED, "language": lang_code, "lenses": list(lenses),
        "verdicts": verdicts, "key": key,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("\nwrote %s (%d verdicts from %d judges, %d failed calls)"
          % (a.out, len(verdicts), len(live), failures))
    print("Next: python bench/agreement.py %s  - how much the judges actually agree" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
