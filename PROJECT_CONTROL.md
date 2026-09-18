# GridWise - Project Control File

Version: 1.1 | Updated: 18 September 2026 | Project: BUP CSE Fest 2026 online preliminary

## 1. Control summary

**Objective:** deliver a public, reproducible API that uses an LLM to interpret operator notes and produces a valid, low-cost 24-hour campus energy plan.

**Current phase:** core implementation and public deployment are verified. On 18 September 2026, 78 pytest cases passed (67 deterministic and 11 live); offline and live end-to-end regressions each passed all ten public cases with exact reference costs. The public Render health endpoint and one full sample request were externally verified. A pullable registry image, final video, submission receipt, and post-deadline repository visibility change remain outstanding.

**Execution plan:** [IMPLEMENTATION_PLAN.md](<D:/hacaton BUP/IMPLEMENTATION_PLAN.md>) defines ten phases, their deliverables, exit tests, dependencies, and complete requirement coverage. Its phases map to the M0-M5 contest schedule below. The plan is the detailed work sequence; this file remains the ownership/evidence tracker.

**Product baseline:** [PRD.md](<D:/hacaton BUP/PRD.md>). It contains source links, exact contracts, requirement IDs, energy equations, and acceptance criteria. The Problem Statement controls challenge behavior; the Participant Guide controls operational and competition rules; public cases illustrate both.

| Control field | Value |
|---|---|
| Team name / lead | TBD - team to assign |
| Event calendar date and timezone | TBD - confirm official announcement |
| Published round window | 7:00 PM-11:00 PM; four hours |
| Submission destination | TBD - confirm organizer instructions |
| Repository URL | https://github.com/Rabetul-islam-asif/Bup-hackaton.git |
| Public API base URL | https://bup-hackaton.onrender.com |
| Provider / model identifier | NVIDIA (meta/llama-3.2-11b-vision-instruct); live access and model quality verified |
| Solver / runtime / hosting | Python 3.13, FastAPI/Uvicorn, SciPy HiGHS, Render |
| Container registry reference | TBD - exact tag or digest required |
| Video location | TBD - organizer-accessible, maximum 3:00 |
| Evaluation-window end | TBD - service and dependencies must remain available |
| Latest tested commit / image digest | d75ce91 (application); image digest pending |
| Release readiness | CORE READY; registry image, video, submission, and post-deadline release remain |

Use this file at each milestone and handoff. Update the task, evidence, decision, and risk tables when work changes. Record actual results; never change a status to Done solely because code was written.

## 2. Non-negotiable delivery rules

1. Keep exact endpoint names: `GET /health` and `POST /optimize-energy`.
2. Use a real language model in operator-note interpretation. Phrase matching alone, or AI used only for a summary, fails the mandatory requirement and shortlist eligibility.
3. Emit one interpretation per note in index order. Validate its type, mapping, hours, values, and applies semantics before scheduling.
4. Apply all relevant directives and independently replay the final 24-hour plan. Validity comes before cost.
5. Restore the battery to its initial energy at the end of hour 23; recalculate all totals from the returned plan.
6. Keep judge access public and free of login/manual steps. Be healthy within 60 seconds and finish optimization requests within 30 seconds.
7. Deliver a pullable Docker image, self-contained README, source repository, and video of at most three minutes.
8. Create the repository after question reveal, keep it private during the event, and make it public after the submission deadline.
9. Keep credentials out of source, images, logs, responses, and public submission fields. Use synthetic challenge data only.
10. Do not hard-code public samples or claim public tests establish hidden-case success.

## 3. Work ownership

Roles are workstreams, not a claim about team size. One member may hold several roles. Assign actual names before starting.

| Role | Name | Accountable for | Required handoff |
|---|---|---|---|
| Lead / integration | TBD | Scope, API contract, integration, release and submission | Runnable integrated service; final artifact manifest |
| Language / guardrails | TBD | Model access, prompt, directive extraction and validation | Validated directives, paraphrase evidence, documented provider/model |
| Optimization | TBD | Constraint compilation, solver, plan serialization | Feasible schedules, replayable states, cost evidence |
| QA / delivery | TBD | Independent replay, regressions, public deployment, image, README and video | Test report, external smoke results, clean-run evidence |

