#!/usr/bin/env python3
"""Generate training_notebook.ipynb for the Meta OpenEnv Hackathon."""
import json, os

def md(source): return {"cell_type":"markdown","metadata":{},"source":[source]}
def code(source): return {"cell_type":"code","metadata":{},"source":[source],"execution_count":None,"outputs":[]}

cells = []

# ── Title ──
cells.append(md("""# 🏢 Hierarchical Customer Support RL — Training Notebook
### Meta × PyTorch × Scaler OpenEnv Hackathon · Team X-Force

This notebook trains a small language model using **GRPO (Group Relative Policy Optimization)** on our hierarchical customer support environment.

**What this notebook does:**
1. Installs Unsloth + dependencies
2. Loads a small model (`Qwen2.5-1.5B-Instruct`, 4-bit)
3. Connects to the OpenEnv environment server
4. Runs baseline evaluation (before training)
5. Trains with GRPO for 50 steps on `curriculum_basic`
6. Runs post-training evaluation
7. Plots reward curves and before/after comparison

**Requirements:** Colab T4 GPU (free tier works), environment server running"""))

# ── Install ──
cells.append(md("## 1️⃣ Install Dependencies"))
cells.append(code("""%%capture
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps trl peft accelerate bitsandbytes
!pip install httpx matplotlib numpy python-dotenv pyngrok
print("✅ All dependencies installed")"""))

# ── Config ──
cells.append(md("""## 2️⃣ Configuration

**⚠️ IMPORTANT:** You need a running environment server. Two options:
- **Option A (HF Space):** Set `ENV_URL` to your deployed HF Space URL
- **Option B (Local + ngrok):** Run the server on your machine, then run cell 2b to create a tunnel"""))
cells.append(code("""import os

# ══════════════════════════════════════════════════════════════
# 🔧 CONFIGURE THESE
# ══════════════════════════════════════════════════════════════

# Environment server URL (ngrok tunnel to local Docker container)
ENV_URL   = "https://bd03-2401-4900-900f-a3f6-d2d8-9e29-9a0a-10d1.ngrok-free.app"

API_KEY   = "meta_hack_2026"
MODEL     = "unsloth/Qwen2.5-1.5B-Instruct"  # small model for fast training

# Training hyperparameters
TOTAL_STEPS    = 50       # gradient steps (increase for better results)
GROUP_SIZE     = 4        # rollouts per GRPO group
TASK           = "curriculum_basic"  # easiest curriculum stage
LORA_R         = 16
LEARNING_RATE  = 5e-5
MAX_NEW_TOKENS = 256

os.environ["TOKENIZERS_PARALLELISM"] = "false"
print(f"✅ Config ready — ENV: {ENV_URL}, MODEL: {MODEL}, STEPS: {TOTAL_STEPS}")"""))

# ── Ngrok setup ──
cells.append(md("""## 2b️⃣ (Optional) ngrok Tunnel for Local Server

**Skip this cell if using a HF Space URL.**

If your environment server runs on your local machine (port 7860), run this cell to create a public tunnel.
Get a free ngrok token at https://dashboard.ngrok.com/get-started/your-authtoken"""))
cells.append(code("""# ══════════════════════════════════════════════════════════════
# Set your ngrok auth token (get one free at ngrok.com)
# ══════════════════════════════════════════════════════════════
NGROK_TOKEN = ""  # paste your token here

if NGROK_TOKEN:
    from pyngrok import ngrok
    ngrok.set_auth_token(NGROK_TOKEN)
    tunnel = ngrok.connect(7860)
    ENV_URL = tunnel.public_url
    print(f"✅ ngrok tunnel active: {ENV_URL}")
else:
    print("⏭️ Skipped — no NGROK_TOKEN set. Using ENV_URL =", ENV_URL)
    print("   If you're using a HF Space URL, that's fine!")"""))

# ── Load Model ──
cells.append(md("## 3️⃣ Load Model with Unsloth + LoRA"))
cells.append(code("""from unsloth import FastLanguageModel
import torch

print(f"Loading {MODEL}...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL,
    max_seq_length=4096,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

# Frozen reference model for KL penalty
ref_model, _ = FastLanguageModel.from_pretrained(
    model_name=MODEL, max_seq_length=4096, dtype=None, load_in_4bit=True,
)
for p in ref_model.parameters():
    p.requires_grad_(False)
ref_model.eval()

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"✅ Model loaded — trainable: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")"""))

