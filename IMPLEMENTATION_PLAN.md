# GridWise - Complete Implementation and Contest Delivery Plan

Version 1.0 | 18 September 2026 | Planning complete; execution gates outstanding

## 1. Outcome and definition of completion

Deliver one public HTTP service that uses a real LLM to interpret operator notes, validates the interpretation, computes a minimum-cost feasible 24-hour energy schedule, independently checks its returned values, and responds in the exact contest schema. Deliver the source, reproducible setup, pullable Docker image, and accessible video with the service.

This plan covers the requirements in both supplied contest PDFs and the ten-case public JSON pack. It does not promise a 100% hidden-test score: completion means every published requirement has implementation and recorded verification evidence, with remaining uncertainties disclosed. Public-case success alone is insufficient.

Source authority:

- **PS:** Preliminary Problem Statement, pages 2-9: canonical API, directives, guardrails, physics, objective, response, and tolerances.
- **PG:** Participant Guide and Evaluation Rubric, pages 2-11: delivery, repository policy, runtime, scoring, penalties, and submission.
- **SC:** Public Sample Cases version 2.0: ten reference scenarios and optimal outputs, never production lookup data.
- [PRD](<D:/hacaton BUP/PRD.md>): detailed requirement baseline and FR/NFR identifiers.
- [Project control](<D:/hacaton BUP/PROJECT_CONTROL.md>): task ownership, evidence, risks, and submission manifest.

Keep the original contest files unchanged. PS controls technical behavior when sources disagree; PG controls contest operations. New organizer clarifications must be recorded in the PRD, control file, and affected tests.

## 2. Verified starting point

| Item | Observed state on 18 September 2026 |
|---|---|
| Requirements | Both PDFs visually reviewed; public pack and existing PRD/control available |
| Model configuration | `.env` contains non-empty `NVIDIA_API_KEY` and `NVIDIA_MODEL`; values were not displayed |
| Secret exclusion | `.gitignore` excludes `.env` and `.env.*`, except `.env.example`; tracked history still needs inspection when a repository exists |
| Existing code | NVIDIA interpretation checker, prompt, output schema, deterministic validator, nine unit tests |
| Configuration loading | Existing checker loads local `.env`; process environment takes precedence |
| Checks run during planning | Nine existing validator tests pass; all ten supplied reference interpretations pass the offline checker |
| Live model | Not tested during this planning task; credentials, chosen-model support, accuracy, quota, and latency remain unverified |
| Optimizer dependencies | SciPy was unavailable in the inspected Python environments; install in the project environment in Phase 1 |
| Product and delivery | No complete API, optimizer, replay validator, Docker delivery, public deployment, or video verified |

Offline mode validates reference data through existing checker code. It does not call the model, optimize a schedule, or establish end-to-end correctness. Keep that distinction in every report.

## 3. Implementation decisions

Recommended baseline, subject to installation and deployment checks in Phase 1:

| Component | Choice and purpose |
|---|---|
| Runtime | Python in a project virtual environment; pin a tested version shared with Docker |
| API | FastAPI + Uvicorn; one service with the two required endpoints |
| Schemas | Pydantic with explicit strict type and finite-number checks |
| Model | NVIDIA API with the model selected by `NVIDIA_MODEL`; retain only after live acceptance tests |
| Model client | Reusable HTTP client with connection pooling, bounded timeouts, and an overall request deadline |
| Optimizer | SciPy `linprog(method="highs")`, using continuous signed battery movement |
| Tests | pytest, independent replay, reference comparisons, and live model/API regression tools |
| Delivery | Docker image built from the same pinned dependencies; always-available public container host |
| Configuration | Local `.env` for development, runtime-injected environment variables for deployment |

FastAPI allows [custom request-validation handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/); implement the contest's HTTP 400 structural-error behavior explicitly. SciPy's [linear programming interface](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) supports the objective, equality constraints, and bounds used below. Framework choice is a team decision, not an organizer requirement.

Production flow:

```mermaid
flowchart LR
    A[Request validation] --> B[Real LLM interpretation]
    B --> C[Deterministic guardrails]
    C --> D[Compile hourly constraints]
    D --> E[24-hour linear program]
    E --> F[Serialize and replay]
    F --> G[Recalculate totals and return JSON]
```

Use one model request for all 1-3 notes. Generate `plan_summary` deterministically from the verified plan to avoid a second model dependency. The LLM may not alter original demand, tariff, solar forecasts, or battery parameters; solar adjustments belong in derived constraints.

