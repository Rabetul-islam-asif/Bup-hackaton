# GridWise - Product Requirements Document

Version: 1.1 | Updated: 18 September 2026 | Status: Requirements baseline; model-check tooling exists; full service unimplemented

Companions: [Project control file](<D:/hacaton BUP/PROJECT_CONTROL.md>) and [complete phased implementation plan](<D:/hacaton BUP/IMPLEMENTATION_PLAN.md>).

## 1. Purpose and source authority

Build one publicly reachable HTTP API that interprets campus operator notes with a language model and returns a valid, minimum-cost, 24-hour energy schedule using grid electricity, solar, and a battery.

This PRD covers the BUP CSE Fest 2026 online preliminary. **Official** requirements come from the supplied files; **Team target** and **Proposed** items are planning choices, not additional organizer rules. The folder now contains model-check tooling and local environment configuration; no complete API, optimizer, or deployment has been verified. Nine existing validator tests and offline validation of ten reference interpretations passed on 18 September 2026; these are not live-model or full-service results.

| Reference | Supplied source | Authority |
|---|---|---|
| PS | [Preliminary Problem Statement](<D:/hacaton BUP/BUP_CSE_FEST_2026_Preliminary_Problem_Statement_GridWise_LLM (1).pdf>) | Canonical behavior, API contract, directives, guardrails, energy rules, validity |
| PG | [Participant Guide and Evaluation Rubric](<D:/hacaton BUP/BUP_CSE_FEST_2026_Participant_Guide__Evaluation_Rubric_GridWise_LLM.pdf>) | Canonical deployment, repository, submission, performance, scoring, penalties, tie-breaks |
| SC | [Public Sample Cases, version 2.0](<D:/hacaton BUP/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases (1).json>) | Ten worked examples; not the hidden judge set |

Page references below use PDF page order. Organizer clarifications or a stricter official judge tolerance must be recorded in the project control file and reflected here.

## 2. Problem, users, and outcome

Campus demand, solar availability, and electricity prices change every hour. Operator notes add temporary constraints such as maintenance, reserve requirements, and grid limits. Ignoring or misunderstanding a note can make an otherwise cheap schedule invalid.

| User | Need | Successful outcome |
|---|---|---|
| Automated judge | Submit a scenario and inspect machine-readable results | Correct schema, interpretation, constraint application, and recalculated cost |
| Campus operator, represented by synthetic input | Express operating restrictions in natural language | Each note has a clear interpretation and the schedule follows it |
| Organizer/reviewer | Run and verify the submission independently | Public API, source, documented setup, working Docker image, accessible video |
| Team developer | Diagnose errors rapidly | Separate interpretation, validation, optimization, and replay results |

Core user story: given 24 hourly forecasts, battery parameters, and 1-3 notes, a caller receives one explanation per note and a feasible 24-hour schedule that minimizes grid electricity cost.

## 3. Scope and success measures

### Required scope

- One service with `GET /health` and `POST /optimize-energy`.
- Real language-model interpretation of every operator note.
- All six supported directive types, including irrelevant-note handling.
- Deterministic validation before optimization and replay after optimization.
- Full-horizon scheduling, energy accounting, and response totals.
- Controlled errors, repeated-request reliability, public deployment, and Docker fallback.
- Source repository, self-contained README, and video of at most three minutes.

### Outside preliminary MVP scope

A dashboard, authentication system, mobile app, persistent database, live sensors, real campus/billing data, forecasting, model training, grid export, and multi-day scheduling are unnecessary for this delivery. Battery losses and degradation are not introduced into the supplied ideal battery model. Peak grid usage is a reported metric; the specified objective is total cost, with grid caps enforced where directed.

### Acceptance targets

| Measure | Requirement or team target |
|---|---|
| Mandatory LLM use | Model output participates in the operator-note interpretation used by the optimizer |
| Interpretation | Team target: correct machine-checkable semantics on all 10 public cases and team-written paraphrases |
| Schedule validity | Team target: 10/10 public cases pass independent replay against reference directives |
| Optimal cost | Team target: public-case cost matches the reference within 0.01 BDT, unless officially tightened |
| Readiness | Official: healthy within 60 seconds of service start |
| Request duration | Official: each optimization request completes within 30 seconds |
| Latency | Team target: p95 at or below 5 seconds, the full-credit latency band |
| Reliability | Valid requests do not produce 5xx, invalid JSON, or no response during normal operation |
| Reproduction | Fresh source setup and registry image both start and process a public sample using documented steps |

