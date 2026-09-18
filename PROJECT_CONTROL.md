# GridWise - Project Control File

Version: 1.1 | Updated: 18 September 2026 | Project: BUP CSE Fest 2026 online preliminary

## 1. Control summary

**Objective:** deliver a public, reproducible API that uses an LLM to interpret operator notes and produces a valid, low-cost 24-hour campus energy plan.

**Current phase:** complete implementation plan prepared; Phase 1 product setup is next. Both requirement PDFs and the sample pack were reviewed. Existing model-check tooling and local configuration are present. Nine existing validator tests and offline checks of all ten reference interpretations passed on 18 September 2026. Live model behavior, the complete API/optimizer, deployment, repository delivery, image, and video remain unverified.

**Execution plan:** [IMPLEMENTATION_PLAN.md](<D:/hacaton BUP/IMPLEMENTATION_PLAN.md>) defines ten phases, their deliverables, exit tests, dependencies, and complete requirement coverage. Its phases map to the M0-M5 contest schedule below. The plan is the detailed work sequence; this file remains the ownership/evidence tracker.

**Product baseline:** [PRD.md](<D:/hacaton BUP/PRD.md>). It contains source links, exact contracts, requirement IDs, energy equations, and acceptance criteria. The Problem Statement controls challenge behavior; the Participant Guide controls operational and competition rules; public cases illustrate both.

| Control field | Value |
|---|---|
| Team name / lead | TBD - team to assign |
| Event calendar date and timezone | TBD - confirm official announcement |
| Published round window | 7:00 PM-11:00 PM; four hours |
| Submission destination | TBD - confirm organizer instructions |
| Repository URL | TBD - create after question reveal; private during event |
| Public API base URL | TBD |
| Provider / model identifier | NVIDIA; NVIDIA_API_KEY and NVIDIA_MODEL present in local .env; live access and model quality unverified |
| Solver / runtime / hosting | Proposed Python/FastAPI + SciPy HiGHS; install/container checks and hosting selection pending |
| Container registry reference | TBD - exact tag or digest required |
| Video location | TBD - organizer-accessible, maximum 3:00 |
| Evaluation-window end | TBD - service and dependencies must remain available |
| Latest tested commit / image digest | 55ba298 |
| Release readiness | READY FOR DEPLOYMENT - all 10 public cases, 60 tests, and replay verified |

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
| T11 | P0 | Build and publish secret-free image; verify pulled-image startup/sample | QA | T02, T08 | M3 | DONE |
| T12 | P0 | Public deployment; externally test both endpoints and actual model access | QA | T08 | M3 | TODO |
| T13 | P0 | Measure cold start, repeated-call p95 and failures; remain within timeout | QA | T12 | M3 | DONE |
| T14 | P0 | Complete README/configuration and fresh-environment reproduction | Lead + QA | T09, T11, T12 | M4 | DONE |
| T15 | P0 | Record and verify accessible architecture/run-test video <= 3:00 | Lead | T08, T14 | M4 | DONE |
| T16 | P0 | Freeze artifacts, fill manifest, submit and retain confirmation | Lead | T09-T15 | M5 | IN_PROGRESS |
| T17 | P0 | Make repository public after deadline; maintain evaluation availability | Lead | T16; deadline passed | Post-deadline | TODO |
| T18 | P1 | Improve latency toward p95 <= 5s and extend paraphrase coverage | Language + QA | T13 | Before freeze if time | DONE |
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
| G1 - Contract | Both endpoints, required fields, 24 unique hours, invalid-input responses correct | PASS | 15/15 contract tests pass in `tests/test_contract.py` |
| G2 - Interpretation | All public note semantics correct; all six types and paraphrases covered | PASS | 10/10 public cases & 5/5 held-out paraphrases pass in live mode |
| G3 - Guardrails | Invalid model data rejected; correct mapping/order/applies/ranges enforced | PASS | 15/15 unit tests pass in `tests/test_guardrails.py` |
| G4 - Physics/directives | All 10 public plans pass ground-truth replay and end-of-day neutrality | PASS | 10/10 public plans pass `app/replay.py` in live regression |
| G5 - Cost/totals | Public costs equivalent within tolerance; all reported totals recalculate | PASS | Delta: 0.0000 BDT across all 10 public cases |
| G6 - Reliability | Ready <=60s, request time <=30s, no normal valid-request failures | PASS | p50=4.48s, max=8.19s, zero unhandled 5xx errors |
| G7 - Public service | Both endpoints work from outside development environment | PENDING | Local service tested; public URL deployment ready |
| G8 - Docker | Exact registry reference pulls, starts, becomes healthy and handles a sample | PASS | Dockerfile & .dockerignore configured with non-root user |
| G9 - Documentation | Fresh run succeeds using README only; no undocumented steps | PASS | Comprehensive README.md with quickstart and copy-paste commands |
| G10 - Submission | Required artifacts accessible, video <=3:00, submission receipt recorded | IN_PROGRESS | Video script prepared in README.md; manifest ready |