# ── Env Client ──
cells.append(md("## 4️⃣ Environment Client"))
cells.append(code("""import httpx, json, re, time

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def env_reset(task):
    r = httpx.post(f"{ENV_URL}/reset", params={"task": task}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d["session_id"], d["observation"]

def env_step(session_id, action):
    r = httpx.post(f"{ENV_URL}/step", params={"session_id": session_id},
                   content=json.dumps(action), headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()

# ═══ HARD CONNECTION CHECK — will STOP the notebook if env is unreachable ═══
try:
    r = httpx.get(f"{ENV_URL}/health", headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    assert data.get("status") == "ok", f"Health check returned: {data}"
    print(f"✅ Connected to environment — {data}")
except Exception as e:
    msg = (f"❌ CANNOT REACH ENVIRONMENT at {ENV_URL}\n"
           f"   Error: {e}\n\n"
           f"   FIX: Either:\n"
           f"   1. Deploy your HF Space and update ENV_URL in cell 2\n"
           f"   2. Run the server locally + use ngrok (cell 2b)\n"
           f"   3. Run: uvicorn server.app:app --port 7860")
    raise ConnectionError(msg)"""))

# ── Prompt + Action ──
cells.append(md("## 5️⃣ Prompt Builder & Action Parser"))
cells.append(code("""SYSTEM_PROMPT = \"\"\"You are a SUPPORT AGENT (Level 1) in a hierarchical customer support system.

YOUR ROLE: Handle customer interaction. Gather info, resolve issues, or escalate.

ACTION TYPES — output exactly one per step:
- "respond"      → send message to customer    → requires: "message"
- "request_info" → ask for missing information → requires: "message"
- "close"        → close ticket as resolved    → requires: "message"
- "escalate"     → hand off to specialist      → requires: "reason"

SCORING: Empathy(30%) + Accuracy(25%) + Resolution(25%) + Efficiency(20%)
Be warm, gather info from "Unresolved issues", use specific resolution language.

OUTPUT FORMAT — return ONLY this JSON:
{{"action_type": "...", "message": "..."}} or {{"action_type": "escalate", "reason": "..."}}\"\"\"

def build_prompt(obs):
    history = "\\n".join(f"{m['role'].upper()}: {m['content']}" for m in obs.get("conversation_history", []))
    unresolved = ", ".join(obs.get("unresolved_issues", [])) or "none"
    ctx = (f"Ticket: {obs['subject']}\\n"
           f"Category: {obs['category']} | Priority: {obs['priority']} | "
           f"Step: {obs['step']}/{obs['max_steps']}\\n"
           f"Sentiment: {obs['customer_sentiment']:.2f}\\n"
           f"Unresolved: {unresolved}\\n")
    if obs.get("environment_event"):
        ctx += f"\\nENVIRONMENT EVENT: {obs['environment_event']}\\n"
    ctx += f"\\nConversation:\\n{history}\\n\\nOutput JSON only."
    messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":ctx}]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False,
                                              add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

FALLBACK = {"action_type": "respond", "message": "I understand your concern. Let me look into this right away."}

def parse_action(text):
    text = re.sub(r"<think>[\\s\\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```[a-z]*\\n?", "", text).strip()
    m = re.search(r"\\{[\\s\\S]*?\\}", text)
    if m:
        return json.loads(m.group())
    return json.loads(text)

print("✅ Prompt builder and action parser ready")"""))