Passing public samples does not establish hidden-case performance. Equivalent valid optimal schedules can differ from the sample hourly actions and free-text explanations.

## 4. Required processing flow

```mermaid
flowchart LR
    A[Validate request] --> B[LLM interprets notes]
    B --> C[Deterministic directive guardrails]
    C --> D[Build effective constraints]
    D --> E[Optimize 24-hour schedule]
    E --> F[Replay schedule and recalculate totals]
    F --> G[Return structured JSON]
```

The LLM must not invent demand, solar forecasts, tariffs, battery limits, or unsupported directives. Mathematical scheduling and final checks belong in deterministic code. A model used only to write `plan_summary` does not meet the mandatory LLM requirement. [PS pp. 2-6; PG pp. 4-5]

## 5. API contract

### 5.1 Endpoints and status codes

| Endpoint/status | Required behavior |
|---|---|
| `GET /health` | HTTP 200 with JSON containing `"status": "ok"` when ready |
| `POST /optimize-energy` | Accept one scenario object; return one interpretation-and-plan object |
| HTTP 200 | Successful health or optimization response |
| HTTP 400 | Malformed JSON or structurally invalid request |
| HTTP 422 | Optional for a well-formed but semantically invalid request |
| HTTP 500 | Controlled internal failure without secrets or raw stack traces |

Use JSON requests and responses. The judging path must require no login, dashboard, manual approval, VPN, or private-network access. Endpoint spelling is exact. [PS p. 4; PG p. 4]

### 5.2 Request fields

| Field | Type and meaning |
|---|---|
| `scenario_id` | String identifying the synthetic scenario |
| `operator_notes` | Array of 1-3 non-empty natural-language strings |
| `hours` | Exactly 24 entries, covering each integer hour 0-23 once |
| `battery` | Object with the five numeric parameters below |

Each `hours` entry contains:

| Field | Type and meaning |
|---|---|
| `hour` | Integer 0-23 |
| `demand_kwh` | Number; demand for that hour |
| `solar_kwh` | Number; solar available before directives |
| `tariff_bdt_per_kwh` | Number; grid electricity price |

The `battery` object contains numeric `capacity_kwh`, `initial_energy_kwh`, `minimum_energy_kwh`, `max_charge_kwh_per_hour`, and `max_discharge_kwh_per_hour`.

Reject missing required fields, invalid types, duplicate/missing hours, invalid note counts, and empty notes. Validate finite numeric values and coherent battery bounds, including `0 <= minimum_energy_kwh <= initial_energy_kwh <= capacity_kwh` and non-negative rates. Keep the submitted base data immutable; apply directives to separate derived constraints. [PS pp. 5-6]

### 5.3 Response fields

| Field | Type and requirement |
|---|---|
| `scenario_id` | String; exactly echoes request |
| `directive_interpretation` | One entry per note, ordered by `note_index` |
| `hourly_plan` | Exactly 24 entries covering hours 0-23 once |
| `total_grid_kwh` | Number; sum of returned hourly grid imports |
| `total_cost_bdt` | Number; sum of hourly grid imports multiplied by original tariffs |
| `peak_grid_kwh` | Number; maximum hourly grid import |
| `plan_summary` | Short string describing the actual strategy |

Each interpretation entry contains `note_index` (zero-based integer), `applies` (boolean), `directive_type` (supported enum), `structured_adjustment` (type-specific object or null), and `explanation` (short string).

Each hourly plan entry contains:

| Field | Requirement |
|---|---|
| `hour` | Integer 0-23; team convention is ascending output order |
| `grid_kwh` | Finite, non-negative grid import |
| `solar_used_kwh` | Finite, non-negative solar actually used |
| `battery_action` | Exactly `charge`, `discharge`, or `idle` |
| `battery_kwh` | Finite, non-negative magnitude; zero when idle |
| `battery_energy_after_kwh` | Battery energy after completing the hour |

