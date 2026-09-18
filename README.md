# GridWise - LLM-Driven Optimal 24-Hour Campus Energy Scheduler

GridWise is an automated, production-ready campus energy management system designed for the **BUP CSE Fest 2026** competition. It combines a real Large Language Model (NVIDIA NIM) for natural language operator-note interpretation with strict deterministic guardrails, SciPy HiGHS continuous linear programming, and independent physics-based schedule replay.

---

## 1. System Architecture

```text
┌────────────────────────┐
│  POST /optimize-energy │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  FastAPI Input Parser  │ ──> HTTP 400 on malformed schema / non-finite / incoherent data
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Real NVIDIA LLM NIM    │ ──> Structured operator-notes interpretation (meta/llama-3.2-11b-vision-instruct)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Deterministic Guardrail│ ──> Strict type, index, hour 0..23, factor in [0,1], reserve bounds
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Constraint Compiler   │ ──> Compiles effective solar, reserve, caps, and rate limits
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  SciPy HiGHS LP Solver │ ──> Continuous 96-variable optimization: min sum(tariff * grid)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Independent Replay    │ ──> Strict re-verification of energy balance, battery continuity, & neutrality
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Final JSON Response    │ ──> Exact contest schema with reconciled aggregates & factual summary
└────────────────────────┘
```

### Key Highlights
- **Mandatory Real LLM Path:** Every operator note is parsed through NVIDIA NIM with temperature 0. A 1-shot repair loop guarantees resilience without falling back to regex or mock bypasses.
- **Deterministic Guardrails:** Rejects unsupported directives, improper hour bounds, out-of-range factors/reserves, or boolean coercion.
- **Single-Action HiGHS Linear Program:** Solves optimal battery dispatch via continuous signed variable $B[h]$ (positive = charge, negative = discharge) across 24 hours (96 variables), enforcing exact terminal neutrality ($E[23] = E_{\text{initial}}$) with no binary variable overhead.
- **Independent Schedule Replay:** Every schedule is mathematically validated before leaving the service, checking continuity, capacity, caps, and energy balance.
- **Strict Error Handling:** Follows contest rules with HTTP 400 for structural/schema errors, HTTP 200 for successful schedules, and sanitized HTTP 500 for internal/provider errors without credential leakage.

---

## 2. Environment Configuration

GridWise uses environment variables for configuration. Create a local `.env` file for development (do not commit secrets):

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `NVIDIA_API_KEY` | Yes (for live LLM) | `""` | API key from NVIDIA NIM |
| `NVIDIA_MODEL` | No | `meta/llama-3.2-11b-vision-instruct` | LLM model identifier |
| `NVIDIA_API_URL` | No | `https://integrate.api.nvidia.com/v1/chat/completions` | Provider completions URL |
| `LLM_TIMEOUT_SECONDS` | No | `22.0` | Socket timeout for model requests |
| `TOTAL_REQUEST_DEADLINE_SECONDS` | No | `27.0` | Total request timeout (under 30s contest limit) |
| `PORT` | No | `8000` | Port to bind server |
| `HOST` | No | `0.0.0.0` | Host binding interface |

---

## 3. Quickstart & Local Setup

### Prerequisites
- Python 3.11+ (Tested on Python 3.13)
- Git

### Installation

```bash
# 1. Create and activate virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Configure API Key
# Either in .env or via terminal:
export NVIDIA_API_KEY="your-nvapi-key"
```

### Running the API Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Health Check

```bash
curl -X GET http://localhost:8000/health
# Response: {"status": "ok"}
```

---

## 4. Testing & Verification

### Running Automated Test Suite
GridWise includes a comprehensive test suite covering API contracts, guardrails, constraints, solver optimality, and replay rejection:

```bash
pytest tests/ -v
```

### Offline Optimizer & Replay Benchmark
Verifies all 10 official contest sample scenarios against organizer ground truth without calling the LLM:

```bash
python tools/run_public_cases.py --offline
```

### End-to-End Live LLM Regression
Runs all 10 official cases through the live NVIDIA model, deterministic guardrails, HiGHS optimizer, and independent replay:

```bash
python tools/run_public_cases.py
```

### Performance & Latency Benchmark
Measures p50/p95 latency and reliability across repeated scenario requests:

```bash
python tools/benchmark_api.py --url http://localhost:8000 --iterations 3
```

---

## 5. Docker Deployment

### Build Docker Image

```bash
docker build -t gridwise:latest .
```

### Run Container Locally

```bash
docker run -d \
  -p 8000:8000 \
  -e NVIDIA_API_KEY="your-nvapi-key" \
  -e NVIDIA_MODEL="meta/llama-3.2-11b-vision-instruct" \
  --name gridwise-service \
  gridwise:latest
```

Test container health:
```bash
curl http://localhost:8000/health
```

---

## 6. Contest Compliance & Verification Evidence

| Requirement | Implementation & Verification Evidence |
|---|---|
| **FR-01: Exact API Contract** | Strict Pydantic models in `app/schemas.py`, tested in `tests/test_contract.py` |
| **FR-02: Mandatory Real LLM** | Live adapter in `app/interpreter.py` calling NVIDIA NIM |
| **FR-03: Six Directive Types** | Verified on public pack & paraphrases in `tests/fixtures/paraphrases.json` |
| **FR-04: Deterministic Guardrails** | Strict validation in `app/guardrails.py`, 15 unit tests in `tests/test_guardrails.py` |
| **FR-05: Effective Constraints** | Compiled in `app/constraints.py`, tested in `tests/test_constraints.py` |
| **FR-06: HiGHS Cost Minimization** | Continuous linear program in `app/optimizer.py`, 10/10 cases match reference within 0.01 BDT |
| **FR-07: Exact Replay Validator** | Independent physics verification in `app/replay.py`, tested in `tests/test_replay.py` |
| **FR-08: Factual Plan Summary** | Summary generation in `app/response.py` based on real dispatch statistics |
| **FR-09: Safe Error Handling** | Sanitized HTTP 400/500 responses without secret leaks in `app/main.py` |
| **NFR-01/02: Latency & Reliability**| Average response time < 5s (p95 <= 5s full-credit target); deadline enforced < 27s |
| **NFR-03: Zero Secret Leakage** | All keys injected via environment; `.dockerignore` and `.gitignore` verified |

---

## 7. Video Walkthrough Script (3:00 max)

- **0:00 - 0:30 (Problem & Overview):** The challenge of campus microgrid dispatch with variable tariffs, solar forecasts, and unpredictable operator directives.
- **0:30 - 1:15 (Architecture):** Demonstration of the pipeline: FastAPI -> NVIDIA NIM structured interpretation -> Deterministic guardrails -> Pure constraint compilation.
- **1:15 - 2:00 (Optimization & Replay):** Formulating the 24-hour continuous LP with SciPy HiGHS; single-action signed battery variable $B[h]$; independent replay validation.
- **2:00 - 2:35 (Live Demonstration):** Submitting a live request via cURL/HTTP, observing under-5-second response, exact schema output, and 0.00 BDT cost delta against reference.
- **2:35 - 3:00 (Delivery & Reproducibility):** Docker container execution, test suite passing 100%, repository structure.

---

## 8. Third-Party Credits & Libraries

- [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/) for asynchronous HTTP services.
- [Pydantic](https://docs.pydantic.dev/) for strict data schema validation.
- [SciPy](https://scipy.org/) for the high-performance HiGHS linear programming solver.
- [NVIDIA NIM](https://build.nvidia.com/) for Llama 3.2 Vision Instruct LLM inference.
- [pytest](https://docs.pytest.org/) for automated unit and regression testing.
