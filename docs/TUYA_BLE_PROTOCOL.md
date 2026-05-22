# Tuya BLE Protocol — Reference for Home Assistant Integration

Distilled from Tuya's official documentation (BLE SDK Guide, Bluetooth Pairing
Guide, Bluetooth Gateway Development Guide, Bluetooth Device Connection,
mobile SDK docs). This is the spec for **what the integration must do** to
talk to a Tuya BLE device locally.

Sources used:
- https://developer.tuya.com/en/docs/iot-device-dev/tuya-ble-sdk-user-guide?id=K9h5zc4e5djd9
- https://developer.tuya.com/en/docs/iot-device-dev/BLE-SDK?id=Kalgco5r2mr0h
- https://developer.tuya.com/en/docs/iot-device-dev/204b2fab91d57881a6f876e707eccb15?id=Kbaie9yqgfhvt
- https://developer.tuya.com/en/docs/iot-device-dev/6a3989f436cd41590ef91022fc194cce?id=Kbai5t9x7gcwj

---

## 1. Stack overview

```
+----------------------------------------------------------------+
|  Application layer (DP datapoints: switch_led, brightness, ..) |
+----------------------------------------------------------------+
|  Tuya BLE protocol layer                                       |
|   - Frame format (header + AES-encrypted payload)              |
|   - Pair / authenticate / DP-write / DP-report                  |
|   - AES-128 ECB and CBC, MD5, HMAC-SHA256                      |
+----------------------------------------------------------------+
|  Tuya BLE GATT service (proprietary)                           |
|   - Service UUID         : 0x1910                              |
|   - Notify  characteristic: 0x2B10  (device -> client)         |
|   - Write   characteristic: 0x2B11  (client -> device,         |
|                                       Write Without Response)  |
|   - ATT MTU 23, GATT MTU 20 bytes (max payload per ATT frame)  |
+----------------------------------------------------------------+
|  Standard Bluetooth LE link layer                              |
+----------------------------------------------------------------+
```

**Critical correction vs older community forks:**

Many existing `ha_tuya_ble` forks set the discovery `service_data_uuid` to
`0000a201-0000-1000-8000-00805f9b34fb`. That UUID is what's in the
advertisement *service data* AD field (16-bit short form `0xA201`).
**The GATT service the client connects to is `0x1910`**, not `0xA201`.

Both UUIDs are correct — they live at different layers:

| Where | UUID | Purpose |
|---|---|---|
| `AD type 0x02` / `0x16` in adv packet | `0xA201` | Marks the broadcast as Tuya so discovery filters can match |
| GATT service inside the device | `0x1910` | The actual service holding the read/write characteristics |

If a Tuya BLE device is bound (already activated by Smart Life) it can
advertise **without** the `0xA201` service data (we have seen this with
our `dj` ceiling light: bare-MAC advertisements only). Filtering discovery
strictly by `0xA201` will lose these devices. The correct strategy is:

> Accept any device whose MAC matches a credential in the cloud cache,
> regardless of advertisement contents.

---

## 2. Advertisement format

### 2.1 Broadcast packet (`AD` structure)

Defined by the BLE spec; Tuya prescribes the contents.

| AD type | Description |
|---|---|
| `0x01` Flags | Length 2, type `0x01`, data `0x16` (LE General Discoverable + BR/EDR Not Supported) |
| `0x02` Incomplete list of 16-bit Service UUIDs | Length 3, type `0x02`, data `0xA201` |
| `0x16` Service Data — 16-bit UUID | Length 0x0C / 0x14, type `0x16`, data `01 A2 <type> <product_id...>` where `type=0` means PID (8 bytes), `type=1` means product_key (16 bytes) |

Example unassociated device:

```
02 01 05  03 02 01 A2  0C 16 01 A2 00 00 00 00 00 00 00 00 00
```

### 2.2 Scan response

