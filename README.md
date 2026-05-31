# Lexara — Score & Rewrite API

**Multi-framework readability scoring and grade-targeted rewriting in one workflow.**

Lexara is developer infrastructure for edtech. Score text against Flesch-Kincaid, Dale-Chall, ATOS-style, and Lexile-equivalent frameworks in a single call — then rewrite toward a target grade level and get before/after scores back. One API key. One SDK.

> **Why Lexara vs score-only APIs?** A scoring endpoint tells you a passage is too hard. Lexara closes the loop: score → rewrite → rescore until you hit your target grade — with multi-framework proof at every step.

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

print(result.improvement.summary)
# "Lowered reading level from grade 14.2 to 6.1 (target grade 6). Target met..."

print(result.before.aggregate_grade_level)   # 14.2
print(result.after.aggregate_grade_level)    # 6.1
print(result.after.text)                     # rewritten passage
```

```bash
pytest   # includes rewrite effectiveness evals on educational text
```

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/readability/rewrite` | **Core workflow** — score → rewrite → rescore |
| `POST` | `/v1/readability/score` | Multi-framework score only |
| `GET` | `/health` | Liveness |

Auth: `Authorization: Bearer <key>` or `x-api-key: <key>`

---

## Example 1 — Adjust a science passage (curl)

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the biochemical process by which chlorophyll-containing organisms convert light energy into chemical energy, subsequently producing glucose and releasing oxygen.",
    "target_grade": 6,
    "preserve_meaning": true,
    "max_passes": 5
  }'
```

Key response fields:

```json
{
  "before": {
    "text": "Photosynthesis is the biochemical process...",
    "aggregate_grade_level": 15.4,
    "grade_band": "College",
    "scores": [ { "framework": "flesch_kincaid", "estimated_grade_level": 16.2, "..." : "..." } ]
  },
  "after": {
    "text": "Plants use sunlight to make food. They also make oxygen.",
    "aggregate_grade_level": 5.8,
    "grade_band": "4-5",
    "scores": [ { "framework": "flesch_kincaid", "estimated_grade_level": 4.6, "..." : "..." } ]
  },
  "target": {
    "grade": 6,
    "tolerance": 1.0,
    "hit_target": true,
    "distance_from_target": 0.2,
    "target_grade_band": "6-8"
  },
  "improvement": {
    "grade_level_before": 15.4,
    "grade_level_after": 5.8,
    "grade_level_change": -9.6,
    "target_grade": 6,
    "moved_toward_target": true,
    "summary": "Lowered reading level from grade 15.4 to 5.8 (target grade 6). Target met within ±1 grade levels."
  },
  "pipeline": { "passes_used": 2, "provider": "mock", "degraded": false, "warnings": [] },
  "rewritten_text": "Plants use sunlight to make food. They also make oxygen.",
  "hit_target": true
}
```

---

## Example 2 — Simplify worksheet instructions (Python SDK)

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
    publish_to_lms(result.after.text)
else:
    log(result.improvement.summary, warnings=result.pipeline.warnings)
```

Run: `python examples/adjust_worksheet_instructions.py`

---

## Example 3 — Batch-adjust lesson content

```python
passages = [
    ("The committee will subsequently utilize numerous resources...", 5),
    ("- Define photosynthesis.\n- Explain how plants use sunlight.", 5),
]

for text, target in passages:
    r = client.readability.adjust(text, target_grade=target)
    print(r.improvement.grade_level_before, "→", r.improvement.grade_level_after, r.hit_target)
```

Run: `python examples/adjust_batch.py`

---

## Example 4 — Score only (diagnostics)

When you only need readability diagnostics without rewriting:

```bash
curl -s http://localhost:8000/v1/readability/score \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "The cat sat on the mat.", "frameworks": ["flesch_kincaid", "lexile_estimated"]}'
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

# Score only
scores = client.readability.score(text)
```

`adjust()` returns typed `RewriteResponse` with `before`, `after`, `target`, `improvement`, and `pipeline` blocks.

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
| `LEXARA_API_KEYS` | `dev-local-key` | Valid API keys |

---

## Safe customer claims

**Say:** multi-framework score + rewrite in one API call; before/after grade proof; developer-friendly SDK.

**Don't say:** official Lexile/ATOS/Dale-Chall certification; guaranteed rewrite on every passage (check `hit_target`, `pipeline.warnings`).

---

## Suggested homepage / API copy

**Headline:** Score readability across frameworks. Rewrite to your target grade. One API call.

**Subhead:** Lexara is edtech developer infrastructure — multi-framework scoring and grade-targeted rewriting in a single workflow. Not just a score. A score you can act on.

**API one-liner:** `POST /v1/readability/rewrite` — score your text, rewrite toward a target grade, rescore until you hit it. Returns before/after snapshots across Flesch-Kincaid, Dale-Chall, ATOS-style, and Lexile-equivalent frameworks.

**Differentiator bullets:**
- Score-only APIs tell you the problem. Lexara fixes it in the same request.
- Multi-framework before/after — not a single proprietary number.
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
pytest                         # unit + scoring regression + rewrite evals
pytest tests/test_rewrite_effectiveness.py -v
pytest -m integration          # live OpenAI (requires LEXARA_OPENAI_API_KEY)
```
