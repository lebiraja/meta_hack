"""
submit_training_job.py — Submit the GRPO training pipeline as an HF Job.

The Job runs on a100-large (80GB VRAM), connects to the Space env server
for rollouts, trains for ~12h, merges LoRA, and pushes to HF Hub.

Usage:
    python submit_training_job.py

Env vars (optional overrides):
    SPACE_URL   — env server URL (default: the public Space URL)
    HF_REPO     — where to push merged model (default: lebiraja/customer-support-grpo)
    SKIP_SFT    — set 1 to skip SFT warmstart
    SKIP_GRPO   — set 1 to skip GRPO (merge only)
"""

import os
import sys
from huggingface_hub import run_job, fetch_job_logs, inspect_job

# ── Config ────────────────────────────────────────────────────────────────────

SPACE_URL  = os.getenv("SPACE_URL",  "https://lebiraja-customer-support-env.hf.space")
HF_REPO    = os.getenv("HF_REPO",   "lebiraja/customer-support-grpo")
HF_TOKEN   = os.getenv("HF_TOKEN",  "")
SKIP_SFT   = os.getenv("SKIP_SFT",  "0")
SKIP_GRPO  = os.getenv("SKIP_GRPO", "0")
FLAVOR     = os.getenv("JOB_FLAVOR", "a100-large")   # 80GB A100, $2.50/hr
TIMEOUT    = os.getenv("JOB_TIMEOUT", "15h")          # 15h covers full pipeline

# Docker image: unsloth official image with CUDA + all training deps preinstalled
IMAGE = "unsloth/unsloth:latest"

# The command clones our repo and runs start_training.sh
COMMAND = [
    "bash", "-c",
    f"""
set -euo pipefail

echo "=== HF Job Training Pipeline ===" && \\
echo "Space URL: {SPACE_URL}" && \\
echo "HF Repo:   {HF_REPO}" && \\

# Install missing deps not in unsloth image
pip install -q httpx python-dotenv vaderSentiment structlog slowapi fastapi 2>&1 | tail -3 && \\

# Clone our repo
git clone https://huggingface.co/spaces/lebiraja/customer-support-env /workspace/repo && \\
cd /workspace/repo && \\

# Install the package
pip install -q -e . 2>&1 | tail -3 && \\

# Run the training pipeline
ENV_URL="{SPACE_URL}" \\
HF_REPO="{HF_REPO}" \\
CKPT_DIR="/workspace/checkpoints" \\
MERGED_DIR="/workspace/merged_model" \\
LOG_DIR="/workspace/logs" \\
SKIP_SFT="{SKIP_SFT}" \\
SKIP_GRPO="{SKIP_GRPO}" \\
bash start_training.sh

echo "=== Training Job Complete ==="
"""
]

# ── Submit ────────────────────────────────────────────────────────────────────

def main():
    if not HF_TOKEN:
        print("ERROR: set HF_TOKEN env var before submitting")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Submitting HF Training Job")
    print(f"  Hardware : {FLAVOR}  (A100 80GB, $2.50/hr)")
    print(f"  Timeout  : {TIMEOUT}")
    print(f"  Env URL  : {SPACE_URL}")
    print(f"  Push to  : {HF_REPO}")
    print(f"{'='*60}\n")

    job = run_job(
        image=IMAGE,
        command=COMMAND,
        flavor=FLAVOR,
        timeout=TIMEOUT,
        secrets={"HF_TOKEN": HF_TOKEN},
        env={
            "ENV_URL":   SPACE_URL,
            "HF_REPO":   HF_REPO,
            "SKIP_SFT":  SKIP_SFT,
            "SKIP_GRPO": SKIP_GRPO,
            "JUDGE_MODE": "terminal_only",   # faster rollouts during training
        },
        labels={"project": "meta-hack", "type": "grpo-training"},
    )

    print(f"  Job submitted!")
    print(f"  Job ID  : {job.id}")
    print(f"  Job URL : {job.url}")
    print(f"\n  Watch logs:\n  python submit_training_job.py --logs {job.id}")
    print(f"\n  Or via CLI:\n  hf jobs logs {job.id}")
    print(f"{'='*60}\n")

    # Save job ID for later reference
    with open("last_job_id.txt", "w") as f:
        f.write(job.id)
    print(f"  Job ID saved to last_job_id.txt")


def stream_logs(job_id: str):
    print(f"\n  Streaming logs for job: {job_id}")
    print(f"  (Ctrl+C to stop — job keeps running)\n")
    try:
        for line in fetch_job_logs(job_id=job_id):
            print(line, end="", flush=True)
    except KeyboardInterrupt:
        info = inspect_job(job_id=job_id)
        print(f"\n\n  Job status: {info.status.stage}")
        print(f"  Job URL   : {info.url}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--logs":
        stream_logs(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "--logs":
        # Read from last_job_id.txt
        try:
            job_id = open("last_job_id.txt").read().strip()
            stream_logs(job_id)
        except FileNotFoundError:
            print("No last_job_id.txt found. Run: python submit_training_job.py --logs <job_id>")
    else:
        main()