Return numeric JSON values, not formatted numeric strings. Explanations and summaries must describe the computed result. [PS pp. 7-8]

## 6. Operator-note semantics and guardrails

| Directive type | Exact `structured_adjustment` shape | Deterministic effect |
|---|---|---|
| `solar_reduction` | `{"hours": [...], "factor": number}` | Available solar equals original solar times the remaining fraction |
| `minimum_battery_reserve` | `{"hours": [...], "minimum_energy_kwh": number}` | End-of-hour battery energy is at least the greater of base reserve and directive reserve |
| `no_charge_window` | `{"hours": [...]}` | Charge amount is zero in the listed hours |
| `no_discharge_window` | `{"hours": [...]}` | Discharge amount is zero in the listed hours |
| `max_grid_window` | `{"hours": [...], "max_grid_kwh": number}` | Grid import does not exceed the stated cap in each listed hour |
| `no_op` | `null` | No change to optimization |

Required interpretation behavior:

1. Exactly one entry per original note, ordered `0..N-1`, with no missing or duplicate mapping.
2. `no_op` is the only directive with `applies: false`; its adjustment is null. Every other type has `applies: true` and the required object shape.
3. Directive hours are unique integers 0-23 in ascending order.
4. Whole-hour windows include the start and exclude the end: 1 PM to 3 PM becomes `[13, 14]`.
5. `factor` is finite and in `[0, 1]`. An 80% reduction leaves `factor: 0.2`; output reduced *to* 80% means `factor: 0.8`.
6. Reserve values are finite, non-negative, and no greater than capacity. A reserve of 50% of a 200 kWh capacity means 100 kWh.
7. Grid caps are finite and non-negative.
8. Irrelevant notes must not introduce a constraint. Valid hidden notes each map to one published type or `no_op` and can use unseen wording.
9. Reject malformed or unsupported model output in a controlled manner. Do not silently convert interpretation failures into `no_op` or skip validation.
10. Apply all relevant directives before solving. Correct extraction without correct scheduling fails downstream checks.

Organizer scoring scenarios are feasible and do not require mutually contradictory hard constraints. Multiple reserve constraints can be enforced together using the highest active reserve; multiple grid caps using the lowest active cap. **Unresolved specification edge:** overlapping solar-reduction notes do not have an explicit combination rule in the provided pack. Record an organizer clarification before treating multiplication, minimum factor, or overwrite as official behavior. [PS pp. 3-6, 8-9; SC SAMPLE-03 and SAMPLE-09]

## 7. Energy model and optimization

For each hour `h`, let `G[h]` be grid import, `S[h]` solar used, `C[h]` charge, `D[h]` discharge, and `E[h]` end-of-hour battery energy. Inputs include demand `L[h]`, tariff `T[h]`, and effective solar `Solar[h]` after validated directives.

```text
Minimize: sum(G[h] * T[h]) for h = 0..23

G[h] + S[h] + D[h] = L[h] + C[h]
E[-1] = initial_energy_kwh
E[h] = E[h-1] + C[h] - D[h]

G[h] >= 0
0 <= S[h] <= Solar[h]
0 <= C[h] <= max_charge_kwh_per_hour
0 <= D[h] <= max_discharge_kwh_per_hour
active_minimum_reserve[h] <= E[h] <= capacity_kwh

C[h] = 0 during no_charge_window
D[h] = 0 during no_discharge_window
G[h] <= active_grid_cap[h] where a cap applies
E[23] = initial_energy_kwh
```

Only one battery action is represented per hour. The implementation must produce a plan consistent with that representation; it cannot return simultaneous charging and discharging. The supplied model has no charge/discharge loss term. Unused solar may be curtailed; negative grid import/export is not allowed. [PS pp. 4, 6-8]

**Proposed implementation approach:** use SciPy HiGHS linear programming behind a small optimizer interface, subject to installation/container verification. For this lossless battery, represent movement as one signed continuous variable B[h]: positive means charge, negative means discharge. Enforce G[h] + S[h] - B[h] = L[h], E[h] = E[h-1] + B[h], and -max_discharge <= B[h] <= max_charge. No-charge windows impose B[h] <= 0; no-discharge windows impose B[h] >= 0. All grid, solar, reserve, capacity, and terminal bounds above still apply. This represents one action per hour directly with 96 continuous variables across 24 hours. Preserve continuous quantities and verify serialized plans independently; do not discretize battery energy or add binary variables unnecessarily. Detailed work and exit tests are in implementation-plan phases 4-5.

