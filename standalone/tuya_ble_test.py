"""
Standalone Tuya BLE controller for the no-name Smart Ceiling Lights lamp.

Goal: control the lamp from a plain Python script (no HA) so we can iterate
quickly and prove the protocol works end-to-end. Once stable, fold any
learnings back into custom_components/tuya_ble/.

Usage on the Pi:
  python3 tuya_ble_test.py scan         # passively wait for the lamp's adv
  python3 tuya_ble_test.py status       # connect + read current status
  python3 tuya_ble_test.py on            # turn lamp on
  python3 tuya_ble_test.py off           # turn lamp off
  python3 tuya_ble_test.py toggle        # flip current state

It connects directly with the cached local_key (no HA, no cloud roundtrip).
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Reuse the protocol implementation that already ships with our fork.
# Symlink/copy custom_components/tuya_ble into ./vendor/ before running, OR
# point sys.path at it.
HERE = Path(__file__).resolve().parent
TUYA_BLE_PKG = HERE.parent / "custom_components" / "tuya_ble" / "tuya_ble"
if not TUYA_BLE_PKG.exists():
    raise SystemExit(
        f"Missing tuya_ble package at {TUYA_BLE_PKG}. "
        f"Run this script from a clone that has custom_components/tuya_ble/."
    )
sys.path.insert(0, str(TUYA_BLE_PKG.parent))

# Now import the protocol bits from the integration.
from tuya_ble import (  # type: ignore
    AbstaractTuyaBLEDeviceManager,
    TuyaBLEDataPoint,
    TuyaBLEDataPointType,
    TuyaBLEDevice,
    TuyaBLEDeviceCredentials,
)

from bleak import BleakScanner
from bleak.backends.device import BLEDevice

LAMP_MAC = "DC:23:51:8C:87:40"
LAMP_UUID = "uuid703a44302aaf"
LAMP_LOCAL_KEY = "914EE0E51BDD750F"
LAMP_DEVICE_ID = "bf6e9artje1djyjh"
LAMP_CATEGORY = "dj"
LAMP_PRODUCT_ID = "10qaawhk"

DP_SWITCH_LED = 20
DP_WORK_MODE = 21
DP_BRIGHT_VALUE = 22
DP_TEMP_VALUE = 23

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
)
_LOGGER = logging.getLogger("tuya_ble_test")
logging.getLogger("bleak").setLevel(logging.WARNING)
logging.getLogger("bleak_retry_connector").setLevel(logging.INFO)


class StaticCredentialsManager(AbstaractTuyaBLEDeviceManager):
    """Manager stub that hands out a single hardcoded credential set."""

    def __init__(self):
        self._creds = TuyaBLEDeviceCredentials(
            uuid=LAMP_UUID,
            local_key=LAMP_LOCAL_KEY,
            device_id=LAMP_DEVICE_ID,
            category=LAMP_CATEGORY,
            product_id=LAMP_PRODUCT_ID,
            device_name="Smart Ceiling Light",
            product_model="30CM",
            product_name="Smart Ceiling Lights",
        )

    async def get_device_credentials(
        self, address: str, force_update: bool = False, save_data: bool = False
    ) -> TuyaBLEDeviceCredentials | None:
        if address.upper() == LAMP_MAC:
            return self._creds
        return None


async def find_lamp(timeout: float = 60.0) -> BLEDevice | None:
    """Scan continuously for the target MAC up to `timeout` seconds."""
    _LOGGER.info("Scanning for %s (max %.0fs)...", LAMP_MAC, timeout)
    found: list[BLEDevice] = []
    seen = asyncio.Event()

    def cb(dev: BLEDevice, adv):
        if dev.address.upper() == LAMP_MAC and not found:
            _LOGGER.info("Saw lamp: rssi=%s name=%r", adv.rssi, dev.name)
            found.append(dev)
            seen.set()

    scanner = BleakScanner(detection_callback=cb, scanning_mode="active")
    await scanner.start()
    try:
        await asyncio.wait_for(seen.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout: lamp never advertised in window")
    finally:
        await scanner.stop()
    return found[0] if found else None


async def connect_lamp() -> TuyaBLEDevice | None:
    ble_dev = await find_lamp()
    if ble_dev is None:
        return None
    manager = StaticCredentialsManager()
    dev = TuyaBLEDevice(manager, ble_dev)
    _LOGGER.info("Calling TuyaBLEDevice.initialize()...")
    await dev.initialize()
    _LOGGER.info("Device initialized: name=%s product=%s", dev.name, dev.product_name)
    _LOGGER.info("Sending TuyaBLEDevice.update() (request current status)...")
    try:
        await asyncio.wait_for(dev.update(), timeout=30)
    except asyncio.TimeoutError:
        _LOGGER.warning("update() didn't complete within 30s, continuing anyway")
    return dev


async def cmd_scan() -> int:
    dev = await find_lamp(timeout=60)
    return 0 if dev else 1


async def cmd_status() -> int:
    dev = await connect_lamp()
    if dev is None:
        return 1
    _LOGGER.info("Current datapoint state:")
    for dp_id, dp in dev.datapoints._datapoints.items():
        _LOGGER.info("  dp_id=%s value=%r", dp_id, dp.value)
    await dev.stop()
    return 0


async def cmd_set_switch(state: bool) -> int:
    dev = await connect_lamp()
    if dev is None:
        return 1
    _LOGGER.info("Setting switch_led=%s", state)
    dp = dev.datapoints.get_or_create(
        DP_SWITCH_LED,
        TuyaBLEDataPointType.DT_BOOL,
        state,
    )
    await dp.set_value(state)
    _LOGGER.info("Command sent. Sleeping 3s before disconnect...")
    await asyncio.sleep(3)
    await dev.stop()
    return 0


async def cmd_toggle() -> int:
    dev = await connect_lamp()
    if dev is None:
        return 1
    cur = dev.datapoints._datapoints.get(DP_SWITCH_LED)
    cur_val = bool(cur.value) if cur is not None else False
    new_val = not cur_val
    _LOGGER.info("Toggling switch_led %s -> %s", cur_val, new_val)
    dp = dev.datapoints.get_or_create(
        DP_SWITCH_LED, TuyaBLEDataPointType.DT_BOOL, new_val
    )
    await dp.set_value(new_val)
    await asyncio.sleep(3)
    await dev.stop()
    return 0


COMMANDS = {
    "scan": cmd_scan,
    "status": cmd_status,
    "on": lambda: cmd_set_switch(True),
    "off": lambda: cmd_set_switch(False),
    "toggle": cmd_toggle,
}


async def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python3 tuya_ble_test.py [scan|status|on|off|toggle]")
        return 2
    return await COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
