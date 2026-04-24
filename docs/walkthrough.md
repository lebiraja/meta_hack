# Meta OpenEnv Hackathon — Round 2 Upgrade Documentation

This document serves as the comprehensive completion report and technical walkthrough for the Round 2 upgrade of the `customer-support-env`.

## 1. Architectural Overhaul: Hierarchical Multi-Agent System

We transitioned the environment from a single-agent RL loop to a robust **3-Level Hierarchical Multi-Agent System**, designed to simulate complex, real-world enterprise customer support workflows. 

The environment now dynamically manages states and role transitions between three distinct agent levels:

1. **Level 1: Support Agent**
   - **Role**: Front-line interaction, gathers information, provides initial responses.
   - **Actions**: `respond`, `request_info`, `close`, `escalate` (to L2).
2. **Level 2: Supervisor**
   - **Role**: Oversight, QA, policy enforcement, and coaching. Reviews every L1 action before it reaches the customer.
   - **Actions**: `supervisor_approve`, `supervisor_reject`, `supervisor_feedback` (sends back to L1), `supervisor_escalate` (to L3).
3. **Level 3: Manager**
   - **Role**: Executive escalation, conflict resolution, policy overriding.
   - **Actions**: `manager_override`, `manager_resolve`, `manager_send_back`.

This is implemented via the new `HierarchicalCustomerSupportEnv` class, utilizing a phase-based state machine (`HierarchyState`) that routes actions and transitions seamlessly. Crucially, the environment maintains **100% backward compatibility** with Round 1 single-agent tasks.

## 2. Core Feature Additions

### LLM-Driven Customer Simulator & Hinglish Degradation
- **File**: `env/customer_simulator.py`
- Replaced deterministic customer logic with a dynamic LLM-driven simulator.
- Tracks `frustration_level` based on agent interactions.
- **Hinglish Degradation**: If frustration exceeds `0.6`, the customer simulator begins degrading its language into Hinglish, simulating real-world agitated Indian enterprise customers.

### Hybrid Reward Engine & LLM-as-a-Judge
- **Files**: `env/reward_engine.py`, `env/llm_judge.py`
- Eliminated gamable, purely deterministic rewards.
- Implemented an asynchronous LLM-as-a-Judge module evaluating 5 specific rubrics: `empathy`, `resolution`, `policy_adherence`, `oversight_quality`, and `decision_quality`.
- **Role-Specific Rewards**: The engine now issues isolated scores for `support_agent`, `supervisor`, and `manager`, enabling targeted RL updates (e.g., GRPO) per role.
- **Anti-Gaming Penalties**: Strict deductions for hallucinated policies, ignored supervisor feedback, and repetitive loops.

### Dynamic Policy Drift Engine
- **File**: `env/policy_engine.py`
- Introduces mid-episode "schema drift" to test agent adaptability. 
- Example: The system might inject an `ENVIRONMENT EVENT: Refund portal is down` at step 3, forcing the Supervisor to reject a Support Agent's attempt to issue a refund and demanding an alternative solution.

### Indian Enterprise Dataset
- **File**: `env/ticket_store.py`
- Added 6 high-complexity, hierarchical tickets focused on the Indian Enterprise context (UPI failures, Big Billion Days timeouts, KYC rejections, SLA breaches).

### Hierarchy Graders
- **Files**: `env/graders/task_hierarchy_easy.py`, `medium.py`, `hard.py`
- Developed 3 new graders explicitly designed to evaluate the multi-agent interaction flow, ensuring L2s actually review and L3s actually resolve critical paths.

## 3. Workflow & Integration

### Server Routing
- **File**: `server/app.py`
- The FastAPI server was upgraded to auto-detect task requests. Requests starting with `hierarchy_*` are routed to the `HierarchicalCustomerSupportEnv`, while standard tasks use `CustomerSupportEnv`.

### Inference Loop
- **File**: `inference.py`
- The inference script was entirely rewritten to support dynamic role switching. 
- It parses the `active_role` from the observation state and injects role-specific system prompts (Support Agent vs. Supervisor vs. Manager) containing contextual data like `supervisor_feedback` and `manager_directives`.
- Retains API key failover logic using NVIDIA NIM endpoints.

### API Specification
- **File**: `openenv.yaml`
- Bumped version to `2.0.0`.
- Added 3 new hierarchy tasks and expanded the action/observation space to include fields like `active_role`, `supervisor_feedback`, and `policy_context`.

## 4. Testing & Results

The entire system is successfully dockerized and validated.

### Test Suite Execution
- Wrote extensive `pytest` test cases covering session isolation, LLM-as-a-judge boundaries, hierarchy phase transitions, and end-to-end API flows.
- **Result**: `50/50 tests passed` in 3.71s within the Docker container.

### Live Endpoint Verification
- Started the `meta_hack-env` Docker container and ran a live `test_live.py` validation script.
- **Single-Agent Backward Compatibility**: Verified `easy` and `hard` tasks complete properly.
- **Hierarchy Easy Flow**: Verified `L1 respond` → `L2 approve` → `L1 close` → `L2 approve`.
- **Hierarchy Hard Flow**: Verified `L1 respond` → `L2 escalate` → `L3 resolve`.
- **Role Rewards Verification**: Confirmed JSON output parses correct dense role-rewards (e.g., `{'support_agent': 0.425, 'supervisor': 0.725, 'manager': 0.65}`).

## 5. Next Steps

With the environment, endpoints, and inference architecture fully deployed and validated on the `feat/round2` branch, the final step for Hackathon readiness is:

1. **Training Pipeline**: Develop the `train_grpo.py` script utilizing Unsloth / TRL to consume the new `role_rewards` dictionaries and fine-tune models to operate efficiently within this hierarchical structure.
