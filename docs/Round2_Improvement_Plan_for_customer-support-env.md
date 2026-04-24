# Round 2 Improvement Plan for Customer Support Env

## 1. Current Codebase Summary
**What the environment currently does:**
It simulates an RL environment where an AI agent acts as a customer support representative. The agent interacts with simulated customers across 4 difficulties (easy, medium, hard, nightmare) by picking from a discrete set of actions (`respond`, `request_info`, `escalate`, `close`). It receives shaped rewards based on tone (VADER sentiment), efficiency (steps taken), accuracy (information gathering), and resolution (keyword matching).

**Strengths:**
* **Excellent Architecture:** Fast, session-isolated, stateless API using FastAPI. Good use of Pydantic for validation and strict typing.
* **Production-Ready Server:** Rate-limiting, max session caps, PII sanitization, and structured logging are already in place.
* **Counter-Intuitive Tasks:** The `hard` task (where immediate escalation is required instead of self-resolution) is a great concept that breaks standard LLM behavior.

**Major Weaknesses (vs Hackathon Requirements):**
* **Rule-Based & Gammable Rewards:** VADER sentiment is archaic and easily gamed (an agent just spamming "happy happy joy joy" gets high tone scores). The resolution reward relies on rigid keyword lists (`_RESOLUTION_SIGNALS`) rather than semantic understanding.
* **Static Customer Simulator:** The customer replies are randomly selected from a hardcoded dictionary (`_FOLLOW_UPS`). Real OpenEnv innovation requires dynamic, LLM-driven state transitions.
* **No Training Pipeline:** There is no Unsloth, TRL, or GRPO training script present to actually train a model against this environment.
* **No UI/Visuals:** HF Space requirements usually expect a frontend (like Gradio or Streamlit) to visualize the agent interacting with the environment, not just an API.

## 2. Alignment with Official Hackathon Themes (April 2026)
**Which theme does it currently fit?**
It broadly fits "Enterprise AI" or "Autonomous Agents". However, it currently feels like a generic Western customer support bot.

**Which theme + sub-theme would give the highest innovation score (40%)?**
To maximize the "Environment Innovation" judging criteria, you need an ambitious, highly specific angle. 
* **Recommended Target Theme:** **Autonomous Enterprise Support in the Indian Context.**
* **The Ambitious Angle:** Focus the environment specifically on high-stress, uniquely Indian enterprise scenarios. For example: UPI transaction failures (money deducted but merchant not received), KYC document rejection loops, or festive-season (Big Billion Days) SLA breaches. Add a dynamic customer simulator that sometimes switches to "Hinglish" when frustrated. This makes the environment culturally relevant, highly novel, and much harder for off-the-shelf Western LLMs to solve without fine-tuning.

## 3. Gap Analysis Against Judging Criteria
* **Environment Innovation (40%):** Currently low. Hardcoded strings and regexes do not scream "2026 RL Environment". **Gap:** Needs an LLM-driven customer simulator and an LLM-as-a-Judge reward function.
* **Storytelling & Presentation (30%):** Good start with the README, but lacks a compelling business narrative. **Gap:** Frame this as a tool saving millions of dollars in SLA breach fines for Tier-1 companies.
* **Showing Improvement in Rewards (20%):** **Major Gap.** You currently have no baseline vs. trained agent plots because you haven't trained an agent yet.
* **Reward & Training Pipeline (10%):** **Major Gap.** No TRL/GRPO training script.
* **Minimum Requirements:** You are missing the Hugging Face Space UI and the training script using Unsloth/TRL.

## 4. Technical OpenEnv Compliance & Architecture Review
* `models.py`: Excellent use of `ActionType` enums and Pydantic validation.
* `environment.py`: Clean state management. The `_simulate_customer_reply` function is the weakest link. It should be replaced with an async LLM call.
* `openenv.yaml`: Well-structured and OpenEnv compliant.
* `server/app.py`: Great production hardening (SlowAPI, 64KB limits, TTL sweeps).
* **Issue:** The reward function logic inside `reward_engine.py` is synchronous and CPU-bound (Scikit-learn TF-IDF, VADER). If you switch to an LLM-as-a-judge, you will need to handle async calls to the LLM API within the step function, or use a fast local reward model.

## 5. Reward System Analysis & Upgrade Plan
**Current State:** 
Dense but highly gamable. VADER and regex are brittle.

**Upgrade Plan (Hybrid Dense Reward):**
Keep efficiency and exact-match logic (like accuracy for regexes) as rule-based, but upgrade Tone and Resolution to **LLM-as-a-Judge**.
1. **Rule-Based (Fast):**
   * Efficiency Penalty (steps used).
   * Loop Penalty (TF-IDF cosine similarity > 0.85).
   * Escalation Penalty (rule-based).
2. **LLM-as-a-Judge (Semantic):**
   * Run a parallel async call to a fast model (e.g., Llama-3-8B-Instruct or a NIM endpoint) to grade the agent's last response on a strict rubric:
     * *Empathy (0-1):* Did the agent acknowledge the specific pain point?
     * *Policy Adherence (0-1):* Did the agent follow the standard operating procedure for this specific ticket type?
     * *Resolution Accuracy (0-1):* Did the agent actually resolve the issue, or just pretend to?

