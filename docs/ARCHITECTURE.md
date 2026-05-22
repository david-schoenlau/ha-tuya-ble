# Architecture: Pi-as-Tuya-BLE-Gateway + HA Integration

This is the plan we're executing on. It splits the original "lamp doesn't
work in HA" problem into two independent subprojects that can be built and
tested separately.

## Goals

1. **Stop depending on the Smart Life app and Tuya cloud at runtime.**
   The Tuya IoT cloud account is acceptable as a *one-time setup* helper
   (to fetch each device's `local_key`). After that, everything runs on
   our own LAN.
2. **Be portable.** Code lives in a Python package on a Raspberry Pi.
   Anyone with a Pi 4 + 1 BLE lamp + cloud creds can reproduce the setup.
3. **Be honest about reach.** If RF doesn't reach, that's not a software
   bug. We can put the gateway on a Pi physically near the lamp and let
   HA live elsewhere — the LAN handles the distance.
4. **Be a learning project.** Code is readable, comments explain the
   protocol decisions, and `research/` holds every source we consulted.

## Topology

```
                            LAN / Wi-Fi
       +-----------------------------------------+
       |                                         |
   homelab Pi 4                              edge Pi 3
   ============                              ===========
   * Home Assistant                          * pyrtuya_ble lib
   * HA integration                          * tuya_gateway daemon
     "tuya_ble (via gateway)"   <----------  * persistent BT to lamp(s)
       (HTTP/MQTT client)         HTTP/MQTT  * pair handshake + AES
                                             * exposes JSON API:
                                                GET  /devices
                                                POST /devices/{id}/dp
                                                GET  /devices/{id}/state
                                                WS   /events     ◄── live DP updates
                                             * physically NEAR the lamp
                                               (good RF, no walls)
```

For now `edge` is a Pi 3B that's been idle. Could be replaced later by an
ESP32 BLE proxy + bridge daemon, but the *protocol layer* stays Python on
a real Linux host because Tuya BLE needs AES + state and ESPHome's
`bluetooth_proxy` only forwards raw GATT.

## Subproject 1 — `pyrtuya_ble`: Pi as Tuya BLE master

A standalone Python package + CLI. Talks Tuya BLE directly with a device.
No HA, no daemon, no gateway. Just a library you can `pip install` and
script against.

**Capabilities (in build order):**

1. Connect to a device by MAC using known `local_key`
2. Per-session pair handshake → derive `session_key`
3. Read current DPs (light on/off, brightness, color temp)
4. Write a DP (turn on, set brightness)
5. Subscribe to DP-report notifications (passive updates from the lamp)
6. **Initial pair from scratch** (later) — bind an unpaired device without
   ever opening the Smart Life app. Needs more research into how
   `local_key` is generated/exchanged on first bind.

**Tested via:**
- `pyrtuya_ble lamp --mac DC:23:51:8C:87:40 --key 914EE0E51BDD750F status`
- `pyrtuya_ble lamp --mac ... --key ... on`
- `pyrtuya_ble lamp --mac ... --key ... brightness 50%`

**Code lives in:** `standalone/pyrtuya_ble/`

## Subproject 2 — `tuya_gateway` daemon + HA integration

Two pieces, one repo each.

### 2a) The gateway daemon (runs on a Pi near the lamps)

A FastAPI (or aiohttp) service that wraps `pyrtuya_ble`. Holds persistent
BT connections to one or more lamps, exposes a clean local API:

```
POST /v1/devices                        # register a device {mac, local_key, name}
GET  /v1/devices                        # list
GET  /v1/devices/{mac}/state            # current DP state, cached
POST /v1/devices/{mac}/dp               # write DPs: {"switch_led": true}
WS   /v1/events                         # live DP-report stream
```

Auth: shared bearer token (env var). Local-LAN-only by default.

State: SQLite for device registry. In-memory cache for current DP state.

### 2b) HA integration (runs on the HA Pi)

A new HA custom integration domain `tuya_gateway_ble` (not `tuya_ble` — we
keep our existing one alongside for comparison). The integration talks to
the gateway over HTTP and creates HA entities (light/sensor/switch) for
each device known to the gateway.

**Architectural win:** HA never touches BT. All the BLE/encryption/timing
problems are in one process on the gateway Pi. HA just sees an HTTP API.

## Why two pieces, not one

- Two physically separate Pis means we can put the BT antenna near the
  lamps without moving HA.
- Restarting HA does not break BT connections.
- Multiple HA instances (or even non-HA scripts) can use the same gateway.
- We can swap the gateway implementation (Python on Pi today, Rust or
  Go later, ESP32 + custom firmware way later) without touching HA.

## Sequencing

1. Research swarm (running now) populates `research/` with the protocol
   detail, prior art, BlueZ specifics, pair handshake.
2. **Subproject 1** — `pyrtuya_ble` lib + CLI. Iterate against the actual
   lamp via `standalone/`.
3. **Subproject 2a** — `tuya_gateway` daemon. Wraps lib, exposes HTTP API.
   Deploy to `edge` Pi physically near the lamp.
4. **Subproject 2b** — HA integration consuming the gateway. Deploy to
   `homelab` Pi. Light entity appears. Smoke test.
5. Move existing `custom_components/tuya_ble/` to `legacy/` once 2b works.

## Non-goals (for now)

- Initial pairing from scratch (Smart Life still does first bind)
- OTA updates over BLE
- Tuya BLE Mesh devices (we only have single-master BLE here)
- Cloud-side anything (no MQTT to Tuya, no Nabu Casa proxy)

## Acceptance criterion

A user with the same lamp + a fresh Pi should be able to follow our README
and have HA controlling the lamp within 30 minutes, without touching the
Smart Life app after the initial bind, and without any frame of code
touching `apigw.tuyaeu.com` after the one-time `local_key` pull.
