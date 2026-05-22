"""Minimal data models for pyrtuya_ble.

Trimmed down from tkhadimullin/tuya_ble_lock - we removed lock-specific
records (members, credentials, temp passwords). What is left are the
per-device credentials needed to authenticate against a Tuya BLE device.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TuyaBLEDeviceCredentials:
    """Per-device secrets retrieved from the Tuya IoT cloud once.

    All fields are required to perform the per-connection pair handshake.
    `auth_key` is needed only for *initial* activation of a never-paired
    device; for the everyday session pair against a Smart Life-bound
    device, only `device_id`, `login_key`, and `vid` are used.
    """

    mac: str
    device_id: str          # 16 ASCII chars, e.g. "bf6e9artje1djyjh"
    login_key: str          # 16 ASCII chars; on-wire `local_key`
    vid: str = ""           # virtual id from cloud; padded to 22 bytes
    auth_key: str = ""      # 32 hex chars; only for initial activation
    uuid: str = ""          # advertised UUID from cloud
    product_id: str = ""
    name: str = ""
