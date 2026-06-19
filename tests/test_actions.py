import asyncio
import sys

from ecoworthy_bms.safety.actions import SafetyActions, event_payload, format_command
from ecoworthy_bms.safety.failsafe import Safety
from ecoworthy_bms.model import Reading


def _reading(soc=24, v=12.6, i=-6.0):
    return Reading(voltage_v=v, current_a=i, soc_pct=soc, soh_pct=100,
                   remaining_ah=36.0, full_ah=150.0, cycles=9,
                   cell_temps_c=(23, 24, 24, 25), ambient_c=24, mosfet_c=26,
                   cells_v=(3.2, 3.2, 3.2, 3.2))


def test_event_payload_with_and_without_reading():
    p = event_payload(Safety(False, "low"), _reading(soc=24, v=12.6))
    assert p["is_safe"] is False and p["state"] == "UNSAFE" and p["reason"] == "low"
    assert p["soc"] == 24 and p["voltage"] == 12.6
    p2 = event_payload(Safety(True, "ok"))
    assert p2["state"] == "SAFE" and p2["soc"] is None


def test_format_command_substitutes_tokens():
    p = event_payload(Safety(False, "reserve low"), _reading(soc=20))
    cmd = format_command("notify --state {state} --soc {soc} --msg '{reason}'", p)
    assert cmd == "notify --state UNSAFE --soc 20 --msg 'reserve low'"


def test_any_enabled():
    assert SafetyActions().any_enabled() is False
    assert SafetyActions(shell_cmd="echo hi").any_enabled() is True
    assert SafetyActions(mqtt_enabled=True, mqtt_host="h", mqtt_topic="t").any_enabled() is True
    assert SafetyActions(mqtt_enabled=True).any_enabled() is False   # host/topic missing


def test_fire_runs_shell_command(tmp_path):
    if sys.platform == "win32":
        return  # POSIX shell assumed in CI; dispatch path identical
    marker = tmp_path / "fired.txt"
    act = SafetyActions(shell_cmd=f"echo {{state}}:{{soc}} > {marker}")
    asyncio.run(act.fire(Safety(False, "low"), _reading(soc=24)))
    assert marker.exists()
    assert marker.read_text().strip() == "UNSAFE:24"
