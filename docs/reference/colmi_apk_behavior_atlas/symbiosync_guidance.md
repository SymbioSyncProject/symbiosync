# Implementation guidance for SymbioSync

## Core principle

Copy verified transport behavior. Do not copy vendor certainty.

Every biometric-adjacent value should carry provenance:

- transport: UART, LargeData, cloud, local DB, app-generated
- mode: live/manual, historical/device-sync, cloud-sync, synthetic, inferred
- stage: command sent, transport accepted, response parsed, value decoded
- freshness: current, stale, unavailable, historical
- source claim: device-reported, vendor-app-generated, SymbioSync-inferred, unknown

## Recommended implementation order

1. Improve raw evidence and request/result logging for Colmi packets.
2. Query and expose capability bitfields conservatively.
3. Implement manual/live HR, SpO2, and HRV with truthful stages.
4. Reconcile SpO2 historical commands before implementing historical SpO2.
5. Implement historical HR/HRV/sleep/temperature as stored history, not current body-state.
6. Keep OneKey out of normal health surfaces unless marked as synthetic/vendor-composite.

Run 4 / next research round should focus on SpO2 historical reconciliation, not
general APK wandering: `BloodOxygenRepository.syncAutoBloodOxygen(0/255)` and
LargeData cmd `0x2A` versus SDK interval oxygen cmd `0x5F`.

## Internal shape

Even if implemented in one file at first, keep conceptual boundaries clear:

- UART small-data commands
- LargeData commands
- measurement lifecycle orchestration
- capability/settings mapping
- storage/history parsing
- provenance/truth wrapping

## User-facing rule

Never display a Colmi value without enough context to answer:

- Where did this come from?
- When was it captured?
- Is it current or historical?
- Is it device-reported or generated?
- What stage of delivery/parsing was actually observed?
