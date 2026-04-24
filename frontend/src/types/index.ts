export type TaskName =
  | "easy"
  | "medium"
  | "hard"
  | "nightmare"
  | "hierarchy_easy"
  | "hierarchy_medium"
  | "hierarchy_hard"
  | "curriculum_basic"
  | "curriculum_supervisor"
  | "curriculum_full_hierarchy"
  | "curriculum_nightmare";

export type ActionType =
  | "respond"
  | "escalate"
  | "close"
  | "request_info"
  | "supervisor_approve"
  | "supervisor_reject"
  | "supervisor_feedback"
  | "supervisor_escalate"
  | "manager_override"
  | "manager_resolve"
  | "manager_send_back";

export type AgentRole = "support_agent" | "supervisor" | "manager";

export type Priority = "low" | "medium" | "high" | "critical";

export type MessageRole = "customer" | "agent" | "supervisor" | "manager" | "system";

export interface Message {
  role: MessageRole;
  content: string;
}

export interface HierarchyState {
  support_agent_actions: number;
  supervisor_reviews: number;
  manager_interventions: number;
  current_phase: string;
  escalation_reason: string | null;
  supervisor_feedback_history: string[];
  manager_directive_history: string[];
  pending_l1_action: Record<string, unknown> | null;
}

export interface Observation {
  session_id: string;
  ticket_id: string;
  category: string;
  priority: Priority;
  subject: string;
  conversation_history: Message[];
  step: number;
  max_steps: number;
  customer_sentiment: number;
  mood_trajectory: number[];
  unresolved_issues: string[];
  is_done: boolean;
  task: string;
  active_role: string;
  supervisor_feedback: string | null;
  manager_directive: string | null;
  hierarchy_state: HierarchyState | null;
  environment_event: string | null;
  policy_context: string;
  escalation_chain: string[];
}

export interface Reward {
  value: number;
  resolution_score: number;
  tone_score: number;
  efficiency_score: number;
  accuracy_score: number;
  breakdown: Record<string, number>;
  empathy_score: number;
  oversight_score: number;
  decision_quality_score: number;
  policy_adherence_score: number;
  role_rewards: Record<string, number>;
}

export interface Action {
  action_type: ActionType;
  message?: string | null;
  reason?: string | null;
  role?: AgentRole;
  internal_note?: string | null;
  feedback_to_agent?: string | null;
}

export interface ActionLogEntry {
  step: number;
  role?: string;
  action_type: string;
  message?: string;
  reason?: string;
  feedback?: string;
  reward: number;
}

export interface StepResponse {
  observation: Observation;
  reward: Reward;
  done: boolean;
  info: { ticket_id: string; action_log: ActionLogEntry[]; error: null };
  final_score?: number;
}

export interface ResetResponse {
  session_id: string;
  observation: Observation;
}

export interface LeaderboardEntry {
  agent_name: string;
  task_level: string;
  total_score: number;
  steps_taken: number;
}

export interface ChatResponse {
  agent_reply: string;
  action_type: ActionType;
  active_role: AgentRole;
  reward: number;
  step: number;
  max_steps: number;
  done: boolean;
  customer_sentiment: number;
  unresolved_issues: string[];
  environment_event: string | null;
  final_score: number | null;
}
