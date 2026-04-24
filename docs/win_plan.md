# 🏆 Win Plan — OpenEnv Hackathon

**Team X-Force | Current Score: ~78/100 | Target: 90+**  
**Deadline: 8 April 11:59 PM** ⚠️ *ALREADY PASSED — verify with organizers if late fixes are accepted*

---

## 🚨 CRITICAL: Verify NOW (Disqualification Risks)

These items can **disqualify you** if they fail. Check them FIRST.

### 1. Run `openenv validate`

```bash
pip install openenv-core
openenv validate .
```

If this fails, **nothing else matters**. Fix whatever it flags.

> [!CAUTION]
> This is the #1 unknown risk. The automated Phase 1 judging runs this validator. If you haven't tested it, you're flying blind.

### 2. Run the Pre-Submission Validation Script

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/scripts/validate-submission.sh | \
  bash -s -- https://lebiraja-customer-support-env.hf.space ./
```

Or download and run locally against your HF Space URL.

### 3. Verify inference.py Runs End-to-End

```bash
API_BASE_URL=https://integrate.api.nvidia.com/v1 \
MODEL_NAME=nvidia/nemotron-super-49b-v1 \
ENV_URL=https://lebiraja-customer-support-env.hf.space \
HF_TOKEN=your_token \
python inference.py
```

Must complete all 3 tasks without errors and produce scores. **Judges WILL run this.**

### 4. Verify HF Space Responds to `reset()`

```bash
curl -X POST https://lebiraja-customer-support-env.hf.space/reset?task=easy
# Must return HTTP 200 with session_id + observation
```

### 5. Confirm Resources Are Under Limits

> Runtime of inference script should be less than 20min  
> Make sure your env and inference can run on vcpu=2, memory=8gb

Your server is lightweight (no ML models loaded), so this should be fine. But verify inference.py completes in <20 min.

---

## 🔴 HIGH IMPACT Fixes (Score: +8-12 points)

### 6. Fix: Angry Agent Scores 1.0 on Easy Tasks

**Problem:** The grader ignores tone entirely. A hostile, rude agent gets a perfect score as long as it follows the right action sequence. Judges doing exploit checks WILL find this.

**Fix in `env/graders/task_easy.py`:**
```python
# Add tone penalty to final score
tone_avg = # average tone_score across steps
if tone_avg < 0.3:
    score *= 0.5  # Hostile agent gets max 50%
elif tone_avg < 0.5:
    score *= 0.75
```

**Impact:** +3-5 on Task & Grader Quality. This directly addresses the exploit check in Phase 3 judging.

### 7. Fix: Terse/Minimal Agent Still Scores Well

**Problem:** Agent saying "Email?" → "Refund done." → "Closed." scores 0.755. That's too generous for zero-effort responses.

**Fix:** Add a minimum message length or detail check to the grader.

### 8. Add Customer Reply Variation

**Problem:** Customer replies are template-based. Judges will notice "I'm not seeing any update on my end" appearing identically across sessions.

**Fix in `env/environment.py`:**
```python
import random

RESPONSES = {
    "neutral": [
        "I'm not seeing any update on my end. Did that go through?",
        "OK, I'll wait. Let me know when you have more info.",
        "Thanks for looking into this. What's the next step?",
        "Alright, I appreciate you checking on this.",
    ]
}
# Pick randomly instead of using fixed template
reply = random.choice(RESPONSES[sentiment_bucket])
```

**Impact:** +2-3 points. Makes the environment feel dynamic and real.

---

## 🟡 MEDIUM IMPACT Improvements (Score: +3-5 points)

### 9. Sync HF Space with Local Server

**Problem:** HF Space has **no auth and no rate limiting**. The local server (10.15.26.219) has both. The HF Space is what judges test.

**Decision needed:** For the competition, auth is NOT required. But the extra endpoints (`/leaderboard`, `/replay`, `/benchmark`) that exist on HF Space are NOT in your `openenv.yaml`. This could confuse the validator.

**Recommendation:** Keep the extra endpoints (they show ambition), but make sure `openenv validate` doesn't fail because of them.

### 10. Improve Baseline Scores in README

Your current README says:

```
easy:   ~0.65
medium: ~0.55
hard:   ~0.40
```

These are **low**. Judges interpret this as: either your reward function is broken, or you haven't tuned inference.py. You should:
- Tune `SYSTEM_PROMPT` in inference.py to score higher
- Update README with actual reproducible scores
- Scoring 0.8+ on easy and 0.7+ on medium is achievable with prompt tuning

### 11. Add Integration Tests

**Current test coverage:** Unit tests only (`tests/test_env.py`). No integration tests hitting the server endpoints.

```python
# tests/test_integration.py
def test_full_easy_episode():
    """Run a complete easy episode and verify score > 0."""
    r = client.post("/reset?task=easy")
    assert r.status_code == 200
    sid = r.json()["session_id"]
    
    r = client.post(f"/step?session_id={sid}", json={
        "action_type": "close", "message": "Refund processed."
    })
    assert r.status_code == 200
    assert 0.0 <= r.json()["final_score"] <= 1.0
```

**Impact:** +1-2 on Code Quality.

---

## 🟢 POLISH (Nice-to-Have, +1-2 points each)

### 12. Make Hard Task HARDER

Currently, a 1-step escalation with the right keywords scores 1.0. Consider:
- Requiring the agent to **acknowledge the customer first** before escalating (empathy check)
- Requiring the escalation reason to reference the **specific ticket details** (not just generic "SLA breach")

### 13. Add More Tickets

You have 30 tickets (10 per level). Adding 5-10 more per level shows depth and increases replayability.

### 14. Add a `__version__` or Metadata Endpoint

Small touch that shows professionalism:
```json
GET /
{
  "name": "CustomerSupportEnv",
  "version": "1.0.0",
  "openenv": "1.0",
  "tasks": ["easy", "medium", "hard"],
  "docs": "/docs"
}
```
*You already have this — ✅ good.*

---

## 📋 Priority Checklist

Do these **in order**. Stop when you're out of time.

| # | Task | Time | Impact | Risk if Skipped |
|:-:|------|:----:|:------:|:---------------:|
| 1 | Run `openenv validate` | 5 min | — | **DISQUALIFICATION** |
| 2 | Run pre-submission validation script | 5 min | — | **DISQUALIFICATION** |
| 3 | Verify inference.py end-to-end | 10 min | — | **DISQUALIFICATION** |
| 4 | Fix angry agent getting 1.0 (grader tone check) | 30 min | +4 | Judges exploit it |
| 5 | Add customer reply variation | 20 min | +2 | Feels templated |
| 6 | Tune inference.py for higher baseline scores | 30 min | +3 | Low scores look bad |
| 7 | Update README with real scores | 5 min | +1 | Scores look estimated |
| 8 | Add integration tests | 20 min | +1 | — |
| 9 | Fix terse agent scoring | 15 min | +1 | — |

**Minimum viable path to maximize score: Items 1-4 (50 minutes, +4-5 points)**

---

## Score Projection

```
Current:   78/100  (top 20-30%)
After #4:  82/100  (top 15-20%)
After #5:  84/100  (top 10-15%)
After #6:  87/100  (top 5-10%)
After all: 90/100  (potential winner)
```

---

*Good luck, Team X-Force. The foundation is solid — now polish it. 🚀*