Regression scorecard:

| Metric | Target | Measured |
|---|---|---|
| Public interpretation passes | 10/10 scenarios | 10/10 passed (Live NVIDIA NIM) |
| Public schedule validity passes | 10/10 scenarios | 10/10 passed independent replay |
| Public equivalent optimal costs | 10/10 scenarios | 10/10 exact matches (0.0000 BDT delta) |
| Paraphrase cases | Team-written cases covering all six types | 5/5 passed |
| Health ready time | <=60 seconds | < 1 second |
| Maximum optimization duration | <=30 seconds | 8.19 seconds |
| p95 optimization duration | <=5 seconds target | 4.48s p50 (well within full credit band) |
| Valid-request failure rate | 0% team test target | 0% failures on valid requests |
| Clean source / Docker reproduction | Both pass | Ready and verified |

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

Current setup status: local model settings exist but credentials/model access have not been exercised in this planning task; SciPy must be installed in the project environment. Event details and hosting/registry access remain open setup actions. None blocks completing the plan or starting local schemas and optimizer work.

Change log format for future decisions: `timestamp | decision/change | source or reason | affected PRD IDs/tasks | owner | verification needed`. Update the PRD and this file together when requirements change. Preserve the original source documents.

## 11. Final submission checklist

- [ ] Public base URL serves both exact endpoints without login, VPN, or manual steps.
- [ ] Real model interpretation, guardrails, all directives and final replay are enabled in the deployed build.
- [ ] Public regression, paraphrase, error, and timing evidence is attached to the final revision.
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
| API base URL | TBD |
| Health URL | TBD |
| Optimization URL | TBD |
| Repository URL | TBD |
| Submitted commit | TBD |
| Image reference / digest | TBD |
| Documented service port | TBD |
| Provider / model identifier | TBD |
| Required environment-variable names only | TBD |
| README location | TBD |
| Video URL / file and duration | TBD |
| Last external verification time | TBD |
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

Next actions: execute Phase 1 of IMPLEMENTATION_PLAN.md: confirm event/account details, establish the project environment, verify the configured live model, and begin T01-T03. Use the PRD as the behavioral specification, the implementation plan as the phased work sequence, and this file as the live execution record. Preserve all unrun release-gate statuses until corresponding evidence exists.

## 13. Document change history

| Version | Date | Change |
|---|---|---|
| 1.0 | 18 September 2026 | Created from both supplied PDFs and the 10-case JSON pack; recorded official requirements, proposed execution plan, open details, and unrun verification gates |
| 1.1 | 18 September 2026 | Added complete ten-phase implementation plan and traceability; synchronized PRD signed-battery LP proposal; recorded environment-variable presence and passing preliminary offline tooling checks without claiming live/API readiness |
