import asyncio
import httpx
import time
import statistics

BASE_URL = "http://localhost:7860"

async def test_reset(client, i):
    start = time.time()
    try:
        resp = await client.post(f"{BASE_URL}/reset?task=hard")
        return {"status": resp.status_code, "time": time.time() - start, "id": i}
    except Exception as e:
        return {"status": 0, "time": time.time() - start, "id": i, "error": str(e)}

async def heavy_load_test():
    print("🚀 Starting Heavy Concurrency Test (200 parallel resets)...")
    
    # 1. Concurrency Check
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Launch 200 requests instantly
        tasks = [test_reset(client, i) for i in range(200)]
        results = await asyncio.gather(*tasks)
    
    successes = [r for r in results if r["status"] == 200]
    rate_limited = [r for r in results if r["status"] == 429]
    errors = [r for r in results if r["status"] not in (200, 429)]
    times = [r["time"] for r in successes]
    
    print(f"📊 Results for 200 Resets:")
    print(f"   Successes (HTTP 200): {len(successes)}")
    print(f"   Rate Limited (HTTP 429): {len(rate_limited)} -> (Demonstrates strict IP limits work!)")
    print(f"   Errors/Crashes: {len(errors)}")
    if times:
        print(f"   Avg Latency: {(sum(times)/len(times))*1000:.2f} ms")
        print(f"   Max Latency: {max(times)*1000:.2f} ms")

    print("\n🚀 Testing Deep Session Tracking (1 full nightmare session)")
    async with httpx.AsyncClient() as client:
        # Reset specific session
        resp = await client.post(f"{BASE_URL}/reset?task=nightmare")
        if resp.status_code == 429:
             print("Skipping due to rate limit (we just hit 200!). Localhost limits protect us.")
             return
        
        session_id = resp.json()["session_id"]
        
        # Take 5 fast steps to simulate heavy compute (Semantic TF-IDF + Embeddings)
        print("   Running back-to-back rapid steps...")
        step_times = []
        for _ in range(5):
            s = time.time()
            res = await client.post(f"{BASE_URL}/step?session_id={session_id}", json={
                "action_type": "respond", "message": "Can I help you?"
            })
            step_times.append(time.time() - s)
        
        
        print(f"   5-Step Sequence complete.")
        print(f"   Avg Step Latency (including ML grading): {(sum(step_times)/5)*1000:.2f} ms")
        
        # Test state
        state_res = await client.get(f"{BASE_URL}/state/{session_id}")
        print(f"   /state length: {len(str(state_res.json()))} chars")
        
        # Close
        close_res = await client.post(f"{BASE_URL}/step?session_id={session_id}", json={"action_type": "close"})
        print(f"   Final reward processed! {close_res.json()['reward']['value']}")
        
if __name__ == "__main__":
    asyncio.run(heavy_load_test())
