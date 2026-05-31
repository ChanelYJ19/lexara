# Lexara — 5-Minute Live Demo Script

**Format:** Customer call, Show HN live demo, or investor walkthrough.  
**Runtime:** ~5 minutes with no questions. Budget 8–10 minutes if the audience is technical.  
**Runnable script:** `python demo/demo.py` (requires API running and OpenAI provider set)

---

## Before you start — what to have open

**Terminal 1 — API server:**
```bash
export LEXARA_LLM_PROVIDER=openai
export LEXARA_OPENAI_API_KEY=sk-...
lexara-api
# → Uvicorn running on http://localhost:8000
```

**Terminal 2 — Demo runner:**
```bash
source .venv/bin/activate        # activate the project virtualenv first
export LEXARA_LLM_PROVIDER=openai
export LEXARA_OPENAI_API_KEY=sk-...
# Ready to run: python demo/demo.py
```

**Browser tab:** `http://localhost:8000/docs` — for showing the live JSON response if the audience wants it.

**Verify before starting:**
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# Confirm: "llm_provider": "openai"
```

> **Hard stop:** If `llm_provider` is `mock`, do not proceed. The rewrite quality is not representative. Set `LEXARA_LLM_PROVIDER=openai` and restart the API.

---

## Step 1 — Problem (30 seconds)

**What to do:** Open with the confidence case — Demo C. No passage to show yet; just set up the framing.

**Say out loud:**
> "Most readability tools give you a score and stop there. You still have to fix the text by hand. Lexara rewrites toward a target grade and returns structured proof — before and after, four frameworks. But before we get to the hard case, let me show you what happens when content is already right."

---

## Step 2 — Efficiency (30 seconds)

**What to do:** Run Demo C.

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis lets plants make food from sunlight. Plants need sun and water to grow.",
    "target_grade": 5,
    "tolerance": 1.0
  }' | python3 -m json.tool
```

**Say out loud:**
> "This passage is already at grade 5. Watch `execution.skipped` — it's true. `passes_used` is zero. No LLM call, no token cost. Lexara scores first and only rewrites when it has to. For high-volume content pipelines, that matters. Now let's look at the hard case."

---

## Step 3 — Rewrite (60 seconds)

**What to do:** Run Demo A. Show the passage on screen first, then run the call.

```
Photosynthesis is the biochemical process by which chlorophyll-containing
organisms convert light energy into chemical energy, subsequently producing
glucose and releasing oxygen as a byproduct of cellular metabolism.
```

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the biochemical process by which chlorophyll-containing organisms convert light energy into chemical energy, subsequently producing glucose and releasing oxygen as a byproduct of cellular metabolism.",
    "target_grade": 6,
    "max_passes": 5,
    "tolerance": 1.5
  }' | python3 -m json.tool
```

**Expected output** (verified 2026-05-31 with gpt-4o-mini):
```
input.estimated_grade_level:  18.3
output.estimated_grade_level:  7.4
outcome.hit_target:            true
output.text:
  "Photosynthesis helps plants make food. Plants have a green color called
   chlorophyll. This color captures light from the sun. Then, plants change
   this light into chemical energy to produce glucose, and they release
   oxygen as a result."
```

**Say out loud:**
> "This is a real curriculum import. It scores at college level — grade 18. One call, grade 7.4 out. `hit_target` is true, within our ±1.5 tolerance of grade 6. The rewritten text is in `output.text`. And `outcome.summary` gives you a plain-language description of what changed — that's what you surface to the teacher or log for audit."

**Pause for questions here** if the audience wants to dig into the passage or the output shape.

---

## Step 4 — Proof (60 seconds)

**What to do:** Point to `input.frameworks` and `output.frameworks` in the JSON response.

**Say out loud:**
> "Here's what makes this defensible. We don't use one proprietary readability number. We score across four frameworks — Flesch-Kincaid, Dale-Chall, ATOS-style, and Lexile-equivalent. Every one of them moved toward the target. `frameworks_improved` lists them. When a district asks 'how do you know this is grade 6?' — you show them this."

**Pause for questions here** if the audience is technical and wants to understand the scoring methodology.

---

## Step 5 — Teacher workflow (60 seconds)

**What to do:** Run Demo B.

```bash
curl -s http://localhost:8000/v1/readability/rewrite \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Students will subsequently utilize the provided manipulatives to demonstrate their comprehension of fractional equivalence, and they must obtain sufficient evidence before completing the assessment.",
    "target_grade": 4,
    "preserve_meaning": true,
    "max_passes": 4
  }' | python3 -m json.tool
```

**Say out loud:**
> "Third scenario: a teacher copies LMS instructions into your product. They read at grade 11. The students are in grade 4. We set `preserve_meaning: true` — every fact, every instructional step stays. Only the vocabulary and sentence length change. This is the flag that makes it safe for academic content."

> "`outcome.hit_target` tells you whether to ship. If it's false, `outcome.summary` tells you how far off it landed — you surface that to the teacher instead of silently shipping a miss."

---

## Step 6 — Ship check (30 seconds)

**What to do:** Point to `outcome.hit_target`, `execution.warnings`, and `execution.degraded` in the docs or in your last response.

**Say out loud:**
> "Every response gives you a structured go/no-go signal. `hit_target` is true or false — your product decides what to do with that. `execution.warnings` tells you if something degraded gracefully. `execution.degraded` is the hard flag: no usable rewrite came back at all. You're never guessing whether the output is good — you have a scored grade, four framework readings, and a boolean."

**Close with:**
> "That's the full loop: score, rewrite, rescore, prove. One endpoint. The SDK is one line: `client.readability.rewrite(text, target_grade=6)`."

---

## Handling common questions

| Question | Answer |
|---|---|
| "What's the hit rate?" | 58% of passages hit target within ±1 grade level using gpt-4o-mini on our K-12 test set. Works best for grade 4–12 targets. |
| "What if it misses?" | `outcome.hit_target` is false. `outcome.summary` gives the actual landing grade. You decide whether to surface it or retry with wider tolerance. |
| "Can you guarantee grade X?" | No, and we document that. Always check `hit_target` before shipping. Grade targets below 4 on academic-register text are reliably difficult. |
| "Which LLM does it use?" | Currently OpenAI gpt-4o-mini. Provider is configurable — `LEXARA_LLM_PROVIDER`. |
| "Is the Lexile score official?" | No. `lexile_estimated` is a Lexile-scale estimate, not an official MetaMetrics score. Labeled clearly in every response. |
| "Does it preserve meaning?" | `preserve_meaning: true` keeps facts, numbers, names, and instructional steps. Human review is still recommended for high-stakes content. |
