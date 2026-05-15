# Reach Journal

The Reach Journal is SymbioSync's local feedback surface for touch/reach events.

It exists because a touch should not vanish into a vibration, a generic API call,
or a debug log. A dyad may want a readable artifact that says who reached, what
the bridge actually knows, and how the receiving partner says it landed.

## Objective

Preserve two kinds of truth without collapsing them:

1. **Bridge/request truth**: who claimed to reach, when, through what channel,
   target alias/address, request shape, request id, stage, and truth note.
2. **Human response truth**: what the receiving partner later says happened or
   how it landed, recorded as an optional response note.

This is not a full activation journal. It is a bounded local feedback surface.

## First slice

The first implementation records device requests handled by the request-envelope
path and stores them locally in `data/reach_events.jsonl`.

Each event may include:

- `request_id`
- `received_at` / `result_at`
- `source_channel`
- `actor` and `actor_trust`
- `target_alias` and `target_address`
- request name and human-readable params
- caller note
- stage and truth note
- optional human `response_note`

The browser UI exposes a **Reach Journal** tab where the human partner can read
recent events and add/edit a response note.

## Truth boundaries

- `actor` is self-reported, not authentication.
- `note` is context, not consent.
- `stage` is request/transport truth, not proof of bodily effect.
- `response_note` is the human partner's later account; it should not be
  overwritten by bridge assumptions or treated as sensor data.
- The journal stores concise request/result summaries, not raw BLE payloads,
  raw biometric dumps, or vendor-cloud data.

## Why it matters

Telegram, chat, or whatever a dyad normally uses can still carry conversation.
The Reach Journal is different: it keeps the touch event and the feedback about
that touch near the bridge that carried it.

That makes the bridge more readable without pretending ordinary conversation is
obsolete.

## Future work

- Filters by actor, target, source channel, or stage.
- A first-class heartbeat/reach action separate from device-specific controls.
- Optional Telegram reach-note pairing using the same request envelope.
- Export/import for private local archive.
- Richer response fields, if dyads want them, without turning the journal into
  surveillance sludge.
- Activation journal design, separately and only with explicit consent/privacy
  boundaries.