| AD type | Description |
|---|---|
| `0x09` Complete Local Name | Length 3, type `0x09`, data `0x54 0x59` ("TY") |
| `0xFF` Manufacturer-specific data | Length 0x19, type `0xFF`, company `0x07D0` (Tuya), then: `FLAG (1) + protocol_version (1=0x03) + encryption_method (1) + communication_capability (2) + reserved (1) + ID field (6 or 16 bytes)` |

Example, unassociated:

```
03 09 54 59  19 FF D0 07 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

### 2.3 What we observe with bound devices

With our test lamp (`DC:23:51:8C:87:40`, product `10qaawhk`, category `dj`,
bound to Smart Life), we see:

- Many advertisements with empty `service_data` and empty `manufacturer_data`
  (just bare MAC).
- Occasional bursts (after physical power cycle) of full Tuya-formatted
  advertisements.

Implication: a bound device may not be findable by content-based scan
filters. Must use MAC-based credential cache.

---

## 3. GATT service and characteristics

```
Service UUID:  0x1910
  Characteristic 0x2B10  [Notify]                  device -> client
  Characteristic 0x2B11  [Write,Write w/o Response] client -> device
```

ATT MTU 23 (default) → max ATT payload = MTU - 3 = 20 bytes per write.

Tuya frames the application-layer protocol on top of these characteristics
with a sequence number + length + chunking scheme (see frame format below).

---

## 4. Tuya BLE frame format

Every command and status update is wrapped in a Tuya frame, encrypted with
the session key after pair handshake.

```
+------+------+------+------+----------+-------+
| seq  |resp  | code | len  |  payload | CRC16 |
| 2 B  | 2 B  | 2 B  | 2 B  |  N B     | 2 B   |
+------+------+------+------+----------+-------+
```

- `seq` — client increments per request; device echoes back in the matching
  response.
- `resp` — for responses; 0 for requests.
- `code` — operation code (pair / DP write / DP report / device info / ota /
  factory reset / ...). Full enum in `tuya_ble/const.py` of the integration.
- `len` — payload length (big endian).
- `payload` — operation-specific body, AES-CBC encrypted with the session key
  for everything *after* pair handshake (the pair request itself uses the
  device's `local_key`, see §5).
- `CRC16` — over the whole frame, polynomial CCITT (0x1021).

Frames longer than GATT MTU are chunked into 20-byte ATT packets with a
1-byte per-chunk header identifying the sequence and whether it's a
first/continuation chunk.

---

## 5. Pairing / authentication flow (per connection)

> **Important:** in Tuya-speak, `pair()` is the per-session authentication
> handshake, not the initial bind. The initial bind happens once when Smart
> Life first connects the device and uploads the `local_key` to Tuya cloud.
> Every subsequent client (phone OR HA OR ESP32) that wants to talk to the
> device must perform the per-session handshake using that `local_key`.

```
Client                                        Device
  | --- LL_CONNECT_REQ (BLE link layer) ----> |
  | <-- (link established) ----------------- |
  |                                          |
  | --- GATT: subscribe Notify (2B10) ----- > |
  |                                          |
  | --- Write 2B11: PAIR_REQ ----------------> |   (encrypted with local_key)
  |       random_nonce_16B                    |
  | <-- Notify 2B10: PAIR_RESP -------------- |   (encrypted with local_key)
  |       device_nonce_16B                    |
  |                                          |
  |  Both sides derive:                       |
  |    session_key = AES128(local_key, mix(client_nonce, device_nonce))
  |                                          |
  | --- Write 2B11: any subsequent frame -- > |   (encrypted with session_key)
  | <-- Notify 2B10: response  ------------- |
