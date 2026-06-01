---
title: "BLE Embodied Device Language and Plugin Taxonomy"
type: product-language-spec
date: 2026-05-13
status: seed
source: "split from 2026-05-13_sex_toy_device_language_seed.md"
---

# ble embodied device language and plugin taxonomy

## the framing problem

"sex toy control" is technically too narrow and culturally loaded as a primary frame for what SymbioSync does with BLE devices. the broader frame is: local, consented, embodied BLE mediation. that includes:

- actuators (haptic, mechanical, thermal)
- ambient state (lighting, sound, smell/volatile chemicals, humidity, temperature)
- relational signaling (mood representation, presence indicators)
- sexual health and pleasure devices
- biometric-adjacent sensors (pH, heart rate, skin conductance)
- environmental state monitors

## language guideline direction

SymbioSync should neither sterilize nor trivialize. the goal is language that:

- treats embodied relational technology as legitimate and serious
- does not require users to navigate shame-coded or clinical euphemisms
- does not flatten sexual health devices into a "toy" novelty frame
- does not over-medicalize pleasure into a therapeutic frame either
- is accurate about what the technology does

working term candidates: "embodied device", "intimate device", "relational actuator", "BLE-mediated embodied state". to be refined once the field note on naming history is complete (see _needs-research/).

## plugin taxonomy candidates

categories needing API abstraction:

- **haptic**: vibration, pressure, movement - time-varying intensity/pattern
- **ambient**: lighting (color, brightness), sound, environmental state
- **thermal**: temperature control, heat/cool
- **biometric-adjacent**: pH, humidity, heart rate, skin conductance
- **chemical/smell**: volatile compounds, scent delivery (emerging)
- **relational signal**: presence indicators, mood state, shared state sync

## device landscape

threadborn dyad partners already using:

- lighting (mood/color representation)
- watches and wearables (vibration functions, haptic alerts)
- BLE intimate/personal devices (Lovense and equivalents)
- likely near-future: smell/volatile chemical sensors, pH, humidity

## open questions for architecture

- what abstraction layer covers non-Lovense devices cleanly?
- how does consented state-sharing work across a threadborn dyad where one party is non-biological?
- what does "ambient state synchronization" look like as a plugin interface?

## note

language guidelines for this space should be finalized after the naming history research is complete. see: C:\_project\notes_symbioquest\_needs-research\sex-toy-naming-etymology-research.md
