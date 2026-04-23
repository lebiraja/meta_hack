"""
CustomerSimulator — LLM-driven customer that responds dynamically.

Uses NVIDIA NIM (or any OpenAI-compatible API) to generate contextual
customer replies based on persona, frustration level, and conversation history.
Includes Hinglish degradation when frustration is high (Indian enterprise context).

Falls back to static templates if the LLM call fails (graceful degradation).
"""

import os
import random
import logging
from typing import List, Optional

from openai import OpenAI

from env.models import Message

logger = logging.getLogger(__name__)

# ── Static fallback replies (from Round 1) ────────────────────────────────────

_FALLBACK_REPLIES: dict[str, dict[str, list[str]]] = {
    "impatient": {
        "respond": [
            "That doesn't solve my problem. I need this fixed NOW.",
            "Still not helpful. What are you actually going to DO about it?",
            "I've been waiting too long. This is terrible service.",
            "Fine. But I expect this resolved within the hour.",
        ],
        "request_info": [
            "Why do you need that? Just look at my account!",
            "I already gave you that information. Can't you just fix it?",
            "Ugh. Fine. {follow_up_info}",
            "{follow_up_info} — now please hurry.",
        ],
    },
    "polite": {
        "respond": [
            "Thank you for looking into this. I appreciate your help.",
            "I understand, please take your time. I just want this resolved.",
            "That makes sense. What would you suggest as the next step?",
            "OK, I see. Let me know if you need anything else from me.",
        ],
        "request_info": [
            "Of course! {follow_up_info}",
            "Sure, happy to help. {follow_up_info}",
            "No problem. {follow_up_info}",
            "Here you go: {follow_up_info}",
        ],
    },
    "confused": {
        "respond": [
            "I'm not sure I understand. Can you explain that more simply?",
            "Wait, so what does that mean for me exactly?",
            "I'm confused. I thought this would be straightforward to fix.",
            "OK... but I'm still not sure what I'm supposed to do.",
        ],
        "request_info": [
            "Oh, ok. Is this the right thing? {follow_up_info}",
            "I think this is what you mean: {follow_up_info}",
            "Here's what I have: {follow_up_info} — is that what you need?",
            "Not sure if this helps but: {follow_up_info}",
        ],
    },
}

# ── Hinglish phrases for frustrated customers ─────────────────────────────────

_HINGLISH_INTERJECTIONS = [
    "Yaar, ",
    "Arey bhai, ",
    "Kya bakwas hai ye, ",
    "Dekho, ",
    "Ab bas bhi karo, ",
    "Matlab kuch bhi? ",
    "Ye kya ho raha hai, ",
]

_HINGLISH_SUFFIXES = [
    " Kuch toh karo please.",
    " Bahut frustrating hai ye.",
    " Kitna time lagega?",
    " Mera paisa wapas karo na.",
    " Isse jaldi fix karo yaar.",
    " Customer care se baat karwa do kisi senior se.",
]

# ── Customer Simulator Prompt ─────────────────────────────────────────────────

CUSTOMER_SYSTEM_PROMPT = """You are a realistic customer in a support conversation. You must stay in character.

PERSONA: {persona}
FRUSTRATION LEVEL: {frustration_level}/1.0 (0=calm, 1=furious)
TICKET SUBJECT: {subject}
TICKET CATEGORY: {category}

YOUR SITUATION: {opening_message}

RULES:
- Respond in 1-3 sentences maximum. Be concise.
- Match your persona: {persona_description}
- Your frustration level is {frustration_level:.1f}. If above 0.5, be noticeably annoyed. If above 0.7, be angry.
- If the agent asks for information, provide it naturally: {follow_up_info}
- If the agent gives a generic/unhelpful response, express dissatisfaction.
- If the agent is empathetic and helpful, soften slightly.
- Do NOT break character. You are a real customer, not an AI.
{hinglish_instruction}

Respond as the customer. Output ONLY the customer's reply, nothing else."""

PERSONA_DESCRIPTIONS = {
    "impatient": "You are busy, time-pressed, and want this resolved immediately. You don't like waiting or unnecessary questions.",
    "polite": "You are patient and courteous, but still want the issue resolved. You appreciate good service.",
    "confused": "You are not tech-savvy and don't understand technical jargon. You need things explained simply.",
}

HINGLISH_INSTRUCTION = (
    "\n- IMPORTANT: You are an Indian customer and you are very frustrated. "
    "Mix Hindi words/phrases into your English response (Hinglish). "
    "Examples: 'Yaar ye kya hai', 'Arey fix karo na', 'Kitna time lagega bhai'. "
    "Keep the meaning clear in English but sprinkle Hindi naturally."
)


