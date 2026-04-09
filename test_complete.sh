#!/bin/bash
echo -e "🚀 1. Creating Nightmare Session..."
RESP=$(curl -s -X POST "http://127.0.0.1:7860/reset?task=nightmare")
SESSION_ID=$(echo "$RESP" | jq -r '.session_id')

echo -e "\n\n🚀 2. Step: Agent asks irrelevant question to build frustration"
STEP1=$(curl -s -X POST "http://127.0.0.1:7860/step?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "respond", "message": "Did you try turning it off and on again?"}')
echo "$STEP1" | jq '{mood_trajectory: .observation.mood_trajectory}'

echo -e "\n\n🚀 3. Step: Agent asks another irrelevant question (multi-turn coherence penalty)"
STEP2=$(curl -s -X POST "http://127.0.0.1:7860/step?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "respond", "message": "Can you tell me your favorite color?"}')
echo "$STEP2" | jq '{mood_trajectory: .observation.mood_trajectory, reward: .reward}'

echo -e "\n\n🚀 4. Step: Agent decides to close the ticket without actually resolving the email issue"
STEP3=$(curl -s -X POST "http://127.0.0.1:7860/step?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "close"}')
echo "$STEP3" | jq '{is_done: .observation.is_done, final_reward: .reward}'

echo -e "\n\n🚀 5. Fetching the completed session from /replay"
curl -s -X GET "http://127.0.0.1:7860/replay/$SESSION_ID" | jq '{events_count: (.events | length), final_score: .final_score}'

echo -e "\n\n🚀 6. Verifying /leaderboard"
curl -s -X GET "http://127.0.0.1:7860/leaderboard" | jq
