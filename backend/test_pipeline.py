"""Test the full async background-removal pipeline."""
import requests
import time
import sys

BASE = "http://localhost:8001"

# 1. Submit async task
print("=== Submitting async task ===")
with open("test_image.jpg", "rb") as f:
    resp = requests.post(f"{BASE}/api/remove-bg", files={"file": ("test.jpg", f, "image/jpeg")})
print(f"Submit: {resp.status_code}")
data = resp.json()
print(f"Response: {data}")
task_id = data["task_id"]

# 2. Poll for completion
print("\n=== Polling for completion ===")
while True:
    status = requests.get(f"{BASE}/api/task/{task_id}").json()
    pct = status["progress"] * 100
    print(f"  Status: {status['status']} - {status['stage']} ({pct:.0f}%)")
    if status["status"] in ("done", "error"):
        break
    time.sleep(0.5)

# 3. Download result
if status["status"] == "done":
    print("\n=== Downloading result ===")
    result = requests.get(f"{BASE}/api/task/{task_id}/result")
    with open("test_result.png", "wb") as f:
        f.write(result.content)
    print(f"Result saved: {len(result.content)} bytes -> test_result.png")
else:
    print(f"\nError: {status.get('error')}")
    sys.exit(1)
