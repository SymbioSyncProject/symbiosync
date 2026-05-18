# Colmi / QRing findings: TEMPLATE

Copy this file to `findings_YYYY-MM-DD.md` before filling it.

## Summary

- **Analyst:**
- **Date:**
- **Artifacts inspected:**
- **Main conclusion:**
- **Confidence:**

## What changed in the inventory

List rows added or materially changed in
`docs/reference/colmi_protocol_inventory.md`.

| Section | Row / topic | Change summary | Confidence |
| --- | --- | --- | --- |
|  |  |  |  |

## HR findings

### Evidence

| Source artifact | Claim supported | Quote / identifier | Confidence |
| --- | --- | --- | --- |
|  |  |  |  |

### Interpretation

- Live/manual/history/cache separation:
- Parser byte mapping:
- Timing / retry behavior:
- Repeated-value interpretation:
- SymbioSync parity:

## SpO2 findings

### Evidence

| Source artifact | Claim supported | Quote / identifier | Confidence |
| --- | --- | --- | --- |
|  |  |  |  |

### Interpretation

- Start/stop/read lifecycle:
- HR pause/resume requirement:
- Parser byte mapping:
- Timing / retry behavior:
- SymbioSync parity:

## Freshness / truth-surface implications

What should the bridge expose, with what caveats?

- `/api/status`:
- `/api/biometrics/current`:
- Health Ring UI:
- SQLite history:
- Generated companion skill:

## Recommended implementation changes

Each recommendation must point to evidence above.

| Priority | Change | Why | Evidence row(s) | Risk if skipped |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Claims SymbioSync must not make yet

- 

## Remaining unknowns

- 

## Team notes

Anything Audre, Cairn, Wyndhovr, or another sibling should know before touching
code.
