# The exact prompt given to each judge

One call per lens per paragraph.

## Lens: sounds_human

```
Does this paragraph read like a person wrote it, or like a language model? Score 0-10. A model-sounding paragraph is generic, evenly balanced, and full of hedged filler. A human-sounding one commits to something.

Score 0 to 10, where 0 means the text fails completely on this lens and 10 means it could not
be improved on it. Judge ONLY this lens, ignore everything else about the text. Answer with a JSON object
{"score": <integer 0-10>, "reason": "<one sentence, quoting the words from the text that decided it>"}
and nothing else.

---
<paragraph>
---
```

## Lens: language_correctness

```
Is the Romanian correct? Score 0-10. Check diacritics (ș ț with comma, never cedilla), agreement, prepositions, and whether any phrasing reads as translated from English.

Score 0 to 10, where 0 means the text fails completely on this lens and 10 means it could not
be improved on it. Judge ONLY this lens, ignore everything else about the text. Answer with a JSON object
{"score": <integer 0-10>, "reason": "<one sentence, quoting the words from the text that decided it>"}
and nothing else.

---
<paragraph>
---
```

## Lens: follows_instruction

```
Did it do exactly what was asked: 90-110 words, no title, no list, no bold, no invented figures about named banks? Score 0-10.

Score 0 to 10, where 0 means the text fails completely on this lens and 10 means it could not
be improved on it. Judge ONLY this lens, ignore everything else about the text. Answer with a JSON object
{"score": <integer 0-10>, "reason": "<one sentence, quoting the words from the text that decided it>"}
and nothing else.

---
<paragraph>
---
```
