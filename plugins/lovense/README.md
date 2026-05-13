# Lovense plugin

The Lovense plugin is SymbioSync's current actuator/control plugin. It talks
directly to Lovense BLE devices using the ASCII command protocol.

## Status

Alpha.

The Ferri is the primary tested hardware path. Other devices have command support
based on protocol documentation, community sources, APK protocol inference, and
the shared Lovense BLE protocol, but most have not yet been verified on physical
hardware in this project.

Important truthfulness note: current command success mostly means the local BLE
stack accepted a write. It should not be treated as proof that hardware physically
actuated unless the relevant command path receives or infers stronger evidence.
Tightening this result model is active work.

## Tested hardware

| Device | Capabilities | Status |
|--------|--------------|--------|
| Ferri | Vibrate | Primary tested device, daily-use path |

## Supported via protocol

| Device | Capabilities | Notes |
|--------|-------------|-------|
| **Vibrate-only** | | |
| Lush (1/2/3/4) | Vibrate | G-spot egg |
| Lush Mini | Vibrate | Smaller G-spot egg |
| Lush Anal | Vibrate | Anal vibrator |
| Hush (1/2) | Vibrate | Butt plug |
| Ambi | Vibrate | Bullet vibrator |
| Exomoon | Vibrate | Lipstick bullet |
| Diamo | Vibrate | Cock ring |
| Gemini | Vibrate | Nipple clamps |
| Mission 2 | Vibrate | Vibrating dildo |
| **Multi-motor** | | |
| Edge (1/2) | Vibrate + Vibrate1/2 | Prostate massager, 2 motors |
| Dolce | Vibrate + Vibrate1/2 | Dual vibrator, 2 motors |
| Hyphy | Vibrate + Vibrate1/2 | Dual-end high frequency |
| **Rotation** | | |
| Nora | Vibrate + Rotate + Accel | Rabbit vibrator, rotating head |
| Ridge | Vibrate + Rotate | Anal beads, rotating |
| **Air pump** | | |
| Max (1/2) | Vibrate + Air (0-5) + Accel | Inflatable stroker |
| Gush (1/2) | Vibrate + Air | Glans massager |
| **Thrusting** | | |
| Gravity | Vibrate + Thrust | Thrusting dildo |
| Solace | Vibrate + Thrust | Thrusting stroker |
| Solace Pro | Vibrate + Thrust | Premium thrusting stroker |
| Vulse | Vibrate + Thrust | Thrusting G-spot egg |
| Spinel | Vibrate + Thrust | Thrusting + heating dildo |
| Sex Machine | Vibrate + Thrust | Thrusting machine |
| **Suction** | | |
| Tenera 2 | Vibrate + Suck | Clitoral suction |
| **Fingering** | | |
| Flexer | Vibrate + Finger | Insertable dual panty |
| **Depth sensor** | | |
| Calor | Vibrate + Multi + Depth | Stroker with depth sensor |
| **Other** | | |
| Domi 2 | Vibrate + LED | Mini wand, ring LEDs |
| Osci 3 | Vibrate | G-spot oscillator |
| Lapis | Vibrate + Multi | Strapless strap-on |

All supported Lovense devices also expose battery query, power-off, and status
keepalive commands where firmware supports them.

## BLE command reference

All commands are ASCII strings terminated with `;`. The plugin currently writes
without response to avoid queue pressure and BLE stalls. That is transport-level
behavior, not proof of physical actuation.

### Universal

| Command | Range | Response | Description |
|---------|-------|----------|-------------|
| `Vibrate:x;` | 0-20 | `OK;` | Set vibration level |
| `Vibrate1:x;` | 0-20 | `OK;` | Motor 1 on multi-motor devices |
| `Vibrate2:x;` | 0-20 | `OK;` | Motor 2 on multi-motor devices |
| `Battery;` | | `NN;` | Battery percentage |
| `DeviceType;` | | `L:FW:MAC;` | Model letter, firmware, BT address |
| `Status:1;` | | `2;` | Keepalive; `2` means normal |
| `PowerOff;` | | `OK;` | Remote power-off |
| `AutoSwith:On/Off:On/Off;` | | `OK;` | Auto-standby settings |
| `Light:on/off;` | | `OK;` | LED toggle on newer devices |

### Rotation

| Command | Range | Response | Description |
|---------|-------|----------|-------------|
| `Rotate:x;` | 0-20 | `OK;` | Set rotation speed |
| `RotateChange;` | | `OK;` | Toggle rotation direction |

### Air pump

| Command | Range | Response | Description |
|---------|-------|----------|-------------|
| `Air:Level:x;` | 0-5 | `OK;` | Set absolute inflation level |
| `Air:In:x;` | 1-5 | `OK;` | Inflate by x steps |
| `Air:Out:x;` | 1-5 | `OK;` | Deflate by x steps |

### Other actuator commands

| Command | Range | Response | Description |
|---------|-------|----------|-------------|
| `Thrusting:x;` | 0-20 | `OK;` | Set thrust speed |
| `Suck:x;` | 0-20 | `OK;` | Set suction level |
| `Fingering:x;` | 0-20 | `OK;` | Set fingering speed |

### Accelerometer

| Command | Response | Description |
|---------|----------|-------------|
| `StartMove:1;` | `GxxxxyyyyzzzZ;` | Start 3-axis accel stream |
| `StopMove:1;` | `OK;` | Stop accel stream |

## BLE service UUIDs

Tried in order at connection time:

| Generation | Service UUID | Notes |
|------------|--------------|-------|
| XY30+ (2022+) | `58300001-0023-4bd4-bbd5-a6920e4c5653` | Most current toys |
| Gen-2 Nordic UART | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | Mid-generation toys |
| Gen-1 | `0000fff0-0000-1000-8000-00805f9b34fb` | Oldest toys |

## Known limitations

- Delivery semantics are still too optimistic. `ok` often means API/transport
  acceptance rather than hardware-delivered proof.
- Many device mappings are not locally hardware-tested.
- Heating commands are not implemented.
- Gen-1 devices may need different characteristic handling.

## Protocol sources

- APK static analysis: `com.component.dxtoy.core.commandcore.bean.BaseToyCommandBean`
  from Lovense Connect 3.5.4 and Lovense Remote
- [lovesense-py protocol docs](https://lovesense-py.readthedocs.io/en/latest/protocol.html)
- [lumpenspace/goontech.md](https://gist.github.com/lumpenspace/fa371d44498d2668b1794bc3d520c072)
- Intiface Central BLE capture logs
- Ferri field testing
