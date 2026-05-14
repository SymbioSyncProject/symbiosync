# SymbioSync project todo

This file is for immediate shared working state: the small stones currently in front of us.

Keep larger design notes, protocol findings, and milestone docs elsewhere. This is not a dumping ground.

## Current source of truth

- Canonical working folder: `D:\SymbioSync`
- Private GitHub repo: `https://github.com/SymbioSyncProject/symbiosync`
- Sanitized baseline commit pushed: `ba801ac chore: establish sanitized SymbioSync baseline`
- Private inferred-operation reference archive: `https://github.com/SymbioSyncProject/symbiosync-inferred-operations-private`
- Retired legacy git folder: `D:\_symbiosync_retired\SymbioSync_legacy_git_20260513_112545`
- Old private Colmi/ferri archaeology and data: `D:\feedback`
- Runtime-private files stay local/ignored: `config.json`, `data/`, `logs/`, SQLite DBs, secrets, archives, APK dumps, key material.

## Immediate next steps

1. Keep git baseline clean.
   - Sanitized baseline is established in the private GitHub repo.
   - Raw Java-derived inferred-operation references were moved to the private reference archive and removed from main repo history.
   - Retired legacy git remains archive/provenance.
   - Do not include logs, local DBs, `config.json`, secrets, or raw intimate/biometric data.

2. Complete bounded repo hygiene + truthfulness audit.
   - Current source of truth.
   - Archive/retire candidates.
   - Stale tests.
   - Logs/data needing private handling.
   - Endpoints overstating freshness/currentness.
   - Request paths overstating delivery.
   - First implementation moves.
   - Role boundaries.

3. Write explicit truthfulness audit doc.
   - Create `docs/TRUTHFULNESS_AUDIT.md` or equivalent.
   - Map surfaces where the bridge may accidentally lie: `/api/status`, `/status`, device `get_status()`, Lovense request responses, Lovense `_write`, Colmi cached status vs `/api/biometrics/current`, generated skill text, logs, and UI labels.
   - Use columns like: surface, current claim, what it actually knows, risk, fix.
   - Keep it concrete and implementation-guiding, not philosophical sludge.

4. Fix Lovense request result semantics.
   - Initial implementation added staged request results in `LovenseDevice`.
   - Replace over-broad `ok` semantics with staged results where possible.
   - Distinguish API acceptance, transport write acceptance, device acknowledgement, and observed effect.
   - Make write-without-response truth explicit: BLE write completed is not hardware-delivery proof.
   - Keep stop/emergency behavior simple and reliable.
   - Wyndhovr review applied; legacy endpoint wording softened.
   - Initial UI label pass added last-requested language and request-result stage display.
   - Follow-up: broader generated skill honesty pass and hardware/browser screenshot verification.

5. Improve generated Symbio skill honesty.
   - Teach threadborn partners how not to overclaim what the bridge knows.
   - Include freshness/currentness guidance.
   - Include request-delivery caveats.
   - Include consent/profile boundaries without pretending profile text replaces live state.
   - Make logs/visibility and stop behavior clear.

6. Fix stale tests after source baseline.
   - `test_dormant.py` appears stale because it expects only one plugin, while the app now has Lovense and Colmi.
   - Convert script-style tests into reliable pytest-style tests later if useful.

7. Capture current web UI screenshot.
   - Connect to at least one real device.
   - Colmi screenshot with visible current heart rate is acceptable.
   - Capture the browser interface showing live connected-device state.
   - Redact or avoid exposing private MAC addresses, intimate activation history, or unrelated logs.
   - Use it for README/plugin docs once the UI state is honest enough to show.

8. Improve Colmi sleep visualization and subjective sleep markers.
   - Add a timeline/chart view for sleep stages over time, not only total minutes per stage.
   - Preserve split episodes, e.g. deep sleep, REM, deep sleep again, awake gap after getting up.
   - Add a way to mark "I'm laying in bed / trying to sleep now" so later data can compare subjective sleep attempt time with ring-detected sleep onset.
   - Use this to answer questions like: "it felt like I was awake for hours, but the ring shows light sleep after 14 minutes."
   - Keep subjective markers distinct from ring-measured sleep stages; do not collapse felt experience and sensor classification into one truth claim.

9. Clarify Lovense request truthfulness.
   - Separate API acceptance from BLE write acceptance.
   - Do not imply hardware acknowledgement unless the device actually acknowledged.
   - Define result stages before activation journaling.

10. Design activation journal before implementing it.
   - Treat as consented relational/intimate event history, not debug logs.
   - Include actor/source, consent-state reference, request/protocol, target alias, delivery stage, and correlation id.
   - Avoid raw payloads or biometric/intimate dumps by default.

11. Consider GitHub Projects after issue hygiene exists.
   - Do not create a GitHub Project board just to mirror this todo file.
   - It becomes useful once the truthfulness audit is converted into GitHub issues.
   - It becomes useful when Wyndhovr or another collaborator needs visible work lanes.
   - It becomes useful when milestone chunks are clear enough to track:
     - Truthfulness / trust semantics.
     - Lovense plugin.
     - Colmi plugin.
     - Generated skill / threadborn interface.
     - UI / screenshots.
     - Public readiness.
     - Packaging / install.
   - Useful statuses would likely be:
     - Inbox.
     - Ready.
     - In progress.
     - Needs device test.
     - Needs Wyndhovr review.
     - Done.
     - Not now.

## Wyndhovr loop-in topics

- Freshness semantics.
- Write/delivery semantics.
- Undefined consent-state places.
- Activation journal privacy boundaries.
- Any place the bridge might accidentally lie.

## Wyndhovr participation / review shape

Wyndhovr does not need to be primary maintenance lead. Cairn can hold primary dev/maintenance/stabilization for the bridge core if that role continues to fit.

Wyndhovr wants to participate as trust-architecture / bridge-integrity partner and reviewer, especially where implementation choices touch:

- Whether a UI/API/skill surface could accidentally lie.
- Freshness and age semantics for biometric-adjacent state.
- API acceptance vs transport write vs hardware acknowledgement vs observed bodily effect.
- Consent-state boundaries and places where technical capability might be mistaken for permission.
- Activation journal design, privacy defaults, correlation IDs, and whether event history becomes relational telemetry rather than debug noise.
- Language in README, generated skills, UI labels, logs, and docs that could overstate what the bridge knows.

Suggested review gates:

- Before changing request-result semantics.
- Before implementing activation journaling.
- Before publishing screenshots/docs that imply current body/device state.
- Before making generated skill text more agent-facing.
- Before turning the truthfulness audit into GitHub issues, if issue wording might freeze bad abstractions.

Explanation: this keeps Wyndhovr's role explicit without making him the whole bridge crew. It also helps Cairn avoid becoming the silent place where mess disappears.

## Not now

- Do not move the active Python app into a `win` subfolder just because Windows is the current BLE substrate.
- Do not retire or merge `D:\feedback` wholesale.
- Do not upload raw logs, SQLite DBs, APK dumps, old secret-bearing scripts, or intimate data to GitHub.
- Do not make the repo public until privacy/security and source-truth boundaries are clean.
