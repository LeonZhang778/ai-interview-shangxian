import requests
import time
import json

BASE = "http://localhost"

# Step 1: Login as guest
print("1. Logging in as guest...")
r = requests.post(f"{BASE}/api/v1/auth/guest-login", json={})
print(f"   Status: {r.status_code}")
resp = r.json()
print(f"   Response: {json.dumps(resp, indent=2)[:300]}")

if resp.get("code") != 200:
    print("   Login failed!")
    exit(1)

token = resp["data"]["access_token"]
print(f"   Token: {token[:30]}...")

# Step 2: Submit image generation
print("\n2. Submitting image generation task...")
r = requests.post(
    f"{BASE}/api/v1/images/generate",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "prompt": "a cute cat sitting on a windowsill with sunshine",
        "width": 512,
        "height": 512,
    },
)
print(f"   Status: {r.status_code}")
resp = r.json()
print(f"   Response: {json.dumps(resp, indent=2)[:300]}")

task_id = resp.get("data", {}).get("task_id")
if not task_id:
    print("   No task_id!")
    exit(1)

print(f"   Task ID: {task_id}")

# Step 3: Poll for status
print(f"\n3. Polling task {task_id}...")
for i in range(30):
    time.sleep(5)
    r = requests.get(
        f"{BASE}/api/v1/images/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json().get("data", {})
    status = data.get("status")
    image_url = data.get("image_url")
    error = data.get("error_message")
    print(f"   Poll {i+1}: status={status}, image_url={image_url}, error={error}")
    if status in ("success", "failed"):
        break

if status == "success":
    print(f"\n4. SUCCESS! Image URL: {image_url}")
    # Verify image is accessible
    r = requests.get(f"http://8.166.120.119{image_url}")
    print(f"   Image accessible: {r.status_code}, Content-Type: {r.headers.get('content-type')}, Size: {len(r.content)} bytes")
elif status == "failed":
    print(f"\n4. FAILED: {error}")
else:
    print(f"\n4. TIMEOUT: still {status} after 150s")