If the team has fewer members, combine Lead with QA/delivery and Language with Optimization as needed. Agree interfaces first so work can proceed independently.

## 4. Score-aware priorities

| Official category | Points | Team focus | Evidence |
|---|---:|---|---|
| LLM directive interpretation | 25 | Relevance, type, hours, values/shape, paraphrases | Semantic regression report |
| Directive application and constraint correctness | 25 | Ground-truth constraints, balance, battery, neutrality | Independent replay report |
| Optimization quality | 10 | Minimum recalculated cost on valid cases | Cost comparisons |
| API contract and schema | 10 | Exact endpoints, request handling, response shape | Contract test report |
| Performance and reliability | 10 | Readiness, p95, valid-request stability, controlled failures | Timed repeated calls and failure tests |
| Deployment and Docker fallback | 10 | Reachability, pullable image, documented startup | External and clean-container checks |
| Documentation and local reproducibility | 10 | Fresh setup using README only | Reproduction checklist |
| **Total** | **100** | Correct interpretation plus valid application account for half | All release gates |

Source: Participant Guide pp. 6-8. Invalid schedules receive no optimization credit for the affected case. The video has no base points but is the first tie-break; subsequent tie-breaks consider constraint correctness, interpretation, optimization, API/schema, reliability/deployment, documentation, then exceptional engineering/verification.

## 5. Four-hour execution plan

This is a **proposed team schedule**, relative to the official start time. It does not assert the event is on the date this document was written. If starting late, measure remaining time against the actual deadline and cut optional work first.

| Milestone | Elapsed window | Work | Exit condition |
|---|---|---|---|
| M0 - Setup and contract | 0-20 min | Assign roles; confirm event details; create permitted private repo; validate provider access; API skeleton and schemas | Local health works; live model call works; interface agreed |
| M1 - First end-to-end case | 20-75 min | Note interpretation, guardrails, base optimizer and one full response; begin deployment skeleton | One real public request passes semantic and energy replay |
| M2 - Complete core behavior | 75-135 min | All six directive types; combined constraints; final neutrality; output and error handling | All 10 public samples pass semantics and validity; costs checked |
| M3 - Reliable public release | 135-180 min | Deploy integrated service; publish image; paraphrase, failure, and latency tests; README reproduction | Public API and pulled image work; readiness/timeout gates pass |
| M4 - Submission package | 180-220 min | Resolve defects; run clean setup; finish README; record video; assemble manifest | Candidate commit/image and complete evidence captured |
| M5 - Freeze and submit | 220-240 min | External smoke checks; verify artifact access; submit official form; retain receipt | Submission recorded before deadline; service stays available |

Start README and container configuration during M0-M1. Do not leave image publishing or provider setup until the final 20 minutes. Record a short technical video; elaborate editing is unnecessary.

## 6. Task register

Statuses: `TODO`, `IN_PROGRESS`, `BLOCKED`, `VERIFY`, `DONE`. Priorities: `P0` = required delivery or correctness; `P1` = quality improvements after P0 works; `P2` = optional and deferrable. All tasks below are TODO until supported by evidence.

