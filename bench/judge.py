#!/usr/bin/env python3
"""Score the paragraph probe with a blind jury.

The other three probes are decided by code. The paragraph is not: whether a text reads like a person
wrote it cannot be counted, so it gets judged. Two things keep that honest:

  1. BLIND. Paragraphs are stripped of their model name and shuffled under IDs (P01, P02, ...) with a
     fixed seed, so the judge never learns which model wrote what and the shuffle is reproducible.
  2. SEPARATE LENSES. Each lens is a separate call with its own question. A single "rate this 0-10"
     collapses three different failures into one number and hides all of them.

Two ways to run it, and the export path is the important one: it means you never have to trust our jury.

    python bench/judge.py results.json --export out/          # anonymised paragraphs + the exact prompts
    python bench/judge.py results.json --api --out jury.json  # judge via an API you point it at

For --api, set JUDGE_URL, JUDGE_KEY_ENV and JUDGE_MODEL. Use a model from a DIFFERENT family than the
ones being judged, and say which one you used: a judge scoring its own family is a conflict, not a score.
"""
import argparse, json, os, random, re, sys, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
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


def call_judge(url, key, model, prompt, timeout=180):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key,
               "User-Agent": "free-llm-benchmark/1.0"}
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as f:
            data = json.load(f)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None, "judge did not return JSON"
        parsed = json.loads(m.group(0))
        score = parsed.get("score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 10:
            return None, "judge returned score=%r" % score
        return {"score": score, "reason": str(parsed.get("reason", ""))[:300]}, None
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except Exception as e:
        return None, str(e)[:120]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="the JSON written by benchmark.py")
    ap.add_argument("--export", metavar="DIR", help="write anonymised paragraphs and prompts, judge them yourself")
    ap.add_argument("--api", action="store_true", help="judge via JUDGE_URL / JUDGE_KEY_ENV / JUDGE_MODEL")
    ap.add_argument("--out", default="jury.json")
    ap.add_argument("--language", default=None, help="language pack for the lens questions (default: from results)")
    a = ap.parse_args()

    lang_code, paragraphs = load_paragraphs(a.results)
    lang = json.loads((HERE / "languages" / ((a.language or lang_code) + ".json")).read_text(encoding="utf-8"))
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
            "# The exact prompt given to each judge\n\nOne call per lens per paragraph.\n\n"
            + "\n\n".join("## Lens: %s\n\n```\n%s\n\n%s\n\n---\n<paragraph>\n---\n```" % (name, q, GRID)
                          for name, q in lenses.items()) + "\n",
            encoding="utf-8", newline="\n")
        print("wrote %s/paragraphs-anonymised.md, key.json and judge-prompts.md" % d)
        print("Judge them with any model you like, then feed the scores back as jury.json.")
        return 0

    if not a.api:
        print("Nothing to do: pass --export or --api.")
        return 1

    url, key_env, model = os.environ.get("JUDGE_URL"), os.environ.get("JUDGE_KEY_ENV"), os.environ.get("JUDGE_MODEL")
    if not (url and key_env and model and os.environ.get(key_env)):
        print("Set JUDGE_URL, JUDGE_KEY_ENV, JUDGE_MODEL and the key variable itself. For example:\n"
              "  export JUDGE_URL=https://api.groq.com/openai/v1/chat/completions\n"
              "  export JUDGE_KEY_ENV=GROQ_API_KEY JUDGE_MODEL=openai/gpt-oss-120b")
        return 1
    api_key = os.environ[key_env]

    verdicts, failures = [], 0
    for lens_name, question in lenses.items():
        for p in anon:
            prompt = "%s\n\n%s\n\n---\n%s\n---" % (question, GRID, p["text"])
            got, err = call_judge(url, api_key, model, prompt)
            if got is None:
                failures += 1
                print("  %s %-22s FAILED: %s" % (p["id"], lens_name, err), flush=True)
            else:
                verdicts.append({"id": p["id"], "lens": lens_name, **got})
                print("  %s %-22s %2s  %s" % (p["id"], lens_name, got["score"], got["reason"][:70]), flush=True)
            time.sleep(1)

    Path(a.out).write_text(json.dumps({
        "judge_model": model, "judge_url": url, "seed": SEED, "language": lang_code,
        "lenses": list(lenses), "verdicts": verdicts, "key": key,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("\nwrote %s (%d verdicts, %d failed calls)" % (a.out, len(verdicts), failures))
    print("A judge scoring its own model family is a conflict. Judge model used: %s" % model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
