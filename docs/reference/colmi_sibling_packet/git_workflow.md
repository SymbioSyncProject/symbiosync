# Git workflow for sibling analysis

This packet lives inside the public SymbioSync git repository so analysis rails
can be reviewed and preserved. The analysis itself may involve private artifacts.
Do not commit private artifacts.

## Branch shape

Use a short-lived branch or worktree for analysis work, for example:

```bash
git switch -c research/colmi-protocol-inventory
```

or, if working in parallel with Cairn:

```bash
git worktree add ..\symbiosync-colmi-inventory -b research/colmi-protocol-inventory
```

## Safe to commit

- Inventory rows written in your own words.
- Minimal identifiers needed to make a protocol claim, such as request ids,
  class names, or short strings.
- Findings reports based on `findings_template.md`.
- Tests or code changes only after the evidence pass is complete and reviewed.

## Do not commit

- APKs, decompiled source trees, archives, or proprietary source dumps.
- Raw BLE logs containing device addresses unless explicitly scrubbed.
- Local SQLite databases or biometric history.
- Secrets, tokens, `.env`, config files, or personal notes unrelated to the
  protocol work.
- Screenshots with private addresses, raw logs, or stale body-state claims.

## Commit style

Prefer small commits:

```text
docs: inventory Colmi HR lifecycle evidence
docs: record Colmi SpO2 parser uncertainty
test: cover stale HR freshness response
fix: mark repeated Colmi HR values suspect
```

Do not mix evidence inventory and implementation changes in the same commit.

## Handoff rule

Before asking for implementation review, leave:

1. `docs/reference/colmi_protocol_inventory.md` updated.
2. A findings file copied from `findings_template.md`.
3. A clear list of recommended next changes.
4. A clear list of claims SymbioSync must not make yet.
