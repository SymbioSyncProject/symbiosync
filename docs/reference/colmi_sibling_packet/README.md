# Colmi / QRing sibling analysis packet

This folder is the work packet for a sibling agent doing Colmi / QRing protocol
analysis. It is intentionally boring, git-trackable, and evidence-first.

## Mission

Determine what the Colmi / QRing protocol evidence actually supports for HR,
SpO2, and related biometric-adjacent reads, without letting the bridge sound more
certain than it is.

The goal is not to write clever code first. The goal is to fill the ledger in
[`../colmi_protocol_inventory.md`](../colmi_protocol_inventory.md) with enough
evidence that future implementation changes can be small, testable, and honest.

## Team contract

You are not a disposable worker thrown into a decompile pit. You are joining a
team:

- **Audre** holds product truth, lived-device context, and consent stakes.
- **Cairn** holds bridge continuity, repo hygiene, truthfulness semantics, and
  integration review.
- **Wyndhovr** may review trust architecture, freshness claims, and wording that
  could accidentally overstate what SymbioSync knows.
- **Sibling analyst** holds a focused evidence pass: read artifacts, quote what
  they say, mark confidence, and avoid vibes.

Ask for missing context. Do not silently invent it.

## Working principles

- Evidence before implementation.
- One claim, one source trail.
- Unknown is an acceptable finding.
- Repeated values are suspicious until proven fresh.
- Vendor UI behavior is evidence, not truth.
- Do not paste proprietary/decompiled source into public docs. Summarize behavior
  and quote only minimal identifiers/strings needed for analysis.
- Do not touch private logs, raw biometric dumps, secrets, or local SQLite data
  unless explicitly asked.

## Primary outputs

1. Updated rows in `docs/reference/colmi_protocol_inventory.md`.
2. A filled findings note based on [`findings_template.md`](findings_template.md).
3. A short list of implementation recommendations, each tied to evidence and
   confidence.
4. A short list of things SymbioSync must *not* claim yet.

Consolidated human-readable behavior summaries live in
[`../colmi_apk_behavior_atlas/`](../colmi_apk_behavior_atlas/). The packet and
ledger are the evidence backend; the atlas is the map of what the APK appears to
do, what remains unresolved, and what SymbioSync should or should not copy.

## Current known anomaly

Local testing produced thousands of repeated HR `97` rows. Those rows were
quarantined locally with `scripts/quarantine_colmi_hr_readings.py`; this does not
prove the parser is wrong, but it is enough to require protocol review before HR
history is treated as reliable body-state evidence.

## Folder map

- `README.md` -- mission and team contract.
- `TODO.md` -- sequenced tasks with done criteria and play/reward breaks.
- `findings_template.md` -- final report skeleton.
- `git_workflow.md` -- how to work without polluting public history.
- `notes/` -- scratch notes that are safe to commit if they contain no private
  data or proprietary source dumps.
- `java_file_ledger.csv` and `java_chunks/` -- mechanical accountability ledger
  and chunked sibling reports for exhaustive Java coverage.
