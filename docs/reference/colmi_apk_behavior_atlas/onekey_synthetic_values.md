# OneKey synthetic values

The vendor OneKey flow is a trust-surface hazard.

## What the APK appears to do

OneKey starts a composite measurement using:

```text
StartHeartRateReq.getSimpleReq((byte)5)
StopHeartRateReq.stopHealthCheck()
notify/listener type 105
```

Device-derived values:

- HR from `StartHeartRateRsp.getValue()`
- BP from `StartHeartRateRsp.getSbp()` / `getDbp()`

Phone-generated values:

- SpO2 randomly selected from `{96, 97, 98, 99}`
- wellness score as `Random.nextInt(4) + 96`
- fatigue as a time-of-day pseudo-random value

These values are saved together in the OneKey result object, without a clear
measured-vs-generated boundary.

## SymbioSync decision

Do not implement OneKey as a normal health feature.

If OneKey is exposed at all, expose it as a vendor composite experiment with
per-field provenance:

```json
{
  "domain": "spo2",
  "value": 98,
  "source": "vendor_app_generated",
  "synthetic": true,
  "measured": false,
  "truth_note": "Vendor APK appears to randomly generate OneKey SpO2. Do not treat as device measurement."
}
```

This finding is the clearest example of why SymbioSync must copy protocol truth,
not vendor claims.