Recompute totals from the serialized hourly plan, and replay that same plan before returning it. Preserve enough numeric precision to keep both hourly residuals and accumulated cost errors within tolerance. Do not independently round every intermediate state to two decimals.

## 8. Functional requirement register

| ID | Requirement | Acceptance evidence | Source |
|---|---|---|---|
| FR-01 | Implement exact endpoints and request validation | Health, valid request, malformed JSON, duplicate hour, missing field tests | PS pp. 4-5 |
| FR-02 | Interpret every note through a real LLM | Provider/model configuration and execution evidence; semantic comparisons | PS pp. 2-4; PG pp. 4-5 |
| FR-03 | Support all six directive types and paraphrases | Reference semantics and independent paraphrase tests | PS pp. 3-4, 9 |
| FR-04 | Validate model output deterministically | Invalid enums, ranges, shapes, note mapping, and applies tests | PS pp. 5-6 |
| FR-05 | Build and enforce all applicable constraints | Replay against reference directives, including combined constraints | PS pp. 4, 6, 8 |
| FR-06 | Minimize cost subject to validity and final neutrality | Reference-cost comparisons and valid replay | PS pp. 4, 6, 9 |
| FR-07 | Return complete response and accurate totals | Schema checks, scenario echo, aggregate recalculation | PS pp. 7-8 |
| FR-08 | Explain interpretations and actual plan briefly | Human review for accurate, non-invented explanations | PS p. 7 |
| FR-09 | Fail predictably on invalid input/model/provider failures | Failure injection; no crash, fabricated success, or leaked secrets | PS pp. 4, 6; PG p. 8 |
| FR-10 | Provide repeatable delivery artifacts | External endpoint test, clean source run, pulled-image run, README, video | PG pp. 3-6, 11 |

## 9. Operational requirements

| ID | Requirement | Verification |
|---|---|---|
| NFR-01 | Ready within 60 seconds; available throughout evaluation | Cold start and externally observed health checks |
| NFR-02 | Requests complete within 30 seconds; target p95 <= 5 seconds | Timed repeated requests against the deployed service |
| NFR-03 | No secret values in repository, image, logs, or responses | Review environment handling, image contents, logs, and failure responses |
| NFR-04 | LLM quota, credentials, limits, and availability remain usable | Real deployed model calls; team verifies quota and access |
| NFR-05 | Clean reproducibility without manual code changes or training | Execute README from a fresh environment |
| NFR-06 | Registry image uses an exact tag/digest, documented port, and `0.0.0.0` bind | Pull and run the submitted image independently |
| NFR-07 | Synthetic challenge data only | Review fixtures and data paths |

Official p95 scoring bands: `<=5s`: 3/3 points; `>5s..15s`: 2/3; `>15s..30s`: 1/3; `>30s`: 0/3 and timed-out requests fail. [PG p. 8]

**Proposed reliability policy:** use a bounded provider timeout and at most one retry only if the total request budget permits it. Validate every retry result. Use a controlled 500 when an internal/model failure cannot be recovered; this avoids fabricated success but still counts as a failure for a valid judge request. Do not present error handling as a substitute for provider availability. A backup, if added, must still satisfy the mandatory model interpretation requirement.

## 10. Acceptance and test plan

### Public regression suite

POST each `cases[i].input` from SC, not the enclosing sample-pack object. Compare interpretation semantics with `expected_output.directive_interpretation`, excluding free-text wording. Replay the response against the supplied reference directives as well as its reported interpretation: checking only the service's own interpretation can hide a wrong extraction.

