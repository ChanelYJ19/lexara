# Lexara — Rewrite to Target Grade API

**Rewrite text to the right grade and prove it — multi-framework scoring is the verification layer.**

Lexara is developer infrastructure for edtech. One API call: score your passage, rewrite toward a target grade, rescore until you hit it (or exhaust passes). Returns `input` → `output` with per-framework proof. Score-only diagnostics available when you don't need a rewrite yet.

> **Why Lexara vs score-only APIs?** A scoring endpoint tells you a passage is too hard. Lexara closes the loop: rewrite → verify → retry — with multi-framework before/after proof at every step.

---

## Quick start (rewrite workflow)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
lexara-api   # http://localhost:8000/docs
```

```python
from lexara import LexaraClient

client = LexaraClient(api_key="dev-local-key")

result = client.readability.adjust(
    "Photosynthesis converts light energy into chemical energy...",
    target_grade=6,
)

print(result.outcome.summary)
print(f"passes: {result.execution.passes_used} | hit: {result.hit_target}")
print(f"frameworks improved: {result.outcome.frameworks_improved}")

print(result.input.estimated_grade_level)   # before
print(result.output.estimated_grade_level)  # after
print(result.output.text)                   # rewritten passage
```

```bash
pytest   # includes rewrite effectiveness evals + canonical example validation
```

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/readability/rewrite` | **Core workflow** — rewrite to target grade + scored proof |
| `POST` | `/v1/readability/score` | Diagnostics only — no rewrite |
| `GET` | `/health` | Liveness |

Auth: `Authorization: Bearer <key>` or `x-api-key: <key>`

---

## Response shape (rewrite-first)

Read the response in this order:

| Block | What it tells you |
|-------|-------------------|
| `input` / `output` | The transformation — original text vs rewritten text, each with `estimated_grade_level` and `frameworks[]` |
| `outcome` | Verification — `hit_target`, grade moved `estimated_grade_from` → `estimated_grade_to`, `frameworks_improved`, `summary` |
| `target` | The grade goal (`grade`, `tolerance`, `grade_band`) |
| `execution` | Pipeline — `passes_used`, `provider`, `skipped`, `warnings` |

Computed shortcuts: `rewritten_text` (= `output.text`), `hit_target` (= `outcome.hit_target`).

---

## Canonical examples

Full request/response payloads live in [`examples/canonical/`](examples/canonical/):

| File | Scenario |
|------|----------|
| `rewrite_hit_target.json` | Rewrite succeeds in one pass (`hit_target: true`) |
| `rewrite_improved_miss.json` | Rewrite improves but misses target (`moved_toward_target: true`, `hit_target: false`) |
| `rewrite_already_at_target.json` | Input already at target — no LLM call (`execution.skipped: true`) |

---

## Example 1 — Rewrite a passage (curl)

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the biochemical process by which chlorophyll-containing organisms convert light energy into chemical energy.",
    "target_grade": 6,
    "preserve_meaning": true,
    "max_passes": 5
  }'
```

Key response fields:

```json
{
  "input": {
    "text": "Photosynthesis is the biochemical process...",
    "estimated_grade_level": 15.4,
    "grade_band": "College",
    "frameworks": [{ "framework": "flesch_kincaid", "estimated_grade_level": 16.2 }]
  },
  "output": {
    "text": "Plants use sunlight to make food. They also make oxygen.",
    "estimated_grade_level": 5.8,
    "grade_band": "4-5",
    "frameworks": [{ "framework": "flesch_kincaid", "estimated_grade_level": 4.6 }]
  },
  "target": { "grade": 6, "tolerance": 1.0, "grade_band": "6-8" },
  "outcome": {
    "estimated_grade_from": 15.4,
    "estimated_grade_to": 5.8,
    "grade_change": -9.6,
    "target_grade": 6,
    "hit_target": true,
    "distance_from_target": 0.2,
    "moved_toward_target": true,
    "frameworks_improved": ["flesch_kincaid", "dale_chall", "atos_estimated", "lexile_estimated"],
    "summary": "Lowered from grade 15.4 to 5.8 (target 6, within ±1)."
  },
  "execution": {
    "passes_used": 2,
    "provider": "mock",
    "skipped": false,
    "provider_calls_attempted": 2,
    "provider_calls_failed": 0,
    "warnings": [],
    "degraded": false
  },
  "rewritten_text": "Plants use sunlight to make food. They also make oxygen.",
  "hit_target": true
}
```

---

## Example 2 — Already at target (no LLM call)

When text already reads at the target grade, Lexara scores it, skips the rewrite, and returns `execution.skipped: true`:

```python
result = client.readability.adjust(
    "Photosynthesis lets plants make food from sunlight. Plants need sun and water.",
    target_grade=5,
    tolerance=1.0,
)
assert result.execution.skipped is True
assert result.execution.passes_used == 0
assert result.hit_target is True
assert result.output.text == result.input.text
```

See `examples/canonical/rewrite_already_at_target.json`.

---

## Example 3 — Simplify worksheet instructions (Python SDK)

```python
from lexara import LexaraClient

