# pyrtuya_ble

A standalone Python package that talks **Tuya BLE** directly to a device over
Bluetooth Low Energy. No Home Assistant, no Tuya cloud at runtime — once
you have the device's `login_key` (a 16-character ASCII secret you fetch
from the Tuya IoT cloud one time), every operation is local.

Built for a no-name "Smart Ceiling Lights" lamp (Tuya category `dj`,
product `10qaawhk`) but the session/protocol layer is generic and will
talk any Tuya BLE device — the lock-shaped, fingerbot-shaped, lamp-shaped
parts are all just DPs on the same wire format.

This is **subproject 1** of the wider Pi-as-Tuya-BLE-Gateway plan. See
the parent repo's `docs/ARCHITECTURE.md`.

## Install

On a Raspberry Pi running Linux with BlueZ:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The package depends on `bleak` (Linux/BlueZ backend), `bleak-retry-connector`,
`pycryptodomex`, and `aiohttp`.

## Quick start

You need three secrets, all 16 ASCII chars, plus the lamp's MAC:

| Secret | Where to get it |
|---|---|
| `--mac DC:23:51:8C:87:40` | Tuya IoT cloud → device factory infos |
| `--device-id bf6e9artje1djyjh` | Tuya IoT cloud → device list |
| `--key 914EE0E51BDD750F`  | Tuya IoT cloud → device list → `local_key` |

You can also export them once:

```bash
export TUYA_MAC=DC:23:51:8C:87:40
export TUYA_DEVICE_ID=bf6e9artje1djyjh
export TUYA_LOGIN_KEY=914EE0E51BDD750F
```

Then:

```bash
# See if the lamp is even broadcasting (max 45s scan)
python -m pyrtuya_ble scan

# Read current state
python -m pyrtuya_ble status

# Turn on / off
python -m pyrtuya_ble on
python -m pyrtuya_ble off

# Toggle (read current, flip)
python -m pyrtuya_ble toggle

# Set brightness 1..100 (mapped to Tuya raw 10..1000)
python -m pyrtuya_ble brightness 50

# Set color temperature 2000..6500 K (mapped to Tuya raw 0..1000)
python -m pyrtuya_ble temp 4500

# Verbose: -v INFO, -vv DEBUG
python -m pyrtuya_ble -vv status
```

## API

```python
from pyrtuya_ble import TuyaBLELockSession, TuyaBLELight
from bleak import BleakScanner

ble_dev = await BleakScanner.find_device_by_address("DC:23:51:8C:87:40")
session = TuyaBLELockSession(
    ble_device=ble_dev,
    login_key=b"914EE0E51BDD750F",
    virtual_id=b"\x00" * 22,
    device_uuid="bf6e9artje1djyjh",
)
light = TuyaBLELight(session)
await light.connect()
await light.turn_on()
await light.set_brightness_pct(60)
await light.disconnect()
```

## Architecture

```
+----------------------------------------------------------+
|  TuyaBLELight                  (light DP mapping)        |
|    .turn_on() / .turn_off() / .set_brightness_pct() ...  |
+----------------------------------------------------------+
|  TuyaBLELockSession            (generic Tuya BLE session)|
|    .async_connect()            -> connects + pair        |
|    .async_send_dp(...)         -> any DP write           |
|    .async_query_status()       -> ask for DP report      |
+----------------------------------------------------------+
|  protocol.py / crypto.py       (frame layer + AES-CBC)   |
+----------------------------------------------------------+
|  bleak                         (BLE GATT)                |
+----------------------------------------------------------+
|  BlueZ                         (Linux kernel BT stack)   |
+----------------------------------------------------------+
```

The class is still called `TuyaBLELockSession` because it was lifted from
`tkhadimullin/tuya_ble_lock` — the protocol is identical, the name is
unfortunate.

## Credits

The `crypto`, `protocol`, and `session` modules were originally written by
**[tkhadimullin](https://github.com/tkhadimullin) for
`tuya_ble_lock`** (MIT). We stripped the Home Assistant integration layer
and the lock-specific UI, leaving the protocol core. Light DP mapping and
CLI are new.

Background research and the broader gateway architecture live in the
parent repo's `research/` and `docs/` dirs.

## License

MIT. See `LICENSE`.
