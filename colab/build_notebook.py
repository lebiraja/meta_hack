#!/usr/bin/env python3
"""Build training_notebook.ipynb — v5 with full visualisations."""
import json, uuid, textwrap

def uid(): return str(uuid.uuid4())[:8]
def md(src):   return {"cell_type":"markdown","id":uid(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","execution_count":None,"id":uid(),"metadata":{},"outputs":[],"source":src}

NB_ROOT = "/home/lebi/projects/meta_hack/colab"
OUT     = f"{NB_ROOT}/training_notebook.ipynb"

cells = []

# ─────────────────────────────────────────────────────────────────────────────
# 0. Title
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(textwrap.dedent("""\
    # 🏢 Hierarchical Customer Support RL — GRPO Training (v5)
    **Meta × PyTorch × Scaler OpenEnv Hackathon**

    Trains `Qwen2.5-1.5B-Instruct` (fits Colab T4) with **GRPO** on `curriculum_basic`.
    Points at the live HF Space: `lebiraja/customer-support-env`.

    **v5 fixes:**
    - ✅ JSON preprocessor — literal `\\n` + Python `#` comments in model output
    - ✅ Truncated JSON repair — missing `}` auto-closed
    - ✅ FALLBACK-PENALIZED — garbled outputs → `INVALID_PENALTY`, not env reward
    - ✅ All 6 action types incl. `query_user_profile` / `query_order_details`
    - ✅ Role-aware prompts — support_agent / supervisor / manager
    - ✅ Early stopping on collapse
    - ✅ `kl_coef=0.1` (stable; 0.04 caused collapse in v1)
    - ✅ **Rich visualisation** — 6-panel dashboard (reward, loss, LR, invalid rate, eval, before/after)
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 1. Install
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 1️⃣  Install Dependencies"))
cells.append(code(textwrap.dedent("""\
    %%capture
    !pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    !pip install --no-deps trl peft accelerate bitsandbytes
    !pip install httpx matplotlib numpy
    print("✅ Done")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(textwrap.dedent("""\
    ## 2️⃣  Authentication

    The Space is currently **private**. Paste a HF read token below.
    Once it's made public, leave `HF_TOKEN = ""`.
""")))
cells.append(code(textwrap.dedent("""\
    # ── 🔑 HF Space Authentication ────────────────────────────────────────────
    # Get a token at https://huggingface.co/settings/tokens (read access is enough)
    # Leave empty once the Space is public.

    HF_TOKEN = ""   # ← paste your token here, e.g. "hf_xxxx..."

    _auth_header = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN.strip() else {}
    print("🔑 Auth header set" if HF_TOKEN.strip() else "⚠️  No token — only works if Space is public")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 3. Config
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 3️⃣  Configuration"))
cells.append(code(textwrap.dedent("""\
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # ── Environment ───────────────────────────────────────────────────────────
    ENV_URL = "https://lebiraja-customer-support-env.hf.space"
    API_KEY = "meta_hack_2026"

    # ── Model ─────────────────────────────────────────────────────────────────
    MODEL = "unsloth/Qwen2.5-1.5B-Instruct"   # ~1 GB 4-bit, fits Colab T4

    # ── Task ──────────────────────────────────────────────────────────────────
    TASK = "curriculum_basic"   # L1-only, easiest — advance once score ≥ 0.65

    # ── Hyperparameters ───────────────────────────────────────────────────────
    TOTAL_STEPS     = 40      # increase to 100+ for real improvement
    GROUP_SIZE      = 4       # rollouts per GRPO group
    LORA_R          = 16
    LEARNING_RATE   = 5e-5
    MAX_NEW_TOKENS  = 128     # v5: sweet spot (avoid truncation without waste)
    KL_COEF         = 0.1    # v5: 0.04 caused collapse in v1, 0.1 is stable
    CLIP_EPS        = 0.2
    INVALID_PENALTY = -0.2   # reward for unparseable / wrong-role outputs
    N_EVAL          = 5       # episodes per eval run

    HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json", **_auth_header}

    print(f"{'─'*55}")
    print(f"  ENV    : {ENV_URL}")
    print(f"  MODEL  : {MODEL}  |  TASK: {TASK}")
    print(f"  STEPS  : {TOTAL_STEPS}  GROUP: {GROUP_SIZE}  LR: {LEARNING_RATE}")
    print(f"  kl_coef: {KL_COEF}  max_tokens: {MAX_NEW_TOKENS}  penalty: {INVALID_PENALTY}")
    print(f"{'─'*55}")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 4. Health check
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 4️⃣  Verify Environment Connection"))
cells.append(code(textwrap.dedent("""\
    import httpx, json, re, time

    try:
        r = httpx.get(f"{ENV_URL}/health", headers=HEADERS, timeout=15)
        r.raise_for_status()
        h = r.json()
        print("✅ Environment reachable!")
        print(f"   status        : {h.get('status')}")
        print(f"   env_functional: {h.get('env_functional')}")
        print(f"   sessions      : {h.get('active_sessions')}/{h.get('session_cap')}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ConnectionError("❌ 401 — set HF_TOKEN in cell 2 (Space is private)")
        raise
    except Exception as e:
        raise ConnectionError(
            f"\\n❌ Cannot reach {ENV_URL}\\n   Error: {e}\\n\\n"
            f"   Fixes:\\n"
            f"   • Private Space → set HF_TOKEN in the Auth cell\\n"
            f"   • Space sleeping → visit the URL in browser to wake it"
        )
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Load model
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 5️⃣  Load Model + LoRA"))
cells.append(code(textwrap.dedent("""\
    from unsloth import FastLanguageModel
    import torch

    MAX_SEQ_LEN = 2048
    print(f"Loading {MODEL} (4-bit)...")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL, max_seq_length=MAX_SEQ_LEN, dtype=None, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
        lora_alpha=32, lora_dropout=0.05, bias="none",
        use_gradient_checkpointing="unsloth", random_state=42,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token    = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Frozen reference model for KL penalty
    ref_model, _ = FastLanguageModel.from_pretrained(
        model_name=MODEL, max_seq_length=MAX_SEQ_LEN, dtype=None, load_in_4bit=True,
    )
    for p in ref_model.parameters(): p.requires_grad_(False)
    ref_model.eval()

    # Clear max_length from generation config to silence the warning
    if hasattr(model, "generation_config"):
        model.generation_config.max_length = None

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"✅ Model ready — trainable: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 6. Helpers (prompts, parser, env client)
#    Use triple-single-quotes for outer string to avoid conflict with """
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(textwrap.dedent("""\
    ## 6️⃣  Prompts, Action Parser & Env Client (v5)

    Full v5 parser: JSON preprocessor + truncated-JSON repair + `<think>` stripping.
    All 6 action types. Role-aware prompts (support_agent / supervisor / manager).
""")))

HELPERS_SRC = '''\
# ── System Prompts ────────────────────────────────────────────────────────────

SUPPORT_AGENT_PROMPT = """You are a SUPPORT AGENT (Level 1) in a hierarchical customer support system.

YOUR ROLE: Handle initial customer interaction. Gather info, resolve issues, or escalate when needed.
ABOVE YOU: A Supervisor reviews every action you take. They may reject or give feedback.

{supervisor_feedback_section}{manager_directive_section}{policy_section}

ACTION TYPES — output exactly one per step:
- "respond"               -> send a message to the customer          -> requires: "message"
- "request_info"          -> ask for missing information             -> requires: "message"
- "close"                 -> close the ticket as resolved            -> requires: "message"
- "escalate"              -> hand off to specialist                  -> requires: "reason"
- "query_user_profile"    -> look up customer account (internal)    -> requires: "email"
- "query_order_details"   -> look up order details (internal)       -> requires: "order_id"

SCORING: Empathy(30%) + Accuracy(25%) + Resolution(25%) + Efficiency(20%)

OUTPUT FORMAT — return ONLY valid JSON:
{{"action_type": "respond", "message": "..."}}
{{"action_type": "escalate", "reason": "..."}}
{{"action_type": "query_user_profile", "email": "customer@example.com"}}
{{"action_type": "query_order_details", "order_id": "ORD-12345"}}
WARNING: Use "email" for query_user_profile, "order_id" for query_order_details. NEVER "message"."""

SUPERVISOR_PROMPT = """You are a SUPERVISOR (Level 2) reviewing the Support Agent's last action.

ACTION: Type={pending_action_type}  Content={pending_action_content}
POLICY: {policy}

OUTPUT one of:
{{"action_type": "supervisor_approve", "message": "Approved."}}
{{"action_type": "supervisor_feedback", "feedback_to_agent": "..."}}
{{"action_type": "supervisor_reject",   "feedback_to_agent": "..."}}
{{"action_type": "supervisor_escalate", "reason": "..."}}"""

MANAGER_PROMPT = """You are a MANAGER (Level 3). Handle escalated cases.
REASON: {escalation_reason}  POLICY: {policy}

OUTPUT one of:
{{"action_type": "manager_resolve",   "message": "..."}}
{{"action_type": "manager_override",  "message": "..."}}
{{"action_type": "manager_send_back", "feedback_to_agent": "..."}}"""


# ── Action parser (v5) ────────────────────────────────────────────────────────
_ROLE_ACTIONS = {
    "support_agent": {"respond","escalate","close","request_info","query_user_profile","query_order_details"},
    "supervisor":    {"supervisor_approve","supervisor_reject","supervisor_feedback","supervisor_escalate"},
    "manager":       {"manager_override","manager_resolve","manager_send_back"},
}
_REQUIRED_FIELDS = {
    "respond":"message","request_info":"message","close":"message","escalate":"reason",
    "query_user_profile":"email","query_order_details":"order_id",
    "supervisor_approve":"message","supervisor_reject":"feedback_to_agent",
    "supervisor_feedback":"feedback_to_agent","supervisor_escalate":"reason",
    "manager_override":"message","manager_resolve":"message","manager_send_back":"feedback_to_agent",
}
_FALLBACK_ACTIONS = {
    "support_agent": {"action_type":"respond","message":"I apologize for the inconvenience. Let me look into this right away."},
    "supervisor":    {"action_type":"supervisor_approve","message":"Approved."},
    "manager":       {"action_type":"manager_resolve","message":"I am resolving this escalation directly."},
}

def _preprocess_json(s):
    result, in_string, i = [], False, 0
    while i < len(s):
        ch = s[i]
        if ch == "\\\\" and in_string:
            result.append(ch); i += 1
            if i < len(s): result.append(s[i]); i += 1
            continue
        if ch == '"':
            in_string = not in_string; result.append(ch)
        elif in_string:
            if   ch == "\\n": result.append("\\\\n")
            elif ch == "\\r": result.append("\\\\r")
            elif ch == "\\t": result.append("\\\\t")
            elif ord(ch) < 0x20: result.append(f"\\\\u{ord(ch):04x}")
            else: result.append(ch)
        elif ch == "#":
            while i < len(s) and s[i] != "\\n": i += 1
            continue
        else:
            result.append(ch)
        i += 1
    return "".join(result)

def _repair_truncated_json(text):
    start = text.find("{")
    if start == -1: return None
    fragment = text[start:].rstrip()
    if fragment.endswith("}"): return fragment
    in_string, i = False, 0
    while i < len(fragment):
        ch = fragment[i]
        if ch == "\\\\" and in_string: i += 2; continue
        if ch == '"': in_string = not in_string
        i += 1
    if in_string: fragment += '"'
    fragment += "}"
    try: json.loads(fragment); return fragment
    except json.JSONDecodeError: return None

def parse_action(text, active_role="support_agent"):
    fb = dict(_FALLBACK_ACTIONS.get(active_role, _FALLBACK_ACTIONS["support_agent"]))
    if not text or not text.strip(): return fb, True
    cleaned = re.sub(r"<think>[\\s\\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    if cleaned.startswith("```"):
        cleaned = "\\n".join(l for l in cleaned.split("\\n") if not l.startswith("```")).strip()
    match = re.search(r"\\{[\\s\\S]*\\}", cleaned)
    raw = match.group(0) if match else None
    if raw is None and "{" in cleaned: raw = _repair_truncated_json(cleaned)
    if raw is None: return fb, True
    try: action = json.loads(_preprocess_json(raw))
    except json.JSONDecodeError: return fb, True
    if not isinstance(action, dict): return fb, True
    at = action.get("action_type","")
    _NORMALIZE = {
        "response":"respond","request_information":"request_info",
        "request":"request_info","query_user":"query_user_profile",
        "query_order":"query_order_details","close_ticket":"close",
    }
    at = _NORMALIZE.get(at, at)
    action["action_type"] = at
    if not at or at not in _ROLE_ACTIONS.get(active_role, _ROLE_ACTIONS["support_agent"]): return fb, True
    req = _REQUIRED_FIELDS.get(at)
    if req and not (action.get(req) or "").strip(): return fb, True
    return action, False


# ── Prompt builder ────────────────────────────────────────────────────────────
def build_prompt(obs):
    role, policy = obs.get("active_role","support_agent"), obs.get("policy_context","Standard SOP.")
    hierarchy = obs.get("hierarchy_state") or {}
    if role == "supervisor":
        pending = hierarchy.get("pending_l1_action") or {}
        system = SUPERVISOR_PROMPT.format(
            pending_action_type=pending.get("action_type","unknown"),
            pending_action_content=pending.get("message") or pending.get("reason") or "N/A",
            policy=policy)
    elif role == "manager":
        system = MANAGER_PROMPT.format(escalation_reason=hierarchy.get("escalation_reason","N/A"), policy=policy)
    else:
        system = SUPPORT_AGENT_PROMPT.format(
            supervisor_feedback_section=(f"\\nSUPERVISOR FEEDBACK: {obs.get('supervisor_feedback')}\\n" if obs.get("supervisor_feedback") else ""),
            manager_directive_section=(f"\\nMANAGER DIRECTIVE: {obs.get('manager_directive')}\\n" if obs.get("manager_directive") else ""),
            policy_section=f"\\nPOLICY: {policy}")
    history = obs.get("conversation_history") or []
    if len(history) > 12: history = history[:2] + history[-10:]
    hist_txt = "\\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
    unresolved = ", ".join(obs.get("unresolved_issues",[]) or []) or "none"
    ctx = (f"Ticket: {obs['subject']}\\nCategory: {obs['category']} | Priority: {obs['priority']} | "
           f"Step: {obs['step']}/{obs['max_steps']}\\nSentiment: {obs['customer_sentiment']:.2f}\\n"
           f"Unresolved: {unresolved}\\n")
    if obs.get("environment_event"): ctx += f"\\nEVENT: {obs['environment_event']}\\n"
    retrieved = obs.get("retrieved_data") or {}
    users  = list((retrieved.get("users")  or {}).items())[:4]
    orders = list((retrieved.get("orders") or {}).items())[:4]
    if users or orders:
        ctx += "\\n## KNOWN DATA (cite verbatim)\\n"
        for e, r in users:  ctx += f"User({e}): {json.dumps(r)}\\n"
        for o, r in orders: ctx += f"Order({o}): {json.dumps(r)}\\n"
    ctx += f"\\nConversation:\\n{hist_txt}\\n\\nOutput JSON only."
    msgs = [{"role":"system","content":system},{"role":"user","content":ctx}]
    try:    return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError: return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


# ── Env client ────────────────────────────────────────────────────────────────
def env_reset(task):
    r = httpx.post(f"{ENV_URL}/reset", params={"task":task}, headers=HEADERS, timeout=30)
    r.raise_for_status(); d = r.json(); return d["session_id"], d["observation"]

def env_step(sid, action):
    r = httpx.post(f"{ENV_URL}/step", params={"session_id":sid},
                   content=json.dumps(action), headers=HEADERS, timeout=60)
    r.raise_for_status(); return r.json()

print("✅ v5 prompts, parser, and env client ready")
'''
cells.append(code(HELPERS_SRC))

# ─────────────────────────────────────────────────────────────────────────────
# 7. Rollout utilities
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 7️⃣  Rollout Utilities (v5: FALLBACK-PENALIZED)"))
cells.append(code(textwrap.dedent("""\
    def generate_text(prompt, do_sample=True):
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                           max_length=MAX_SEQ_LEN - MAX_NEW_TOKENS).to("cuda")
        plen = inputs["input_ids"].shape[1]
        with torch.no_grad():
            ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS,
                                 temperature=0.7 if do_sample else 1.0,
                                 top_p=0.9 if do_sample else 1.0,
                                 do_sample=do_sample,
                                 pad_token_id=tokenizer.pad_token_id,
                                 eos_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(ids[0, plen:], skip_special_tokens=True)

    def get_log_probs(mdl, prompt, completion):
        full = prompt + completion
        ef = tokenizer(full, return_tensors="pt", truncation=True, max_length=MAX_SEQ_LEN).to("cuda")
        ep = tokenizer(prompt,  return_tensors="pt", truncation=True, max_length=MAX_SEQ_LEN).to("cuda")
        plen = ep["input_ids"].shape[1]
        with torch.no_grad():
            logits = mdl(**ef).logits[0]
        lp      = torch.log_softmax(logits, dim=-1)
        comp_ids = ef["input_ids"][0, plen:]
        if len(comp_ids) == 0: return torch.zeros(1, device="cuda")
        pp = lp[plen-1 : plen-1+len(comp_ids)]
        ml = min(len(pp), len(comp_ids))
        return pp[:ml].gather(1, comp_ids[:ml].unsqueeze(1)).squeeze(1)

    def run_episode(task, do_sample=True):
        steps, (sid, obs) = [], env_reset(task)
        done, guard, step_idx = False, 0, 0
        while not done and guard < obs.get("max_steps",10)+3:
            guard += 1
            role       = obs.get("active_role","support_agent")
            prompt     = build_prompt(obs)
            completion = generate_text(prompt, do_sample)
            action, is_fallback = parse_action(completion, role)
            if is_fallback and step_idx == 0:
                print(f"  [INVALID] first step — {completion[:60]!r}")
                return None
            if is_fallback:
                print(f"  [FALLBACK] step {step_idx} role={role}")
            result = env_step(sid, action)
            reward = INVALID_PENALTY if is_fallback else result["reward"]["value"]
            done   = result["done"]
            steps.append({"prompt":prompt,"completion":completion,"reward":reward,
                          "done":done,"final_score":result.get("final_score"),"is_fallback":is_fallback})
            obs = result["observation"]; step_idx += 1
        return steps

    def episode_score(steps):
        if not steps: return INVALID_PENALTY
        n = len(steps)
        norm = sum(0.95**t for t in range(n)) or 1.0
        step_avg = sum(0.95**t * s["reward"] for t,s in enumerate(steps)) / norm
        final    = steps[-1].get("final_score") or 0.0
        return 0.50 * step_avg + 0.50 * final

    def grpo_advantages(rewards):
        if len(rewards)<2: return [0.0]*len(rewards)
        mu = sum(rewards)/len(rewards)
        sigma = (sum((r-mu)**2 for r in rewards)/len(rewards))**0.5
        return [(r-mu)/(sigma+1e-8) for r in rewards]

    print("✅ Rollout utilities ready (v5: FALLBACK-PENALIZED)")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 8. Baseline eval
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 8️⃣  Baseline Evaluation (Before Training)"))
cells.append(code(textwrap.dedent("""\
    FastLanguageModel.for_inference(model)
    print(f"Running {N_EVAL} baseline episodes on '{TASK}'...")

    baseline_scores = []
    for i in range(N_EVAL):
        steps = run_episode(TASK, do_sample=False)
        s = episode_score(steps)
        baseline_scores.append(s)
        fb = sum(1 for st in (steps or []) if st.get("is_fallback"))
        print(f"  Episode {i+1}: score={s:.3f}  steps={len(steps) if steps else 0}  fallbacks={fb}")

    baseline_mean = sum(baseline_scores) / len(baseline_scores)
    print(f"\\n📊 Baseline mean score: {baseline_mean:.3f}")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 9. Training loop — tracks lr, invalid_rate, eval_scores for full dashboard
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(textwrap.dedent("""\
    ## 9️⃣  GRPO Training Loop (v5)

    Tracks: reward · loss · learning rate · invalid rate · eval scores — all plotted later.
    Early stopping on 5 consecutive collapse steps (invalid_rate ≥ 90%).
""")))
cells.append(code(textwrap.dedent("""\
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import CosineAnnealingLR

    FastLanguageModel.for_training(model)
    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                      lr=LEARNING_RATE, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=TOTAL_STEPS, eta_min=LEARNING_RATE * 0.1)

    # ── Metric logs (used by the visualisation cell) ──────────────────────────
    log_steps        = []   # gradient step numbers
    log_rewards      = []   # mean group reward
    log_losses       = []   # GRPO loss
    log_lr           = []   # learning rate
    log_invalid_rate = []   # fraction of invalid episodes
    eval_steps       = []   # steps where eval was run
    eval_scores      = []   # eval mean_final_score at each eval point

    best_score, consecutive_collapse = 0.0, 0

    print(f"🚀 GRPO training — {TOTAL_STEPS} steps  group={GROUP_SIZE}  kl_coef={KL_COEF}")
    print("=" * 60)
    t0 = time.time()

    for step in range(1, TOTAL_STEPS + 1):

        # ── 1. Collect rollouts ──────────────────────────────────────────────
        FastLanguageModel.for_inference(model)
        group = [run_episode(TASK, do_sample=True) for _ in range(GROUP_SIZE)]

        rewards      = [episode_score(ep) for ep in group]
        invalid_rate = sum(1 for ep in group if ep is None) / len(group)
        advantages   = grpo_advantages(rewards)

        # ── 2. GRPO loss ─────────────────────────────────────────────────────
        FastLanguageModel.for_training(model)
        total_loss, total_tokens = torch.tensor(0.0, requires_grad=True, device="cuda"), 0

        for ep_steps, adv in zip(group, advantages):
            if not ep_steps: continue
            adv_t = torch.tensor(float(adv), device="cuda")
            for s in ep_steps:
                if not s["completion"].strip(): continue
                cur_lp = get_log_probs(model, s["prompt"], s["completion"])
                with torch.no_grad():
                    ref_lp = get_log_probs(ref_model, s["prompt"], s["completion"])
                ml = min(len(cur_lp), len(ref_lp))
                if ml == 0: continue
                ratio   = (cur_lp[:ml] - ref_lp[:ml]).exp()
                clipped = ratio.clamp(1 - CLIP_EPS, 1 + CLIP_EPS)
                pg_loss = -torch.min(ratio * adv_t, clipped * adv_t).mean()
                kl_loss = (cur_lp[:ml] - ref_lp[:ml]).mean()
                total_loss   = total_loss + (pg_loss + KL_COEF * kl_loss) * ml
                total_tokens += ml

        # ── 3. Gradient update ───────────────────────────────────────────────
        if total_tokens > 0:
            loss = total_loss / total_tokens
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                filter(lambda p: p.requires_grad, model.parameters()), 0.5)
            optimizer.step(); scheduler.step(); optimizer.zero_grad()
            loss_val = loss.item()
        else:
            optimizer.zero_grad(); loss_val = 0.0

        mean_r  = sum(rewards) / len(rewards)
        curr_lr = optimizer.param_groups[0]["lr"]

        log_steps.append(step)
        log_rewards.append(mean_r)
        log_losses.append(loss_val)
        log_lr.append(curr_lr)
        log_invalid_rate.append(invalid_rate)

        # ── 4. Logging ───────────────────────────────────────────────────────
        if step % 5 == 0 or step == 1:
            elapsed = time.time() - t0
            print(f"  [Step {step:3d}/{TOTAL_STEPS}]  loss={loss_val:.4f}  reward={mean_r:.3f}"
                  f"  invalid={invalid_rate:.0%}  lr={curr_lr:.2e}  elapsed={elapsed:.0f}s")

        # ── 5. Early stopping ────────────────────────────────────────────────
        if invalid_rate >= 0.9:
            consecutive_collapse += 1
            print(f"  ⚠️  Collapse {consecutive_collapse}/5  invalid={invalid_rate:.0%}")
            if consecutive_collapse >= 5:
                print(f"\\n🛑 [EARLY STOP] at step {step}"); break
        else:
            consecutive_collapse = 0

        # ── 6. Quick eval every 10 steps ─────────────────────────────────────
        if step % 10 == 0:
            FastLanguageModel.for_inference(model)
            sc = [episode_score(run_episode(TASK, do_sample=False)) for _ in range(3)]
            FastLanguageModel.for_training(model)
            me = sum(sc) / len(sc)
            mark = " ✨ NEW BEST" if me > best_score else ""
            if me > best_score: best_score = me
            eval_steps.append(step); eval_scores.append(me)
            print(f"  [Eval@{step}]  mean={me:.3f}  best={best_score:.3f}{mark}")

    print(f"\\n✅ Done in {time.time()-t0:.0f}s  |  best_score={best_score:.3f}")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 10. Post-training eval
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 🔟  Post-Training Evaluation"))
cells.append(code(textwrap.dedent("""\
    FastLanguageModel.for_inference(model)
    print(f"Running {N_EVAL} post-training episodes on '{TASK}'...")

    trained_scores = []
    for i in range(N_EVAL):
        steps = run_episode(TASK, do_sample=False)
        s = episode_score(steps)
        trained_scores.append(s)
        fb = sum(1 for st in (steps or []) if st.get("is_fallback"))
        print(f"  Episode {i+1}: score={s:.3f}  steps={len(steps) if steps else 0}  fallbacks={fb}")

    trained_mean = sum(trained_scores) / len(trained_scores)
    print(f"\\n📊 Post-training : {trained_mean:.3f}")
    print(f"📊 Baseline      : {baseline_mean:.3f}")
    print(f"📈 Improvement   : {baseline_mean:.3f} → {trained_mean:.3f}  ({trained_mean - baseline_mean:+.3f})")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 11. 6-panel visualisation dashboard
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(textwrap.dedent("""\
    ## 📊  Training Dashboard (6 panels)

    | Panel | What it shows |
    |-------|--------------|
    | Reward | Mean group reward per step (raw + smoothed) |
    | Loss | GRPO loss per step |
    | Learning Rate | Cosine annealing schedule |
    | Invalid Rate | Fraction of invalid (unparseable) episodes |
    | Eval Scores | Model score at each eval checkpoint + best line |
    | Before / After | Episode-level score comparison |
""")))
cells.append(code(textwrap.dedent("""\
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import numpy as np

    def smooth(vals, w=5):
        if len(vals) < w: return vals, list(range(len(vals)))
        s = np.convolve(vals, np.ones(w)/w, mode="valid").tolist()
        return s, list(range(w-1, len(vals)))

    fig = plt.figure(figsize=(20, 10))
    fig.suptitle(f"GRPO Training Dashboard (v5) — {MODEL} on {TASK}",
                 fontsize=14, fontweight="bold", y=1.01)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2])

    # ── 1. Reward ─────────────────────────────────────────────────────────────
    ax1.plot(log_steps, log_rewards, color="steelblue", alpha=0.25, lw=1)
    rs, ri = smooth(log_rewards)
    ax1.plot([log_steps[i] for i in ri], rs, color="steelblue", lw=2, label="Smoothed")
    ax1.axhline(baseline_mean, color="tomato",  ls="--", alpha=0.7, label=f"Baseline {baseline_mean:.2f}")
    ax1.axhline(trained_mean,  color="seagreen",ls="--", alpha=0.7, label=f"Trained  {trained_mean:.2f}")
    ax1.set_title("🎯 Reward"); ax1.set_xlabel("Step"); ax1.set_ylabel("Mean Reward")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    # ── 2. Loss ───────────────────────────────────────────────────────────────
    ax2.plot(log_steps, log_losses, color="tomato", alpha=0.25, lw=1)
    ls_, li = smooth(log_losses)
    ax2.plot([log_steps[i] for i in li], ls_, color="tomato", lw=2)
    ax2.set_title("📉 GRPO Loss"); ax2.set_xlabel("Step"); ax2.set_ylabel("Loss")
    ax2.grid(alpha=0.3)

    # ── 3. Learning Rate ──────────────────────────────────────────────────────
    ax3.plot(log_steps, [lr * 1e5 for lr in log_lr], color="mediumpurple", lw=2)
    ax3.set_title("📐 Learning Rate"); ax3.set_xlabel("Step")
    ax3.set_ylabel("LR (×10⁻⁵)"); ax3.grid(alpha=0.3)
    ax3.annotate(f"Start: {log_lr[0]:.1e}", xy=(log_steps[0],  log_lr[0]*1e5),  fontsize=8, color="mediumpurple")
    ax3.annotate(f"End:   {log_lr[-1]:.1e}", xy=(log_steps[-1], log_lr[-1]*1e5), fontsize=8, color="mediumpurple",
                 ha="right")

    # ── 4. Invalid Rate ───────────────────────────────────────────────────────
    ax4.fill_between(log_steps, log_invalid_rate, alpha=0.25, color="darkorange")
    ax4.plot(log_steps, log_invalid_rate, color="darkorange", lw=1.5)
    ax4.axhline(0.9, color="red", ls="--", alpha=0.6, label="Collapse threshold (90%)")
    ax4.set_title("⚠️  Invalid Rate"); ax4.set_xlabel("Step")
    ax4.set_ylabel("Fraction invalid"); ax4.set_ylim(0, 1.05)
    ax4.legend(fontsize=8); ax4.grid(alpha=0.3)

    # ── 5. Eval Scores ────────────────────────────────────────────────────────
    if eval_steps:
        ax5.plot(eval_steps, eval_scores, "o-", color="gold", lw=2, ms=7, label="Eval score")
        ax5.axhline(max(eval_scores), color="gold", ls="--", alpha=0.5,
                    label=f"Best {max(eval_scores):.3f}")
        ax5.fill_between(eval_steps, eval_scores, alpha=0.15, color="gold")
    ax5.axhline(baseline_mean, color="tomato",  ls=":", alpha=0.6, label=f"Baseline {baseline_mean:.2f}")
    ax5.set_title("🏆 Eval Score History"); ax5.set_xlabel("Step"); ax5.set_ylabel("Score")
    ax5.legend(fontsize=8); ax5.grid(alpha=0.3)

    # ── 6. Before / After ─────────────────────────────────────────────────────
    x = np.arange(N_EVAL); w = 0.35
    ax6.bar(x - w/2, baseline_scores, w, label="Before", color="#ff6b6b", alpha=0.85)
    ax6.bar(x + w/2, trained_scores,  w, label="After",  color="#51cf66", alpha=0.85)
    ax6.axhline(baseline_mean, color="tomato",  ls="--", alpha=0.6, label=f"Baseline avg {baseline_mean:.2f}")
    ax6.axhline(trained_mean,  color="seagreen",ls="--", alpha=0.6, label=f"Trained avg  {trained_mean:.2f}")
    ax6.set_title("📊 Before vs After"); ax6.set_xlabel("Episode"); ax6.set_ylabel("Score")
    ax6.set_xticks(x); ax6.set_xticklabels([f"Ep {i+1}" for i in range(N_EVAL)])
    ax6.legend(fontsize=8); ax6.grid(alpha=0.3)

    plt.savefig("training_dashboard_v5.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("📁 Saved → training_dashboard_v5.png")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 12. Summary
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## ✅  Summary"))
cells.append(code(textwrap.dedent("""\
    print("=" * 60)
    print("  GRPO TRAINING SUMMARY (v5)")
    print("=" * 60)
    print(f"  Model           : {MODEL}")
    print(f"  Task            : {TASK}")
    print(f"  Steps run       : {len(log_steps)} / {TOTAL_STEPS}")
    print(f"  Group size      : {GROUP_SIZE}")
    print(f"  kl_coef         : {KL_COEF}  (v5 stable value)")
    print(f"  invalid_penalty : {INVALID_PENALTY}")
    print()
    print(f"  Baseline score  : {baseline_mean:.3f}")
    print(f"  Trained score   : {trained_mean:.3f}")
    print(f"  Best eval score : {best_score:.3f}")
    delta = trained_mean - baseline_mean
    print(f"  Improvement     : {delta:+.3f}  ({100*delta/max(0.01,abs(baseline_mean)):+.1f}%)")
    print(f"  Mean invalid    : {sum(log_invalid_rate)/max(1,len(log_invalid_rate)):.1%}")
    print()
    print(f"  Final LR        : {log_lr[-1]:.2e}")
    print(f"  Final loss      : {log_losses[-1]:.4f}")
    print(f"  Final reward    : {log_rewards[-1]:.3f}")
    print("=" * 60)
    print()
    print("💡 Next steps:")
    print("   • Increase TOTAL_STEPS to 200+ for meaningful learning")
    print("   • Advance TASK to 'curriculum_supervisor' once score >= 0.65")
    print("   • GROUP_SIZE=8 gives more stable advantage estimates")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# 13. Save / Push
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md("## 💾  Save / Push to HF Hub (Optional)"))
cells.append(code(textwrap.dedent("""\
    # ── Save LoRA adapter locally ──────────────────────────────────────────────
    # model.save_pretrained("trained_lora_adapter")
    # tokenizer.save_pretrained("trained_lora_adapter")
    # print("✅ Saved to trained_lora_adapter/")

    # ── Push to HF Hub (write token required) ─────────────────────────────────
    # HF_WRITE_TOKEN = "hf_xxxx..."   # ← write-access token, keep private
    # model.push_to_hub("lebiraja/customer-support-grpo-v5-colab", token=HF_WRITE_TOKEN)
    # tokenizer.push_to_hub("lebiraja/customer-support-grpo-v5-colab", token=HF_WRITE_TOKEN)

    print("💾 Uncomment lines above to save / push your trained adapter.")
""")))

# ─────────────────────────────────────────────────────────────────────────────
# Assemble and write
# ─────────────────────────────────────────────────────────────────────────────
nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"gpuType": "T4", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"✅ Notebook written → {OUT}")
print(f"   Cells: {len(cells)}")
print(f"   Plots: 6-panel dashboard (reward, loss, LR, invalid rate, eval scores, before/after)")
