# Lexara

**Rewrite educational text to your target grade. Prove it with multi-framework scores.**

Lexara is developer infrastructure for edtech builders. One API call scores your passage, rewrites it toward a target US grade level, rescoring after each pass until the target is met — then returns `input` → `output` with per-framework before/after proof.

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"text":"Photosynthesis is the biochemical process by which chlorophyll-containing organisms convert light energy into chemical energy.","target_grade":6,"max_passes":5}'
```

Not a readability score you stare at. A rewrite you can ship — with evidence.

---

## Why Lexara exists

### Score-only is not enough

A score-only API tells you a worksheet reads at grade 11. It does not give you a grade-5 version. Your user still has to rewrite by hand, guess whether it worked, and hope one readability number reflects their district's expectations.

That is a diagnostic. Edtech products need an **action**: adjust the text, verify the result, retry if needed.

### Why multi-framework scoring + rewrite together

No single readability formula is authoritative — districts, publishers, and literacy tools reference different frameworks (Flesch-Kincaid, Dale-Chall, Lexile-style, ATOS-style). Lexara:

1. **Scores across frameworks** before and after the rewrite
2. **Rewrites toward your target grade**, not a single opaque number
3. **Returns proof** — `outcome.hit_target`, `frameworks_improved`, and per-framework grades on both sides

Scoring is the **verification layer** for the rewrite. The product is the loop: **rewrite → rescore → prove**.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
lexara-api   # → http://localhost:8000/docs
```

### 1. Rewrite (curl) — start here

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Students will subsequently utilize the provided manipulatives to demonstrate their comprehension of fractional equivalence.",
    "target_grade": 4,
    "preserve_meaning": true,
    "max_passes": 4
  }' | python3 -m json.tool
```

Look for: `outcome.summary`, `outcome.hit_target`, `input.estimated_grade_level`, `output.estimated_grade_level`, `output.text`.

### 2. Rewrite (Python SDK)

```python
from lexara import LexaraClient, Tone

client = LexaraClient(api_key="dev-local-key")

result = client.readability.rewrite(
    "Photosynthesis is the biochemical process by which chlorophyll-containing "
    "organisms convert light energy into chemical energy.",
    target_grade=6,
    preserve_meaning=True,
    max_passes=5,
)

print(result.outcome.summary)
print(f"{result.input.estimated_grade_level} → {result.output.estimated_grade_level} (target {result.target.grade})")
print(f"Hit target: {result.hit_target} | Frameworks improved: {result.outcome.frameworks_improved}")
print(result.output.text)
```

### 3. Score only (when you don't need a rewrite yet)

```python
scored = client.readability.score(
    passage,
    frameworks=["flesch_kincaid", "lexile"],
)
print(scored.aggregate.estimated_grade_level)
```

Use `POST /v1/readability/score` for diagnostics. Use `rewrite` when you need to **act** on the result.

---

## Demo-ready examples

Three passages you can run in a customer call, Show HN thread, or live demo. All work with the local mock provider (no API spend).

### Demo A — Science passage: college → grade 6

**Story:** *"Your curriculum import is too hard for middle school. One call fixes and proves it."*

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the biochemical process by which chlorophyll-containing organisms convert light energy into chemical energy, subsequently producing glucose and releasing oxygen as a byproduct of cellular metabolism.",
    "target_grade": 6,
    "max_passes": 5,
    "tolerance": 1.5
  }'
```

```python
from lexara import LexaraClient

PASSAGE = (
    "Photosynthesis is the biochemical process by which chlorophyll-containing "
    "organisms convert light energy into chemical energy, subsequently producing "
    "glucose and releasing oxygen as a byproduct of cellular metabolism."
)

client = LexaraClient(api_key="dev-local-key")
r = client.readability.rewrite(PASSAGE, target_grade=6, max_passes=5, tolerance=1.5)
print(f"Before: grade {r.input.estimated_grade_level}  After: grade {r.output.estimated_grade_level}")
print(r.output.text)
```

**Talk track:** Show `input.frameworks[]` vs `output.frameworks[]` — four frameworks moved, not one proprietary number.

---

### Demo B — Worksheet instructions: teacher tone, grade 4

**Story:** *"Teachers paste LMS instructions. Lexara returns student-ready text with meaning preserved."*

