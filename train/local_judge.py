"""
train/local_judge.py — Local Qwen3-1.5B judge for intermediate step evaluation.

Loads a small 4-bit quantized model on the same GPU as the policy model.
Used for empathy scoring on non-terminal steps, replacing slow API calls.

API judge (NVIDIA NIM): ~3500ms/call — used only at terminal step
Local judge (Qwen3-1.5B 4-bit ~1GB VRAM): ~50ms/call — used for all other steps

This gives ~3.7× speedup on rollout collection for hierarchy episodes.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_EMPATHY_PROMPT = """Rate the EMPATHY of this customer support message on 0.0-1.0.

1.0=excellent: specific acknowledgment, warm, validates feelings
0.7=good: polite but not deeply empathetic
0.5=neutral: professional but cold/robotic
0.3=poor: dismissive or canned
0.0=terrible: rude or hostile

Message: {message}

Output ONLY JSON: {{"score": <float>}}"""


class LocalJudge:
    """
    Lightweight local LLM judge using Qwen3-1.5B 4-bit quantization.

    Designed to coexist with a larger policy model on the same GPU.
    Falls back to a neutral 0.5 score if the model fails to load.
    """

    def __init__(self, model_name: str = "unsloth/Qwen3-1.5B-Instruct", device: str = "cuda"):
        self._model = None
        self._tokenizer = None
        self._device = device
        self._lock = threading.Lock()
        self._available = False

        if not model_name:
            logger.info("LocalJudge: no model_name — local judge disabled")
            return

        try:
            self._load_model(model_name)
        except Exception as e:
            logger.warning(f"LocalJudge: failed to load {model_name}: {e} — falling back to 0.5")

    def _load_model(self, model_name: str) -> None:
        try:
            from unsloth import FastLanguageModel
            self._model, self._tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_name,
                max_seq_length=512,
                load_in_4bit=True,
                dtype=None,
            )
            FastLanguageModel.for_inference(self._model)
            self._available = True
            logger.info(f"LocalJudge: loaded {model_name} successfully")
        except ImportError:
            # Fallback to transformers if unsloth not available
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            import torch
            bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb,
                device_map=self._device,
            )
            self._model.eval()
            self._available = True
            logger.info(f"LocalJudge: loaded {model_name} via transformers")

    @property
    def available(self) -> bool:
        return self._available

    def _infer(self, prompt: str, max_new_tokens: int = 64) -> str:
        """Run local inference. Thread-safe via lock."""
        import torch
        with self._lock:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
            with torch.no_grad():
                out = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.1,
                    do_sample=False,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            # Decode only the newly generated tokens
            new_ids = out[0][inputs["input_ids"].shape[1]:]
            return self._tokenizer.decode(new_ids, skip_special_tokens=True).strip()

    def _parse_score(self, raw: str) -> Optional[float]:
        raw = raw.strip()
        if "```" in raw:
            raw = re.sub(r"```json?\s*", "", raw)
            raw = raw.replace("```", "").strip()
        try:
            result = json.loads(raw)
            score = float(result.get("score", 0.5))
            return max(0.0, min(1.0, score))
        except Exception:
            # Try to extract any float from the response
            m = re.search(r"\b(0\.\d+|1\.0|0|1)\b", raw)
            if m:
                return max(0.0, min(1.0, float(m.group(1))))
            return None

    def score_empathy_fast(self, prompt: str, completion: str) -> Optional[float]:
        """
        Score empathy of an agent's completion. Returns None on failure.

        Extracts just the agent message from the completion to keep the
        local judge prompt short (<512 tokens total).
        """
        if not self._available or not completion:
            return None

        # Extract the agent message from the completion JSON
        message = completion
        try:
            data = json.loads(completion)
            message = data.get("message") or data.get("feedback_to_agent") or completion
        except Exception:
            # Try regex for "message": "..."
            m = re.search(r'"message"\s*:\s*"([^"]{10,500})"', completion)
            if m:
                message = m.group(1)

        if not message or len(message.strip()) < 10:
            return None

        judge_prompt = _EMPATHY_PROMPT.format(message=message[:400])
        try:
            raw = self._infer(judge_prompt)
            return self._parse_score(raw)
        except Exception as e:
            logger.debug(f"LocalJudge.score_empathy_fast failed: {e}")
            return None


# ── Singleton ──────────────────────────────────────────────────────────────────

_local_judge_instance: Optional[LocalJudge] = None
_init_lock = threading.Lock()


def get_local_judge(model_name: Optional[str] = None, device: str = "cuda") -> LocalJudge:
    """Get or create the singleton local judge. Thread-safe."""
    global _local_judge_instance
    if _local_judge_instance is None:
        with _init_lock:
            if _local_judge_instance is None:
                name = model_name or os.environ.get(
                    "LOCAL_JUDGE_MODEL", "unsloth/Qwen3-1.5B-Instruct"
                )
                _local_judge_instance = LocalJudge(model_name=name, device=device)
    return _local_judge_instance
