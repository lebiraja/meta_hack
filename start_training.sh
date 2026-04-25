#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start_training.sh — One-shot training pipeline for HF Spaces
#
# Run this from the Space terminal:
#   bash start_training.sh
#
# What it does (in order):
#   1. Verify env server is healthy on :7860
#   2. Download judge model if not cached
#   3. Start local judge server on :8002 (background)
#   4. SFT warmstart — teaches JSON format (~1h)
#   5. GRPO training — full 5-stage curriculum (~10h)
#   6. Merge LoRA adapters into full model
#   7. Push merged model to HuggingFace Hub
#   8. Restart inference server with trained model
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Config — edit these ───────────────────────────────────────────────────────
POLICY_MODEL="${TRAIN_MODEL:-unsloth/Qwen3-8B}"
JUDGE_MODEL="${LOCAL_JUDGE_MODEL:-unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit}"
HF_REPO="${HF_REPO:-lebiraja/customer-support-grpo-v2}"
HF_REPO_GGUF="${HF_REPO_GGUF:-lebiraja/customer-support-grpo-v2-gguf}"
HF_TOKEN="${HF_TOKEN:-}"
ENV_URL="${ENV_URL:-http://localhost:7860}"
JUDGE_PORT="${JUDGE_PORT:-8002}"
CKPT_DIR="${CKPT_DIR:-/tmp/checkpoints}"
MERGED_DIR="${MERGED_DIR:-/tmp/merged_model}"
SKIP_SFT="${SKIP_SFT:-0}"       # set to 1 to skip SFT warmstart
SKIP_GRPO="${SKIP_GRPO:-0}"     # set to 1 to skip GRPO (merge only)

LOG_DIR="${LOG_DIR:-/tmp/logs}"
mkdir -p "$LOG_DIR" "$CKPT_DIR" "$MERGED_DIR"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] $*${NC}"; }
warn()  { echo -e "${YELLOW}[$(date '+%H:%M:%S')] $*${NC}"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] $*${NC}"; exit 1; }

# ── Step 0: Build frontend static export ─────────────────────────────────────
info "Step 0/8 — Building Next.js frontend for static serving on :7860 ..."
if [ -d "frontend" ] && command -v npm &>/dev/null; then
    cd frontend
    NEXT_STATIC_EXPORT=true \
    NEXT_PUBLIC_API_URL="" \
    npm run build 2>&1 | tail -5
    cd ..
    info "  Frontend built → frontend/out/ ✓"
    info "  Visit the Space URL to see the AgentOS UI (no separate port needed)"
else
    warn "  Skipping frontend build (frontend/ not found or npm not available)"
fi

# ── Step 1: Verify env server ─────────────────────────────────────────────────
info "Step 1/8 — Checking env server at $ENV_URL ..."
for i in $(seq 1 12); do
    if curl -sf "$ENV_URL/health" | grep -q "ok"; then
        info "  Env server healthy ✓"
        break
    fi
    warn "  Waiting for env server... ($i/12)"
    sleep 5
    if [ "$i" -eq 12 ]; then
        error "Env server not responding at $ENV_URL — is Docker running? (docker compose up -d env)"
    fi
done

# ── Step 2: Start local judge server ─────────────────────────────────────────
info "Step 2/8 — Starting local judge server on :$JUDGE_PORT ..."

# Kill existing judge if running
pkill -f "serve_judge.py" 2>/dev/null || true
sleep 1

LOCAL_JUDGE_MODEL="$JUDGE_MODEL" \
JUDGE_PORT="$JUDGE_PORT" \
nohup python serve_judge.py > "$LOG_DIR/judge.log" 2>&1 &
JUDGE_PID=$!
echo "$JUDGE_PID" > "$LOG_DIR/judge.pid"
info "  Judge PID=$JUDGE_PID — waiting for model to load (~30s)..."