```python
from lexara import LexaraClient, Tone

client = LexaraClient(api_key="dev-local-key")

result = client.readability.rewrite(
    "Students will subsequently utilize the provided manipulatives to demonstrate "
    "their comprehension of fractional equivalence, and they must obtain sufficient "
    "evidence before completing the assessment.",
    target_grade=4,
    tone=Tone.friendly,
    preserve_meaning=True,
    max_passes=4,
)

if result.hit_target:
    ship_to_lms(result.output.text)
else:
    print(result.outcome.summary, result.execution.warnings)
```

Run: `python examples/sdk_rewrite_to_target.py`

---

### Demo C — Already at target: no LLM call

**Story:** *"Lexara doesn't burn tokens when content is already right — it scores, verifies, and skips."*

```python
from lexara import LexaraClient

client = LexaraClient(api_key="dev-local-key")

result = client.readability.rewrite(
    "Photosynthesis lets plants make food from sunlight. Plants need sun and water to grow.",
    target_grade=5,
    tolerance=1.0,
)

assert result.execution.skipped is True
assert result.execution.passes_used == 0
assert result.hit_target is True
assert result.output.text == result.input.text
print(result.outcome.summary)
# → "Already at grade 5.1 (target 5, within ±1). No rewrite needed."
```

Full payload: `examples/canonical/rewrite_already_at_target.json`

**Run all three:** `python examples/demo_showcase.py`

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/readability/rewrite` | **Primary** — rewrite to target grade + multi-framework proof |
| `POST` | `/v1/readability/score` | Diagnostics only — no rewrite |
| `GET` | `/health` | Liveness |

Auth: `Authorization: Bearer <key>` or `x-api-key: <key>`

### Rewrite response (read in this order)

| Block | Meaning |
|-------|---------|
| `input` / `output` | Original vs rewritten text + per-framework grades |
| `outcome` | `hit_target`, grade from → to, `frameworks_improved`, `summary` |
| `target` | Goal grade, tolerance, grade band |
| `execution` | Passes used, provider, `skipped`, `warnings` |

Shortcuts: `rewritten_text`, `hit_target`.

Canonical JSON: [`examples/canonical/`](examples/canonical/)

---

## Python SDK

```python
from lexara import LexaraClient, Tone, RewriteOptions

client = LexaraClient(api_key="...", timeout=120, max_retries=2)

# Hero workflow
result = client.readability.rewrite(
    text,
    target_grade=5,
    preserve_meaning=True,
    tone=Tone.friendly,
    max_passes=4,
)