| Case | Main coverage | Reference optimal cost, BDT |
|---|---|---:|
| SAMPLE-01 | Solar factor 0.25 at hours 12-13; distractor | 38,365 |
| SAMPLE-02 | No charging at hours 2-4 | 42,885 |
| SAMPLE-03 | 50% capacity reserve becomes 100 kWh at hours 18-20 | 35,480 |
| SAMPLE-04 | No discharge at hours 18-19 | 40,495 |
| SAMPLE-05 | Grid cap 155 kWh at hours 18-20 | 33,950 |
| SAMPLE-06 | Solar reduction, no-charge window, distractor | 34,090 |
| SAMPLE-07 | 90 kWh reserve plus 180 kWh grid cap | 38,550 |
| SAMPLE-08 | Separate charge and discharge outages | 37,665 |
| SAMPLE-09 | 80% reduction means factor 0.2; distractor | 34,873 |
| SAMPLE-10 | 80 kWh reserve, 190 kWh grid cap, distractor | 41,620 |

These are supplied reference values, not measured implementation results. Do not hard-code case IDs, note wording, values, or schedules. Do not require a byte-for-byte match of hourly actions, peak values, total grid usage, or prose when another valid optimal solution exists; returned aggregates must always match the returned plan.

### Additional test groups

- **Language:** unseen paraphrases; AM/PM and 24-hour notation; noon; percentages versus fractions; reduction *by* versus reduction *to*; irrelevant future events; relative reserve values.
- **Contract:** 23/25 hours, duplicate/out-of-range hours, missing fields, invalid types, blank notes, 0/4 notes, invalid JSON, non-finite numbers, and inconsistent battery parameters.
- **Guardrails:** fabricated directive types, duplicate note indexes, missing entries, invalid applies values, wrong adjustment shape, invalid factors/reserves/caps.
- **Scheduling:** no solar, surplus solar/curtailment, flat tariffs, zero available charge/discharge rate, tight reserve/cap combinations, early/late restrictions, and final-hour neutrality. Use feasible scenarios for success assertions.
- **Resilience:** model timeout, malformed model response, provider failure, repeated requests, and isolation between different scenarios.
- **Release:** cold-start readiness, p95 timing, public access from outside development, and a pulled Docker image processing a full sample.

Use absolute energy and cost tolerance of 0.01 kWh/BDT unless the official judge tightens it. Type, enum, note-mapping, and hour-set errors are exact structural failures. The supplied pack does not define a separate dimensionless factor tolerance; team tests should expect the intended factor rather than treating 0.01 kWh as a factor tolerance.

## 11. Delivery and release acceptance

The release must include the public base URL, newly created GitHub repository following event timing/visibility rules, source and configuration, tested registry image reference, and accessible video of at most 3:00.

README must document the exact provider/model or local model identifier, LLM role, guardrails, optimizer/solver, dependencies and credits, environment-variable names without values, source setup, exact run command, health and optimization curl examples, public-sample test command and expected result, Docker pull/run commands, port, limitations, and secret handling.

Repository policy: create after question reveal, keep private during the event, and make public after the submission deadline. Source, public API, image, and video must remain accessible for evaluation. [PG pp. 3-6, 11]

The video is required and is the first tie-break review; it contributes no base points. Explain the problem, model-to-guardrail-to-optimizer architecture, implementation choices, and how to run/test the service.

## 12. Open decisions and specification gaps

| Item | Current state | Resolution needed |
|---|---|---|
| Team members and role assignments | Not supplied | Team assigns names in project control file |
| Provider/model, solver, language/framework, hosting and registry | NVIDIA settings present; proposed Python/FastAPI and SciPy HiGHS; live model, dependency installation, hosting and registry unverified | Follow implementation-plan phases 1, 3 and 8 before treating selections as verified |
| Event calendar date, timezone and evaluation-window end | Not established by the supplied round-window text | Confirm official event announcement; do not infer the event date from document creation date |
| Submission destination and exact release freeze policy | Not supplied in these files | Confirm official submission instructions |
| Overlapping solar-reduction semantics | Not explicitly defined | Organizer clarification before relying on a combination rule |
| Overnight window interpretation | Not explicitly defined | Confirm expected normalization if relevant; do not claim it as specified |
| Zero-optimum scoring edge | PG p. 7 formula text is cut off after `quality_ratio` for positive team cost | Consult organizer clarification if calculating that score; do not invent the missing formula |

These gaps do not block the specified API, ordinary same-day directives, supplied public samples, or the core delivery plan.
