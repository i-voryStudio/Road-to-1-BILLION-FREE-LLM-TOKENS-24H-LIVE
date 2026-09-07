"""What a radar state means, defined ONCE and imported by both consumers.

`bench/probe_alive.py` writes one of these states per endpoint per day into `data/uptime.jsonl`:

    alive             HTTP 200 with text in the message
    empty             HTTP 200 with NO text in the message: a reasoning model that spent its whole
                      budget thinking, or a switch we failed to set
    down              connection failure, timeout, 5xx other than 503
    overloaded        HTTP 503
    rate_limited      HTTP 429
    payment_required  HTTP 402
    blocked           401 / 403 / 406 / 451: the endpoint refused THIS caller
    no_key            we hold no credential for it, so nothing was sent

Two questions are asked of that history, and they are different questions, so `empty` lands on a
different side of each:

  IS THE ENDPOINT THERE?   (gate_viability.py, the fourteen-day rule)
      An `empty` 200 is the endpoint answering. It took the request, ran the model and returned a
      well-formed reply whose text happens to be blank. Burying a live service for a missing
      reasoning switch would blame the provider for a mistake on the caller's side, so for burial
      `empty` counts as UP.

  DID THE ENDPOINT GIVE US ANYTHING?   (rank.py, the answered_rate in the value formula)
      A blank reply is worth nothing to the reader: the quota is gone and there is no output.
      For value, `empty` counts as NOT ANSWERED, exactly like `down`.

Both readings are correct for their question. What was wrong before this file existed was that the
two sets lived in two files with no sentence connecting them, and a reader comparing GRAVEYARD.md
("the endpoint answered") with the ranking ("answered 0 of 2") saw a contradiction where there is a
distinction. Now there is one place that says which is which.

`blocked` is in NEITHER set, on purpose. It says the endpoint refused the caller - the IP, the region,
a revoked credential - which is a fact about the caller, not about the endpoint's health or value.
It is skipped, like a day that was not probed. `rate_limited` and `payment_required` answer the
first question (the endpoint is there) and neither the second nor its opposite: a 429 is not a
verdict on whether the model gives you text, so rank.py leaves it out of the rate.
"""

# rank.py: the answered_rate. Only a reply with text in it counts.
ANSWERED = frozenset({"alive"})
NOT_ANSWERED = frozenset({"down", "overloaded", "empty"})

# gate_viability.py: the fourteen-day rule. Anything that proves a server is behind the URL counts.
UP_STATES = frozenset({"alive", "empty", "rate_limited", "payment_required"})
DOWN_STATES = frozenset({"down", "overloaded"})

# Skipped by both: not a measurement of the endpoint.
NOT_A_VERDICT = frozenset({"blocked", "no_key"})