# Or bundle options (all fields optional except target_grade on rewrite call)
opts = RewriteOptions(preserve_meaning=True, tone=Tone.friendly, max_passes=4)
result = client.readability.rewrite(text, target_grade=5, options=opts)
```

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `target_grade` | required | Desired US grade level (1–16) |
| `preserve_meaning` | `True` | Keep facts, numbers, names, steps |
| `tone` | `neutral` | `friendly`, `formal`, `playful`, `academic`, … |
| `max_passes` | `3` | Max rewrite → rescore iterations |
| `frameworks` | all | Frameworks used to judge progress |
| `tolerance` | `1.0` | Grade levels within target = hit |

**Examples:** `examples/sdk_rewrite_to_target.py` · `examples/sdk_rewrite_inspect_scores.py` · `examples/sdk_score_only.py`

**Exceptions:** `AuthenticationError` · `ValidationError` · `LexaraTimeoutError` · `LexaraConnectionError` · `LexaraAPIError`

---

## How rewrite works

Each `POST /v1/readability/rewrite` request:

1. Scores `input` across selected frameworks
2. Skips the LLM if already within `tolerance` of `target_grade`
3. Otherwise **rewrite → rescore → retry** up to `max_passes`
4. Returns the best attempt with full before/after snapshots

Provider failures become `execution.warnings` — the endpoint returns 200 with the best text so far. Check `outcome.hit_target` and `execution.degraded` before shipping to users.

---

## Frameworks & safe claims

| Framework | ID | Confidence | What to tell customers |
|-----------|-----|------------|------------------------|
| Flesch-Kincaid Grade | `flesch_kincaid` | **exact** | Standard formula; syllable counts use an estimated syllable heuristic |
| New Dale-Chall | `dale_chall` | **estimated** | Published formula; familiar-word list is approximate, not the licensed 3,000-word list |
| ATOS-style | `atos_estimated` | **estimated** | ATOS-style estimate — **not** an official Accelerated Reader level |
| Lexile-equivalent | `lexile_estimated` | **estimated** | Lexile-scale estimate — **not** an official MetaMetrics Lexile score |

Legacy aliases: `atos` → `atos_estimated`, `lexile` → `lexile_estimated`.

### Safe to say

- Rewrite toward a target US grade level in one API call
- Multi-framework before/after proof (`input.frameworks` → `output.frameworks`)
- Flesch-Kincaid uses the standard grade formula; other frameworks are clearly labeled `estimated`
- Developer-friendly SDK: `client.readability.rewrite(text, target_grade=6)`

### Do not say

- Official Lexile, ATOS, or Dale-Chall certification
- Guaranteed rewrite success on every passage — always check `outcome.hit_target`
- Single "true" reading level — Lexara returns multiple frameworks intentionally

---

## Configuration

See `.env.example`.

| Var | Default | Meaning |
|-----|---------|---------|
| `LEXARA_LLM_PROVIDER` | `mock` | `mock` (local/dev) or `openai` (real rewrites) |
| `LEXARA_OPENAI_API_KEY` | – | Required when provider is `openai` |
| `LEXARA_OPENAI_MODEL` | `gpt-4o-mini` | Chat model for rewrites |
| `LEXARA_API_KEYS` | `dev-local-key` | Valid API keys |

Real provider setup:

```bash
pip install -e ".[openai]"
export LEXARA_LLM_PROVIDER=openai
export LEXARA_OPENAI_API_KEY=sk-...
lexara-api
```

---

## Rewrite effectiveness evals

Measure rewrite quality before demos — not just formula correctness:

```bash
lexara-eval                              # table summary (mock)
lexara-eval --output eval/results.json   # save JSON for review
```

Dataset: `src/lexara/eval/data/rewrite_effectiveness.json` (grades 2–12, five passage types).

With OpenAI: `lexara-eval --provider openai --output eval/results-openai.json`

---

## Homepage & API copy (suggested)

**Headline:** Rewrite text to your target grade. Prove it across four frameworks.

**Subhead:** Lexara is edtech API infrastructure — score, rewrite, rescore, and return before/after proof in one call. Not a number. A number you acted on.

**API one-liner:** `POST /v1/readability/rewrite` — rewrite toward a target grade; get `input`, `output`, and `outcome.hit_target` with Flesch-Kincaid, Dale-Chall, ATOS-style, and Lexile-equivalent verification.

**Bullets for landing page:**
- Score-only APIs diagnose. Lexara rewrites and proves the result.
- Multi-framework before/after — not one proprietary readability number.
- One SDK call: `client.readability.rewrite(passage, target_grade=6)`
- Skips the LLM when text is already at target.

---

## Demo script (5 minutes)

Use this flow in a customer call or Show HN live demo:

1. **Problem (30s)** — Paste the Demo A science passage. *"This reads at college level. Your middle-school product can't use it as-is."*
2. **Rewrite (60s)** — Run curl or SDK. Show `outcome.summary` and grade drop in `input` → `output`.
3. **Proof (60s)** — Expand `input.frameworks` and `output.frameworks`. *"We don't trust one formula — we show four, before and after."*
4. **Teacher workflow (60s)** — Demo B worksheet instructions with `tone=friendly`. Show rewritten bullet-friendly text.
5. **Efficiency (30s)** — Demo C already-at-target. *"No LLM call when content is already right."*
6. **Ship check (30s)** — Point at `outcome.hit_target`, `execution.warnings`, and the safe-claims table. *"You decide when to ship; Lexara gives you structured proof."*

Runnable: `python examples/demo_showcase.py`

---

## Architecture

| Layer | Role |
|-------|------|
| `api/` | HTTP, auth, middleware |
| `services/` | Rewrite + scoring orchestration |
| `scoring/` | Pure readability formulas |
| `rewriting/` | LLM provider + rewrite/rescore pipeline |
| `eval/` | Rewrite effectiveness harness |
| `client.py` | Python SDK |

---

## Tests

```bash
pytest                                    # full suite (mock, no network)
pytest tests/test_eval_harness.py -v
pytest tests/test_client.py -v

# Live OpenAI — opt-in:
LEXARA_OPENAI_API_KEY=sk-... pytest -m integration -v
```