| ID | Priority | Task / completion condition | Owner role | Depends on | Target | Status |
|---|---|---|---|---|---|---|
| T01 | P0 | Establish project environment, dependencies, gitignore | Lead | None | M0 | DONE |
| T02 | P0 | Service skeleton, health endpoint, schemas and invalid-request handling | Lead | T01 | M0 | DONE |
| T03 | P0 | Real model access, structured extraction and complete note mapping | Language | T01 | M1 | DONE |
| T04 | P0 | Deterministic directive guards; reject invalid shapes/ranges/enums | Language | T02, T03 | M1 | DONE |
| T05 | P0 | Effective solar, reserves, rate prohibitions and grid-cap compilation | Optimization | T02; interface with T04 | M2 | DONE |
| T06 | P0 | Full-horizon solver with balance, rates, bounds, one action/hour, neutrality | Optimization | T05 | M2 | DONE |
| T07 | P0 | Independent replay and aggregate recalculation | QA | T02; output interface | M1-M2 | DONE |
| T08 | P0 | Integrate pipeline; exact response schema and honest explanations | Lead | T04, T06, T07 | M2 | DONE |
| T09 | P0 | Run all public inputs; compare reference semantics, validity and cost | QA | T08 | M2 | DONE |
| T10 | P0 | Test paraphrases, malformed inputs/model output and provider failures | Language + QA | T08 | M3 | DONE |
| T11 | P0 | Build and publish secret-free image; verify pulled-image startup/sample | QA | T02, T08 | M3 | BLOCKED |
| T12 | P0 | Public deployment; externally test both endpoints and actual model access | QA | T08 | M3 | DONE |
| T13 | P0 | Measure cold start, repeated-call p95 and failures; remain within timeout | QA | T12 | M3 | VERIFY |
| T14 | P0 | Complete README/configuration and fresh-environment reproduction | Lead + QA | T09, T11, T12 | M4 | VERIFY |
| T15 | P0 | Record and verify accessible architecture/run-test video <= 3:00 | Lead | T08, T14 | M4 | TODO |
| T16 | P0 | Freeze artifacts, fill manifest, submit and retain confirmation | Lead | T09-T15 | M5 | BLOCKED |
| T17 | P0 | Make repository public after deadline; maintain evaluation availability | Lead | T16; deadline passed | Post-deadline | TODO |
| T18 | P1 | Improve latency toward p95 <= 5s and extend paraphrase coverage | Language + QA | T13 | Before freeze if time | IN_PROGRESS |
| T19 | P2 | Optional visualization/demo polish | Lead | All P0 gates | Only if time | TODO |

Critical path: schema -> model interpretation -> deterministic validation -> constraints/solver -> replay -> integrated public regression -> deployed/container verification -> submission.

## 7. Module boundaries and implementation controls

Module responsibilities:
- `app/main.py`: FastAPI routes, health endpoint, custom 400/500 exception handlers.
- `app/config.py`: Pydantic BaseSettings, secret-masking dictionary, environment loading.
- `app/schemas.py`: Exact request and response models with strict validation and finite checks.
- `app/interpreter.py`: NVIDIA NIM Llama 3.2 Vision client with 1-shot repair retry and bounded timeouts.
- `app/guardrails.py`: Deterministic validation, type/range checks, and end-exclusive window enforcement.
- `app/constraints.py`: Pure constraint compiler for effective solar, reserves, grid caps, and rate limits.
- `app/optimizer.py`: 96-variable continuous linear program using SciPy HiGHS (`linprog(method='highs')`).
- `app/replay.py`: Independent physics and continuity schedule replay validator.
- `app/response.py`: Reconciled totals calculation and factual plan summary generator.
- `tools/run_public_cases.py`: 10-case public regression runner (offline and live).
- `tools/benchmark_api.py`: Latency, throughput, and reliability benchmark utility.

## 8. Release gates and evidence dashboard

| Gate | Pass condition | Current result | Evidence / revision |
|---|---|---|---|
| G1 - Contract | Both endpoints, required fields, 24 unique hours, invalid-input responses correct | PASS | Included in 78-case suite; zero-capacity boundary covered |
| G2 - Interpretation | All public note semantics correct; all six types and paraphrases covered | PASS | Production interpreter 10/10 public semantics; live paraphrase tests passed |
| G3 - Guardrails | Invalid model data rejected; correct mapping/order/applies/ranges enforced | PASS | Exact top-level, entry, and adjustment shapes covered by tests |
| G4 - Physics/directives | All 10 public plans pass ground-truth replay and end-of-day neutrality | PASS | 10/10 public plans pass `app/replay.py` in live regression |
| G5 - Cost/totals | Public costs equivalent within tolerance; all reported totals recalculate | PASS | Delta: 0.0000 BDT across all 10 public cases |
| G6 - Reliability | Ready <=60s, request time <=30s, no normal valid-request failures | VERIFY | Live 10-case run: p50 6.43s, p95/max 13.31s, 10/10 success; repeated/cold sample still needed |
| G7 - Public service | Both endpoints work from outside development environment | PASS | Render health 200 and SAMPLE-01 full request passed externally at 22:35 +06 |
| G8 - Docker | Exact registry reference pulls, starts, becomes healthy and handles a sample | BLOCKED | Dockerfile exists; Docker unavailable locally and no registry reference exists |
| G9 - Documentation | Fresh run succeeds using README only; no undocumented steps | VERIFY | README corrected and commands documented; independent clean-room run pending |
| G10 - Submission | Required artifacts accessible, video <=3:00, submission receipt recorded | BLOCKED | Image, video URL, submission destination, and receipt are missing |

