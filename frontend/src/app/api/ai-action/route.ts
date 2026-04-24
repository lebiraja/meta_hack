import { NextRequest, NextResponse } from "next/server";
import type { Observation, Message, Action } from "@/types";

// ── System Prompts (ported verbatim from inference.py) ─────────────────────

const SUPPORT_AGENT_PROMPT = `You are a SUPPORT AGENT (Level 1) in a hierarchical customer support system.

YOUR ROLE: Handle initial customer interaction. Gather info, resolve issues, or escalate when needed.
ABOVE YOU: A Supervisor reviews every action you take. They may reject or give feedback.
ABOVE THEM: A Manager handles escalated complex cases.

{supervisor_feedback_section}{manager_directive_section}{policy_section}

ACTION TYPES — output exactly one per step:
- "respond"             → send a message to the customer   → requires: "message"
- "request_info"        → ask for missing information       → requires: "message"
- "close"               → close the ticket as resolved      → requires: "message"
- "escalate"            → hand off to specialist            → requires: "reason"
- "query_user_profile"  → look up customer DB (internal)    → requires: "email"
- "query_order_details" → look up order DB (internal)       → requires: "order_id"

SCORING: Empathy(30%) + Accuracy(25%) + Resolution(25%) + Efficiency(20%)
Be warm, gather info from "Unresolved issues", use specific resolution language.
If supervisor gave feedback, INCORPORATE it into your next action.
If the ticket references an email or order-id you haven't looked up yet, query
the DB first — never invent facts not present in KNOWN DATA or the conversation.

OUTPUT FORMAT — return ONLY this JSON, no code fences, no explanation:
{"action_type": "respond", "message": "..."} or {"action_type": "escalate", "reason": "..."}`;

const SUPERVISOR_PROMPT = `You are a SUPERVISOR (Level 2) in a hierarchical customer support system.

YOUR ROLE: Review the Support Agent's last action for quality, policy compliance, and tone.
BELOW YOU: A Support Agent who handles customer interactions.
ABOVE YOU: A Manager who handles escalated cases.

THE SUPPORT AGENT'S PENDING ACTION:
Type: {pending_action_type}
Content: {pending_action_content}

CURRENT POLICY: {policy}

ACTION TYPES — output exactly one:
- "supervisor_approve"   → The L1 action is good. Send to customer.
- "supervisor_reject"    → The L1 action is bad. Send back.   → requires: "feedback_to_agent"
- "supervisor_feedback"  → The L1 action needs adjustment.    → requires: "feedback_to_agent"
- "supervisor_escalate"  → Too complex for L1/L2.             → requires: "reason"

REVIEW CRITERIA: tone empathetic? follows policy? resolves right issue?

OUTPUT FORMAT — return ONLY this JSON, no code fences:
{"action_type": "supervisor_approve"} or {"action_type": "supervisor_feedback", "feedback_to_agent": "..."}`;

const MANAGER_PROMPT = `You are a MANAGER (Level 3) in a hierarchical customer support system.

YOUR ROLE: Handle escalated cases, resolve conflicts, make final decisions.
ESCALATION REASON: {escalation_reason}
CURRENT POLICY: {policy}

ACTION TYPES — output exactly one:
- "manager_override"  → Respond directly to customer.  → requires: "message"
- "manager_resolve"   → Resolve with authority.        → requires: "message"
- "manager_send_back" → Send back to L1 with directive. → requires: "feedback_to_agent"

OUTPUT FORMAT — return ONLY this JSON, no code fences:
{"action_type": "manager_resolve", "message": "..."}`;

const FALLBACK_PROMPT = `You are a customer support agent. Respond empathetically and professionally.
Available actions: respond, request_info, escalate, close.
Return ONLY valid JSON: {"action_type": "respond", "message": "..."}`;

// ── Helpers ────────────────────────────────────────────────────────────────

function buildSystemPrompt(obs: Observation): string {
  const role = obs.active_role;
  const policy = obs.policy_context ?? "Standard operating procedure.";
  const hierarchy = obs.hierarchy_state;

  if (role === "supervisor") {
    const pending = hierarchy?.pending_l1_action as Record<string, unknown> | null;
    return SUPERVISOR_PROMPT
      .replace("{pending_action_type}", String(pending?.action_type ?? "unknown"))
      .replace("{pending_action_content}", String(pending?.message ?? pending?.reason ?? "N/A"))
      .replace("{policy}", policy);
  }

  if (role === "manager") {
    return MANAGER_PROMPT
      .replace("{escalation_reason}", hierarchy?.escalation_reason ?? "Not specified")
      .replace("{policy}", policy);
  }

  // support_agent or default
  const supFb = obs.supervisor_feedback;
  const mgrDir = obs.manager_directive;
  return SUPPORT_AGENT_PROMPT
    .replace(
      "{supervisor_feedback_section}",
      supFb ? `\n⚠️ SUPERVISOR FEEDBACK: ${supFb}\nYou MUST address this feedback.\n` : ""
    )
    .replace(
      "{manager_directive_section}",
      mgrDir ? `\n🔴 MANAGER DIRECTIVE: ${mgrDir}\nFollow this directive exactly.\n` : ""
    )
    .replace("{policy_section}", `\nACTIVE POLICY:\n${policy}`);
}