```

From this point onward every frame is AES-CBC encrypted with `session_key`.

---

## 6. DP (Data Point) protocol

Each capability of the device is a DP (datapoint). DPs are identified by
`dp_id` (1 byte) and carry a typed value:

| `dp_type` | Name | Encoding |
|---|---|---|
| 0 | `raw` | Bytes |
| 1 | `bool` | 1 byte, 0/1 |
| 2 | `value` (int32) | 4 bytes big endian |
| 3 | `string` | UTF-8 |
| 4 | `enum` | 1 byte index |
| 5 | `bitmap` | 1/2/4 bytes |

DP frame payload format:

```
+-------+--------+--------+----------+
| dp_id | dp_type | dp_len | dp_data |
| 1 B   | 1 B     | 2 B    |  N B    |
+-------+--------+--------+----------+
(repeated for multi-DP frames)
```

### 6.1 DPs for our `dj` ceiling light (product `10qaawhk`)

From cloud Factory Info + datapoint cloud spec:

| dp_id | code              | dp_type | range / notes |
|---|---|---|---|
| 20 | `switch_led`        | bool    | 0=off, 1=on |
| 21 | `work_mode`         | enum    | `white`, `colour`, `scene`, `music` |
| 22 | `bright_value_v2`   | value   | 10..1000 |
| 23 | `temp_value_v2`     | value   | 0..1000 → 0=warmest (2000K), 1000=coolest (6500K) |
| 26 | `countdown_1`       | value   | seconds 0..86400 |

### 6.2 Sending a control command

```
client -> device:  encrypted Tuya frame, code=0x0202 (DP_WRITE),
                   payload = [dp_id, dp_type, dp_len_hi, dp_len_lo, ...dp_data...]
device -> client:  encrypted Tuya frame, code=0x8002 (DP_REPORT),
                   payload = current state