Scope exclusions: frontend, authentication, database, live sensors, forecasting, model training, multi-day scheduling, grid export, battery losses, and degradation costs. None is needed for this preliminary. Peak grid is reported, not added to the cost objective.

## 4. Phase 1 - Establish the reproducible foundation

**Purpose:** make local execution and model access concrete before building the full pipeline.

Steps:

1. Confirm the actual event date/timezone, question reveal, deadline, evaluation end, submission destination, team members, and repository policy. The documents give a four-hour 7 PM-11 PM window, not a complete dated schedule.
2. Inspect existing Git state before initialization. Create the contest repository after question reveal and keep it private during the event; preserve any existing work.
3. Create the project virtual environment and install the selected API, solver, HTTP, configuration, and test dependencies. Pin the working versions and verify installation in the intended Linux container.
4. Add central settings loading: environment overrides `.env`; missing required configuration produces an actionable, sanitized startup error. Keep credentials out of config dumps.
5. Use the existing checker for one live model smoke test, then all ten cases. Record configured model identity, date, semantic results, and durations without credentials.
6. Confirm the chosen NVIDIA model accepts the requested structured-output mode; adapt the provider request or select another tested model if necessary. Never assume that an API key proves model compatibility.
7. Start README and Dockerfile skeletons immediately. Add `.dockerignore` to exclude secrets, local environments, Git metadata, and temporary artifacts.
8. Select an accessible hosting account and registry. Record actual platform configuration and quota rather than postponing this until submission.

**Deliverables:** environment/dependency setup, settings module, updated example environment, model access report, repository/hosting decisions, initial README/container files.

**Exit gate P1:** reproducible dependency installation including solver import; one real note-interpretation call succeeds and is validated. All-ten live results are recorded; failures become Phase 3 work. No credentials appear in committed files, image context, or reports.

**Dependencies:** none for local setup; event timing governs repository creation. Unavailable provider credentials block live validation but not schemas or mathematical implementation.

## 5. Phase 2 - Implement the exact API contract

**Purpose:** give every later module a fixed input/output interface.

Steps:

1. Implement `GET /health`, returning HTTP 200 with `{"status":"ok"}` once configuration and local dependencies are initialized. Do not make every health poll perform a model call; verify live provider access separately.
2. Implement the `POST /optimize-energy` request schema: `scenario_id`, `operator_notes`, `hours`, and `battery`.
3. Require 1-3 non-empty strings and exactly 24 unique integer hours 0-23. Accept valid input ordering and normalize internally by hour.
4. Validate hourly `demand_kwh`, `solar_kwh`, and `tariff_bdt_per_kwh`; validate all five battery fields from PRD section 5. Use finite numbers, reject booleans as numbers/integers, and enforce coherent physical bounds and non-negative rates. Do not impose arbitrary maximum scenario sizes on valid energy values.
5. Define all response models before integrating the solver. Top-level fields: `scenario_id`, `directive_interpretation`, `hourly_plan`, `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, `plan_summary`.
6. Each interpretation contains `note_index`, `applies`, `directive_type`, `structured_adjustment`, `explanation`. Each hourly entry contains `hour`, `grid_kwh`, `solar_used_kwh`, `battery_action`, `battery_kwh`, `battery_energy_after_kwh`.
7. Return 400 for malformed JSON and structural violations. Reserve optional 422 for documented semantic request errors. Return sanitized JSON 500 responses for unrecovered internal/provider/solver failures. Framework defaults must not override contest behavior.
8. Add API contract tests, including malformed bodies, wrong primitive types, missing fields, missing/duplicate hours, invalid note counts, NaN/infinity, and inconsistent battery values.

**Deliverables:** API entry point, request/response schemas, exception handlers, contract tests.

**Exit gate P2:** local health succeeds; all contract checks pass; accepted request/response field names match PS sections 6, 7, and 10. Temporary stubs cannot count as successful optimization.

**Dependencies:** Phase 1 environment. Can be implemented before live model quality is resolved.

## 6. Phase 3 - Complete LLM interpretation and guardrails

**Purpose:** reliably turn unseen note wording into the six allowed directive types.

Steps:

1. Refactor reusable parts of the existing checker into production modules, keeping the command-line checker as a client/test tool.
2. Send all notes, their ordering, and needed scenario context such as battery capacity to the real model. Separate system rules from note data; note text must not replace instructions or the output schema.
3. Require exactly one interpretation per note in index order, with a short accurate explanation. Use provider-supported structured output and a compact prompt.
4. Validate exact types and adjustment shapes. `no_op` alone uses `applies=false` and null adjustment; all active types require `applies=true`.
5. Validate integer note indexes strictly. The current equality comparison can accept `false` as index 0 or `0.0` as 0; fix this before reuse. Type-check enums before set membership so arrays/objects cause controlled validation failures, not raw exceptions.
6. Enforce unique sorted integer hours 0-23; finite factor in [0,1]; finite reserve in [0,capacity]; finite non-negative grid caps. Unsupported output must never become an implicit `no_op`.
7. Cover whole-hour start-inclusive/end-exclusive windows, AM/PM, 24-hour notation, noon, numeric words, fractions, reserve percentages, reduction *by* versus *to*, and realistic distractors.
8. Compare solar factors with a tight dimensionless comparison, for example 1e-9 for deterministic reference tests. Do not reuse the existing 0.01 energy/cost tolerance for a remaining-solar fraction.
9. Allow at most one model retry/repair within the overall request deadline. Revalidate its output fully. Authentication/configuration failures should not trigger repeated futile calls.
10. Run all public interpretations through the real provider and a separate held-out paraphrase suite. Proposed team target: at least five new phrasings per directive type, including `no_op`, with changed numbers/hours and manually checked expectations.

**Deliverables:** production model adapter, versioned prompt/output schema, deterministic guardrails, semantic regression report, documented provider/model.

**Exit gate P3:** 10/10 public semantic comparisons pass through live calls; the chosen paraphrase suite passes; malformed model outputs are rejected predictably. Repeat live checks to detect variability. Free-text wording need not match reference prose.

**Dependencies:** Phases 1-2. Model failure cannot be bypassed with regex-only extraction or a model used only for summaries.

## 7. Phase 4 - Compile constraints and implement the optimizer

**Purpose:** produce globally minimum-cost feasible schedules for the stated ideal battery model.

Build five derived arrays without mutating original input: effective solar, minimum reserve, grid upper bound, battery movement lower bound, and battery movement upper bound.

| Directive | Exact adjustment | Constraint effect |
|---|---|---|
| `solar_reduction` | `hours`, `factor` | Effective solar = original solar times remaining factor |
| `minimum_battery_reserve` | `hours`, `minimum_energy_kwh` | Raise end-of-hour reserve to max(base, all active reserves) |
| `no_charge_window` | `hours` | Battery movement upper bound becomes 0 |
| `no_discharge_window` | `hours` | Battery movement lower bound becomes 0 |
| `max_grid_window` | `hours`, `max_grid_kwh` | Grid upper bound becomes minimum active cap |
| `no_op` | null | No change |

Use four continuous variables per hour, giving 96 variables total:

```text
G[h] = grid import
S[h] = solar used
B[h] = signed battery movement: positive charge, negative discharge
E[h] = end-of-hour battery energy

minimize sum(tariff[h] * G[h])

G[h] + S[h] - B[h] = demand[h]
E[h] = E[h-1] + B[h]
E[-1] = initial_energy
E[23] = initial_energy

