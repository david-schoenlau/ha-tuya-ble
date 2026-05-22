"""Command-line interface for pyrtuya_ble.

Usage:
    python -m pyrtuya_ble [--mac MAC] [--key LOGIN_KEY] [--device-id DEVID]
                          [--vid VID] [--protocol N] [--scan-timeout SECS]
                          ACTION [VALUE]

ACTION:
    scan                   Scan for the MAC; report RSSI; exit.
    status                 Connect, pair, query DPs, print state.
    on                     Turn light on.
    off                    Turn light off.
    toggle                 Read current state; flip on<->off.
    brightness PCT         Set brightness 1..100.
    temp KELVIN            Set color temperature 2000..6500 K.

If MAC/KEY/DEVICE-ID/VID are omitted, falls back to env vars TUYA_MAC,
TUYA_LOGIN_KEY, TUYA_DEVICE_ID, TUYA_VID.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from bleak import BleakScanner

from .light import TuyaBLELight
from .session import TuyaBLELockSession


def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


async def _find_ble_device(mac: str, timeout: float):
    """Continuous scan looking specifically for the target MAC."""
    seen = asyncio.Event()
    holder: list = []

    def cb(dev, _adv):
        if dev.address.upper() == mac.upper():
            if not holder:
                holder.append(dev)
                seen.set()

    scanner = BleakScanner(detection_callback=cb, scanning_mode="active")
    await scanner.start()
    try:
        await asyncio.wait_for(seen.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    finally:
        await scanner.stop()
    return holder[0] if holder else None


def _credentials_from_args(args) -> tuple[bytes, bytes, str]:
    """Return (login_key_bytes, vid_bytes_padded_to_22, device_id_str)."""
    login_key = args.key or _env("TUYA_LOGIN_KEY")
    device_id = args.device_id or _env("TUYA_DEVICE_ID")
    vid = args.vid or _env("TUYA_VID", "") or ""
    if not login_key:
        sys.exit("error: --key (or env TUYA_LOGIN_KEY) is required")
    if not device_id:
        sys.exit("error: --device-id (or env TUYA_DEVICE_ID) is required")
    if len(login_key) != 16:
        sys.exit(f"error: login_key must be 16 ASCII chars, got {len(login_key)}")
    if len(device_id) != 16:
        sys.exit(f"error: device_id must be 16 ASCII chars, got {len(device_id)}")
    vid_padded = (vid.encode() + b"\x00" * 22)[:22]
    return login_key.encode(), vid_padded, device_id


async def _open_light(args) -> TuyaBLELight:
    """Scan for the device, build a session, connect+pair, return Light wrapper."""
    print(f"scanning for {args.mac} (max {args.scan_timeout}s)...", flush=True)
    ble_dev = await _find_ble_device(args.mac, args.scan_timeout)
    if not ble_dev:
        sys.exit(
            f"error: did not see {args.mac} on the air within "
            f"{args.scan_timeout}s.\n"
            "Power-cycle the lamp at the wall switch and try again."
        )
    print(f"found {ble_dev.address} (name={ble_dev.name!r})", flush=True)

    login_key, vid, device_id = _credentials_from_args(args)
    session = TuyaBLELockSession(
        ble_device=ble_dev,
        login_key=login_key,
        virtual_id=vid,
        device_uuid=device_id,
        protocol_version=args.protocol,
    )
    light = TuyaBLELight(session)
    print("connecting + pair handshake...", flush=True)
    ok = await light.connect()
    if not ok:
        sys.exit("error: connect/pair failed (see logs)")
    print("connected", flush=True)
    return light


async def cmd_scan(args) -> int:
    print(f"scanning for {args.mac} (max {args.scan_timeout}s)...", flush=True)
    dev = await _find_ble_device(args.mac, args.scan_timeout)
    if not dev:
        print("not found")
        return 1
    print(f"found {dev.address} name={dev.name!r}")
    return 0


async def cmd_status(args) -> int:
    light = await _open_light(args)
    try:
        st = await light.query()
        print(
            f"  switch_led      = {st.on}\n"
            f"  brightness raw  = {st.brightness} ({st.brightness_pct}%)\n"
            f"  color_temp raw  = {st.color_temp} ({st.color_temp_kelvin} K)\n"
            f"  work_mode       = {st.work_mode}"
        )
    finally:
        await light.disconnect()
    return 0


async def cmd_set_switch(args, value: bool) -> int:
    light = await _open_light(args)
    try:
        if value:
            await light.turn_on()
        else:
            await light.turn_off()
        print(f"  switch_led <- {value}")
    finally:
        await light.disconnect()
    return 0


async def cmd_toggle(args) -> int:
    light = await _open_light(args)
    try:
        await light.query()
        await (light.turn_off() if light.state.on else light.turn_on())
        print(f"  switch_led <- {light.state.on}")
    finally:
        await light.disconnect()
    return 0


async def cmd_brightness(args, pct: int) -> int:
    light = await _open_light(args)
    try:
        await light.set_brightness_pct(pct)
        print(f"  brightness <- {pct}%")
    finally:
        await light.disconnect()
    return 0


async def cmd_temp(args, kelvin: int) -> int:
    light = await _open_light(args)
    try:
        await light.set_color_temp_kelvin(kelvin)
        print(f"  color_temp <- {kelvin} K")
    finally:
        await light.disconnect()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="python -m pyrtuya_ble",
        description="Talk to a Tuya BLE light directly from the command line.",
    )
    p.add_argument("--mac", default=_env("TUYA_MAC"), help="BLE MAC of the lamp.")
    p.add_argument("--key", default=None, help="login_key (16 ASCII chars).")
    p.add_argument("--device-id", default=None, help="device_id (16 ASCII chars).")
    p.add_argument("--vid", default=None, help="virtual id (may be empty).")
    p.add_argument(
        "--protocol", type=int, default=4,
        help="Tuya BLE protocol version: 3 (legacy 0x1910) or 4 (modern FD50).",
    )
    p.add_argument(
        "--scan-timeout", type=float, default=45.0,
        help="Seconds to wait for the lamp's advertisement before giving up.",
    )
    p.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase log verbosity.",
    )
    p.add_argument("action", choices=("scan", "status", "on", "off", "toggle",
                                      "brightness", "temp"))
    p.add_argument("value", nargs="?", help="Required for `brightness` and `temp`.")
    args = p.parse_args()

    log_level = logging.WARNING - 10 * args.verbose
    logging.basicConfig(
        level=max(logging.DEBUG, log_level),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )
    logging.getLogger("bleak").setLevel(logging.WARNING)

    if not args.mac:
        sys.exit("error: --mac (or env TUYA_MAC) is required")

    if args.action == "scan":
        return asyncio.run(cmd_scan(args))
    if args.action == "status":
        return asyncio.run(cmd_status(args))
    if args.action == "on":
        return asyncio.run(cmd_set_switch(args, True))
    if args.action == "off":
        return asyncio.run(cmd_set_switch(args, False))
    if args.action == "toggle":
        return asyncio.run(cmd_toggle(args))
    if args.action == "brightness":
        if not args.value:
            sys.exit("error: brightness needs a value 1..100")
        return asyncio.run(cmd_brightness(args, int(args.value)))
    if args.action == "temp":
        if not args.value:
            sys.exit("error: temp needs a Kelvin value 2000..6500")
        return asyncio.run(cmd_temp(args, int(args.value)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