client = LexaraClient(api_key="dev-local-key")

result = client.readability.adjust(
    "Students will subsequently utilize the provided manipulatives to demonstrate "
    "their comprehension of fractional equivalence.",
    target_grade=4,
    tone="friendly",
    max_passes=4,
)

if result.hit_target:
    publish_to_lms(result.output.text)
else:
    log(result.outcome.summary, warnings=result.execution.warnings)
```

Run: `python examples/adjust_worksheet_instructions.py`

---

## Example 4 — Batch-adjust lesson content

```python
passages = [
    ("The committee will subsequently utilize numerous resources...", 5),
    ("- Define photosynthesis.\n- Explain how plants use sunlight.", 5),
]

for text, target in passages:
    r = client.readability.adjust(text, target_grade=target)
    print(r.outcome.estimated_grade_from, "→", r.outcome.estimated_grade_to, r.hit_target)
```

Run: `python examples/adjust_batch.py`

---

## Example 5 — Score only (diagnostics)

When you only need readability diagnostics — or want to check grade before calling rewrite:

```bash
curl -s http://localhost:8000/v1/readability/score \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "The cat sat on the mat.", "frameworks": ["flesch_kincaid", "lexile_estimated"]}'
```

Then rewrite with the same text:

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "The cat sat on the mat.", "target_grade": 2, "max_passes": 3}'
```

---

## Python SDK

```python
from lexara import LexaraClient

client = LexaraClient(api_key="...")

# Core workflow (preferred)
result = client.readability.adjust(text, target_grade=5)

# Equivalent
result = client.readability.rewrite(text, target_grade=5)

# Score only — pair with adjust() when text needs changing
scores = client.readability.score(text)
```

`adjust()` returns typed `RewriteResponse` with:

| Field | Meaning |
|-------|---------|
| `input` / `output` | Text + multi-framework verification at each step |
| `outcome.hit_target` | Whether target grade was met |
| `outcome.frameworks_improved` | Frameworks that moved closer to target |
| `outcome.summary` | Plain-language before → after outcome |
| `execution.passes_used` | Rewrite/rescore loops (0 if already at target) |
| `execution.skipped` | True when text was already at target |
| `rewritten_text` | Shortcut for `output.text` |

---

## Rewrite + rescore workflow

Each `POST /v1/readability/rewrite` request runs:

1. **Score input** across selected frameworks
2. **Skip LLM** if already within `tolerance` of `target_grade`
3. Otherwise **rewrite → rescore → retry** up to `max_passes`
4. Return the **best attempt** (closest to target) with input/output snapshots and `outcome` verification

Prompts preserve facts, numbers, names, and instructional steps when `preserve_meaning=true`. Provider and rescore failures emit structured `execution.warnings` and set `execution.degraded=true` without crashing the request.

---

## Scoring engine

Each framework lives in `src/lexara/scoring/frameworks/`:

| Framework | ID | `confidence` |
|-----------|-----|--------------|
| Flesch-Kincaid Grade | `flesch_kincaid` | `exact` |
| New Dale-Chall | `dale_chall` | `estimated` |
| ATOS-style | `atos_estimated` | `estimated` |
| Lexile-equivalent | `lexile_estimated` | `estimated` |

Every score response includes text stats: `sentence_count`, `word_count`, `avg_sentence_length`, `avg_word_length`, `syllable_estimate`, `difficult_word_count`.

Legacy aliases `atos` / `lexile` resolve to `*_estimated`.

Regression bands: `tests/fixtures/scoring_calibration.json`  
Rewrite evals: `tests/fixtures/rewrite_eval_cases.json`

---

## Configuration

See `.env.example`. Key vars:

| Var | Default | Meaning |
|-----|---------|---------|
| `LEXARA_LLM_PROVIDER` | `mock` | `mock` or `openai` for real rewrites |
| `LEXARA_OPENAI_API_KEY` | – | Required when provider is `openai` |
| `LEXARA_OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model for rewrites |
| `LEXARA_OPENAI_TIMEOUT_SECONDS` | `60` | Per-request timeout |
| `LEXARA_OPENAI_MAX_RETRIES` | `2` | Retries on transient OpenAI errors |
| `LEXARA_OPENAI_MAX_COMPLETION_TOKENS` | `4096` | Cap output tokens per LLM call |
| `LEXARA_API_KEYS` | `dev-local-key` | Valid API keys |

---

## Real LLM provider (OpenAI alpha)

For customer-facing rewrite quality, switch from the deterministic mock to OpenAI:

```bash
pip install -e ".[openai]"
export LEXARA_LLM_PROVIDER=openai
export LEXARA_OPENAI_API_KEY=sk-...
lexara-api
```

The OpenAI provider is alpha-hardened:

- **Timeouts** — `LEXARA_OPENAI_TIMEOUT_SECONDS` per request
- **Retries** — transient errors (timeout, connection, rate limit) with exponential backoff; honors `Retry-After` when present
- **Structured output** — `response_format: json_object` + strict parse of `{"rewritten_text": "..."}`
- **Parse fallback** — lenient plain-text fallback if JSON shape is wrong (logged as warning)
- **Failure-safe** — provider errors become `execution.warnings`; the rewrite endpoint returns 200 with the best text so far
- **Cost hooks** — structured `llm_completion` logs with token counts and estimated USD cost

Provider failures never crash `POST /v1/readability/rewrite` — check `execution.degraded` and `execution.warnings`.

---

## Running real-provider tests safely

Integration tests are **opt-in** and **never run in default `pytest`**.

```bash
pip install -e ".[openai,dev]"

# Live rewrite quality contract (costs a few cents; uses your API key)
LEXARA_OPENAI_API_KEY=sk-... pytest -m integration -v

# Only the live OpenAI rewrite test:
LEXARA_OPENAI_API_KEY=sk-... pytest tests/test_openai_contract.py::test_openai_rewrite_produces_simpler_text -v
```

**Safety rules:**

- Do **not** set `LEXARA_OPENAI_API_KEY` in CI unless you intend to run integration tests.
- Default `pytest` uses the mock provider only — no network, no spend.
- `test_openai_provider_failure_returns_structured_warnings` uses an invalid key but is marked `integration` and hits the network once; run it only when validating failure behavior.
- Monitor logs for `llm_completion` (success) and `llm_completion_failed` (retries).

---

## Safe customer claims

**Say:** rewrite to target grade with multi-framework before/after proof; developer-friendly SDK.

**Don't say:** official Lexile/ATOS/Dale-Chall certification; guaranteed rewrite on every passage (check `outcome.hit_target`, `execution.warnings`).

---

## Suggested homepage / API copy

**Headline:** Rewrite text to your target grade. Prove it with multi-framework scores.

**Subhead:** Lexara is edtech developer infrastructure — not a score you stare at, but a rewrite you can ship with before/after verification in one API call.

**API one-liner:** `POST /v1/readability/rewrite` — rewrite toward a target grade, rescore until you hit it, return input/output snapshots with Flesch-Kincaid, Dale-Chall, ATOS-style, and Lexile-equivalent proof.

**Differentiator bullets:**
- Score-only APIs tell you the problem. Lexara fixes it in the same request.
- `input` → `output` transformation with `outcome.hit_target` and `frameworks_improved`.
- One SDK method: `client.readability.adjust(text, target_grade=6)`

---

## Architecture

| Layer | Role |
|-------|------|
| `api/` | HTTP, auth, middleware |
| `services/` | Rewrite + scoring orchestration |
| `scoring/` | Pure readability formulas |
| `rewriting/` | LLM provider + rewrite/rescore pipeline |
| `client.py` | Typed Python SDK |

---

## Tests

```bash
pytest                                    # full suite (mock provider, no network)
pytest tests/test_canonical_examples.py   # validate canonical JSON payloads
pytest tests/test_rewrite_workflow_alpha.py -v
pytest tests/test_rewrite_effectiveness.py -v
pytest tests/test_openai_provider.py -v   # mocked OpenAI SDK (no network)

# Live OpenAI — opt-in, requires key, may incur cost:
LEXARA_OPENAI_API_KEY=sk-... pytest -m integration -v
```