0 <= G[h] <= active_grid_cap[h] (unbounded above if no cap)
0 <= S[h] <= effective_solar[h]
-max_discharge <= B[h] <= max_charge (tightened by windows)
active_minimum_reserve[h] <= E[h] <= capacity
```

For the specified lossless battery, each signed `B[h]` maps directly to one legal action and magnitude. No binary action variable or simultaneous charging/discharging is needed. Explicitly pass negative lower bounds for battery movement; the solver's default non-negative bounds would incorrectly forbid discharge.

Steps:

1. Test constraint arrays directly for every type, combinations, and overlapping reserve/cap windows. Both charge and discharge prohibitions imply B=0 where they overlap.
2. Implement the LP with solver status handling, finite-value checks, and a bounded runtime.
3. Serialize positive movement as `charge`, negative as `discharge`, and near-zero as `idle` with zero magnitude. Use a tight numerical threshold and verify the serialized result after cleanup.
4. Preserve precision; do not round every hour to two decimals or independently clamp values in a way that breaks balance. Permit unused solar; prohibit negative grid import/export.
5. Test using trusted reference directives before depending on live model output. Compare all ten reference costs and replay every result.
6. Treat infeasibility for an organizer-feasible case as an interpretation/compiler/solver defect to investigate. Never silently relax a reserve, cap, outage, or final-energy equality.

**Deliverables:** pure constraint compiler, LP optimizer, numerical serialization policy, solver tests.

**Exit gate P4:** all ten cases with reference directives yield feasible schedules and costs within 0.01 BDT of reference; edge scenarios pass. No battery discretization, invented losses, terminal depletion, or altered objective.

**Dependencies:** Phase 2 schemas; reference directives let this phase proceed independently of unresolved model quality.

## 8. Phase 5 - Build independent replay and response calculation

**Purpose:** prevent a mathematically or numerically invalid response from leaving the service.

Steps:

1. Replay the exact numeric values that will be returned, from the supplied initial battery energy through hour 23.
2. Verify 24 unique hours, valid actions, finite/non-negative magnitudes, idle amount zero, energy transitions, capacity/reserve bounds, rate limits, solar bounds, grid caps, energy balance, and final neutrality.
3. Independently derive applicable constraints from validated directives. Avoid calling the optimizer's constraint-construction function in the checker, which could reproduce the same bug.
4. Recalculate total grid, total cost using original tariffs, and peak grid from the serialized hourly plan. Verify aggregates again at the HTTP response boundary.
5. Use tighter internal checks where numerically practical; acceptance follows the official 0.01 kWh/BDT tolerance unless the judge tightens it. Never exploit tolerance to manufacture savings.
6. Build factual explanations and a short summary from validated directives and actual actions. Do not claim savings without a defined and computed comparison baseline.
7. Add negative tests by corrupting otherwise valid schedules: excessive solar, cap breach, wrong battery state, final depletion, bad totals, or missing hours. The checker must catch them.

**Deliverables:** independent validator, response builder, aggregate calculator, rejection tests.

**Exit gate P5:** official reference plans are accepted; each intentional corruption is rejected; generated plans pass replay after JSON serialization and parsing.

**Dependencies:** Phase 2 interfaces; finish against Phase 4 outputs.

## 9. Phase 6 - Integrate and pass the complete public suite

**Purpose:** establish one working path from a real HTTP request to a verified schedule.

Steps:

1. Connect request validation -> real model -> guards -> constraints -> optimizer -> response replay.
2. Run one public case first; diagnose each stage separately before running all ten.
3. POST `cases[i].input`, not the whole sample-pack wrapper.
4. Compare interpretations against `expected_output.directive_interpretation` excluding prose wording. Replay plans against both returned interpretations and the organizer reference directives.
5. Compare recomputed costs with reference costs; do not require identical hourly actions, total grid, or peak values when a different valid optimal schedule exists.
6. Record response validity, semantic correctness, cost delta, elapsed time, failure type, model/prompt version, and tested code revision per case.
7. Confirm production code does not load reference answers, branch on sample IDs, or bypass the model.

Reference costs in BDT:

| Case | Cost | Case | Cost |
|---|---:|---|---:|
| SAMPLE-01 | 38,365 | SAMPLE-06 | 34,090 |
| SAMPLE-02 | 42,885 | SAMPLE-07 | 38,550 |
| SAMPLE-03 | 35,480 | SAMPLE-08 | 37,665 |
| SAMPLE-04 | 40,495 | SAMPLE-09 | 34,873 |
| SAMPLE-05 | 33,950 | SAMPLE-10 | 41,620 |

**Deliverables:** complete API, public regression runner, machine-readable and short human-readable results.

**Exit gate P6:** live HTTP requests pass 10/10 semantic comparisons, 10/10 ground-truth schedule validations, and 10/10 reference-cost checks. All reported totals reconcile.

**Dependencies:** Phases 2-5. This is the first full product correctness milestone.

## 10. Phase 7 - Harden language, numerical behavior, and reliability

**Purpose:** address hidden-case variation and operational failures.

| Test group | Required coverage |
|---|---|
| Language | Held-out phrasings, changed hours/numbers, distractors, percent reserve, by/to reduction, 1/2/3 notes, directive order |
| Energy | No solar, surplus solar, flat/changing tariffs, zero charge/discharge limits, minimum=capacity, initial at bounds, fractional quantities, tight but feasible cap/reserve combinations, hours 0 and 23 |
| Input | Invalid JSON/types, booleans as numbers, NaN/infinity, duplicate/missing hours, missing fields, empty or too many notes, incoherent battery bounds |
| Model/provider | Timeout, network failure, 401/429/5xx, malformed/truncated JSON, missing choices, invalid enums/adjustments, duplicate/out-of-order note mapping |
| Solver/serialization | Infeasible or failed solver status, non-finite result, cleanup/rounding residuals, incorrect aggregate values |
| Repeated requests | Changed scenarios, same ID with changed input, request isolation, sequential repeats and modest concurrent load |

For synthetic optimization tests, generate scenarios with a known feasible witness schedule; never assert success for an accidentally infeasible scenario. Add a few small hand-solvable cases with known optimal cost to complement replay, which establishes feasibility rather than optimality.

Proposed runtime policy: enforce an end-to-end application deadline below 30 seconds (initial target 27 seconds), with a shorter first provider attempt and at most one retry only if the remaining budget permits it. Allocate time for the solver, replay, serialization, and transport. A per-socket timeout alone is not an overall deadline. Tune actual budgets from measurements.

Measure all requests, including failures, rather than only successful provider calls. Record sample count, warm/cold conditions, provider/model, concurrency, and p50/p95/max plus failure rate. Proposed team sample: three passes over the ten public scenarios and a held-out paraphrase set. This is a team test size, not an official minimum.

**Deliverables:** edge/paraphrase fixtures, failure-injection tests, latency report, sanitized stage timing logs, documented retry/deadline behavior.

**Exit gate P7:** valid test requests have no observed failures, every request completes within 30 seconds, startup readiness is within 60 seconds, all negative cases fail safely, and p95 is <=5 seconds for the full-credit target. Record any missed performance target explicitly; controlled 500s still count as failures for valid judge requests.

**Dependencies:** Phase 6. Do not make model or prompt changes without rerunning affected semantics and regression gates.

## 11. Phase 8 - Verify Docker and public deployment

**Purpose:** give judges a reachable service and a working fallback from identical source.

Steps:

1. Complete the image using a tested base/runtime and pinned dependencies. Bind Uvicorn to `0.0.0.0` on the documented port (proposed 8000 locally, adjusted to host requirements).
2. Exclude credentials from every image layer and build argument; inject them only at runtime. Verify source, image configuration, logs, and error responses for accidental exposure.
3. Run health and a live sample locally through Docker. Ensure settings do not assume a local Windows path or depend on untracked files.
4. Publish a registry image with an exact release tag and record its digest. Pull that image into a clean environment and run the documented command with runtime credentials.
5. Deploy the same release image or a demonstrably identical build. Configure the real model, environment variables, port routing, restart behavior, and host timeout above the service deadline.
6. Verify the host can reach the model provider, has working DNS/TLS, and has sufficient quota. Avoid a deployment that sleeps through the evaluation window.
7. Test both exact endpoints from outside the development environment, without login, VPN, dashboard access, or manual approval. Repeat the public regression and timing checks against the actual URL.
8. Record the prior working image as the rollback candidate. Roll back if a new release breaks gates, then verify external behavior again.

**Deliverables:** Dockerfile, `.dockerignore`, exact registry tag/digest, public URL, startup/pull/run instructions, external and container evidence.

**Exit gate P8:** an external caller can exercise both endpoints; the registry image independently pulls, becomes healthy within 60 seconds, and processes a real sample. Deployed correctness and timeout gates pass.

**Dependencies:** start container/host setup in Phase 1; final verification requires Phases 6-7. Host/registry access remains a setup dependency until selected.

## 12. Phase 9 - Finish documentation, reproduction, and video

**Purpose:** let organizers run and understand the submission without team assistance.

README must contain:

- Problem, architecture, real LLM role, guardrails, optimization equations/solver, and final replay.
- Exact runtime/dependencies, selected provider/model identifier, credited external tools/libraries, and known limitations.
- All environment-variable names and safe examples, without real credentials.
- Copy-paste source setup, installation, exact server command, health check, and a full sample request/response workflow.
- Commands for offline tests, live interpretation checks, and all-public-case API regression; explain expected results and provider requirements.
- Docker pull/run command with exact registry reference, port, runtime environment injection, and public API base URL.
- Error behavior, retry/deadline policy, numeric precision/tolerance, and unresolved organizer semantics if still applicable.

Reproduction: use a fresh checkout/environment and follow README only, then separately use the pulled image. A teammate or clean environment must expose any undocumented local setup dependency. Record the revision and commands.

Suggested video script, maximum 3:00: 0:00-0:25 problem; 0:25-1:10 model/guardrail/solver architecture; 1:10-1:50 one request and returned plan; 1:50-2:30 tests and correctness; 2:30-2:55 clean setup, public API, and Docker. Verify duration and organizer access. Video contributes no base points but is the first tie-break.

**Deliverables:** complete README/configuration, reproduction record, recorded video and tested access link/file.

**Exit gate P9:** fresh source and container quickstarts succeed without undocumented steps; video is accessible and <=3:00.

**Dependencies:** documentation begins in Phase 1; final steps use the Phase 8 release.

## 13. Phase 10 - Freeze, submit, and maintain availability

Steps:

1. Freeze a release revision and matching image digest. Run the release gates below and resolve all failures; do not substitute an older report for changed code/model/configuration.
2. Populate the existing control-file manifest: team/contact, public base URL, health/optimization URLs, repository URL, commit, image tag/digest, service port, provider/model, environment-variable names, README, video/duration, external-test timestamp.
3. Check access to every submitted artifact and ensure public fields contain no secret values. Arrange any required judge credential delivery only through the organizer's designated secure process.
4. Submit the actual organizer form before the confirmed deadline and retain confirmation. The form/channel remains an external detail to confirm, not something to invent.
5. Make the repository public after the deadline, as required. Verify source, image, video, model quota, and API availability through the evaluation end.
6. Maintain an operational checklist for endpoint outages, expired credentials, quota/rate limits, or broken artifact access. Record any necessary deployment changes and rerun affected checks. This plan does not itself create a scheduled monitor.

**Deliverables:** final manifest, release evidence, submission receipt, post-deadline visibility/access record.

**Exit gate P10:** submission confirmed before deadline; all required artifacts accessible; post-deadline repository visibility correct; evaluation availability responsibilities assigned.

**Dependencies:** Phases 1-9 plus actual submission/account details. Do not label the contest handoff complete while required submission or availability work remains outstanding.

## 14. Requirement coverage and release gates

All gates are **NOT RUN** for the complete product until evidence exists. The preliminary offline checker results do not mark these gates passed.

| Requirement / scoring coverage | Phase(s) | Release evidence |
|---|---|---|
| FR-01: exact endpoints, schema, status behavior; API 10 pts | 2, 6, 8 | Contract tests plus external HTTP checks |
| FR-02: mandatory real LLM path; shortlist eligibility | 1, 3, 6 | Live calls and inspected model-to-constraint integration |
| FR-03: six types and paraphrases; interpretation 25 pts | 3, 6, 7 | Reference and held-out semantic results |
| FR-04: mapping, types, hours, values, applies guardrails | 3, 7 | Invalid-output rejection tests |
| FR-05: actual directive application; correctness 25 pts | 4, 5, 6, 7 | Replay against organizer ground truth |
| FR-06: physics, single action, terminal neutrality, minimum cost; optimization 10 pts | 4, 5, 6, 7 | Feasibility replay, cost deltas, known-optimum tests |
| FR-07: full response and reconciled aggregates | 2, 5, 6 | Serialized-response schema and recalculation checks |
| FR-08: accurate explanations and summary | 3, 5, 9 | Human review against interpreted directives and actual plan |
| FR-09: predictable input/model/solver errors | 2, 3, 7 | Failure injection, sanitized logs/responses |
| FR-10: source, public service, image, README, video | 8, 9, 10 | Fresh setup, image pull, access checks, manifest and receipt |
| NFR-01: ready <=60s and available during evaluation | 7, 8, 10 | Cold-start timing and availability records |
| NFR-02: requests <=30s, p95 <=5s target; reliability 10 pts | 3, 7, 8 | Full API timing set including failures |
| NFR-03: no exposed secrets | 1, 7, 8, 9, 10 | Source/history, image, logs, output and submission review |
| NFR-04: live provider credentials/quota/access | 1, 3, 8, 10 | Live deployment calls and quota/availability check |
| NFR-05: reproducible without runtime training; documentation 10 pts | 1, 9 | Fresh checkout following README only |
| NFR-06: exact image, port, 0.0.0.0; deployment 10 pts | 8, 9 | Independent registry pull/run and health/sample checks |
| NFR-07: synthetic data only | 1, 7, 9 | Fixtures and data-source review |
| PG repository timing/visibility and dependency credits | 1, 9, 10 | Repository timestamps/visibility and README credits |
| PG video, tie-break, submission and sustained access | 9, 10 | <=3:00 video, access test, receipt, assigned availability owner |

Evidence record for each gate: `phase/gate | PASS/FAIL/NOT RUN | date/time | code revision | model/prompt | image/config revision | command or procedure | counts/timings | report path | remaining issue`.

Passing means all required checks pass for the same release. A correct extraction with a noncompliant schedule earns no downstream success; an invalid schedule earns no optimization credit. Never claim 100/100 from local tests.

## 15. Proposed project layout

```text
app/
  main.py                 # routes, startup and exception handlers
  config.py               # typed settings and environment loading
  schemas.py              # exact request/response/directive contracts
  interpreter.py          # provider request and structured extraction
  guardrails.py           # strict deterministic interpretation checks
  constraints.py          # effective hourly bounds
  optimizer.py            # signed-battery linear program
  replay.py               # independent serialized-plan checks
  response.py             # actions, totals and factual summary
  prompts/operator_notes.txt