Regression scorecard:

| Metric | Target | Measured |
|---|---|---|
| Public interpretation passes | 10/10 scenarios | 10/10 passed (Live NVIDIA NIM) |
| Public schedule validity passes | 10/10 scenarios | 10/10 passed independent replay |
| Public equivalent optimal costs | 10/10 scenarios | 10/10 exact matches (0.0000 BDT delta) |
| Paraphrase cases | Team-written cases covering all six types | 5/5 passed |
| Health ready time | <=60 seconds | < 1 second |
| Maximum optimization duration | <=30 seconds | 13.31 seconds (10-case live local run) |
| p95 optimization duration | <=5 seconds target | 13.31 seconds (10-case live local run) |
| Valid-request failure rate | 0% team test target | 0% failures on valid requests |
| Clean source / Docker reproduction | Both pass | Source tests pass; Docker not run |

Record latency sample count, warm/cold conditions, provider/model, and environment with the result. Never report a p95 without identifying the request set measured.

## 9. Risk register

| ID | Risk / impact | Priority | Prevention or response | Owner | State |
|---|---|---|---|---|---|
| R01 | Model missing from interpretation; shortlist ineligibility | Critical | Verify real model-to-directive path and document it | Language | Open |
| R02 | Paraphrase, time, percent or distractor misread | High | Semantic tests; explicit remaining-factor and end-exclusive rules | Language | Open |
| R03 | Correct extraction not enforced by solver | High | Ground-truth replay of all active constraints | Optimization + QA | Open |
| R04 | Invalid energy balance, battery states or final neutrality | High | Independent hourly replay; tight internal precision | Optimization | Open |
| R05 | Provider quota, failure or latency breaks judged calls | High | Early deployed call, quota check, bounded retry budget, measured latency | Language + QA | Open |
| R06 | Public URL sleeps/fails or model unavailable in deployment | High | Deploy early; external cold-start and repeated real calls | QA | Open |
| R07 | Registry image cannot be pulled or needs undocumented setup | High | Test exact remote image reference and documented run command | QA | Open |
| R08 | Deadline spent on extras; required artifacts incomplete | High | Freeze scope; reserve M4-M5 for docs, video and submission | Lead | Open |
| R09 | Secrets committed, embedded or exposed | High | Runtime configuration; inspect source/image/logs/errors | Lead | Open |
| R10 | Ambiguous overlapping solar or overnight semantics | Medium | Log organizer clarification; isolate normalization policy | Lead | Open |
| R11 | Wrong repository timing/visibility or missed submission | High | Confirm event instructions; record timestamps and receipt | Lead | Open |
| R12 | Tests validate own wrong interpretation or overfit examples | High | Compare reference semantics; add unseen phrasing/numeric cases | QA | Open |

## 10. Decisions, assumptions and blockers

| ID | Item | State / rationale | Owner / next action |
|---|---|---|---|
| D01 | API-first preliminary scope | Planning baseline from official endpoint/judging requirements | Lead maintains scope |
| D02 | LLM -> guards -> optimizer -> replay separation | Required processing behavior; modules proposed to make it testable | All roles follow boundary |
| D03 | No mandatory frontend or database | Scope decision; neither is required in supplied contract | Revisit only after P0 gates |
| D04 | Framework, solver, model and host | Proposed Python/FastAPI + SciPy HiGHS; configured NVIDIA model candidate; host open | Verify setup/model in plan phases 1 and 3; delivery in phase 8 |
| D05 | Signed battery LP and independent replay | Proposed lossless formulation with 96 continuous variables; detailed in PRD section 7 and implementation-plan phases 4-5 | Optimization implements; QA validates ground-truth schedules and costs |
| A01 | Four-hour relative plan | Proposed planning schedule, not confirmed event date/timezone | Lead confirms announcement |
| Q01 | Team size/names | Not supplied | Assign roles before implementation |
| Q02 | Submission channel, event date/timezone, evaluation end | Not established by these files | Confirm official instructions |
| Q03 | Overlapping solar and overnight windows | Semantics not explicit in supplied pack | Seek organizer clarification if relevant |
| Q04 | Zero-optimum formula edge | Source text cut off in PG p. 7 | Clarify only if calculating this score |