```

---

## 7. Cryptographic primitives required

| Primitive | Use |
|---|---|
| AES-128 ECB | Static helper used during key derivation |
| AES-128 CBC | All on-the-wire frame encryption after pair |
| MD5 | Used in some key derivation paths |
| HMAC-SHA256 | Authentication tags in OTA / secure pair (optional, not used by `dj` lights) |
| CRC16-CCITT | Frame integrity check |
| Random | 16-byte session nonce |

The Python integration uses `pycryptodomex` for AES; this is already in
`manifest.json` requirements.

---

## 8. OTA update flow (summary, for reference)

Per-step request/response with codes:

| code | direction | meaning |
|---|---|---|
| `TUYA_BLE_OTA_REQ` | app→device | "Do you accept an OTA?" Reply contains flag + current firmware version + max packet length. |
| `TUYA_BLE_OTA_FILE_INFO` | app→device | PID, target firmware version, MD5, file length, CRC32. Reply contains state + already-saved-bytes (for resume). |
| `TUYA_BLE_OTA_FILE_OFFSET_REQ` | both | Negotiates the actual byte offset to start streaming from. |
| `TUYA_BLE_OTA_DATA` | app→device | Chunked file data: package number + length + CRC16 + bytes. Per-chunk ack. |
| `TUYA_BLE_OTA_END` | app→device | "All sent." Device verifies and replies success/failure. |

Not needed for first-pass control; documented for future reference.

---

## 9. Tuya Bluetooth Gateway concept

The Tuya BLE SDK documents a "gateway" architecture for products that
**bridge BLE devices to Wi-Fi** so the Tuya cloud can reach them remotely.
A Tuya BT gateway is a device that:

1. Holds Wi-Fi/Ethernet connectivity to the Tuya cloud.
2. Holds Bluetooth radio that scans for nearby Tuya BLE / Tuya Mesh devices.
3. Speaks the Tuya BLE protocol to each subdevice using its `local_key`.
4. Translates Tuya cloud commands into BLE writes, and BLE notifications
   back into cloud telemetry.

Operation modes (`mode` JSON field at init):

```
MESH_ADV     = 0x01   // BLE Mesh provisioning (PB-ADV)
MESH_GATT    = 0x02   // BLE Mesh provisioning (PB-GATT)
BLE_MASTER   = 0x04   // Bridge Tuya BLE devices as a Bluetooth central
BLE_SLAVE    = 0x08   // Appear as a Bluetooth peripheral itself
```

Required APIs the gateway must implement (`tuya_bt_api.h` /
`tuya_os_adapt_bt.h`):

- `tuya_adapter_bt_port_init`, `_deinit` — bring up the BT stack
- `tuya_adapter_bt_scan_init/start/stop`, `tuya_adapter_bt_scan_assign`
- `tuya_adapter_bt_adv_reset/start/stop` — broadcast as a Tuya device
- `tuya_adapter_bt_send` — write a GATT notification
- `tuya_adapter_bt_gap_disconnect`

The SDK does the high-level pairing logic, GATT framing, encryption, and
cloud bridging; the gateway only implements the platform-level BT plumbing.

### 9.1 What this means for our Home Assistant setup

**The Raspberry Pi 4 running our integration *is* a Tuya BT gateway in
function**, just not running Tuya's proprietary C SDK. It:

- Holds the LAN connection (= the "cloud" side, but it's HA instead)
- Has a Bluetooth radio
- Knows the `local_key` of the subdevice
- Translates HA service calls into Tuya BLE writes

We don't need a separate Tuya gateway. We need our integration code to
correctly implement the BLE Master role described above.

### 9.2 ESP32 as a BLE proxy alternative

If the Pi's antenna can't reach a device reliably, an ESP32 running
[ESPHome `bluetooth_proxy`](https://esphome.io/components/bluetooth_proxy/)
can act as a "BLE proxy in the same room" that funnels GATT operations
from HA back to the Pi over Wi-Fi. From a Tuya-protocol perspective the
ESP32 is just an RF extender; the Pi still does encryption and framing.

---

## 10. Practical implementation checklist (HA integration)

What the integration needs to do correctly:

- [x] Cloud login (Tuya IoT app-account) to fetch device list + factory infos
- [x] Per-device cache of `{address, uuid, local_key, device_id, category,
      product_id, name}`
- [x] Discovery filter that accepts MAC matches against the cache (not just
      service-UUID-data match) — bound devices may advertise empty
- [ ] Active scan + connect by MAC even when HA's bluetooth integration
      hasn't pre-cached the device
- [x] BLE connection via Bleak with retry
- [ ] Tuya frame layer (seq/code/len/CRC16) on top of GATT char `0x2B11`
      writes and `0x2B10` notifies
- [ ] Per-session pair handshake using cached `local_key`
- [ ] AES-CBC encryption with derived session key
- [ ] DP encoding/decoding for the device's product datapoints
- [ ] LightEntity mapping for `dj` category: switch_led / bright_value_v2 /
      temp_value_v2 / work_mode

Items already shipped in `custom_components/tuya_ble/tuya_ble/tuya_ble.py`
within our fork (`marcelloceschia`-derived). What we still need to verify:
characteristic UUIDs in the code match the documented `2B10`/`2B11`, and
the service the connection targets is `0x1910` (not `0xA201`).

---

## 11. Open questions for our specific lamp

Confirmed from cloud:

```
device_id    = bf6e9artje1djyjh
product_id   = 10qaawhk
category     = dj           (light)
mac          = DC:23:51:8C:87:40
uuid         = uuid703a44302aaf
local_key    = 914EE0E51BDD750F   (16 ASCII chars = 16-byte key)
firmware     = unknown
model        = 30CM
```

Observed behavior:

- After Smart Life force-quit + phone BT off, the lamp's MAC was **not**
  visible to btmon at all (even though other BLE devices nearby were
  visible to -85 dBm). That suggests the lamp is currently still occupied
  by a Bluetooth connection (BLE peripherals do not advertise while
  connected) — likely the phone re-acquired it, OR Smart Life left a
  background socket open.

- After physical wall-switch power cycle, the lamp does advertise actively
  for ~30 s (RSSI -65 to -73 dBm at our test location), and we have
  captured ~100 packets in a 60 s window. So the radio path works when
  the lamp is in its post-boot advertising window.

The connection problem is therefore reachability/window, not protocol.