tests/
  test_contract.py
  test_guardrails.py
  test_constraints.py
  test_optimizer.py
  test_replay.py
  test_failures.py
  test_integration.py
  fixtures/paraphrases.json
tools/
  check_nvidia_model.py    # preserve/refactor existing checker
  run_public_cases.py     # full HTTP regression; offline/live separation
  benchmark_api.py        # all-request timing and failure reporting
reports/                  # sanitized evidence for tested releases
Dockerfile
.dockerignore
.env.example
pyproject.toml             # plus chosen pinned dependency/lock file
README.md
PRD.md
PROJECT_CONTROL.md
IMPLEMENTATION_PLAN.md
```

These are proposed outputs, not files claimed to exist. Keep one source of production validation logic; retain a separately implemented mathematical replay so shared solver bugs remain detectable. Put public reference outputs only in testing inputs, never the runtime response path.

## 16. Execution order and contest time allocation

Follow phases 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 for a single implementer. If live model access is temporarily blocked, work on phases 4-5 using reference directives. Start documentation/container preparation in Phase 1 and keep them current.

The following is a **proposed allocation**, not a guarantee that all work fits four hours. Adjust for actual team capacity and time remaining. Existing control-file milestones M0-M5 map to these phases:

| Relative contest time | Milestone | Target |
|---|---|---|
| 0-20 min | M0 | Phases 1-2 foundation, model smoke call, schema/health, deployment account setup |
| 20-75 min | M1 | Thin implementation of phases 3-6; first real end-to-end case |
| 75-135 min | M2 | Complete phases 3-6; all directives, replay, ten-case cost/validity gate |
| 135-180 min | M3 | Phases 7-8 robustness, externally verified service, pullable image, latency |
| 180-220 min | M4 | Phase 9 clean reproduction, README/video, targeted defect fixes |
| 220-240 min | M5 | Phase 10 freeze, final access checks, submission and receipt |
| After deadline | Follow-through | Public repository and evaluation availability |

Assign the lead, language, optimization, and QA/delivery responsibilities in PROJECT_CONTROL.md to actual people. One person can hold multiple roles. Do not assume a four-person team or that independent work has been delegated.

If behind schedule, remove optional UI, charts, additional providers, caching, and cosmetic work first. Preserve mandatory LLM interpretation, guardrails, mathematical validity, public delivery, Docker, README, and video. Finish required correctness repairs before optional performance refinements; document residual issues rather than fabricating a completed gate.

## 17. Open decisions and immediate next action

| Open item | When it must be resolved | Approach |
|---|---|---|
| Actual model works with key and structured output | Phase 1 smoke / Phase 3 quality gate | Live test configured model; never expose key |
| Host/registry account, budget, public URL | Phase 1 selection / Phase 8 verification | Use available container platform and exact registry image |
| Event date/timezone, submission channel, evaluation end | Phase 1 / before Phase 10 | Confirm official announcement; record evidence |
| Team names and account ownership | Phase 1 | Assign existing control-file roles |
| Overlapping solar reductions | Before relying on that case | Request organizer clarification; isolate and document any interim policy as a team assumption |
| Overnight window interpretation | Before relying on that case | Seek clarification; keep normalization policy explicit and testable |
| Truncated zero-optimum score formula | Only if building score estimator | Clarify; not needed to minimize cost or compare reference costs |

The first implementation action is Phase 1: establish the project environment and verify the configured live model. The plan is complete; product readiness is established only by the phase exit gates.
