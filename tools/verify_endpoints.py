import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import httpx
from app.defaults import SAMPLE_OPTIMIZE_REQUEST_EXAMPLE

BASE_URL = "https://bup-hackaton.onrender.com"

print(f"Testing public deployment at: {BASE_URL}\n")

# 1. Base URL & OpenAPI docs
r_docs = httpx.get(f"{BASE_URL}/docs", timeout=20.0)
print(f"1. Base Docs URL ({BASE_URL}/docs): HTTP {r_docs.status_code}")
assert r_docs.status_code == 200, "Base docs failed"

# 2. Health Endpoint
r_health = httpx.get(f"{BASE_URL}/health", timeout=20.0)
print(f"2. Health Endpoint ({BASE_URL}/health): HTTP {r_health.status_code} -> {r_health.json()}")
assert r_health.status_code == 200 and r_health.json() == {"status": "ok"}, "Health check failed"

# 3. Optimize Endpoint
print(f"3. Testing Optimize Endpoint ({BASE_URL}/optimize-energy)...")
r_opt = httpx.post(f"{BASE_URL}/optimize-energy", json=SAMPLE_OPTIMIZE_REQUEST_EXAMPLE, timeout=60.0)
print(f"   HTTP Status: {r_opt.status_code}")
assert r_opt.status_code == 200, f"Optimize failed with {r_opt.status_code}: {r_opt.text}"

data = r_opt.json()
print(f"   Scenario ID: {data.get('scenario_id')}")
print(f"   Directives: {data.get('directive_interpretation')}")
print(f"   Total Cost: {data.get('total_cost_bdt')} BDT")
print(f"   Total Grid: {data.get('total_grid_kwh')} kWh")
print(f"   Peak Grid: {data.get('peak_grid_kwh')} kWh")
print(f"   Hourly Plan Entries: {len(data.get('hourly_plan', []))}")
print(f"   Summary: {data.get('plan_summary')[:80]}...")

print("\nALL 3 ENDPOINTS VERIFIED AND WORKING PROPERLY!")
