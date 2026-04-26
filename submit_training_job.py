"""
submit_training_job.py — Submit the GRPO training pipeline as a self-contained HF Job.

Usage (single account):
    HF_TOKEN=hf_xxx python submit_training_job.py

Usage (friend pays, you push to your repos):
    HF_TOKEN=hf_your_token SUBMIT_TOKEN=hf_friends_token python submit_training_job.py

    HF_TOKEN     = YOUR token — used inside the job to clone the Space and push the model
    SUBMIT_TOKEN = FRIEND's token — used to submit the job (billing goes to their account)
    If SUBMIT_TOKEN is not set, HF_TOKEN is used for both (single-account mode).

    python submit_training_job.py --logs           # stream logs from last job
    python submit_training_job.py --logs <job_id>  # stream specific job
    python submit_training_job.py --status         # check last job status
"""

import os
import sys
from huggingface_hub import run_job, fetch_job_logs, inspect_job

# ── Config ────────────────────────────────────────────────────────────────────

HF_REPO          = os.getenv("HF_REPO",      "lebiraja/customer-support-grpo-v5")
HF_REPO_GGUF     = os.getenv("HF_REPO_GGUF", "lebiraja/customer-support-grpo-v5-gguf")
HF_TOKEN         = os.getenv("HF_TOKEN",     "")   # YOUR token — clone Space + push model
SUBMIT_TOKEN     = os.getenv("SUBMIT_TOKEN", HF_TOKEN)  # FRIEND's token — billing only
SKIP_SFT         = os.getenv("SKIP_SFT",     "1")
SKIP_GRPO        = os.getenv("SKIP_GRPO",    "0")
GGUF_EXPORT      = os.getenv("GGUF_EXPORT",  "1")
FLAVOR           = os.getenv("JOB_FLAVOR",   "l40sx1")   # L40S 48GB, $1.80/hr → ~$11 for 150 steps
TIMEOUT          = os.getenv("JOB_TIMEOUT",  "10h")
NVIDIA_API_KEY_1 = os.getenv("NVIDIA_API_KEY_1", "")
SPACE_REPO       = os.getenv("SPACE_REPO",   "lebiraja/customer-support-env")
TRAIN_MODEL      = os.getenv("TRAIN_MODEL",  "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit")
TOTAL_STEPS      = os.getenv("TOTAL_STEPS",  "150")  # ~6hr total incl. evals + post ≈ $11

# Unsloth image has CUDA 12.1 + PyTorch + unsloth + trl preinstalled
IMAGE = "unsloth/unsloth:latest"

COMMAND = [
    "bash", "-c",
    r"""
set -euo pipefail
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        AgentOS GRPO Training Job — Self-Contained    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 0: Create writable dirs FIRST (before anything redirects to them) ──
mkdir -p /workspace/logs /workspace/checkpoints /workspace/merged_model
cd /workspace

# ── Step 1: Install extra deps not in unsloth image ────────────────────────
echo "[SETUP] Installing extra dependencies..."
pip install -q httpx python-dotenv vaderSentiment structlog slowapi fastapi uvicorn 2>&1 | tail -3
echo "[SETUP] Done ✓"

# ── Step 2: Clone the repo (Space repo, since we already mirror to it) ─────
echo "[SETUP] Cloning repo from huggingface.co/spaces/${SPACE_REPO}..."
git clone "https://user:${HF_TOKEN}@huggingface.co/spaces/${SPACE_REPO}" /workspace/repo
cd /workspace/repo
pip install -q -e . 2>&1 | tail -3 || true
echo "[SETUP] Repo ready ✓"

# ── Step 3: Start env server locally on :7860 ──────────────────────────────
echo "[ENV] Starting env server on :7860..."
nohup uvicorn server.app:app --host 0.0.0.0 --port 7860 --timeout-keep-alive 30 \
    > /workspace/logs/env.log 2>&1 &
ENV_PID=$!
echo "[ENV] PID=$ENV_PID — waiting for healthy..."

for i in $(seq 1 24); do
    sleep 5
    if curl -sf http://localhost:7860/health 2>/dev/null | grep -q '"env_functional":true'; then
        echo "[ENV] Env server healthy ✓"
        break
    fi
    echo "[ENV] Waiting... (${i}/24)"
    if [ "$i" -eq 24 ]; then
        echo "[ENV] ERROR: env server failed to start within 120s. Logs:"
        tail -50 /workspace/logs/env.log || true
        exit 1
    fi
done

# ── Step 4: Run the full training pipeline ─────────────────────────────────
echo "[TRAIN] Starting training pipeline..."

ENV_URL="http://localhost:7860" \
HF_REPO="${HF_REPO}" \
HF_REPO_GGUF="${HF_REPO_GGUF}" \
HF_TOKEN="${HF_TOKEN}" \
NVIDIA_API_KEY_1="${NVIDIA_API_KEY_1:-}" \
CKPT_DIR="/workspace/checkpoints" \
MERGED_DIR="/workspace/merged_model" \
LOG_DIR="/workspace/logs" \
SKIP_SFT="${SKIP_SFT}" \
SKIP_GRPO="${SKIP_GRPO}" \
GGUF_EXPORT="${GGUF_EXPORT}" \
JUDGE_MODE="terminal_only" \
bash start_training.sh

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              Training Job Complete ✓                 ║"
echo "╚══════════════════════════════════════════════════════╝"
"""
]

