# GridWise

GridWise is the BUP CSE Fest 2026 preliminary-round API for a minimum-cost,
24-hour campus energy schedule. A live NVIDIA model converts each operator note
into one of the six allowed directive types. Deterministic code validates those
directives, compiles constraints, solves the full-day linear program with SciPy
HiGHS, and replays the serialized plan before returning it.

Public service: `https://bup-hackaton.onrender.com`

## Processing pipeline

```text
POST /optimize-energy
  -> strict request validation (HTTP 400 on invalid input)
  -> NVIDIA NIM interpretation (at most two calls in one deadline)
  -> exact directive-shape and range guardrails
  -> hourly constraint compilation
  -> SciPy HiGHS cost minimization
  -> six-decimal plan serialization
  -> independent physics, directive, neutrality, and aggregate replay
  -> contest response (HTTP 200)
```

The optimizer uses a signed battery movement for each hour: positive means
charge and negative means discharge. It enforces demand balance, available
solar, battery capacity and rates, active reserve/grid/window directives, and
the final battery energy equal to the initial energy. Grid export, battery
losses, and battery degradation costs are outside the supplied model.

## Configuration

Copy `.env.example` to `.env` and add a fresh NVIDIA key. `.env` files are
excluded from Git and Docker build context.

| Variable | Required | Default |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | empty |
| `NVIDIA_MODEL` | No | `meta/llama-3.2-11b-vision-instruct` |
| `NVIDIA_API_URL` | No | NVIDIA chat-completions endpoint |
| `LLM_TIMEOUT_SECONDS` | No | `22` |
| `TOTAL_REQUEST_DEADLINE_SECONDS` | No | `27` |
| `HOST` | No | `0.0.0.0` |
| `PORT` | No | `8000` |

PowerShell configuration:

```powershell
Copy-Item .env.example .env
$env:NVIDIA_API_KEY = "your-nvapi-key"
```

Linux/macOS configuration:

```bash
cp .env.example .env
export NVIDIA_API_KEY="your-nvapi-key"
```

## Run locally

Python 3.13 is used by the Docker image and was used for the recorded local
verification.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For Linux/macOS, activate with `source .venv/bin/activate`; the remaining
commands are the same.

`GET /health` returns `200 {"status":"ok"}` only when the model key is
configured. It returns HTTP 503 when the service cannot accept live work.

```bash
curl --fail http://localhost:8000/health
```

Create a request file from the first official public case and call the endpoint:

```powershell
python -c "import json,pathlib; p=next(pathlib.Path('.').glob('*Public_Sample_Cases*.json')); d=json.loads(p.read_text(encoding='utf-8-sig')); pathlib.Path('sample-request.json').write_text(json.dumps(d['cases'][0]['input']),encoding='utf-8')"
curl.exe -X POST http://localhost:8000/optimize-energy -H "Content-Type: application/json" --data-binary "@sample-request.json"
```

The successful response contains `scenario_id`, one
`directive_interpretation` entry per note, 24 ordered `hourly_plan` entries,
`total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, and `plan_summary`.
Malformed requests return HTTP 400. Provider, infeasibility, or internal replay
failures return a sanitized HTTP 500 response.

## Verification

Run deterministic tests without using provider quota:

```powershell
python -m pytest -m "not live" -q
python tools/run_public_cases.py --offline
python tools/check_nvidia_model.py --offline
python -m pip check
```

Run the marked live tests and both full public-case paths with a configured key:

```powershell
python -m pytest -m live -q
python tools/check_nvidia_model.py --timeout 27
python tools/run_public_cases.py --timeout 27
```

Benchmark a running HTTP service. The benchmark validates the response schema,
directive semantics, organizer-reference constraints, physics replay,
aggregates, and expected cost for every successful call.

```powershell
python tools/benchmark_api.py --url http://localhost:8000 --iterations 3
```

Recorded on 18 September 2026 with the configured NVIDIA model:

- 78/78 pytest cases passed: 67 deterministic and 11 live integration/paraphrase cases.
- Offline optimizer/replay: 10/10 public cases, zero cost delta.
- Live production interpreter: 10/10 directive semantics; p95 12.81 seconds.
- Live full pipeline: 10/10 valid schedules and costs; p50 6.43 seconds,
  p95/max 13.31 seconds.
- `pip check` reported no broken requirements; `compileall` passed.

Provider latency varies, so these measurements are evidence from one run rather
than a guaranteed service level. The application limits one interpretation to
two provider calls and a configurable overall budget below the contest's
30-second request limit.

## Docker

Build and run the same service locally:

```bash
docker build -t gridwise:latest .
docker run --rm -p 8000:8000 \
  -e NVIDIA_API_KEY="your-nvapi-key" \
  -e NVIDIA_MODEL="meta/llama-3.2-11b-vision-instruct" \
  gridwise:latest
```

The image binds to `0.0.0.0`, exposes port 8000, runs as a non-root user, and
has a `/health` healthcheck. A registry image reference is still pending; do
not treat the local tag as a pullable contest artifact. Docker was not available
on the verification workstation, so the Dockerfile still needs a clean external
build-and-run check.

## Known boundaries

- The live provider remains an external dependency; quota, regional outages,
  and latency can cause sanitized HTTP 500 responses.
- The public specification does not define how two overlapping solar-reduction
  notes combine. This implementation uses the most restrictive remaining
  factor for an overlapping hour.
- Overnight natural-language windows are not normalized across midnight unless
  they are expressed as separate same-day windows. The published examples are
  start-inclusive and end-exclusive within one day.
- The service models a lossless battery and no grid export, matching the supplied
  preliminary problem statement.

## Delivery status

The source and Render service exist. The required pullable registry image,
organizer-accessible video of at most three minutes, submission receipt, and
post-deadline repository visibility change still require external accounts or
manual contest actions. Exact status and evidence are tracked in
`PROJECT_CONTROL.md`.

## Credits

- FastAPI and Uvicorn: HTTP service
- Pydantic: strict request and response models
- SciPy HiGHS: continuous linear programming
- NVIDIA NIM: mandatory language-model interpretation
- Requests: provider and verification HTTP clients
- pytest: automated verification