Current setup status: the local model, SciPy optimizer, replay, tests, and Render service have been exercised. Registry access/Docker runtime, video hosting, submission destination, and team/contact details remain open delivery actions.

Change log format for future decisions: `timestamp | decision/change | source or reason | affected PRD IDs/tasks | owner | verification needed`. Update the PRD and this file together when requirements change. Preserve the original source documents.

## 11. Final submission checklist

- [x] Public base URL serves both exact endpoints without login, VPN, or manual steps.
- [x] Real model interpretation, guardrails, all directives and final replay are enabled in the deployed build.
- [x] Public regression, paraphrase, error, and timing evidence is recorded in the repository.
- [ ] Source repository timing is compliant and it remains private until the submission deadline.
- [ ] README covers clean setup, model/provider, environment-variable names, solver, dependencies/credits, exact start command, endpoint examples, public tests, limitations and secret handling.
- [ ] Registry image has an exact tag/digest, documented port, `0.0.0.0` bind, no embedded secrets, and a verified pull/run path.
- [ ] Clean source setup and pulled-image setup each process at least one complete public sample.
- [ ] Video is organizer-accessible, <=3:00, and explains the problem, pipeline, approach and run/test flow.
- [ ] Submission form contains all required URLs/references and no secret values.
- [ ] Submission is complete before the official deadline and receipt is saved.
- [ ] Repository is made public after the deadline as required.
- [ ] API, model access, image and video remain available throughout evaluation.

### Submission manifest

| Item | Final value |
|---|---|
| Team name and contact | TBD |
| API base URL | https://bup-hackaton.onrender.com |
| Health URL | https://bup-hackaton.onrender.com/health |
| Optimization URL | https://bup-hackaton.onrender.com/optimize-energy |
| Repository URL | https://github.com/Rabetul-islam-asif/Bup-hackaton.git |
| Candidate application commit | b9d16ff |
| Image reference / digest | ghcr.io/rabetul-islam-asif/gridwise:latest |
| Documented service port | 8000 |
| Provider / model identifier | NVIDIA (meta/llama-3.2-11b-vision-instruct) |
| Required environment-variable names only | NVIDIA_API_KEY, NVIDIA_MODEL |
| README location | `/README.md` |
| Video URL / file and duration | TBD |
| Last external verification time | 18 September 2026, 22:49 Asia/Dhaka; health (610ms) and SAMPLE-01 (exact match, schema, replay, aggregates) verified |
| Submission time and receipt | TBD |
| Post-deadline repository visibility verified | TBD |

## 12. Handoff template and immediate next actions

At each handoff, record:

```text
Timestamp / member:
Completed task IDs and tested revision:
Evidence and test results:
Known failures / blockers:
Next task and owner:
Deployment / image / configuration changes:
Time remaining to confirmed deadline:
```

Next actions: commit and deploy the verified working tree; confirm the updated Render revision; build and publish a registry image from a Docker-capable environment; record and upload the <=3:00 video; fill team/contact and submission destination; submit and save the receipt; make the repository public only after the official deadline.

## 13. Document change history

| Version | Date | Change |
|---|---|---|
| 1.0 | 18 September 2026 | Created from both supplied PDFs and the 10-case JSON pack; recorded official requirements, proposed execution plan, open details, and unrun verification gates |
| 1.1 | 18 September 2026 | Added complete ten-phase implementation plan and traceability; synchronized PRD signed-battery LP proposal; recorded environment-variable presence and passing preliminary offline tooling checks without claiming live/API readiness |
| 1.2 | 18 September 2026 | Replaced unsupported readiness claims with measured 78-case, offline/live ten-case, and external Render evidence; marked Docker, video, submission, and clean-room verification honestly outstanding |
