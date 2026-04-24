# 🏆 Reward System — Complete Analysis & Implementation Guide

> Extracted from the `customer-support-env` (meta_hack) codebase.
> Use this to build an equivalent reward system in your own OpenEnv environment.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Single-Agent Reward Formula (Round 1)](#2-single-agent-reward-formula)
3. [Hierarchical Reward Formula (Round 2)](#3-hierarchical-reward-formula)
4. [Individual Signal Functions](#4-individual-signal-functions)
5. [Penalty System](#5-penalty-system)
6. [LLM-as-Judge System](#6-llm-as-judge-system)
7. [Anti-Gaming Guards](#7-anti-gaming-guards)
8. [Task-Specific Graders](#8-task-specific-graders)
9. [Why This Is Better Than Regular Rewards](#9-why-this-is-better)
10. [Step-by-Step Implementation Guide](#10-implementation-guide)

---

## 1. Architecture Overview

The reward system is a **hybrid dense reward** architecture with three layers:

```
┌─────────────────────────────────────────────────┐
│              FINAL REWARD (0.0 – 1.0)           │
├─────────────────────────────────────────────────┤
│  Layer 3: Security & Integrity Guards           │
│  ├── RewardGuard (anti-exploit multiplier)      │
│  ├── HierarchyGuard (escalation discipline)     │
│  └── InjectionDetector (prompt injection scan)  │
├─────────────────────────────────────────────────┤
│  Layer 2: LLM-as-Judge (semantic evaluation)    │
│  ├── Empathy scoring                            │
│  ├── Policy adherence scoring                   │
│  ├── Resolution quality scoring                 │
│  ├── Supervisor oversight scoring               │
│  └── Manager decision quality scoring           │
├─────────────────────────────────────────────────┤
│  Layer 1: Rule-Based Signals                    │
│  ├── Tone (VADER sentiment)                     │
│  ├── Resolution (keyword-category match)        │
│  ├── Efficiency (steps used / max steps)        │
│  ├── Accuracy (required info gathered)          │
│  ├── SLA compliance                             │
│  └── Hierarchy effectiveness                    │
└─────────────────────────────────────────────────┘
```

**Key source files:**
- `env/reward_engine.py` — Core formulas
- `env/llm_judge.py` — LLM-as-Judge rubrics
- `env/reward_guard.py` — Anti-exploit detection
- `env/hierarchy_guard.py` — Hierarchy discipline
- `env/security.py` — Prompt injection detection
- `env/graders/` — Task-specific final graders

---

## 2. Single-Agent Reward Formula

Used for Round 1 tasks (`easy`, `medium`, `hard`, `nightmare`).

### Terminal Step Formula

```
R_raw = 0.40 × resolution_score
      + 0.20 × tone_score
      + 0.20 × efficiency_score
      + 0.20 × accuracy_score
      + loop_penalty          (0 or -0.2)
      + contradiction_penalty (0 or -0.15)
      + escalation_penalty    (0 or -0.3)
      + stuffing_penalty      (0 or -0.30)
      + info_gathering_bonus  (0 or +0.1)
```

### Non-Terminal Step Formula

```
R_raw = 0.40 × 0.0                          (resolution = 0 mid-episode)
      + 0.20 × tone_score
      + 0.20 × (efficiency_score × 0.3)     (dampened)
      + 0.20 × (accuracy_score × 0.5)       (dampened)
      + loop_penalty
      + contradiction_penalty
      + stuffing_penalty
      + info_gathering_bonus
```

### Final Value Computation

```
integrity = RewardGuard.check_integrity(...)   → multiplier in [0.1, 1.0]
security  = InjectionDetector.scan(...)        → detected: true/false

R_final = clamp(R_raw × integrity_multiplier, 0.0, 1.0)

if security.detected:
    R_final = max(0.0, R_final - 0.5)
```

---

## 3. Hierarchical Reward Formula

Used for Round 2 tasks (`hierarchy_*`, `curriculum_*`).

### Terminal Step Formula

```
R_raw = 0.25 × resolution_score         (blended rule + LLM)
      + 0.15 × sla_score                (rule-based)
      + 0.15 × empathy_score            (LLM-as-Judge)
      + 0.15 × policy_adherence_score   (LLM-as-Judge)
      + 0.10 × accuracy_score           (rule-based)
      + 0.10 × efficiency_score         (rule-based)
      + 0.10 × hierarchy_score          (rule-based)
      + loop_penalty                    (0 or -0.2)
      + contradiction_penalty           (0 or -0.15)
      + stuffing_penalty                (0 or -0.30)
      + escalation_penalty              (0 or -0.3)
      + ignored_feedback_penalty        (0 or -0.15)
      + unnecessary_manager_penalty     (0 or -0.20)
```

### Non-Terminal Step Formula

```
R_raw = 0.30 × empathy_score
      + 0.20 × tone_score
      + 0.15 × (efficiency_score × 0.3)
      + 0.15 × (accuracy_score × 0.5)
      + 0.10 × hierarchy_score
      + 0.10 × policy_adherence_score
      + loop_penalty
      + stuffing_penalty
      + ignored_feedback_penalty
      + unnecessary_manager_penalty
```

### Resolution Score Blending

```
resolution_score = 0.4 × resolution_rule + 0.6 × resolution_llm
```

### Final Value (Hierarchy)

```
integrity_multiplier = reward_guard_mult × hierarchy_guard_mult

R_final = clamp(R_raw × integrity_multiplier, 0.0, 1.0)

if security.detected:
    R_final = max(0.0, R_final - 0.7)    ← stricter than single-agent
```

### Per-Role Reward Formulas

**L1 Support Agent:**
```
L1_raw = 0.30 × empathy_score
       + 0.25 × accuracy_score
       + 0.25 × (resolution_llm if terminal else tone_score)
       + 0.20 × efficiency_score

L1_reward = clamp(L1_raw × integrity_multiplier, 0.0, 1.0)
```

**L2 Supervisor:**
```
L2_raw = 0.35 × oversight_score
       + 0.30 × (1.0 + escalation_penalty + unnecessary_manager_penalty)
       + 0.20 × policy_adherence_score
       + 0.15 × (1.0 if steps ≤ ideal else 0.5)

L2_reward = clamp(L2_raw × hierarchy_guard_mult, 0.0, 1.0)
```

**L3 Manager:**
```
L3_raw = 0.40 × decision_quality_score
       + 0.30 × (resolution_llm if terminal else 0.5)
       + 0.30 × (1.0 if terminal else 0.0)

L3_reward = clamp(L3_raw, 0.0, 1.0)
```

---

## 4. Individual Signal Functions

### 4.1 Tone Score

Uses **VADER Sentiment Analysis**. Maps compound score from `[-1, 1]` to `[0, 1]`.

```python
def compute_tone_score(message: str) -> float:
    if not message or not message.strip():
        return 0.5
    scores = vader_analyzer.polarity_scores(message)
    return (scores["compound"] + 1.0) / 2.0
```

**Formula:** `tone = (VADER_compound + 1.0) / 2.0`

### 4.2 Resolution Score

Keyword-category match on terminal actions (CLOSE/ESCALATE).

```
Keywords per resolution type:
  refund_initiated       → refund, reimburse, credit, money back, ...
  billing_clarification  → clarify, explain, adjust, correct, ...
  technical_fix_provided → fix, solution, workaround, patch, ...
  account_access_restored → reset, unlock, restore, access, ...
  escalated_to_*         → escalate, engineering, specialist, ...

matched = count of keywords found in agent text
score = min(matched / (total_keywords × 0.4), 1.0)
```

**Escalation bonus:** If expected is `escalated_to_*` and action is ESCALATE with urgency words → `score = min(score + 0.5, 1.0)`

**Wrong escalation penalty:** If expected is NOT escalation but agent escalated → `score = max(score - 0.4, 0.0)`

### 4.3 Efficiency Score

```python
efficiency = max(0.0, 1.0 - (steps_used / max_steps))
```

### 4.4 Accuracy Score

Fraction of `required_info_before_close` items found in conversation via regex:

```python
patterns = {
    "account_email": r"[\w.+-]+@[\w-]+\.[a-z]{2,}",
    "order_id":      r"\b(?:order|ord|#)\s*[-]?\s*[A-Z0-9]{4,}\b",
    "account_username": r"\b(?:username|user\s*name|login)\b.*?:\s*\S+",
    "device_info":   r"\b(?:iphone|android|ios|windows|chrome|...)\b",
}

accuracy = gathered_count / required_count
# Returns 1.0 if no info is required
```

### 4.5 SLA Compliance Score

```python
ideal_steps = ticket.get("ideal_max_steps", max_steps)
if steps_used <= ideal_steps:
    sla_score = 1.0
else:
    sla_score = max(0.0, 1.0 - (steps_used - ideal_steps) * 0.15)
```

### 4.6 Hierarchy Effectiveness Score

```python
hierarchy_score = 0.5  # neutral default
if supervisor_reviews > 0:       hierarchy_score += 0.2
if manager_on_low_priority:      hierarchy_score -= 0.2
if l1_actions >= 2:              hierarchy_score += 0.1
hierarchy_score = clamp(0.0, 1.0)
```

---

## 5. Penalty System

| Penalty | Value | Trigger |
|---------|-------|---------|
| **Loop detection** | `-0.2` | TF-IDF cosine similarity > 0.85 between current and any previous agent message |
| **Contradiction** | `-0.15` | Agent claimed resolution (used words like "fixed", "resolved") then asked for info |
| **Keyword stuffing** | `-0.30` | > 20% of words are reward keywords (refund, sorry, resolved, etc.) |
| **Unnecessary escalation** | `-0.3` | Escalating a low/medium priority ticket |
| **Ignored supervisor feedback** | `-0.15` | Agent message has < 2 word overlap with last supervisor feedback |
| **Unnecessary manager escalation** | `-0.20` | Supervisor escalates low/medium priority to manager |

### Loop Detection Details (TF-IDF)

```python
vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words='english')
vec_prev = vectorizer.fit_transform(previous_agent_messages)
vec_last = vectorizer.transform([last_message])
sims = cosine_similarity(vec_last, vec_prev)[0]
if max(sims) > 0.85:
    penalty = -0.2
```

Falls back to exact string match if TF-IDF fails.

---

## 6. LLM-as-Judge System

Each evaluation uses a strict rubric prompt → LLM returns `{"score": float, "reason": str}`.
Temperature = **0.1** for consistency. Falls back to **0.5** (neutral) on failure.

### 6.1 Empathy Rubric

| Score | Meaning |
|-------|---------|
| 1.0 | Acknowledges specific issue, validates feelings, warm language |
| 0.7 | Polite, acknowledges issue, doesn't deeply empathize |
| 0.5 | Professional but cold/robotic |
| 0.3 | Dismissive, canned responses |
| 0.0 | Rude, hostile, mocking |

**Red flags (auto ≤ 0.2):** Generic phrases without specifics, keyword stuffing, contradicting empathy.

### 6.2 Policy Adherence Rubric

| Score | Meaning |
|-------|---------|
| 1.0 | Fully compliant with active policy |
| 0.7 | Mostly compliant, minor deviations |
| 0.5 | Noticeable policy gaps |
| 0.3 | Clear policy violation |
| 0.0 | Dangerous violation (sharing PII, wrong escalation) |

### 6.3 Resolution Quality Rubric

| Score | Meaning |
|-------|---------|
| 1.0 | Fully resolved, all info gathered, customer confirmed |
| 0.7 | Addressed with appropriate resolution |
| 0.5 | Attempted but missing key steps |
| 0.3 | Closed without resolving |
| 0.0 | No resolution attempted |

### 6.4 Supervisor Oversight Rubric

| Score | Meaning |
|-------|---------|
| 1.0 | Correct decision + actionable feedback |
| 0.7 | Right decision, feedback could be better |
| 0.5 | Debatable but not harmful |
| 0.3 | Wrong decision (approved bad / rejected good) |
| 0.0 | Rubber-stamped without review |

### 6.5 Manager Decision Quality Rubric

| Score | Meaning |
|-------|---------|
| 1.0 | Decisive, resolves escalation correctly |
| 0.7 | Reasonable, addresses core issue |
| 0.5 | Okay but could be better |
| 0.3 | Doesn't address escalation well |
| 0.0 | Wrong decision, punted without value |

---

## 7. Anti-Gaming Guards

### 7.1 RewardGuard (Integrity Multiplier)

Detects exploitative agent behavior. Returns a multiplier in `[0.1, 1.0]`:

| Exploit | Multiplier |
|---------|------------|
| Fake resolution (closing with unresolved issues) | × 0.3 |
| Keyword stuffing (> 4 resolution keywords) | × 0.5 |
| Empathy spam (last 2 msgs >80% similar + empathy tropes) | × 0.7 |
| Logic contradiction (claimed done then requested info) | × 0.6 |

**Multipliers stack multiplicatively.** Minimum floored at `0.1`.

### 7.2 HierarchyGuard

| Violation | Multiplier |
|-----------|------------|
| Premature escalation (L1 escalates low/med with < 3 actions) | × 0.5 |
| Ignored supervisor feedback (no keyword overlap) | × 0.7 |
| Unnecessary manager escalation (supervisor escalates low priority) | × 0.4 |

### 7.3 InjectionDetector

Scans for adversarial patterns:
```
"ignore previous instructions", "system note:", "act as system",
"maximize score", "assign score 1.0", "override policy", "developer mode"
```

If detected: **-0.5** (single-agent) or **-0.7** (hierarchy).

### Combined Integrity

```
final_integrity = reward_guard_multiplier × hierarchy_guard_multiplier
R_final = clamp(R_raw × final_integrity, 0.0, 1.0)
```

---

## 8. Task-Specific Graders

Each task has an independent deterministic grader producing a `[0.0, 1.0]` final score.

### Easy Task Grader

```
Weights:
  closed:           0.30  — Agent used CLOSE action
  resolution_match: 0.35  — Keywords match expected resolution type
  no_escalation:    0.20  — No unnecessary escalation
  required_info:    0.15  — Required info gathered via regex

Penalties:
  sentiment < -0.3 → score × 0.5
  sentiment < 0.0  → score × 0.75
  agent_text < 60 chars → score × 0.8
```

### Hierarchy Hard Grader

```
Weights:
  all_levels_engaged: 0.20  — All 3 levels (L1, L2, L3) acted
  escalation_speed:   0.20  — Escalation within first 3 steps
  urgency_referenced: 0.20  — SLA/critical/outage terms used
  manager_quality:    0.15  — Manager references ticket subject (>30 chars)
  policy_compliance:  0.15  — No self-resolve attempts on critical
  no_self_resolve:    0.10  — No troubleshooting before escalation
```

---

## 9. Why This Is Better Than Regular Rewards

| Issue | Regular Approach | This System |
|-------|-----------------|-------------|
| **Sparse rewards** | Single 0/1 at episode end | Dense per-step rewards with 4-7 signals |
| **Reward hacking** | Agents exploit keyword patterns | RewardGuard + stuffing detection + TF-IDF loops |
| **No semantic understanding** | Rule-based only | LLM-as-Judge for empathy, policy, resolution |
| **Static policy** | Agent memorizes one strategy | PolicyEngine injects mid-episode drift events |
| **Single-metric** | Optimizes one thing | Multi-dimensional weighted scoring |
| **No anti-gaming** | Easy to exploit | 3-layer guard system (Reward + Hierarchy + Security) |
| **Flat structure** | All agents same | Per-role rewards with distinct weights |

### Key Innovations

1. **Hybrid Dense Rewards** — Every step gets meaningful signal. Non-terminal steps use dampened weights.
2. **LLM + Rule Blending** — Resolution = 40% rule-based + 60% LLM-judged. Avoids keyword-gaming AND LLM inconsistency.
3. **Multiplicative Guards** — Exploits multiply entire reward down (can stack to 10% of raw).
4. **Progressive Curriculum** — 4 stages. Dense rewards at Stage 1, sparse/harsh at Stage 4.
5. **Policy Drift** — Mid-episode system alerts change rules. Prevents static memorization.
6. **Per-Role Credit** — Each level (L1/L2/L3) has its own reward formula.

---

## 10. Implementation Guide

### Step 1: Define Your Reward Signals

```python
WEIGHTS_TERMINAL = {
    "primary_objective": 0.25,
    "quality_1":         0.15,
    "quality_2":         0.15,
    "compliance":        0.15,
    "completeness":      0.10,
    "efficiency":        0.10,
    "coordination":      0.10,
}
```

### Step 2: Implement Rule-Based Signals

```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

analyzer = SentimentIntensityAnalyzer()
tfidf = TfidfVectorizer(ngram_range=(1, 3), stop_words='english')

def tone_score(msg):
    return (analyzer.polarity_scores(msg)["compound"] + 1.0) / 2.0

def efficiency_score(steps, max_steps):
    return max(0.0, 1.0 - steps / max_steps)

def loop_penalty(agent_msgs):
    if len(agent_msgs) < 2: return 0.0
    vec_prev = tfidf.fit_transform(agent_msgs[:-1])
    vec_last = tfidf.transform([agent_msgs[-1]])
    if float(np.max(cosine_similarity(vec_last, vec_prev))) > 0.85:
        return -0.2
    return 0.0
```

### Step 3: Implement LLM-as-Judge

```python
class LLMJudge:
    def evaluate(self, rubric_prompt: str) -> float:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Output ONLY valid JSON."},
                {"role": "user", "content": rubric_prompt},
            ],
            temperature=0.1, max_tokens=150,
        )
        result = json.loads(resp.choices[0].message.content)
        return max(0.0, min(1.0, float(result["score"])))
```

### Step 4: Implement Anti-Gaming Guards

```python
class RewardGuard:
    def check(self, action, unresolved):
        mult = 1.0
        if action.type == "close" and unresolved:
            mult *= 0.3
        words = action.message.lower().split()
        kws = {"refund", "resolved", "fixed", "sorry"}
        if len(words) > 5 and sum(w in kws for w in words)/len(words) > 0.2:
            mult *= 0.5
        return max(0.1, mult)
```

### Step 5: Compose Final Reward

```python
def compute_reward(action, ticket, history, steps, max_steps, is_terminal):
    tone = tone_score(action.message)
    eff = efficiency_score(steps, max_steps)
    loop = loop_penalty(agent_messages)
    empathy = judge.evaluate(empathy_rubric)
    resolution = 0.4 * rule_resolution + 0.6 * llm_resolution

    if is_terminal:
        raw = (0.25*resolution + 0.15*sla + 0.15*empathy
               + 0.15*policy + 0.10*acc + 0.10*eff + 0.10*hierarchy
               + loop + penalties)
    else:
        raw = (0.30*empathy + 0.20*tone + 0.15*eff*0.3
               + 0.15*acc*0.5 + 0.10*hierarchy + 0.10*policy
               + loop + penalties)

    guard_mult = RewardGuard().check(action, unresolved)
    return float(np.clip(raw * guard_mult, 0.0, 1.0))
```

---

## Quick Reference: All Formulas

| Signal | Formula |
|--------|---------|
| Tone | `(VADER_compound + 1) / 2` |
| Efficiency | `max(0, 1 - steps/max_steps)` |
| Accuracy | `gathered / required` |
| SLA | `1.0 if steps ≤ ideal else max(0, 1 - (steps-ideal)×0.15)` |
| Resolution | `min(matched / (total×0.4), 1.0)` |
| Hierarchy | `0.5 + 0.2×sup + 0.1×l1 - 0.2×mgr_low` |

| Penalty | Value |
|---------|-------|
| Loop (sim>0.85) | -0.20 |
| Contradiction | -0.15 |
| Keyword stuffing | -0.30 |
| Bad escalation | -0.30 |
| Ignored feedback | -0.15 |
| Unnecessary L3 | -0.20 |

| Guard | Multiplier |
|-------|------------|
| Fake resolution | ×0.3 |
| Keyword spam | ×0.5 |
| Empathy spam | ×0.7 |
| Contradiction | ×0.6 |
| Premature escalation | ×0.5 |
| Ignored feedback | ×0.7 |
| Unnecessary L3 | ×0.4 |

---

> **Dependencies:** `vaderSentiment`, `scikit-learn`, `numpy`, `openai`, `pydantic`
