# Adding your language

The point of this repo is not our ranking. It is that a free-model ranking can be **run again**, by
someone else, on a language we do not speak. English benchmarks hide the failure that matters most
outside English: a model that reasons fine will still produce text a native speaker would not sign.

A language pack is one JSON file. Copy `ro.json`, keep the structure, replace the content.

## The rule every probe must obey

**A probe passes or fails by code, never by opinion.** If deciding needs a human or a judge, it does not
belong in probes A to C. That is what keeps the mechanical half of the score reproducible: run it twice,
get the same number.

The paragraph probe (D) is the deliberate exception. It cannot be counted, so it goes to a blind jury,
and the two halves are reported separately so you can ignore ours and use only the mechanical half.

## The four probes and what each one is for

| Probe | `kind` | Catches |
|---|---|---|
| A | `arithmetic` | Whether the model can follow a "answer with only the numbers" instruction and do a percentage. One correct pair of numbers, so no judgement needed. |
| B | `diacritics_rewrite` or `constrained_rewrite` | The writing-system trap of your language. This is the probe most worth thinking about. |
| C | `json_extraction` | Structured output: right keys, right types, numbers as numbers. Fed to a real parser. |
| D | `paragraph` | Whether the model can produce publishable prose under a length constraint. Judged blind. |

## Probe B is where your language matters

Every language has a mechanical trap that a model either handles or does not, and it is usually invisible
in English benchmarks. For Romanian it is the difference between **ș ț** (comma below, correct) and
**ş ţ** (cedilla, wrong: a legacy of a Turkish-alphabet mapping). Models emit cedillas constantly, and
a Romanian reader clocks it instantly, so `wrong_diacritics` makes that an automatic failure.

Your language's equivalent might be:

- **Polish, Czech, Turkish, Vietnamese** - a diacritic set a model silently drops or substitutes.
- **German** - ß against ss, and whether compounds survive.
- **Greek, Russian, Serbian** - Latin lookalike letters mixed into the native script (а against a).
- **Arabic, Hebrew** - direction marks, and vowel points appearing where they should not.
- **Japanese, Chinese** - full-width against half-width punctuation, or simplified characters in a
  traditional text.

Set `diacritics` to the characters that must appear and `wrong_diacritics` to the ones that must never
appear. `wrong_diacritics` is the sharpest tool in the file: it turns "the text looks a bit off" into a
pass/fail a script can decide.

## Fields

```jsonc
{
  "language": "Polish",
  "code": "pl",                    // must match the filename: pl.json
  "diacritics": "ąćęłńóśźż...",    // characters that SHOULD appear in correct text
  "wrong_diacritics": "",          // characters that must NEVER appear. Leave "" if there is no such trap
  "wrong_diacritics_note": "",     // explain the trap, so a reader learns something from a failure
  "probes": {
    "A": { "kind": "arithmetic", "prompt": "...", "expect_numbers": [14400, 81600] },
    "B": { "kind": "diacritics_rewrite", "prompt": "...", "min_diacritics": 4,
           "must_contain": ["..."], "min_chars": 50, "max_chars": 220 },
    "C": { "kind": "json_extraction", "prompt": "...",
           "expect": { "key": 2 }, "string_keys": ["name"] },
    "D": { "kind": "paragraph", "prompt": "...", "min_words": 70, "max_words": 140,
           "min_diacritics": 10 }
  },
  "jury": { "sounds_human": "...", "language_correctness": "...", "follows_instruction": "..." }
}
```

Keep the three jury lens names as they are. `rank.py` looks for `sounds_human` by name when it builds
the agent ranking, which is the one that deliberately ignores voice.

## Things that will bite you

- **Do not put a real company, product or person in a prompt.** The prompt comes back in every answer,
  and the answers get published. Our first run leaked a real project name into the results 31 times
  before a check caught it. Use invented names.
- **Keep probe A's expected numbers to five digits and not round thousands.** `numbers_in()` tells a
  list separator from a thousands separator by grouping width; numbers like `14,400` where the trailing
  group is exactly three digits are the ambiguous case the tests pin down.
- **Write probe D so a judge can score it blind.** No topic that gives away which model wrote it.
- **Say what "only the answer" means in your language's phrasing.** Half of all probe A failures are
  models adding an explanation, not models getting the arithmetic wrong. That is a real finding, and it
  should fail for the right reason.

## Before you open the pull request

```bash
python bench/test_probes.py          # add cases for your language, both passing and failing
python bench/gate_publish.py .       # nothing private ships
```

Add at least one case to `test_probes.py` per probe, including one that **must fail**. A checker only
tested on correct answers is not tested. Then run the battery on whatever providers you have keys for
and include the results file in the pull request, with the date.
