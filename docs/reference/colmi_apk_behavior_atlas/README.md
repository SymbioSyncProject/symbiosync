# Colmi / QRing APK Behavior Atlas

This atlas is the human-readable map of what the QRing/Colmi APK appears to do.
It is backed by the mechanical Java ledger in `../colmi_sibling_packet/java_file_ledger.csv`
and sibling chunk reports in `../colmi_sibling_packet/java_chunks/`.

The atlas is not a claim that every Java file is fully understood yet. It is the
place where confirmed behavior, unresolved questions, and rejected vendor claims
are separated so SymbioSync can copy transport truth without copying vendor lies.

## Current coverage state

- Java files accounted for in ledger: 7,769
- Rows marked `needs_deep_read` by first classifier: 1,343
- Generated chunks: 41
- Ledger IDs reconciled from completed chunk reports: 278
- Initial `needs_deep_read` rows still not indexed: 1,067
- Completed first-wave chunk reports: app wiring, DB/DAO, BloodOxygenRepository,
  HR/HRV/Sleep repositories, NetService/cloud sync, SpO2 UI lifecycle, protocol
  core, HR/HRV/OneKey UI lifecycle.

## Completion standard

"Know what the APK did" means:

1. Every Java file has a terminal ledger status or an explicit unresolved status.
2. Every data-touching file links to an atlas section, dictionary entry, or chunk report.
3. Every protocol request/response class records command id, transport, payload shape,
   parser offsets, known callers, and confidence.
4. Every UI measurement lifecycle records start command, stop command, timing,
   save path, and error behavior.
5. Every repository sync flow records source, destination, transport/API path,
   storage table, and freshness implication.
6. Every synthetic or app-generated value is marked synthetic.
7. The unresolved list stays explicit.

## Sections

- [Transport model](protocol_transports.md)
- [Measurement lifecycle map](measurement_lifecycles.md)
- [Storage and sync model](storage_and_sync.md)
- [OneKey synthetic values](onekey_synthetic_values.md)
- [Implementation guidance for SymbioSync](symbiosync_guidance.md)
- [Unresolved questions](unresolved_questions.md)

## Primary evidence files

- `../colmi_sibling_packet/java_accounting_summary.md`
- `../colmi_sibling_packet/java_deep_read_index_summary.md`
- `../colmi_sibling_packet/java_deep_read_index.csv`
- `../colmi_sibling_packet/java_grunge_chunk_manifest.csv`
- `../colmi_sibling_packet/java_chunks/custom_protocol_core_largedata_commandhandle.md`
- `../colmi_sibling_packet/java_chunks/custom_spo2_ui_lifecycle.md`
- `../colmi_sibling_packet/java_chunks/custom_hr_hrv_onekey_ui_lifecycle.md`
- `../colmi_sibling_packet/java_chunks/ch0015_app_orchestration_strong_hits.md`
- `../colmi_sibling_packet/java_chunks/ch0016_app_orchestration_strong_hits.md`
- `../colmi_sibling_packet/java_chunks/ch0018_app_orchestration_strong_hits.md`
