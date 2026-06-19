from ecoworthy_bms.safety.failsafe import FailsafeMonitor
from ecoworthy_bms.model import Reading


def _r(soc, i):
    return Reading(voltage_v=13.0, current_a=i, soc_pct=soc, soh_pct=100,
                   remaining_ah=1.5 * soc, full_ah=150.0, cycles=9,
                   cell_temps_c=(23, 24, 24, 25), ambient_c=24, mosfet_c=26,
                   cells_v=(3.3, 3.3, 3.3, 3.3))


def test_high_soc_is_safe_regardless_of_flow():
    m = FailsafeMonitor(critical_soc_pct=25, recover_soc_pct=35, start_now=0)
    assert m.on_reading(_r(80, -8.0), now=1).is_safe is True
    assert m.on_reading(_r(80, +5.0), now=2).is_safe is True


def test_low_soc_on_battery_trips_unsafe():
    m = FailsafeMonitor(critical_soc_pct=25, start_now=0)
    s = m.on_reading(_r(20, -6.0), now=1)
    assert s.is_safe is False and "critical" in s.reason


def test_low_soc_while_charging_stays_safe():
    m = FailsafeMonitor(critical_soc_pct=25, start_now=0)
    assert m.on_reading(_r(20, +4.0), now=1).is_safe is True


def test_recovery_needs_recover_soc_and_charging():
    m = FailsafeMonitor(critical_soc_pct=25, recover_soc_pct=35, start_now=0)
    assert m.on_reading(_r(20, -6.0), now=1).is_safe is False     # trip
    assert m.on_reading(_r(30, +4.0), now=2).is_safe is False     # charging but < recover
    assert m.on_reading(_r(40, -1.0), now=3).is_safe is False     # >= recover but not charging
    assert m.on_reading(_r(40, +4.0), now=4).is_safe is True      # both -> re-armed


def test_brief_gap_holds_then_stale_unsafe():
    m = FailsafeMonitor(failsafe_timeout_sec=180, start_now=0)
    m.on_reading(_r(80, -8.0), now=100)
    assert m.poll(now=200).is_safe is True       # 100s gap < 180 -> hold last (safe)
    assert m.poll(now=290).is_safe is False      # 190s gap >= 180 -> stale unsafe


def test_startup_grace_then_no_data_unsafe():
    m = FailsafeMonitor(failsafe_timeout_sec=180, start_now=0)
    assert m.poll(now=10).is_safe is True        # within grace
    s = m.poll(now=200)
    assert s.is_safe is False and "no BMS data" in s.reason


def test_fresh_reading_recovers_from_stale():
    m = FailsafeMonitor(failsafe_timeout_sec=180, start_now=0)
    m.on_reading(_r(80, -8.0), now=10)
    assert m.poll(now=300).is_safe is False      # stale
    assert m.on_reading(_r(80, -8.0), now=305).is_safe is True   # data back -> safe