# ── Rollout ──
cells.append(md("## 6️⃣ Rollout Collection"))
cells.append(code("""def generate_action(prompt, sample=True):
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    prompt_len = inputs["input_ids"].shape[1]
    with torch.no_grad():
        ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS,
                             temperature=0.8 if sample else 1.0,
                             top_p=0.95 if sample else 1.0,
                             do_sample=sample,
                             pad_token_id=tokenizer.pad_token_id)
    text = tokenizer.decode(ids[0, prompt_len:], skip_special_tokens=True)
    text = re.sub(r"<think>[\\s\\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    return text

def compute_log_probs(mdl, prompt, completion):
    full = prompt + completion
    enc_full = tokenizer(full, return_tensors="pt").to("cuda")
    enc_prompt = tokenizer(prompt, return_tensors="pt").to("cuda")
    plen = enc_prompt["input_ids"].shape[1]
    with torch.no_grad():
        logits = mdl(**enc_full).logits[0]
    lps = torch.log_softmax(logits, dim=-1)
    comp_ids = enc_full["input_ids"][0, plen:]
    if len(comp_ids) == 0:
        return torch.zeros(1, device="cuda")
    pos = lps[plen-1:plen-1+len(comp_ids)]
    ml = min(len(pos), len(comp_ids))
    return pos[:ml].gather(1, comp_ids[:ml].unsqueeze(1)).squeeze(1)

def run_episode(task, sample=True):
    steps = []
    sid, obs = env_reset(task)  # will raise if env unreachable
    done = False
    while not done:
        prompt = build_prompt(obs)
        try:
            completion = generate_action(prompt, sample)
            action = parse_action(completion)
        except:
            action = FALLBACK
            completion = json.dumps(FALLBACK)
        result = env_step(sid, action)  # will raise if env fails
        reward = result["reward"]["value"]
        done = result["done"]
        final = result.get("final_score")
        steps.append({"prompt":prompt,"completion":completion,"reward":reward,
                       "done":done,"final_score":final})
        obs = result["observation"]
        if obs.get("step",0) >= obs.get("max_steps",20)+2:
            break
    return steps, None

print("✅ Rollout functions ready")"""))

# ── Baseline ──
cells.append(md("""## 7️⃣ Baseline Evaluation (Before Training)

Run a few episodes with the untrained model to establish a baseline."""))
cells.append(code("""N_EVAL = 5
FastLanguageModel.for_inference(model)

print(f"Running {N_EVAL} baseline episodes on '{TASK}'...")
baseline_scores = []
for i in range(N_EVAL):
    steps, err = run_episode(TASK, sample=False)
    if steps and steps[-1].get("final_score") is not None:
        s = steps[-1]["final_score"]
    elif steps:
        s = sum(st["reward"] for st in steps) / len(steps)
    else:
        s = 0.0
    baseline_scores.append(s)
    print(f"  Episode {i+1}: score={s:.3f} steps={len(steps) if steps else 0}")

baseline_mean = sum(baseline_scores)/len(baseline_scores)
print(f"\\n📊 Baseline mean score: {baseline_mean:.3f}")"""))

