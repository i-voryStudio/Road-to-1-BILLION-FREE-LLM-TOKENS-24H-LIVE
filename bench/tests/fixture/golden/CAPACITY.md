| Provider | Received /min, 30 s burst | Why 0 | Allow /min | Req/min | Per day | How we know | Monthly | Once | Key | Card | Phone |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **[alpha](https://console.alpha.example/keys)** | 12,000 (was 30,000) |  | 20,000 in+out | 10 | 1,000,000 | MEASURED; read on a free trial key; may be that tier's allowance, not a standing free tier | - | 500,000 tokens | yes | no | no |
| **[beta](https://inference.beta.example/)** | 8,000 |  | 800,000 in / 50,000 out | 60 | 300,000 | DECLARED | $5 in credits | - | yes | **yes** | ? |
| **[delta](https://delta.example/pricing)** | 2,500 |  | - | 30 | 200,000 | DERIVED | - | - | **no key** | no | no |
| **[epsilon](https://console.epsilon.example/)** | - | no rate: HTTP 403: the endpoint refused the caller | 6,000, scope unspecified (per model, largest) | 20 | 480,000 | DRAWN; drawn at a planned pace of 2 requests a minute and a realised 2.0 (120 launched over 60 minutes, at most 2 in flight) x 700 tokens a call: a floor for the hour measured, times 24, not their ceiling | - | - | yes | ? | ? |
| **[gamma](https://gamma.example/)** | 0 | rate limit reached | - | 5 | 50,000 | DERIVED | - | - | yes | no | no |
