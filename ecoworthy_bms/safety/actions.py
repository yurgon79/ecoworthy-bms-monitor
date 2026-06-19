"""Pluggable safety actions (v0.2).

Fire on every SAFE<->UNSAFE transition so the low-reserve trip can drive more
than astro: run a shell command, POST a webhook, or publish MQTT — alongside the
desktop notification (tray) and the optional ASCOM Alpaca SafetyMonitor.

All actions are opt-in (blank/off = disabled) and best-effort: a failing action
is logged and never crashes the app. Pure helpers (`event_payload`,
`format_command`) are unit-tested; the dispatch is thin async I/O.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from ..model import Reading
from .failsafe import Safety

log = logging.getLogger("ecoworthy_bms.safety.actions")

_TOKENS = ("state", "reason", "soc", "voltage", "current", "is_safe", "ts")


def event_payload(safety: Safety, reading: Optional[Reading] = None,
                  now: Optional[float] = None) -> dict:
    p = {
        "is_safe": safety.is_safe,
        "state": "SAFE" if safety.is_safe else "UNSAFE",
        "reason": safety.reason,
        "ts": int(now if now is not None else time.time()),
        "soc": None, "voltage": None, "current": None,
    }
    if reading is not None:
        p["soc"] = reading.soc_pct
        p["voltage"] = round(reading.voltage_v, 2)
        p["current"] = round(reading.current_a, 2)
    return p


def format_command(template: str, payload: dict) -> str:
    """Substitute {state} {reason} {soc} {voltage} {current} {is_safe} {ts}."""
    out = template
    for k in _TOKENS:
        out = out.replace("{" + k + "}", str(payload.get(k, "")))
    return out


class SafetyActions:
    def __init__(self, *, shell_cmd: str = "", webhook_url: str = "",
                 mqtt_enabled: bool = False, mqtt_host: str = "",
                 mqtt_port: int = 1883, mqtt_topic: str = "") -> None:
        self.shell_cmd = shell_cmd
        self.webhook_url = webhook_url
        self.mqtt_enabled = mqtt_enabled
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic

    @classmethod
    def from_config(cls, cfg) -> "SafetyActions":
        return cls(shell_cmd=cfg.on_transition_command, webhook_url=cfg.webhook_url,
                   mqtt_enabled=cfg.mqtt_enabled, mqtt_host=cfg.mqtt_host,
                   mqtt_port=cfg.mqtt_port, mqtt_topic=cfg.mqtt_topic)

    def any_enabled(self) -> bool:
        return bool(self.shell_cmd or self.webhook_url
                    or (self.mqtt_enabled and self.mqtt_host and self.mqtt_topic))

    async def fire(self, safety: Safety, reading: Optional[Reading] = None) -> None:
        payload = event_payload(safety, reading)
        await asyncio.gather(self._shell(payload), self._webhook(payload),
                             self._mqtt(payload), return_exceptions=True)

    async def _shell(self, payload: dict) -> None:
        if not self.shell_cmd:
            return
        cmd = format_command(self.shell_cmd, payload)
        try:
            proc = await asyncio.create_subprocess_shell(cmd)
            await proc.wait()
        except Exception as e:  # noqa: BLE001
            log.warning("shell action failed: %s", e)

    async def _webhook(self, payload: dict) -> None:
        if not self.webhook_url:
            return
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(self.webhook_url, json=payload) as r:
                    await r.read()
        except Exception as e:  # noqa: BLE001
            log.warning("webhook action failed: %s", e)

    async def _mqtt(self, payload: dict) -> None:
        if not (self.mqtt_enabled and self.mqtt_host and self.mqtt_topic):
            return
        try:
            import paho.mqtt.publish as publish  # optional dep (extra: mqtt)
            await asyncio.to_thread(
                publish.single, self.mqtt_topic, json.dumps(payload),
                hostname=self.mqtt_host, port=self.mqtt_port)
        except Exception as e:  # noqa: BLE001
            log.warning("mqtt action failed: %s", e)
