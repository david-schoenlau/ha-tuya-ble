"""High-level wrapper for a Tuya BLE light device (category `dj`).

Wraps a TuyaBLELockSession (which is actually generic — talks any Tuya BLE
device via DPs, not lock-specific) with light-shaped methods.

DP map for product 10qaawhk (Smart Ceiling Lights, CCT only):

    dp_id  code                 type     range
    -----  -------------------  -------  ----------------------------
    20     switch_led           bool     0 = off, 1 = on
    21     work_mode            enum     0=white, 1=colour, 2=scene, 3=music
    22     bright_value_v2      int      10..1000
    23     temp_value_v2        int      0..1000 (0=warmest 2000K, 1000=coolest 6500K)
    26     countdown_1          int      seconds, 0..86400
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

from .session import TuyaBLELockSession

_LOGGER = logging.getLogger(__name__)

# Tuya DP type codes (from official docs)
DP_TYPE_RAW    = 0
DP_TYPE_BOOL   = 1
DP_TYPE_VALUE  = 2  # int32 big-endian
DP_TYPE_STRING = 3
DP_TYPE_ENUM   = 4
DP_TYPE_BITMAP = 5

# Light-specific DPs
DP_SWITCH_LED      = 20
DP_WORK_MODE       = 21
DP_BRIGHT_VALUE_V2 = 22
DP_TEMP_VALUE_V2   = 23
DP_COUNTDOWN_1     = 26

WORK_MODE_WHITE  = 0
WORK_MODE_COLOUR = 1
WORK_MODE_SCENE  = 2
WORK_MODE_MUSIC  = 3

BRIGHT_MIN = 10
BRIGHT_MAX = 1000

TEMP_MIN = 0     # 2000K
TEMP_MAX = 1000  # 6500K


@dataclass
class LightState:
    on: bool = False
    brightness: int = 0          # 10..1000 raw Tuya scale; 0 if unknown
    color_temp: int = 0          # 0..1000 raw Tuya scale; 0 if unknown
    work_mode: int = WORK_MODE_WHITE

    @property
    def brightness_pct(self) -> int:
        """Brightness as 0..100 percent."""
        if self.brightness <= BRIGHT_MIN:
            return 0
        return round(
            (self.brightness - BRIGHT_MIN) * 100 / (BRIGHT_MAX - BRIGHT_MIN)
        )

    @property
    def color_temp_kelvin(self) -> int:
        """Color temperature in Kelvin (2000..6500)."""
        if self.color_temp < TEMP_MIN:
            return 2000
        if self.color_temp > TEMP_MAX:
            return 6500
        return round(2000 + (self.color_temp / TEMP_MAX) * 4500)


def _pct_to_raw_brightness(pct: int) -> int:
    pct = max(1, min(100, pct))
    return round(BRIGHT_MIN + (pct / 100) * (BRIGHT_MAX - BRIGHT_MIN))


def _kelvin_to_raw_temp(kelvin: int) -> int:
    k = max(2000, min(6500, kelvin))
    return round((k - 2000) / 4500 * TEMP_MAX)


class TuyaBLELight:
    """Thin DP-mapping layer over a TuyaBLELockSession."""

    def __init__(self, session: TuyaBLELockSession) -> None:
        self._session = session
        self.state = LightState()
        self._session.set_dp_report_callback(self._on_dp_report)

    # ---- lifecycle ----

    async def connect(self) -> bool:
        return await self._session.async_connect()

    async def disconnect(self) -> None:
        await self._session.async_disconnect()

    # ---- light operations ----

    async def query(self) -> LightState:
        """Send DEVICE_STATUS request; lamp pushes current DPs in response.

        Updates self.state via the DP-report callback.
        """
        await self._session.async_query_status()
        return self.state

    async def turn_on(self) -> None:
        await self._session.async_send_dp_bool(DP_SWITCH_LED, True)
        self.state.on = True

    async def turn_off(self) -> None:
        await self._session.async_send_dp_bool(DP_SWITCH_LED, False)
        self.state.on = False

    async def set_brightness_pct(self, pct: int) -> None:
        raw = _pct_to_raw_brightness(pct)
        await self._session.async_send_dp(
            DP_BRIGHT_VALUE_V2, DP_TYPE_VALUE, struct.pack(">I", raw)
        )
        self.state.brightness = raw

    async def set_color_temp_kelvin(self, kelvin: int) -> None:
        raw = _kelvin_to_raw_temp(kelvin)
        await self._session.async_send_dp(
            DP_TEMP_VALUE_V2, DP_TYPE_VALUE, struct.pack(">I", raw)
        )
        self.state.color_temp = raw

    async def set_work_mode(self, mode: int) -> None:
        await self._session.async_send_dp(
            DP_WORK_MODE, DP_TYPE_ENUM, bytes([mode & 0xFF])
        )
        self.state.work_mode = mode

    # ---- DP report callback ----

    def _on_dp_report(self, dps: list[dict]) -> None:
        """Each entry: {'dp_id': int, 'dp_type': int, 'value': bytes|int|bool}."""
        for dp in dps:
            dp_id = dp.get("dp_id")
            value = dp.get("value")
            if dp_id == DP_SWITCH_LED:
                self.state.on = bool(value)
            elif dp_id == DP_BRIGHT_VALUE_V2:
                self.state.brightness = int(value) if value is not None else 0
            elif dp_id == DP_TEMP_VALUE_V2:
                self.state.color_temp = int(value) if value is not None else 0
            elif dp_id == DP_WORK_MODE:
                self.state.work_mode = int(value) if value is not None else 0
            else:
                _LOGGER.debug("Unhandled DP %s = %r", dp_id, value)
