# Judge agreement

Judges: **claude** (Anthropic Claude), **glm** (z.ai GLM)

Half of every quality score comes from a model judging text. This page is how far that can
be trusted. The gap is the average distance between judges on the same paragraph, out of 10.

| Lens | Paragraphs | Mean gap | Max gap | Correlation | Reading |
|---|---|---|---|---|---|
| `follows_instruction` | 21 | **1.10** | 9 | 0.73 | close agreement |
| `language_correctness` | 20 | **1.60** | 4 | 0.93 | same ranking, different strictness |
| `sounds_human` | 23 | **1.70** | 5 | -0.07 | usable, but they weight it differently |

## Where they disagreed most

These paragraphs are the most interesting texts in the corpus: they are where the question
stops having an obvious answer. All of them are in `paragraphs-anonymised.md`.

| Gap | Lens | Paragraph | Scores |
|---|---|---|---|
| **9** | `follows_instruction` | P16 | claude 1, glm 10 |
| **5** | `sounds_human` | P20 | claude 8, glm 3 |
| **5** | `sounds_human` | P08 | claude 2, glm 7 |
| **4** | `sounds_human` | P19 | claude 6, glm 2 |
| **4** | `sounds_human` | P01 | claude 7, glm 3 |
| **4** | `language_correctness` | P20 | claude 3, glm 7 |
| **4** | `language_correctness` | P08 | claude 0, glm 4 |
| **4** | `follows_instruction` | P20 | claude 2, glm 6 |
| **3** | `sounds_human` | P12 | claude 6, glm 3 |
| **3** | `sounds_human` | P09 | claude 5, glm 2 |
| **3** | `sounds_human` | P05 | claude 5, glm 2 |
| **3** | `language_correctness` | P12 | claude 3, glm 6 |

## What this does not tell you

Agreement is not correctness. Two judges can agree and both be wrong, and they are more
likely to agree with each other than either is to agree with a native speaker, because
they are both language models. The honest use of this page is as a floor: where the judges
disagree, the score is definitely soft. Where they agree, it might still be.

