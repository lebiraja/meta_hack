#!/bin/bash
echo "Waiting for healthcheck..."
until curl -s http://127.0.0.1:7860/health | grep -q '"status":"ok"'; do sleep 2; done

echo -e "\n\n🚀 1. Starting 'Nightmare' Task Session..."
RESP=$(curl -s -X POST "http://127.0.0.1:7860/reset?task=nightmare")
SESSION_ID=$(echo "$RESP" | jq -r '.session_id')
echo "Created Session ID: $SESSION_ID"
echo "Initial State (Priorities):"
echo "$RESP" | jq '.observation.priority, .observation.subject, .observation.mood_trajectory'

echo -e "\n\n🚀 2. Taking Step 1 (Triggering Frustration & Mood Trajectory)..."
# The customer is locked out and sees unauthorized charges.
# The agent gives a very lazy response to trigger a negative VADER sentiment change.
STEP1=$(curl -s -X POST "http://127.0.0.1:7860/step?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "respond", "message": "Have you tried turning your computer off and back on again?"}')
echo "Mood Updates:"
echo "$STEP1" | jq '{sentiment: .observation.customer_sentiment, trajectory: .observation.mood_trajectory, customer_reply: .observation.conversation_history[-1].content}'

echo -e "\n\n🚀 3. Taking Step 2 (Tool Call - Testing Semantic Resolution/Coherence Penalty...)"
STEP2=$(curl -s -X POST "http://127.0.0.1:7860/step?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "tool_call", "tool_name": "reset_password", "tool_args": {}}')
echo "Reward Values (Semantic & Multi-turn Coherence):"
echo "$STEP2" | jq '{reward: .reward, is_done: .observation.is_done, unresolved: .observation.unresolved_issues}'

echo -e "\n\n🚀 4. Checking /replay/{session_id} Endpoint..."
curl -s -X GET "http://127.0.0.1:7860/replay/$SESSION_ID" | jq '{session_id: .session_id, total_events_recorded: (.events | length)}'

echo -e "\n\n🚀 5. Testing /leaderboard API..."
curl -s -X GET "http://127.0.0.1:7860/leaderboard" | jq