for i in $(seq 1 20); do
    sleep 5
    if curl -sf "http://localhost:$JUDGE_PORT/health" | grep -q '"ready":true'; then
        info "  Local judge ready ✓  ($(curl -s http://localhost:$JUDGE_PORT/health | python3 -c 'import sys,json; print(json.load(sys.stdin)["model"][-30:])' 2>/dev/null))"
        break
    fi
    warn "  Loading judge model... ($((i*5))s)"
    if [ "$i" -eq 20 ]; then
        error "Judge server failed to start. Check $LOG_DIR/judge.log"
    fi
done

export JUDGE_BASE_URL="http://localhost:$JUDGE_PORT/v1"
export JUDGE_MODEL_NAME="local-judge"
export JUDGE_MODE="full"

# ── Step 3: Quick smoke test ──────────────────────────────────────────────────
info "Step 3/8 — Smoke test: env + judge working together..."
SESSION=$(curl -sf -X POST "$ENV_URL/reset?task=curriculum_basic" \
    -H "X-API-Key: meta_hack_2026" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
RESULT=$(curl -sf -X POST "$ENV_URL/step?session_id=$SESSION" \
    -H "Content-Type: application/json" -H "X-API-Key: meta_hack_2026" \
    -d '{"action_type":"respond","message":"I understand your concern. Let me resolve this for you right away."}' \
    | python3 -c "import sys,json; r=json.load(sys.stdin).get('reward',{}); print(f'reward={r.get(\"value\",\"?\")} empathy={r.get(\"empathy_score\",\"?\")}')")
info "  Smoke test result: $RESULT ✓"

# ── Step 4: SFT warmstart ─────────────────────────────────────────────────────
if [ "$SKIP_SFT" = "0" ]; then
    if [ -d "$CKPT_DIR/sft" ]; then
        warn "Step 4/8 — SFT checkpoint found at $CKPT_DIR/sft — skipping (delete to re-run)"
        SFT_CKPT="$CKPT_DIR/sft"
    else
        info "Step 4/8 — SFT warmstart (collect 200 gold episodes + fine-tune ~1h)..."
        TRAIN_MODEL="$POLICY_MODEL" \
        JUDGE_BASE_URL="$JUDGE_BASE_URL" \
        JUDGE_MODEL="$JUDGE_MODEL_NAME" \
        python -m train.sft_warmstart \
            --mode all \
            --n_episodes 200 \
            --steps 500 \
            --out_dir "$CKPT_DIR/sft" \
            --data "$CKPT_DIR/sft_data.jsonl" \
            2>&1 | tee "$LOG_DIR/sft.log"
        SFT_CKPT="$CKPT_DIR/sft"
        info "  SFT warmstart done ✓ — checkpoint: $SFT_CKPT"
    fi
else
    warn "Step 4/8 — SFT skipped (SKIP_SFT=1)"
    SFT_CKPT="$POLICY_MODEL"
fi

# ── Step 5: GRPO training ─────────────────────────────────────────────────────
if [ "$SKIP_GRPO" = "0" ]; then
    info "Step 5/8 — GRPO training (~10h, 5 curriculum stages)..."
    info "  Logs: tail -f $LOG_DIR/train.log"
    info "  Checkpoints every 200 steps → $CKPT_DIR/"

    TRAIN_MODEL="$SFT_CKPT" \
    LOCAL_JUDGE_MODEL="$JUDGE_MODEL" \
    JUDGE_BASE_URL="$JUDGE_BASE_URL" \
    JUDGE_MODEL="$JUDGE_MODEL_NAME" \
    JUDGE_MODE="full" \
    python -m train.run_train \
        --total_steps "${TOTAL_STEPS:-3500}" \
        --ckpt_dir "$CKPT_DIR" \
        2>&1 | tee "$LOG_DIR/train.log"

    info "  GRPO training complete ✓"
else
    warn "Step 5/8 — GRPO skipped (SKIP_GRPO=1)"
fi

# ── Step 6: Find best checkpoint ─────────────────────────────────────────────
info "Step 6/8 — Finding best checkpoint..."
if [ -f "$CKPT_DIR/best/best_score.txt" ]; then
    BEST_CKPT="$CKPT_DIR/best"
    info "  Using best checkpoint: $(cat "$CKPT_DIR/best/best_score.txt")"
elif [ -d "$CKPT_DIR/final" ]; then
    BEST_CKPT="$CKPT_DIR/final"
    warn "  No best/ found — falling back to final checkpoint"
else
    BEST_CKPT=$(ls -dt "$CKPT_DIR"/step_* 2>/dev/null | head -1)
    warn "  No best/ or final/ — using most recent step checkpoint: $BEST_CKPT"
fi

if [ -z "$BEST_CKPT" ]; then
    error "No checkpoint found in $CKPT_DIR — did training complete?"
fi
info "  Using checkpoint: $BEST_CKPT ✓"

# ── Step 7: Merge LoRA ────────────────────────────────────────────────────────
info "Step 7/8 — Merging LoRA adapters into full model (~15min)..."
python -m train.merge_lora \
    --ckpt "$BEST_CKPT" \
    --out  "$MERGED_DIR" \
    2>&1 | tee "$LOG_DIR/merge.log"
info "  Merge complete ✓ — model at $MERGED_DIR"

# ── Step 8: Push to HF Hub ────────────────────────────────────────────────────
if [ -n "$HF_TOKEN" ] && [ -n "$HF_REPO" ]; then
    info "Step 8/8 — Pushing merged model to HuggingFace Hub: $HF_REPO ..."
    python -m train.merge_lora \
        --ckpt "$BEST_CKPT" \
        --out  "$MERGED_DIR" \
        --push \
        --repo "$HF_REPO" \
        --token "$HF_TOKEN" \
        2>&1 | tee -a "$LOG_DIR/merge.log"
    info "  Pushed to https://huggingface.co/$HF_REPO ✓"
else
    warn "Step 8/8 — HF push skipped (set HF_TOKEN and HF_REPO env vars to enable)"
    warn "  To push manually: python -m train.merge_lora --ckpt $BEST_CKPT --out $MERGED_DIR --push --repo YOUR_REPO --token YOUR_TOKEN"
fi

# ── Step 8.5: GGUF Q4 quantization + push to separate HF repo ─────────────────
GGUF_EXPORT="${GGUF_EXPORT:-1}"
if [ "$GGUF_EXPORT" = "1" ] && [ -n "$HF_TOKEN" ] && [ -n "$HF_REPO_GGUF" ]; then
    info "Step 8.5/8 — Exporting GGUF Q4_K_M and pushing to $HF_REPO_GGUF ..."
    python -m train.export_gguf \
        --model "$MERGED_DIR" \
        --out   "$MERGED_DIR/gguf/model-q4_k_m.gguf" \
        --quant q4_k_m \
        --push \
        --repo  "$HF_REPO_GGUF" \
        --token "$HF_TOKEN" \
        2>&1 | tee "$LOG_DIR/gguf.log"
    info "  GGUF pushed to https://huggingface.co/$HF_REPO_GGUF ✓"
else
    warn "Step 8.5/8 — GGUF export skipped (set GGUF_EXPORT=1, HF_TOKEN and HF_REPO_GGUF to enable)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
info "Training pipeline complete!"
echo ""
echo "  Checkpoint : $BEST_CKPT"
echo "  Merged     : $MERGED_DIR"
[ -n "$HF_REPO" ] && echo "  HF Hub (16-bit) : https://huggingface.co/$HF_REPO"
[ -n "$HF_REPO_GGUF" ] && echo "  HF Hub (GGUF)   : https://huggingface.co/$HF_REPO_GGUF"
echo ""
echo "  To serve the trained model for inference:"
echo "    INFERENCE_MODEL=$MERGED_DIR python serve_inference.py"
echo ""
echo "  Logs:"
echo "    $LOG_DIR/judge.log"
echo "    $LOG_DIR/sft.log"
echo "    $LOG_DIR/train.log"
echo "    $LOG_DIR/merge.log"
echo "    $LOG_DIR/gguf.log"
echo ""
echo "  Run GGUF model locally:"
echo "    ollama run hf.co/$HF_REPO_GGUF"
echo "═══════════════════════════════════════════════════════════"
