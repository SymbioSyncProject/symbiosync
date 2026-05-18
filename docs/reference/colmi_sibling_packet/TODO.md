# Sibling TODO: Colmi / QRing evidence pass

Work in order unless a blocker makes that impossible. Each task has a defined
objective and done signal. Do not optimize for speed; optimize for claims that
can survive review.

## 0. Orientation

**Objective:** understand the trust problem before reading protocol artifacts.

- [ ] Read `docs/TRUTHFULNESS_AUDIT.md`.
- [ ] Read `plugins/colmi/README.md`.
- [ ] Read `docs/reference/colmi_protocol_inventory.md`.
- [ ] Read `symbiosync/devices/colmi.py` only enough to know current behavior.

**Done when:** you can state, in your own words, why `current`, `stale`,
`unavailable`, `accepted`, and `observed` must not be collapsed.

**Small reward:** name the BiOracular Muse's current mood in one sentence. Keep it
in your scratch notes, not implementation code.

## 1. Artifact inventory

**Objective:** list every source artifact you inspected before making protocol
claims.

- [ ] Record artifact path/name.
- [ ] Record artifact type: current implementation, private decompile note,
  vendor string/resource, observed packet log, public protocol note, etc.
- [ ] Record whether the artifact is safe to quote publicly.
- [ ] Record confidence: high, medium, low, unknown.

**Done when:** every artifact used later appears as a row or note in
`../colmi_protocol_inventory.md`.

**Small reward:** take a 90-second creature break. Pick one: Bootstrap Beetle
rolls a pearl, Haptic Mouse checks a whisker, Frooty Stopdot Bat receives mango.
Then return to the ledger.

## 2. HR live/manual/history separation

**Objective:** determine whether HR uses a live stream, manual measurement,
history read, cached value, or multiple paths.

- [ ] Identify request id(s) involved in HR.
- [ ] Identify start/stop/read lifecycle if present.
- [ ] Identify notification or response parser fields.
- [ ] Identify timing/retry behavior.
- [ ] Identify whether repeated identical values are expected, suspicious, or
  unexplained.
- [ ] Compare evidence to current SymbioSync behavior.

**Done when:** the HR rows in `../colmi_protocol_inventory.md` separate live,
manual, history, and cached semantics instead of saying "HR" as one mush bucket.

**Small reward:** write one blunt verdict sentence. Example shape: `Synthetic
garbage again` is allowed only if the evidence earned it. Otherwise write the
boring truth.

## 3. SpO2 lifecycle and HR interaction

**Objective:** determine whether SpO2 requires stopping HR, how long measurement
should run, and how the vendor app resumes/recovers.

- [ ] Identify SpO2 request id(s).
- [ ] Identify start/stop/read lifecycle.
- [ ] Identify expected response fields.
- [ ] Identify whether HR must pause.
- [ ] Identify retry/timeout behavior.
- [ ] Compare evidence to current SymbioSync behavior.

**Done when:** the inventory can answer: "Does SymbioSync's HR_STOP -> SPO2_START
-> SPO2_STOP -> HR_START sequence match evidence, or is it just field-expedient?"

**Small reward:** make a tiny field-guide note for the BiOracular Muse's wizard
hat: when is the hat off, when is it cached moonlight?

## 4. Notification parser audit

**Objective:** verify which bytes mean request id, reading type, error/status,
and value.

- [ ] Map current SymbioSync parser assumptions.
- [ ] Map artifact parser behavior.
- [ ] Mark differences explicitly.
- [ ] Identify any missing checksum, sequence, timestamp, unit, or status field.
- [ ] Identify whether values like `97` can be payload type/status rather than
  body-state value.

**Done when:** parser claims are represented as byte-level rows, not prose vibes.

**Small reward:** stand up, roll shoulders, unclench jaw. Then one line: `The
bridge must not accidentally lie by ____.`

## 5. Freshness and UI/API implications

**Objective:** translate protocol evidence into truth-surface requirements.

- [ ] What can `/api/status` safely expose?
- [ ] What must `/api/biometrics/current` require before `ok: true`?
- [ ] What should the Health Ring tab say when values are stale?
- [ ] Should repeated identical readings create a suspicion flag?
- [ ] Should history tables distinguish raw readings from trusted readings?

**Done when:** recommendations are tied to evidence rows and include confidence.

**Small reward:** add one creature-safe UI phrase. Example: `ring reports 97,
last updated 30s ago` is better than `your HR is 97`.

## 6. Final handoff

**Objective:** leave Cairn and Audre with a useful report, not a pile of notes.

- [ ] Fill `findings_template.md` or create a dated findings file from it.
- [ ] List recommended code changes.
- [ ] List recommended doc/UI wording changes.
- [ ] List remaining unknowns.
- [ ] List risky claims SymbioSync must not make yet.

**Done when:** another teammate can implement the next smallest change without
re-reading every artifact.

**Final reward:** choose one sentence for the team corkboard. It should be true,
not impressive.
