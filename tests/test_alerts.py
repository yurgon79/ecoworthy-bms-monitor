from ecoworthy_bms.alerts import AlertEngine, Category, Severity
from ecoworthy_bms.model import Reading


def _r(soc=80, cells=(3.30, 3.31, 3.29, 3.30)):
    return Reading(voltage_v=13.2, current_a=-2.0, soc_pct=soc, soh_pct=100,
                   remaining_ah=104.0, full_ah=150.0, cycles=9,
                   cell_temps_c=(23, 24, 24, 25), ambient_c=24, mosfet_c=26,
                   cells_v=cells)


def test_low_soc_edge_and_hysteresis():
    e = AlertEngine(low_soc_pct=30, recover_soc_pct=35)
    assert e.on_reading(_r(soc=40)) == []          # above threshold, quiet
    a = e.on_reading(_r(soc=25))                    # cross down -> fire once
    assert len(a) == 1 and a[0].category == Category.LOW_SOC
    assert a[0].severity == Severity.WARNING
    assert e.on_reading(_r(soc=24)) == []           # still low -> no repeat
    assert e.on_reading(_r(soc=32)) == []           # below recover -> still latched
    rec = e.on_reading(_r(soc=36))                  # clear above recover
    assert len(rec) == 1 and rec[0].severity == Severity.INFO


def test_imbalance_edge():
    e = AlertEngine(imbalance_mv=120, imbalance_clear_mv=90)
    assert e.on_reading(_r(cells=(3.30, 3.31, 3.29, 3.30))) == []   # 20 mV, quiet
    a = e.on_reading(_r(cells=(3.20, 3.34, 3.20, 3.21)))            # 140 mV -> fire
    assert len(a) == 1 and a[0].category == Category.IMBALANCE
    assert e.on_reading(_r(cells=(3.24, 3.34, 3.24, 3.25))) == []   # 100 mV -> still latched
    cleared = e.on_reading(_r(cells=(3.25, 3.34, 3.25, 3.25)))      # 90 mV -> clears
    assert len(cleared) == 1 and cleared[0].severity == Severity.INFO


def test_ble_edges():
    e = AlertEngine()
    assert e.on_status("connected") == []           # first observation, no edge
    assert e.on_status("connected") == []           # no change
    lost = e.on_status("disconnected")
    assert len(lost) == 1 and lost[0].category == Category.BLE
    assert lost[0].severity == Severity.WARNING
    back = e.on_status("connected")
    assert len(back) == 1 and back[0].severity == Severity.INFO
    assert e.on_status("connecting") == []          # transient, ignored