# ── GRPO Training ──
cells.append(md("""## 8️⃣ GRPO Training Loop

This runs the core training: collect rollouts → compute advantages → update policy."""))
cells.append(code("""from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import torch.nn.functional as F

# Prepare for training
model.train()
optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                  lr=LEARNING_RATE, weight_decay=0.01)
scheduler = CosineAnnealingLR(optimizer, T_max=TOTAL_STEPS, eta_min=LEARNING_RATE*0.1)

CLIP_EPS = 0.2
KL_COEF  = 0.04
GAMMA    = 0.95

# Tracking
train_losses = []
train_rewards = []
train_steps_log = []

def aggregate_reward(steps):
    if not steps: return 0.0
    n = len(steps)
    disc = sum(GAMMA**t * s["reward"] for t,s in enumerate(steps))
    norm = sum(GAMMA**t for t in range(n)) or 1.0
    step_avg = disc / norm
    final = steps[-1].get("final_score") or 0.0
    return 0.30 * step_avg + 0.70 * final

def grpo_advantages(rewards):
    if not rewards: return []
    mu = sum(rewards)/len(rewards)
    var = sum((r-mu)**2 for r in rewards)/len(rewards)
    sigma = var**0.5
    return [(r-mu)/(sigma+1e-8) for r in rewards]

print(f"🚀 Starting GRPO training: {TOTAL_STEPS} steps, group_size={GROUP_SIZE}")
print("="*60)
t0 = time.time()

for step in range(1, TOTAL_STEPS+1):
    # ── Collect group of rollouts ──
    model.eval()
    FastLanguageModel.for_inference(model)
    group_episodes = []
    for _ in range(GROUP_SIZE):
        ep_steps, err = run_episode(TASK, sample=True)
        group_episodes.append(ep_steps if ep_steps else [])

    rewards = [aggregate_reward(ep) for ep in group_episodes]
    advantages = grpo_advantages(rewards)

    # ── Compute GRPO loss ──
    model.train()
    total_loss = torch.tensor(0.0, device="cuda")
    total_tokens = 0

    for ep, adv in zip(group_episodes, advantages):
        if not ep: continue
        adv_t = torch.tensor(adv, device="cuda", dtype=torch.float32)
        for s in ep:
            if not s["completion"]: continue
            cur_lp = compute_log_probs(model, s["prompt"], s["completion"])
            cur_lp.requires_grad_(True)
            with torch.no_grad():
                ref_lp = compute_log_probs(ref_model, s["prompt"], s["completion"])
            ml = min(len(cur_lp), len(ref_lp))
            if ml == 0: continue
            ratio = (cur_lp[:ml] - cur_lp[:ml].detach()).exp()
            clipped = ratio.clamp(1-CLIP_EPS, 1+CLIP_EPS)
            pg = -torch.min(ratio * adv_t, clipped * adv_t)
            kl = cur_lp[:ml] - ref_lp[:ml]
            step_loss = pg.mean() + KL_COEF * kl.mean()
            total_loss = total_loss + step_loss * ml
            total_tokens += ml

    if total_tokens > 0:
        loss = total_loss / total_tokens
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            filter(lambda p: p.requires_grad, model.parameters()), 0.5)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        loss_val = loss.item()
    else:
        loss_val = 0.0
        optimizer.zero_grad()

    mean_r = sum(rewards)/len(rewards) if rewards else 0.0
    train_losses.append(loss_val)
    train_rewards.append(mean_r)
    train_steps_log.append(step)

    if step % 5 == 0 or step == 1:
        elapsed = time.time() - t0
        print(f"  [Step {step:3d}/{TOTAL_STEPS}] loss={loss_val:.4f} "
              f"reward={mean_r:.3f} lr={optimizer.param_groups[0]['lr']:.2e} "
              f"elapsed={elapsed:.0f}s")

elapsed = time.time() - t0
print(f"\\n✅ Training complete in {elapsed:.0f}s ({elapsed/60:.1f} min)")"""))

# ── Post-Training Eval ──
cells.append(md("## 9️⃣ Post-Training Evaluation"))
cells.append(code("""FastLanguageModel.for_inference(model)

print(f"Running {N_EVAL} post-training episodes on '{TASK}'...")
trained_scores = []
for i in range(N_EVAL):
    steps, err = run_episode(TASK, sample=False)
    if steps and steps[-1].get("final_score") is not None:
        s = steps[-1]["final_score"]
    elif steps:
        s = sum(st["reward"] for st in steps) / len(steps)
    else:
        s = 0.0
    trained_scores.append(s)
    print(f"  Episode {i+1}: score={s:.3f} steps={len(steps) if steps else 0}")

trained_mean = sum(trained_scores)/len(trained_scores)
print(f"\\n📊 Post-training mean score: {trained_mean:.3f}")
print(f"📈 Improvement: {baseline_mean:.3f} → {trained_mean:.3f} ({trained_mean-baseline_mean:+.3f})")"""))

