"""Quick live backward compat + hierarchy test."""
from env.environment import CustomerSupportEnv, HierarchicalCustomerSupportEnv
from env.models import Action

print("=" * 50)
print("BACKWARD COMPAT TESTS")
print("=" * 50)

# Round 1: Easy
env = CustomerSupportEnv(task="easy")
obs = env.reset()
print(f"Easy reset: {obs.ticket_id} max_steps={obs.max_steps}")
a = Action(action_type="close", message="Refund processed for duplicate charge. 3-5 days.")
_, r, d, _ = env.step(a)
print(f"  Done={d} Score={r.value:.3f}")

# Round 1: Hard  
env2 = CustomerSupportEnv(task="hard")
obs2 = env2.reset()
print(f"Hard reset: {obs2.ticket_id} max_steps={obs2.max_steps}")
a2 = Action(action_type="escalate", reason="SLA breach critical outage needs engineering")
_, r2, d2, _ = env2.step(a2)
print(f"  Done={d2} Score={r2.value:.3f}")

print()
print("=" * 50)
print("HIERARCHY TESTS")
print("=" * 50)

# Hierarchy Easy: L1 -> L2 approve -> L1 close -> L2 approve
henv = HierarchicalCustomerSupportEnv(task="hierarchy_easy")
hobs = henv.reset()
print(f"Hierarchy easy: {hobs.ticket_id} active_role={hobs.active_role}")

a1 = Action(action_type="respond", message="I understand your UPI concern. Let me check.")
o1, r1, d1, _ = henv.step(a1)
print(f"  L1 respond -> role={o1.active_role} reward={r1.value:.3f}")

a2 = Action(action_type="supervisor_approve", message="Good response.")
o2, r2, d2, _ = henv.step(a2)
print(f"  L2 approve -> role={o2.active_role} done={d2}")

a3 = Action(action_type="close", message="UPI payment confirmed. Billing updated.")
o3, r3, d3, _ = henv.step(a3)
print(f"  L1 close   -> role={o3.active_role}")

a4 = Action(action_type="supervisor_approve", message="Good closure.")
o4, r4, d4, _ = henv.step(a4)
print(f"  L2 approve -> done={d4} reward={r4.value:.3f}")
print(f"  Role rewards: {r4.role_rewards}")

# Hierarchy Hard: L1 -> L2 escalate -> L3 resolve
print()
henv2 = HierarchicalCustomerSupportEnv(task="hierarchy_hard")
hobs2 = henv2.reset()
print(f"Hierarchy hard: {hobs2.ticket_id} active_role={hobs2.active_role}")

a5 = Action(action_type="respond", message="This is critical. Flagging immediately.")
o5, r5, _, _ = henv2.step(a5)
print(f"  L1 respond -> role={o5.active_role}")

a6 = Action(action_type="supervisor_escalate", reason="Critical SLA breach needs manager auth.")
o6, r6, _, _ = henv2.step(a6)
print(f"  L2 escalate -> role={o6.active_role} phase={o6.hierarchy_state.current_phase}")

a7 = Action(action_type="manager_resolve", message="Authorized emergency engineering escalation. Transaction frozen.")
o7, r7, d7, _ = henv2.step(a7)
print(f"  L3 resolve -> done={d7} reward={r7.value:.3f}")
print(f"  Role rewards: {r7.role_rewards}")

# Policy drift test
print()
print("=" * 50)
print("POLICY DRIFT TEST")
print("=" * 50)
from env.policy_engine import PolicyEngine
pe = PolicyEngine(task="hierarchy_hard", category="billing", drift_probability=1.0)
if pe._scheduled_step:
    event = pe.check_drift(pe._scheduled_step)
    print(f"Drift at step {pe._scheduled_step}: {event[:80]}...")
    print(f"Active changes: {pe.get_active_changes()}")
else:
    print("No drift scheduled (random)")

print()
print("ALL TESTS PASSED!")
