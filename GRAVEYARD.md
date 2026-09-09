# Graveyard

Endpoints removed from the main ranking after **14 consecutive days** with no answer, and the date each one died. Buried is not deleted: if one comes back it returns to the ranking with its history intact.

Free endpoints die in months, not years, and usually without an announcement. A list that never removes anything is a list of things that used to work.

History so far: **4 day(s)** of measurements, 40 endpoints probed by the radar.

**Nothing buried yet.** Either everything is answering, or there is not yet 14 days of history to bury anything with. The counts below say which.

---

A day we did not measure is not a day down: if the radar did not run, or we hold no key, that is our gap and it does not count against a provider. An `empty` 200 does not count as down either - the endpoint answered, even if a reasoning switch was missing.


---

## Announced deaths

These did not fade out: a retirement notice exists for each, and each entry says who wrote it, the operator or a third party reporting on the operator. Each is still listed as working by at least one directory updated after that notice, which is the whole argument for re-testing rather than reprinting.

### GitHub Models, retired 2026-07-30

> As of July 30, 2026, GitHub Models is now retired. The playground, model catalog, inference API, and bring your own key (BYOK) are no longer available to any customer, including existing customers with active usage.

Notice from: the operator, in its own words.

Source: https://github.blog/changelog/2026-07-30-github-models-is-now-retired/ (read 2026-09-07).

Today: HTTP 410 github_models_retirement_brownout on models.github.ai/inference/chat/completions, measured 2026-09-07

### Llama API (Meta), retired 2026-07-06

> Meta shut down its hosted Llama API Public Preview on July 6, 2026.

Notice from: a third party, not the operator; the sentence above is that report's, and the retirement is confirmed here only by what the endpoint answers today.

Source: https://rushcommerce.dev/blog/meta-retires-llama-api-open-weights-portability (read 2026-09-07).

Today: HTTP 401 Authentication Error on api.llama.com/v1 and /compat/v1, for a freshly issued key, measured 2026-09-07

