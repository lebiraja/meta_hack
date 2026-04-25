"""
run_benchmark.py — Pre/Post training benchmark for the AgentOS agent.

Runs N episodes per task against the local env (:7860),
calls the local inference server (:8001) for agent actions,
collects per-step reward data, and saves:
  - benchmark_results/results_<label>.json  — raw data
  - benchmark_results/benchmark_<label>.png — full visualization dashboard

Usage:
    python run_benchmark.py                          # label = "pre_train", 5 episodes/task
    python run_benchmark.py --label post_train       # after training
    python run_benchmark.py --episodes 10 --tasks easy medium hard
    python run_benchmark.py --compare pre_train post_train  # overlay comparison plot
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

ENV_URL       = os.getenv("ENV_URL",       "http://localhost:7860")
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8001")
API_KEY       = os.getenv("ENV_API_KEY",   "meta_hack_2026")
HEADERS       = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

ALL_TASKS = [
    "curriculum_basic",
    "curriculum_supervisor",
    "curriculum_full_hierarchy",
    "easy",
    "medium",
    "hard",
    "nightmare",
    "multi_domain",
]

TASK_LABELS = {
    "curriculum_basic":           "Curriculum\nBasic",
    "curriculum_supervisor":      "Curriculum\nSupervisor",
    "curriculum_full_hierarchy":  "Curriculum\nFull Hier.",
    "easy":                       "Easy",
    "medium":                     "Medium",
    "hard":                       "Hard",
    "nightmare":                  "Nightmare",
    "multi_domain":               "Multi\nDomain",
}

RESULTS_DIR = Path("benchmark_results")
RESULTS_DIR.mkdir(exist_ok=True)


# ── Colors ────────────────────────────────────────────────────────────────────
DARK_BG    = "#0a0a0a"
CARD_BG    = "#141414"
BORDER     = "#262626"
INDIGO     = "#6366f1"
INDIGO_DIM = "#4338ca"
GREEN      = "#22c55e"
YELLOW     = "#eab308"
ORANGE     = "#f97316"
RED        = "#ef4444"
NEUTRAL    = "#737373"
TEXT_MAIN  = "#e5e5e5"
TEXT_DIM   = "#525252"

COMPONENT_COLORS = {
    "empathy_score":     "#818cf8",
    "resolution_score":  "#34d399",
    "accuracy_score":    "#fbbf24",
    "tone_score":        "#60a5fa",
    "efficiency_score":  "#f472b6",
}

COMPONENT_LABELS = {
    "empathy_score":     "Empathy",
    "resolution_score":  "Resolution",
    "accuracy_score":    "Accuracy",
    "tone_score":        "Tone",
    "efficiency_score":  "Efficiency",
}


# ── Reward color helper ───────────────────────────────────────────────────────

def reward_color(v: float) -> str:
    if v >= 0.70: return GREEN
    if v >= 0.50: return YELLOW
    if v >= 0.35: return ORANGE
    return RED


# ── Agent call via local inference server ─────────────────────────────────────

_VALID_ACTIONS = {
    "respond", "request_info", "close", "escalate",
    "query_user_profile", "query_order_details",
    "supervisor_approve", "supervisor_reject",
    "supervisor_feedback", "supervisor_escalate",
    "manager_override", "manager_resolve", "manager_send_back",
}

_ACTION_ALIASES = {
    "response": "respond", "reply": "respond", "answer": "respond",
    "close_ticket": "close", "resolve": "close",
    "request": "request_info", "info_request": "request_info",
    "escalate_to_supervisor": "escalate",
}


def agent_action(obs: dict) -> dict:
    """POST to serve_inference.py /agent-action and return parsed action dict."""
    payload = {"observation": obs, "virtualMessages": []}
    try:
        r = requests.post(f"{INFERENCE_URL}/agent-action", json=payload, timeout=60)
        r.raise_for_status()
        action = r.json().get("action", _fallback(obs))
    except Exception as e:
        print(f"    [inference error] {e}")
        return _fallback(obs)

    # Normalize action_type — untrained models sometimes use wrong names
    at = action.get("action_type", "")
    if at not in _VALID_ACTIONS:
        at = _ACTION_ALIASES.get(at, None)
        if at:
            action["action_type"] = at
        else:
            return _fallback(obs)
    return action


def _fallback(obs: dict) -> dict:
    role = obs.get("active_role", "support_agent")
    fallbacks = {
        "support_agent": {"action_type": "respond", "message": "I understand your concern. Let me resolve this for you right away."},
        "supervisor":    {"action_type": "supervisor_approve", "message": "Approved."},
        "manager":       {"action_type": "manager_resolve",    "message": "Escalating to senior team immediately."},
    }
    return fallbacks.get(role, fallbacks["support_agent"])


# ── Single episode runner ─────────────────────────────────────────────────────

def run_episode(task: str, episode_idx: int) -> dict:
    """Run one full episode and return collected metrics."""
    # Reset
    try:
        r = requests.post(f"{ENV_URL}/reset", params={"task": task}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"    [reset error] {e}")
        return None

    session_id = data["session_id"]
    obs        = data["observation"]
    max_steps  = obs.get("max_steps", 10)

    step_rewards     = []
    step_actions     = []
    step_components  = []   # list of reward breakdown dicts
    done             = False
    final_score      = None
    step             = 0

    while not done and step < max_steps:
        t0     = time.time()
        action = agent_action(obs)
        latency = time.time() - t0

        try:
            sr = requests.post(
                f"{ENV_URL}/step",
                params={"session_id": session_id},
                json=action,
                headers=HEADERS,
                timeout=30,
            )
            sr.raise_for_status()
            result = sr.json()
        except Exception as e:
            print(f"    [step error] step={step+1} {e}")
            break

        reward_obj = result.get("reward", {})
        reward_val = reward_obj.get("value", 0.0)
        done       = result.get("done", False)
        obs        = result.get("observation", obs)

        step_rewards.append(reward_val)
        step_actions.append(action.get("action_type", "unknown"))
        step_components.append({
            "empathy_score":    reward_obj.get("empathy_score",    0.5),
            "resolution_score": reward_obj.get("resolution_score", 0.0),
            "accuracy_score":   reward_obj.get("accuracy_score",   0.5),
            "tone_score":       reward_obj.get("tone_score",       0.5),
            "efficiency_score": reward_obj.get("efficiency_score", 0.5),
            "value":            reward_val,
        })

        if done:
            final_score = result.get("final_score", reward_val)

        step += 1
        status = f"{reward_val:.2f}"
        print(f"    step {step:2d}/{max_steps}  action={action.get('action_type','?'):<28}  reward={status}  {'DONE' if done else ''}")

    if final_score is None:
        final_score = step_rewards[-1] if step_rewards else 0.0

    return {
        "task":           task,
        "episode":        episode_idx,
        "final_score":    round(final_score, 4),
        "steps_used":     step,
        "max_steps":      max_steps,
        "step_rewards":   [round(r, 4) for r in step_rewards],
        "step_actions":   step_actions,
        "step_components": step_components,
        "mean_reward":    round(sum(step_rewards) / len(step_rewards), 4) if step_rewards else 0.0,
        "completed":      done,
    }


# ── Full benchmark run ────────────────────────────────────────────────────────

def run_benchmark(tasks: list[str], n_episodes: int, label: str) -> dict:
    print(f"\n{'═'*60}")
    print(f"  AgentOS Benchmark — {label}")
    print(f"  Tasks: {', '.join(tasks)}")
    print(f"  Episodes per task: {n_episodes}")
    print(f"  Env: {ENV_URL}  |  Inference: {INFERENCE_URL}")
    print(f"{'═'*60}\n")

    # Check inference server
    try:
        h = requests.get(f"{INFERENCE_URL}/health", timeout=5).json()
        model_name = h.get("model", "unknown")
        print(f"  Model: {model_name}")
        print(f"  Ready: {h.get('ready', False)}\n")
    except Exception as e:
        print(f"  [WARN] Inference server not reachable: {e}")
        model_name = "unknown"

    all_results = []
    task_summaries = {}

    for task in tasks:
        print(f"\n{'─'*50}")
        print(f"  Task: {task}")
        print(f"{'─'*50}")
        episodes = []

        for i in range(n_episodes):
            print(f"\n  Episode {i+1}/{n_episodes}")
            ep = run_episode(task, i + 1)
            if ep:
                episodes.append(ep)
                all_results.append(ep)
                print(f"  → final_score={ep['final_score']:.3f}  steps={ep['steps_used']}/{ep['max_steps']}")

        if episodes:
            scores = [e["final_score"] for e in episodes]
            task_summaries[task] = {
                "mean_final_score": round(sum(scores) / len(scores), 4),
                "min_score":        round(min(scores), 4),
                "max_score":        round(max(scores), 4),
                "n_episodes":       len(episodes),
                "completion_rate":  round(sum(1 for e in episodes if e["completed"]) / len(episodes), 3),
                "mean_steps":       round(sum(e["steps_used"] for e in episodes) / len(episodes), 1),
                "mean_empathy":     round(sum(c["empathy_score"]    for e in episodes for c in e["step_components"]) / max(sum(len(e["step_components"]) for e in episodes), 1), 4),
                "mean_resolution":  round(sum(c["resolution_score"] for e in episodes for c in e["step_components"]) / max(sum(len(e["step_components"]) for e in episodes), 1), 4),
                "mean_accuracy":    round(sum(c["accuracy_score"]   for e in episodes for c in e["step_components"]) / max(sum(len(e["step_components"]) for e in episodes), 1), 4),
                "mean_tone":        round(sum(c["tone_score"]       for e in episodes for c in e["step_components"]) / max(sum(len(e["step_components"]) for e in episodes), 1), 4),
                "mean_efficiency":  round(sum(c["efficiency_score"] for e in episodes for c in e["step_components"]) / max(sum(len(e["step_components"]) for e in episodes), 1), 4),
            }
            print(f"\n  Summary: mean={task_summaries[task]['mean_final_score']:.3f}  min={task_summaries[task]['min_score']:.3f}  max={task_summaries[task]['max_score']:.3f}")

    output = {
        "label":           label,
        "model":           model_name,
        "timestamp":       datetime.now().isoformat(),
        "n_episodes":      n_episodes,
        "tasks":           tasks,
        "task_summaries":  task_summaries,
        "episodes":        all_results,
    }

    out_path = RESULTS_DIR / f"results_{label}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {out_path}")

    return output


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot_benchmark(data: dict, label: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import numpy as np

    task_summaries = data["task_summaries"]
    episodes       = data["episodes"]
    tasks          = [t for t in data["tasks"] if t in task_summaries]

    if not tasks:
        print("  No data to plot.")
        return

    plt.rcParams.update({
        "figure.facecolor":  DARK_BG,
        "axes.facecolor":    CARD_BG,
        "axes.edgecolor":    BORDER,
        "axes.labelcolor":   TEXT_MAIN,
        "text.color":        TEXT_MAIN,
        "xtick.color":       TEXT_DIM,
        "ytick.color":       TEXT_DIM,
        "grid.color":        BORDER,
        "grid.linewidth":    0.5,
        "font.family":       "monospace",
        "font.size":         9,
    })

    fig = plt.figure(figsize=(20, 24), facecolor=DARK_BG)
    gs  = gridspec.GridSpec(
        4, 3,
        figure=fig,
        hspace=0.55,
        wspace=0.38,
        left=0.06, right=0.97,
        top=0.93,  bottom=0.05,
    )

    n_tasks = len(tasks)
    xlabels = [TASK_LABELS.get(t, t) for t in tasks]
    x       = np.arange(n_tasks)

    # ── Title ─────────────────────────────────────────────────────────────────
    fig.text(
        0.5, 0.965,
        f"AgentOS Benchmark — {label.replace('_', ' ').title()}",
        ha="center", fontsize=18, fontweight="bold", color=TEXT_MAIN,
    )
    fig.text(
        0.5, 0.948,
        f"Model: {data['model']}   ·   {data['n_episodes']} episodes/task   ·   {data['timestamp'][:16]}",
        ha="center", fontsize=9, color=TEXT_DIM,
    )

    # ── 1. Mean final score per task (bar) ────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    means  = [task_summaries[t]["mean_final_score"] for t in tasks]
    mins   = [task_summaries[t]["min_score"]        for t in tasks]
    maxs   = [task_summaries[t]["max_score"]        for t in tasks]
    colors = [reward_color(m) for m in means]
    bars   = ax1.bar(x, means, color=colors, width=0.6, alpha=0.9, zorder=3)
    ax1.errorbar(x, means,
                 yerr=[np.array(means) - np.array(mins),
                       np.array(maxs)  - np.array(means)],
                 fmt="none", color=TEXT_DIM, capsize=5, lw=1.5, zorder=4)
    for bar, val in zip(bars, means):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.015,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=9, color=TEXT_MAIN, fontweight="bold")
    ax1.axhline(0.5, color=YELLOW, lw=1, ls="--", alpha=0.6, zorder=2, label="0.50 threshold")
    ax1.axhline(0.7, color=GREEN,  lw=1, ls="--", alpha=0.6, zorder=2, label="0.70 target")
    ax1.set_xticks(x); ax1.set_xticklabels(xlabels, fontsize=8)
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("Mean Final Score")
    ax1.set_title("Mean Final Score per Task (with min/max range)", color=TEXT_MAIN, pad=8)
    ax1.legend(fontsize=8, labelcolor=TEXT_DIM, framealpha=0.3)
    ax1.grid(axis="y", zorder=1)
    ax1.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(0.05))

    # ── 2. Overall stats card ─────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis("off")
    overall_mean = sum(task_summaries[t]["mean_final_score"] for t in tasks) / n_tasks
    best_task    = max(tasks, key=lambda t: task_summaries[t]["mean_final_score"])
    worst_task   = min(tasks, key=lambda t: task_summaries[t]["mean_final_score"])
    total_eps    = sum(task_summaries[t]["n_episodes"] for t in tasks)
    comp_rate    = sum(task_summaries[t]["completion_rate"] for t in tasks) / n_tasks

    stats = [
        ("Overall Mean",    f"{overall_mean:.3f}", reward_color(overall_mean)),
        ("Best Task",       TASK_LABELS.get(best_task,  best_task).replace("\n", " "),  GREEN),
        ("Worst Task",      TASK_LABELS.get(worst_task, worst_task).replace("\n", " "), RED),
        ("Total Episodes",  str(total_eps),                                             INDIGO),
        ("Completion Rate", f"{comp_rate*100:.0f}%",                                   YELLOW),
    ]
    y_pos = 0.9
    ax2.text(0.5, 1.0, "Summary", ha="center", va="top", fontsize=11,
             fontweight="bold", color=TEXT_MAIN, transform=ax2.transAxes)
    for label_txt, val, col in stats:
        ax2.text(0.08, y_pos, label_txt, ha="left",  va="center", fontsize=8, color=TEXT_DIM,  transform=ax2.transAxes)
        ax2.text(0.92, y_pos, val,       ha="right", va="center", fontsize=9, color=col, fontweight="bold", transform=ax2.transAxes)
        ax2.axhline(y_pos - 0.06, color=BORDER, lw=0.5)
        y_pos -= 0.16

    # ── 3. Reward component radar / grouped bar ───────────────────────────────
    ax3 = fig.add_subplot(gs[1, :2])
    components = ["mean_empathy", "mean_resolution", "mean_accuracy", "mean_tone", "mean_efficiency"]
    comp_colors = [COMPONENT_COLORS[c.replace("mean_", "") + "_score"] for c in components]
    comp_labels = [COMPONENT_LABELS[c.replace("mean_", "") + "_score"] for c in components]
    bar_w  = 0.12
    n_comp = len(components)
    offsets = np.linspace(-(n_comp - 1) * bar_w / 2, (n_comp - 1) * bar_w / 2, n_comp)
    for ci, (comp, color, clabel, offset) in enumerate(zip(components, comp_colors, comp_labels, offsets)):
        vals = [task_summaries[t].get(comp, 0.0) for t in tasks]
        ax3.bar(x + offset, vals, width=bar_w, color=color, alpha=0.85, label=clabel, zorder=3)
    ax3.axhline(0.5, color=TEXT_DIM, lw=0.8, ls="--", alpha=0.4, zorder=2)
    ax3.set_xticks(x); ax3.set_xticklabels(xlabels, fontsize=8)
    ax3.set_ylim(0, 1.0)
    ax3.set_ylabel("Score")
    ax3.set_title("Reward Component Breakdown per Task", color=TEXT_MAIN, pad=8)
    ax3.legend(fontsize=7.5, labelcolor=TEXT_DIM, framealpha=0.3, ncol=5, loc="upper right")
    ax3.grid(axis="y", zorder=1)

    # ── 4. Completion rate ────────────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    comp_rates = [task_summaries[t]["completion_rate"] * 100 for t in tasks]
    bars4 = ax4.barh(xlabels, comp_rates,
                     color=[reward_color(c / 100) for c in comp_rates],
                     alpha=0.85, height=0.6)
    for bar, val in zip(bars4, comp_rates):
        ax4.text(min(val + 2, 95), bar.get_y() + bar.get_height() / 2,
                 f"{val:.0f}%", va="center", fontsize=8, color=TEXT_MAIN)
    ax4.set_xlim(0, 110)
    ax4.set_xlabel("Completion Rate (%)")
    ax4.set_title("Episode\nCompletion Rate", color=TEXT_MAIN, pad=8)
    ax4.axvline(50, color=YELLOW, lw=1, ls="--", alpha=0.5)
    ax4.grid(axis="x")

    # ── 5. Reward trajectory per task (mean reward per step) ─────────────────
    ax5 = fig.add_subplot(gs[2, :])
    for ti, task in enumerate(tasks):
        task_eps = [e for e in episodes if e["task"] == task]
        if not task_eps:
            continue
        max_len = max(len(e["step_rewards"]) for e in task_eps)
        matrix  = np.full((len(task_eps), max_len), np.nan)
        for i, ep in enumerate(task_eps):
            matrix[i, :len(ep["step_rewards"])] = ep["step_rewards"]
        mean_traj = np.nanmean(matrix, axis=0)
        steps     = np.arange(1, max_len + 1)
        color     = reward_color(task_summaries[task]["mean_final_score"])
        ax5.plot(steps, mean_traj, lw=2.0, color=color, alpha=0.9,
                 label=TASK_LABELS.get(task, task).replace("\n", " "), marker="o", markersize=3)
        if len(task_eps) > 1:
            std_traj = np.nanstd(matrix, axis=0)
            ax5.fill_between(steps, mean_traj - std_traj, mean_traj + std_traj,
                             color=color, alpha=0.1)
    ax5.axhline(0.5, color=TEXT_DIM, lw=0.8, ls="--", alpha=0.5)
    ax5.set_xlabel("Step")
    ax5.set_ylabel("Reward")
    ax5.set_ylim(0, 1.05)
    ax5.set_title("Mean Reward Trajectory per Step (shaded = ±1 std)", color=TEXT_MAIN, pad=8)
    ax5.legend(fontsize=8, labelcolor=TEXT_DIM, framealpha=0.3, ncol=4, loc="lower right")
    ax5.grid()

    # ── 6. Action type distribution ───────────────────────────────────────────
    ax6 = fig.add_subplot(gs[3, :2])
    from collections import Counter
    action_counts: Counter = Counter()
    for ep in episodes:
        action_counts.update(ep["step_actions"])
    if action_counts:
        act_labels = [a.replace("_", "\n") for a in action_counts.keys()]
        act_vals   = list(action_counts.values())
        act_colors = [INDIGO if "respond" in a or "approve" in a or "resolve" in a
                      else RED if "escalat" in a
                      else YELLOW if "request" in a or "feedback" in a or "send_back" in a
                      else NEUTRAL
                      for a in action_counts.keys()]
        ax6.bar(range(len(act_vals)), act_vals, color=act_colors, alpha=0.85, width=0.65)
        ax6.set_xticks(range(len(act_vals)))
        ax6.set_xticklabels(act_labels, fontsize=7.5)
        for i, val in enumerate(act_vals):
            ax6.text(i, val + 0.3, str(val), ha="center", fontsize=8, color=TEXT_MAIN)
        ax6.set_ylabel("Count")
        ax6.set_title("Action Type Distribution (all tasks combined)", color=TEXT_MAIN, pad=8)
        ax6.grid(axis="y")

    # ── 7. Score distribution box plot ────────────────────────────────────────
    ax7 = fig.add_subplot(gs[3, 2])
    score_data = [[e["final_score"] for e in episodes if e["task"] == t] for t in tasks]
    score_data = [s for s in score_data if s]
    box_labels = [TASK_LABELS.get(t, t).replace("\n", " ") for t in tasks
                  if [e for e in episodes if e["task"] == t]]
    if score_data:
        bp = ax7.boxplot(
            score_data,
            vert=True,
            patch_artist=True,
            tick_labels=box_labels,
            medianprops=dict(color=INDIGO, lw=2),
            boxprops=dict(facecolor=CARD_BG, color=BORDER),
            whiskerprops=dict(color=TEXT_DIM),
            capprops=dict(color=TEXT_DIM),
            flierprops=dict(marker="o", markersize=4, color=RED, alpha=0.6),
        )
        for patch, t in zip(bp["boxes"], tasks):
            patch.set_facecolor(reward_color(task_summaries[t]["mean_final_score"]) + "33")
        ax7.set_ylabel("Final Score")
        ax7.set_title("Final Score\nDistribution", color=TEXT_MAIN, pad=8)
        ax7.set_ylim(0, 1.05)
        ax7.tick_params(axis="x", labelsize=7, rotation=30)
        ax7.axhline(0.5, color=YELLOW, lw=0.8, ls="--", alpha=0.5)
        ax7.grid(axis="y")

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / f"benchmark_{data['label']}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"  Saved → {out_path}")


# ── Comparison plot (pre vs post) ─────────────────────────────────────────────

def plot_comparison(label_a: str, label_b: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import numpy as np

    path_a = RESULTS_DIR / f"results_{label_a}.json"
    path_b = RESULTS_DIR / f"results_{label_b}.json"

    if not path_a.exists() or not path_b.exists():
        print(f"  Missing results file(s). Run benchmark for both labels first.")
        return

    with open(path_a) as f: data_a = json.load(f)
    with open(path_b) as f: data_b = json.load(f)

    tasks = [t for t in data_a["tasks"] if t in data_a["task_summaries"] and t in data_b.get("task_summaries", {})]
    if not tasks:
        print("  No overlapping tasks between the two runs.")
        return

    plt.rcParams.update({
        "figure.facecolor": DARK_BG, "axes.facecolor": CARD_BG,
        "axes.edgecolor": BORDER, "axes.labelcolor": TEXT_MAIN,
        "text.color": TEXT_MAIN, "xtick.color": TEXT_DIM,
        "ytick.color": TEXT_DIM, "grid.color": BORDER,
        "grid.linewidth": 0.5, "font.family": "monospace", "font.size": 9,
    })

    fig = plt.figure(figsize=(20, 14), facecolor=DARK_BG)
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.5, wspace=0.35,
                            left=0.07, right=0.97, top=0.90, bottom=0.07)

    fig.text(0.5, 0.95, f"Pre vs Post Training — {label_a}  →  {label_b}",
             ha="center", fontsize=16, fontweight="bold", color=TEXT_MAIN)

    n   = len(tasks)
    x   = np.arange(n)
    xlabels = [TASK_LABELS.get(t, t) for t in tasks]
    w   = 0.35

    means_a = [data_a["task_summaries"][t]["mean_final_score"] for t in tasks]
    means_b = [data_b["task_summaries"][t]["mean_final_score"] for t in tasks]
    deltas  = [b - a for a, b in zip(means_a, means_b)]

    COLOR_A = "#64748b"   # slate — pre-train
    COLOR_B = INDIGO      # indigo — post-train

    # ── Panel 1: grouped bar comparison ───────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    bars_a = ax1.bar(x - w / 2, means_a, width=w, color=COLOR_A, alpha=0.8, label=label_a.replace("_", " "))
    bars_b = ax1.bar(x + w / 2, means_b, width=w, color=COLOR_B, alpha=0.9, label=label_b.replace("_", " "))
    for i, (ba, bb, d) in enumerate(zip(bars_a, bars_b, deltas)):
        ax1.text(ba.get_x() + ba.get_width() / 2, ba.get_height() + 0.01,
                 f"{means_a[i]:.2f}", ha="center", fontsize=8, color=COLOR_A)
        ax1.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 0.01,
                 f"{means_b[i]:.2f}", ha="center", fontsize=8, color=COLOR_B, fontweight="bold")
        sign = "+" if d >= 0 else ""
        delta_color = GREEN if d > 0 else RED
        ax1.text(x[i], max(means_a[i], means_b[i]) + 0.055,
                 f"{sign}{d:.2f}", ha="center", fontsize=8.5, color=delta_color, fontweight="bold")
    ax1.axhline(0.5, color=YELLOW, lw=0.8, ls="--", alpha=0.5)
    ax1.set_xticks(x); ax1.set_xticklabels(xlabels, fontsize=8.5)
    ax1.set_ylim(0, 1.15)
    ax1.set_ylabel("Mean Final Score")
    ax1.set_title("Mean Final Score: Pre vs Post Training (Δ shown above)", color=TEXT_MAIN, pad=10)
    ax1.legend(fontsize=9, labelcolor=TEXT_DIM, framealpha=0.3)
    ax1.grid(axis="y")

    # ── Panel 2: delta bar chart ───────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    delta_colors = [GREEN if d >= 0 else RED for d in deltas]
    ax2.barh(xlabels, deltas, color=delta_colors, alpha=0.85, height=0.6)
    for i, d in enumerate(deltas):
        sign = "+" if d >= 0 else ""
        ax2.text(d + (0.005 if d >= 0 else -0.005), i,
                 f"{sign}{d:.3f}", va="center",
                 ha="left" if d >= 0 else "right", fontsize=8, color=TEXT_MAIN)
    ax2.axvline(0, color=TEXT_DIM, lw=1)
    ax2.set_xlabel("Score Improvement (Δ)")
    ax2.set_title("Score Delta\n(Post − Pre)", color=TEXT_MAIN, pad=8)
    ax2.grid(axis="x")

    # ── Panel 3: component comparison heatmap ─────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    components = ["mean_empathy", "mean_resolution", "mean_accuracy", "mean_tone", "mean_efficiency"]
    comp_labels_short = ["Empathy", "Resolution", "Accuracy", "Tone", "Efficiency"]
    delta_matrix = np.array([
        [data_b["task_summaries"][t].get(c, 0) - data_a["task_summaries"][t].get(c, 0)
         for c in components]
        for t in tasks
    ])
    im = ax3.imshow(delta_matrix, aspect="auto", cmap="RdYlGn", vmin=-0.3, vmax=0.3)
    ax3.set_xticks(range(len(comp_labels_short)))
    ax3.set_xticklabels(comp_labels_short, fontsize=8, rotation=30, ha="right")
    ax3.set_yticks(range(len(xlabels)))
    ax3.set_yticklabels([l.replace("\n", " ") for l in xlabels], fontsize=8)
    for i in range(len(tasks)):
        for j in range(len(components)):
            v = delta_matrix[i, j]
            ax3.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=7.5,
                     color="white" if abs(v) > 0.15 else TEXT_MAIN)
    plt.colorbar(im, ax=ax3, fraction=0.046, pad=0.04, label="Δ Score")
    ax3.set_title("Component Improvement Heatmap\n(Post − Pre)", color=TEXT_MAIN, pad=8)

    out_path = RESULTS_DIR / f"comparison_{label_a}_vs_{label_b}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"  Saved → {out_path}")


# ── Print summary table ───────────────────────────────────────────────────────

def print_summary(data: dict):
    summaries = data["task_summaries"]
    tasks     = [t for t in data["tasks"] if t in summaries]
    print(f"\n{'═'*70}")
    print(f"  RESULTS — {data['label']}  |  model: {data['model']}")
    print(f"{'═'*70}")
    header = f"  {'Task':<30} {'Mean':>6} {'Min':>6} {'Max':>6} {'Steps':>6} {'Done':>6}"
    print(header)
    print(f"  {'-'*64}")
    for t in tasks:
        s = summaries[t]
        print(f"  {t:<30} {s['mean_final_score']:>6.3f} {s['min_score']:>6.3f} {s['max_score']:>6.3f} "
              f"{s['mean_steps']:>6.1f} {s['completion_rate']*100:>5.0f}%")
    overall = sum(s["mean_final_score"] for s in summaries.values()) / max(len(summaries), 1)
    print(f"  {'-'*64}")
    print(f"  {'OVERALL':<30} {overall:>6.3f}")
    print(f"{'═'*70}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AgentOS Benchmark Script")
    parser.add_argument("--label",    default="pre_train",
                        help="Label for this run (e.g. pre_train, post_train)")
    parser.add_argument("--episodes", type=int, default=5,
                        help="Episodes per task (default: 5)")
    parser.add_argument("--tasks",    nargs="+", default=ALL_TASKS,
                        help="Tasks to benchmark (default: all)")
    parser.add_argument("--compare",  nargs=2, metavar=("LABEL_A", "LABEL_B"),
                        help="Plot comparison between two saved result files")
    parser.add_argument("--plot-only", action="store_true",
                        help="Skip benchmark run, only regenerate plots from saved JSON")
    args = parser.parse_args()

    if args.compare:
        print(f"\n  Generating comparison: {args.compare[0]}  vs  {args.compare[1]}")
        plot_comparison(args.compare[0], args.compare[1])
        return

    if args.plot_only:
        result_path = RESULTS_DIR / f"results_{args.label}.json"
        if not result_path.exists():
            print(f"  No results file found at {result_path}")
            sys.exit(1)
        with open(result_path) as f:
            data = json.load(f)
        print_summary(data)
        plot_benchmark(data, args.label)
        return

    # Validate tasks
    valid = [t for t in args.tasks if t in ALL_TASKS]
    if not valid:
        print(f"  No valid tasks. Choose from: {ALL_TASKS}")
        sys.exit(1)

    data = run_benchmark(valid, args.episodes, args.label)
    print_summary(data)
    plot_benchmark(data, args.label)
    print(f"\n  Done. Results in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