# ── Submit ────────────────────────────────────────────────────────────────────

def main():
    if not HF_TOKEN:
        print("\n  ERROR: HF_TOKEN is not set (needed to clone Space + push model).")
        print("  Single account : HF_TOKEN=hf_xxx python submit_training_job.py")
        print("  Friend pays    : HF_TOKEN=hf_yours SUBMIT_TOKEN=hf_friends python submit_training_job.py\n")
        sys.exit(1)

    billing_account = "friend's account" if SUBMIT_TOKEN != HF_TOKEN else "your account"
    print(f"\n{'═'*60}")
    print(f"  Submitting Self-Contained HF Training Job")
    print(f"  Image      : {IMAGE}")
    print(f"  Hardware   : {FLAVOR}  (L40S 48GB ≈ $1.80/hr)")
    print(f"  Timeout    : {TIMEOUT}")
    print(f"  Model      : {TRAIN_MODEL}")
    print(f"  Steps      : {TOTAL_STEPS}  (~6hr, ~$11 total)")
    print(f"  Model (16b): {HF_REPO}")
    print(f"  Model (GGUF): {HF_REPO_GGUF}")
    print(f"  Billing    : {billing_account}")
    print(f"  Skip SFT   : {SKIP_SFT}")
    print(f"  GGUF export: {GGUF_EXPORT}")
    print(f"{'═'*60}\n")

    # HF_TOKEN (lebiraja's) goes INSIDE the job for cloning + pushing
    secrets = {"HF_TOKEN": HF_TOKEN}
    if NVIDIA_API_KEY_1:
        secrets["NVIDIA_API_KEY_1"] = NVIDIA_API_KEY_1

    # SUBMIT_TOKEN (friend's) is used to call run_job — billing goes to that account
    job = run_job(
        image=IMAGE,
        command=COMMAND,
        flavor=FLAVOR,
        timeout=TIMEOUT,
        secrets=secrets,
        env={
            "HF_REPO":      HF_REPO,
            "HF_REPO_GGUF": HF_REPO_GGUF,
            "SPACE_REPO":   SPACE_REPO,
            "SKIP_SFT":     SKIP_SFT,
            "SKIP_GRPO":    SKIP_GRPO,
            "GGUF_EXPORT":  GGUF_EXPORT,
            "JUDGE_MODE":   "terminal_only",
            "TRAIN_MODEL":  TRAIN_MODEL,
            "TOTAL_STEPS":  TOTAL_STEPS,
        },
        labels={"project": "meta-hack", "type": "grpo-training"},
        token=SUBMIT_TOKEN,
    )

    with open("last_job_id.txt", "w") as f:
        f.write(job.id)

    print(f"  ✓ Job submitted! Billing → {billing_account}")
    print(f"  Job ID  : {job.id}")
    print(f"  Job URL : {job.url}")
    print(f"\n  Models will appear at:")
    print(f"    https://huggingface.co/{HF_REPO}")
    print(f"    https://huggingface.co/{HF_REPO_GGUF}")
    print(f"\n  Stream logs:")
    print(f"    SUBMIT_TOKEN=hf_friends_token .venv/bin/python submit_training_job.py --logs")
    print(f"{'═'*60}\n")


def stream_logs(job_id: str):
    info = inspect_job(job_id=job_id, token=SUBMIT_TOKEN)
    print(f"\n  Job ID     : {job_id}")
    print(f"  Status     : {info.status.stage}")
    print(f"  URL        : {info.url}")
    print(f"\n  Streaming logs... (Ctrl+C to stop — job keeps running)\n")
    print("─" * 60)
    try:
        for line in fetch_job_logs(job_id=job_id, token=SUBMIT_TOKEN):
            print(line, end="", flush=True)
    except KeyboardInterrupt:
        pass
    info = inspect_job(job_id=job_id, token=SUBMIT_TOKEN)
    print(f"\n{'─'*60}")
    print(f"  Status: {info.status.stage}")


def show_status(job_id: str):
    info = inspect_job(job_id=job_id, token=SUBMIT_TOKEN)
    print(f"\n  Job ID  : {job_id}")
    print(f"  Status  : {info.status.stage}")
    print(f"  URL     : {info.url}")
    if info.status.message:
        print(f"  Message : {info.status.message}")
    print()


def _load_last_job_id() -> str:
    try:
        return open("last_job_id.txt").read().strip()
    except FileNotFoundError:
        print("  No last_job_id.txt found. Submit a job first or pass the job ID explicitly.")
        sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        main()
    elif args[0] == "--logs":
        job_id = args[1] if len(args) > 1 else _load_last_job_id()
        stream_logs(job_id)
    elif args[0] == "--status":
        job_id = args[1] if len(args) > 1 else _load_last_job_id()
        show_status(job_id)
    else:
        print(__doc__)