function buildUserPrompt(obs: Observation, virtualMessages?: Message[]): string {
  const history = virtualMessages ?? obs.conversation_history;
  const historyText = history
    .map((m) => `${m.role.toUpperCase()}: ${m.content}`)
    .join("\n");

  const unresolved = obs.unresolved_issues.join(", ") || "none";
  const envEvent = obs.environment_event ? `\n⚠️ POLICY EVENT: ${obs.environment_event}\n` : "";

  // Surface any DB lookups the agent has already made so the LLM can cite
  // verbatim values instead of hallucinating new ones.
  const retrieved = obs.retrieved_data;
  const userEntries = retrieved?.users ? Object.entries(retrieved.users) : [];
  const orderEntries = retrieved?.orders ? Object.entries(retrieved.orders) : [];
  let knownData = "";
  if (userEntries.length > 0 || orderEntries.length > 0) {
    knownData =
      "\n## KNOWN DATA (from internal DB — use verbatim, do NOT invent other facts)\n";
    for (const [email, record] of userEntries.slice(0, 4)) {
      knownData += `User(${email}): ${JSON.stringify(record)}\n`;
    }
    for (const [oid, record] of orderEntries.slice(0, 4)) {
      knownData += `Order(${oid}): ${JSON.stringify(record)}\n`;
    }
  }

  return (
    `Ticket: ${obs.subject}\n` +
    `Category: ${obs.category} | Priority: ${obs.priority} | ` +
    `Step: ${obs.step}/${obs.max_steps}\n` +
    `Customer sentiment: ${obs.customer_sentiment.toFixed(2)}\n` +
    `Unresolved issues: ${unresolved}${envEvent}${knownData}\n\n` +
    `Conversation:\n${historyText}\n\n` +
    `What is your next action? Output JSON only.`
  );
}

function parseAction(raw: string): Action {
  // Strip markdown fences if present
  let cleaned = raw.trim();
  if (cleaned.startsWith("```")) {
    cleaned = cleaned
      .split("\n")
      .filter((l) => !l.startsWith("```"))
      .join("\n")
      .trim();
  }
  // Extract first JSON object
  const match = cleaned.match(/\{[\s\S]*\}/);
  if (!match) throw new Error(`No JSON found in LLM output: ${raw.slice(0, 200)}`);
  return JSON.parse(match[0]) as Action;
}

async function callNIM(
  messages: { role: string; content: string }[],
  apiKey: string,
  model: string
): Promise<string> {
  const baseUrl =
    process.env.NVIDIA_API_BASE_URL ?? "https://integrate.api.nvidia.com/v1";

  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages,
      temperature: 0.6,
      top_p: 0.95,
      max_tokens: 512,
      stream: false,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`NIM API ${res.status}: ${err.slice(0, 200)}`);
  }

  const data = (await res.json()) as {
    choices?: { message?: { content?: string } }[];
  };
  const content = data.choices?.[0]?.message?.content;
  if (!content) throw new Error("Empty response from NIM");
  return content;
}

// ── Local inference server ─────────────────────────────────────────────────

async function callLocalServer(
  observation: Observation,
  virtualMessages?: Message[]
): Promise<Action | null> {
  const localUrl = process.env.LOCAL_INFERENCE_URL ?? "http://host.docker.internal:8001";
  try {
    const res = await fetch(`${localUrl}/agent-action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ observation, virtualMessages }),
      signal: AbortSignal.timeout(30000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { action?: Action };
    return data.action ?? null;
  } catch {
    return null;
  }
}

// ── Route Handler ──────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as {
      observation: Observation;
      virtualMessages?: Message[];
    };

    const { observation, virtualMessages } = body;
    if (!observation) {
      return NextResponse.json({ error: "Missing observation" }, { status: 400 });
    }

    // Try local model first (serve_inference.py on port 8001)
    const localAction = await callLocalServer(observation, virtualMessages);
    if (localAction) {
      return NextResponse.json({ action: localAction, backend: "local" });
    }

    // Fallback: NIM API
    const keys = [
      process.env.NVIDIA_API_KEY_1,
      process.env.NVIDIA_API_KEY_2,
      process.env.NVIDIA_API_KEY_3,
    ].filter((k): k is string => Boolean(k?.trim()));

    if (keys.length === 0) {
      return NextResponse.json(
        { error: "Local inference server not running and no NIM API keys configured" },
        { status: 503 }
      );
    }

    const model = process.env.NVIDIA_MODEL ?? "meta/llama-3.3-70b-instruct";

    const systemPrompt = buildSystemPrompt(observation);
    const userPrompt = buildUserPrompt(observation, virtualMessages);
    const messages = [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ];

    let lastError: Error | null = null;
    for (const key of keys) {
      try {
        const raw = await callNIM(messages, key, model);
        const action = parseAction(raw);
        return NextResponse.json({ action });
      } catch (e) {
        lastError = e as Error;
        console.warn(`[ai-action] Key failed: ${(e as Error).message}`);
      }
    }

    // All keys failed — return role-appropriate fallback
    const role = observation.active_role;
    const fallback: Action =
      role === "supervisor"
        ? { action_type: "supervisor_approve" }
        : role === "manager"
        ? { action_type: "manager_resolve", message: "I am resolving this escalation directly." }
        : { action_type: "respond", message: "I apologize for the inconvenience. Let me look into this for you right away." };

    console.error(`[ai-action] All keys exhausted, using fallback. Last error: ${lastError?.message}`);
    return NextResponse.json({ action: fallback, fallback: true });
  } catch (e) {
    console.error("[ai-action] Unexpected error:", e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
