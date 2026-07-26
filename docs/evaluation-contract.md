# Baseline Evaluation Contract

The machine-readable contract is [`evaluation/contract.json`](../evaluation/contract.json).
It is the source of truth for the initial 72-case corpus, deterministic grading rules,
release thresholds, reporting requirements, and the advisory independent LLM judge.

Every concrete case must satisfy the contract's required case-schema fields. The exact
judge model is intentionally deferred until the agent-model-boundary decision, but it
must differ from the evaluated agent model.

Every insert, update, and delete case also requires an explicit user confirmation after
the agent presents an exact Stable-ID diff. A confirmation authorizes only that unchanged
stage. Commits create a new artifact, preserve the source workbook, and reopen the output
to verify the authorized cells changed exactly and no others did.
