"""pyrtuya_ble - Talk to Tuya BLE devices directly from Python on Linux/Pi.

Public API:

    from pyrtuya_ble import (
        TuyaBLEDeviceCredentials,
        TuyaBLELockSession,    # the generic Tuya BLE session (poor name; serves lights too)
        TuyaBLELight,
        DeviceAlreadyBoundError,
    )

The session/protocol/crypto modules were lifted from
tkhadimullin/tuya_ble_lock (MIT) and stripped of Home Assistant deps.
Light DP mapping (this package's `light` module) is new and targets the
no-name "Smart Ceiling Lights" lamp (Tuya category `dj`, product `10qaawhk`).
"""

from .models import TuyaBLEDeviceCredentials
from .session import TuyaBLELockSession, DeviceAlreadyBoundError
from .light import TuyaBLELight, LightState

__all__ = [
    "TuyaBLEDeviceCredentials",
    "TuyaBLELockSession",
    "TuyaBLELight",
    "LightState",
    "DeviceAlreadyBoundError",
]

__version__ = "0.0.1"