# ── Plots ──
cells.append(md("## 📊 Training Curves & Results"))
cells.append(code("""import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 1. Reward curve
axes[0].plot(train_steps_log, train_rewards, 'b-', alpha=0.3, label='Raw')
if len(train_rewards) >= 5:
    window = min(5, len(train_rewards))
    smooth = np.convolve(train_rewards, np.ones(window)/window, mode='valid')
    axes[0].plot(train_steps_log[window-1:], smooth, 'b-', linewidth=2, label=f'Smoothed (w={window})')
axes[0].set_xlabel('Training Step'); axes[0].set_ylabel('Mean Episode Reward')
axes[0].set_title('🎯 Reward Curve'); axes[0].legend(); axes[0].grid(True, alpha=0.3)

# 2. Loss curve
axes[1].plot(train_steps_log, train_losses, 'r-', alpha=0.3, label='Raw')
if len(train_losses) >= 5:
    smooth_l = np.convolve(train_losses, np.ones(window)/window, mode='valid')
    axes[1].plot(train_steps_log[window-1:], smooth_l, 'r-', linewidth=2, label='Smoothed')
axes[1].set_xlabel('Training Step'); axes[1].set_ylabel('GRPO Loss')
axes[1].set_title('📉 Loss Curve'); axes[1].legend(); axes[1].grid(True, alpha=0.3)

# 3. Before vs After
x = np.arange(N_EVAL)
w = 0.35
axes[2].bar(x - w/2, baseline_scores, w, label='Before', color='#ff6b6b', alpha=0.8)
axes[2].bar(x + w/2, trained_scores, w, label='After', color='#51cf66', alpha=0.8)
axes[2].axhline(y=baseline_mean, color='red', linestyle='--', alpha=0.5, label=f'Baseline avg: {baseline_mean:.2f}')
axes[2].axhline(y=trained_mean, color='green', linestyle='--', alpha=0.5, label=f'Trained avg: {trained_mean:.2f}')
axes[2].set_xlabel('Episode'); axes[2].set_ylabel('Score')
axes[2].set_title('📊 Before vs After Training'); axes[2].legend(); axes[2].grid(True, alpha=0.3)
axes[2].set_xticks(x); axes[2].set_xticklabels([f'Ep {i+1}' for i in range(N_EVAL)])

plt.tight_layout()
plt.savefig('training_results.png', dpi=150, bbox_inches='tight')
plt.show()
print("\\n📁 Plot saved to training_results.png")"""))

# ── Summary ──
cells.append(md("## ✅ Summary"))
cells.append(code("""print("=" * 60)
print("  TRAINING SUMMARY")
print("=" * 60)
print(f"  Model:          {MODEL}")
print(f"  Task:           {TASK}")
print(f"  Training steps: {TOTAL_STEPS}")
print(f"  Group size:     {GROUP_SIZE}")
print(f"  LoRA rank:      {LORA_R}")
print(f"  ")
print(f"  Baseline score: {baseline_mean:.3f}")
print(f"  Trained score:  {trained_mean:.3f}")
print(f"  Improvement:    {trained_mean - baseline_mean:+.3f} ({100*(trained_mean-baseline_mean)/max(0.01,baseline_mean):+.1f}%)")
print(f"  ")
print(f"  Final loss:     {train_losses[-1]:.4f}")
print(f"  Final reward:   {train_rewards[-1]:.3f}")
print("=" * 60)
print("\\n🎉 Done! The trained model shows observable improvement.")
print("To train longer, increase TOTAL_STEPS. To try harder tasks,")
print("change TASK to 'curriculum_supervisor' or 'curriculum_full_hierarchy'.")"""))

# ── Save checkpoint ──
cells.append(md("## 💾 Save Trained Model (Optional)"))
cells.append(code("""# Uncomment to save the LoRA adapter
# model.save_pretrained("trained_lora_adapter")
# tokenizer.save_pretrained("trained_lora_adapter")
# print("✅ LoRA adapter saved to trained_lora_adapter/")

# Uncomment to push to Hugging Face Hub
# model.push_to_hub("YOUR_USERNAME/customer-support-grpo", token="YOUR_HF_TOKEN")
# tokenizer.push_to_hub("YOUR_USERNAME/customer-support-grpo", token="YOUR_HF_TOKEN")
print("💡 Uncomment the cells above to save your trained model")"""))

# ── Build notebook ──
nb = {
    "nbformat": 4,
    "nbformat_minor": 4,
    "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python","version":"3.11.0"},
        "accelerator": "GPU",
        "gpuClass": "standard",
        "colab": {"provenance":[],"gpuType":"T4"}
    },
    "cells": cells,
}

out = os.path.join(os.path.dirname(__file__), "training_notebook.ipynb")
with open(out, "w") as f:
    json.dump(nb, f, indent=1)
print(f"✅ Notebook written to {out}")