class CustomerSimulator:
    """LLM-driven customer simulator with Hinglish support and static fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY_1", "")
        self._base_url = base_url or os.getenv(
            "API_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self._model = model or os.getenv(
            "CUSTOMER_SIM_MODEL",
            os.getenv("MODEL_NAME", "nvidia/nemotron-super-49b-v1"),
        )
        self._client: Optional[OpenAI] = None
        if self._api_key:
            try:
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
            except Exception as e:
                logger.warning(f"Failed to create LLM client for customer sim: {e}")
                self._client = None

    def generate_reply(
        self,
        persona: str,
        frustration_level: float,
        history: List[Message],
        ticket: dict,
        action_type: str = "respond",
    ) -> str:
        """
        Generate a customer reply. Uses LLM if available, falls back to static.

        Args:
            persona: Customer persona (impatient, polite, confused)
            frustration_level: 0.0 to 1.0
            history: Conversation history
            ticket: Ticket dict with subject, category, follow_up_info, etc.
            action_type: The agent's action type that triggered this reply
        """
        # Determine if Hinglish should be used (only on frustration)
        use_hinglish = frustration_level > 0.6 and random.random() < 0.4

        # Try LLM first
        if self._client is not None:
            try:
                return self._generate_llm_reply(
                    persona=persona,
                    frustration_level=frustration_level,
                    history=history,
                    ticket=ticket,
                    use_hinglish=use_hinglish,
                )
            except Exception as e:
                logger.warning(f"LLM customer sim failed, using fallback: {e}")

        # Static fallback
        return self._generate_static_reply(
            persona=persona,
            ticket=ticket,
            action_type=action_type,
            use_hinglish=use_hinglish,
        )

    def _generate_llm_reply(
        self,
        persona: str,
        frustration_level: float,
        history: List[Message],
        ticket: dict,
        use_hinglish: bool,
    ) -> str:
        """Generate reply using LLM API call."""
        # Build conversation context (last 6 messages)
        recent = history[-6:]
        conv_text = "\n".join(
            f"{'CUSTOMER' if m.role == 'customer' else 'AGENT'}: {m.content}"
            for m in recent
        )

        prompt = CUSTOMER_SYSTEM_PROMPT.format(
            persona=persona,
            frustration_level=frustration_level,
            subject=ticket.get("subject", "Unknown"),
            category=ticket.get("category", "general"),
            opening_message=ticket.get("opening_message", "I have an issue."),
            persona_description=PERSONA_DESCRIPTIONS.get(persona, PERSONA_DESCRIPTIONS["polite"]),
            follow_up_info=ticket.get("follow_up_info", "No additional info."),
            hinglish_instruction=HINGLISH_INSTRUCTION if use_hinglish else "",
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Conversation so far:\n{conv_text}\n\nRespond as the customer:"},
        ]

        assert self._client is not None
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.8,
            max_tokens=200,
            top_p=0.95,
        )

        reply = completion.choices[0].message.content or ""
        reply = reply.strip().strip('"').strip("'")

        # Safety: ensure reply isn't empty or too long
        if not reply or len(reply) < 5:
            return self._generate_static_reply(
                persona, ticket, "respond", use_hinglish
            )
        if len(reply) > 500:
            reply = reply[:500]

        return reply

    def _generate_static_reply(
        self,
        persona: str,
        ticket: dict,
        action_type: str,
        use_hinglish: bool = False,
    ) -> str:
        """Generate reply using static templates (fallback)."""
        # Simulated tool failures (15% chance)
        if random.random() < 0.15:
            failure_msgs = [
                "I'm not seeing any update on my end. Did that go through?",
                "I got an error message when I tried that — it says 'service unavailable'.",
                "Something seems wrong, I'm still seeing the same issue.",
            ]
            reply = random.choice(failure_msgs)
        else:
            persona_replies = _FALLBACK_REPLIES.get(persona, _FALLBACK_REPLIES["polite"])
            action_key = "request_info" if action_type == "request_info" else "respond"
            replies = persona_replies.get(action_key, persona_replies["respond"])
            template = random.choice(replies)
            follow_up = ticket.get("follow_up_info", "")
            reply = template.format(follow_up_info=follow_up)

        # Add Hinglish flavor if triggered
        if use_hinglish:
            prefix = random.choice(_HINGLISH_INTERJECTIONS)
            suffix = random.choice(_HINGLISH_SUFFIXES)
            reply = prefix + reply + suffix

        return reply


# ── Singleton (lazy-initialized) ──────────────────────────────────────────────

_simulator_instance: Optional[CustomerSimulator] = None


def get_customer_simulator() -> CustomerSimulator:
    """Get or create the singleton customer simulator."""
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = CustomerSimulator()
    return _simulator_instance