*Weighting:* LLM Judge (60%), Efficiency (20%), Loop/Contradiction Penalties (20%).

## 6. Novelty & USP Recommendations
To guarantee a top spot, implement these 3 novel features:
1. **Dynamic LLM Customer Persona Simulator:** Replace `_FOLLOW_UPS` with a lightweight LLM prompt that generates customer replies based on a hidden `frustration_level` state variable. If the agent gives a bad response, `frustration_level` spikes, and the customer starts using all-caps or Hinglish.
2. **Schema Drift / Mid-Episode Policy Changes:** Inject system messages mid-conversation. e.g., `[SYSTEM ALERT: The refund portal is currently down. Do not promise immediate refunds.]` The agent must dynamically adjust its strategy. If it promises a refund anyway, massive negative reward.
3. **Multi-Step Tool Use (Partial Observability):** Instead of just `request_info`, add a `query_database` action. The agent doesn't see the customer's order history in the initial observation; it has to explicitly query it using the Order ID provided by the customer.

## 7. Training Pipeline Upgrade
You **must** provide a training script. GRPO (Group Relative Policy Optimization) via TRL is the standard for 2026.
* **Model:** Use `unsloth/Meta-Llama-3-8B-Instruct`.
* **Framework:** Unsloth + Hugging Face TRL (`GRPOTrainer`).
* **Implementation:** 
  1. Write a `train_grpo.py` script.
  2. Create an OpenEnv wrapper that converts your FastAPI `/step` endpoints into a standard Gym/RL environment interface that TRL expects.
  3. Generate N trajectories using the base model.
  4. Train using GRPO for ~500 steps.
  5. **Crucial:** Generate matplotlib plots showing the moving average of the reward increasing over time.

## 8. 48-Hour Onsite Execution Plan (25–26 April)
**Day 1: Environment & UI Overhaul**
* *0-4 Hours:* Replace VADER and regex with LLM-as-a-Judge in `reward_engine.py` (use NVIDIA NIM for speed).
* *4-8 Hours:* Replace the static customer simulator in `environment.py` with an LLM-driven customer. Implement the "Indian Enterprise / UPI Failure" ticket scenarios.
* *8-12 Hours:* Build a Gradio UI (`app_ui.py`) that visually shows the chat history, current sentiment, and real-time reward breakdowns. Mount it alongside the FastAPI app.

**Day 2: Training & Storytelling**
* *12-20 Hours:* Write `train_grpo.py`. Run a short Unsloth/TRL training session on a rented GPU (or Google Colab A100). Save the LoRA weights.
* *20-24 Hours:* Generate evaluation plots (Baseline vs. Trained Agent). Save them in a `results/` folder.
* *24-30 Hours:* Record the 3-minute demo video. Focus 1 minute on the env complexity, 1 minute on the training graph, 1 minute on the UI demo.
* *30-48 Hours:* Deploy to Hugging Face Spaces. Polish README. Buffer time for bugs.

## 9. Deliverables Checklist for Winning Submission
- [ ] **`train_grpo.py`**: Fully functional Unsloth + TRL training script.
- [ ] **`app_ui.py`**: Gradio frontend visualizing the environment in real-time.
- [ ] **Upgraded Environment**: LLM-as-a-judge rewards + dynamic LLM customer simulator.
- [ ] **Plots**: `baseline_vs_trained.png` showing clear reward improvement.
- [ ] **HF Space**: Deployed and public, containing the UI and the API.
- [ ] **Video**: 3-minute presentation (uploaded to YouTube/Vimeo).
- [ ] **README.md**: Updated to highlight the Indian Enterprise context, the LLM Judge, and the training results.

## 10. Specific Code Changes & New Files Needed
1. **Modify `env/reward_engine.py`**: Remove `vaderSentiment`. Add an async function `evaluate_with_llm_judge(action, history, ticket)`.
2. **Modify `env/environment.py`**: Refactor `_simulate_customer_reply` to prompt a lightweight LLM (e.g., Llama-3-8B) with the customer's persona and the conversation history.
3. **Create `train_grpo.py`**: Standalone script using `unsloth` and `trl`.
4. **Create `app_ui.py`**: A Gradio app that talks to your local FastAPI server. Use `gr.Chatbot` to visualize the `customer` and `agent` roles, and `gr.LinePlot` or HTML to show the reward breakdown per step.
5. **Update `requirements.txt`**: Add `trl`, `unsloth` (with specific install instructions), `gradio`, `matplotlib`.

---

### Recommended Next Immediate Action
**Do not touch the FastAPI server yet.** Your immediate next step is to write `train_grpo.py` and prove you can train an Unsloth model against your current (even if flawed) environment API. If the RL loop doesn't converge or connect to your API, the rest of the hackathon doesn't matter. Get a dummy training loop running *today*.
