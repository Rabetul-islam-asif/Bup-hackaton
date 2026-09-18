# NVIDIA model response check

This check measures note-to-directive interpretation only. It validates the exact
machine-readable fields against all 10 organizer examples. It does not validate
the energy optimizer or prove performance on hidden cases.

## 1. Replace the exposed key

Revoke any NVIDIA key that was pasted into chat or source code and generate a new
one. Never paste the replacement into a file in this repository.

In PowerShell, configure the new key only for the current terminal:

```powershell
$env:NVIDIA_API_KEY = Read-Host "Fresh NVIDIA API key"
$env:NVIDIA_MODEL = "meta/llama-3.2-11b-vision-instruct"
```

The input is visible while typing. For stronger local secret handling, use your
deployment platform's secret manager when the service is deployed.

## 2. Run the official sample comparison

```powershell
python tools/check_nvidia_model.py
```

Run one case while tuning:

```powershell
python tools/check_nvidia_model.py --case SAMPLE-09
```

Expected release gate: `10/10 passed`. Also inspect the reported latency. The
competition requires every optimization request to finish within 30 seconds and
awards full latency points at p95 no greater than 5 seconds. This checker times
only model calls, so the finished API will be slightly slower.

## 3. What the checker enforces

- Exactly one interpretation per operator note, in note-index order.
- Only the six official directive types.
- `no_op` uses `applies=false` and a null adjustment; all other directives use
  `applies=true` and the exact adjustment fields for their type.
- Hours are non-empty, unique, sorted integers from 0 through 23.
- Solar factor, battery reserve, and grid-cap ranges are valid.
- Directive semantics match organizer ground truth within numeric tolerance.
- Explanations may use different wording; they must be non-empty.

The request uses NVIDIA guided JSON generation and then applies deterministic
validation. Guided output improves syntax reliability but does not guarantee
correct meaning, which is why the semantic comparison remains necessary.

## 4. Release rule

Do not call a model "perfect" after one successful example. Keep this model only
if it passes all 10 official cases and additional team-written paraphrases on
repeated runs. The deployed service must reject or safely retry invalid model
output before sending directives to the optimizer.

