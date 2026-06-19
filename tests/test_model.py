from ecoworthy_bms.model import PackState, Reading, runtime_str, temp_str


def _r(**kw):
    base = dict(voltage_v=13.2, current_a=-5.0, soc_pct=72, soh_pct=100,
                remaining_ah=104.0, full_ah=150.0, cycles=9,
                cell_temps_c=(23, 24, 24, 25), ambient_c=24, mosfet_c=26,
                cells_v=(3.30, 3.31, 3.29, 3.30))
    base.update(kw)
    return Reading(**base)


def test_power_sign_and_value():
    assert _r(voltage_v=13.0, current_a=-5.0).power_w == -65.0
    assert _r(voltage_v=14.0, current_a=2.0).power_w == 28.0


def test_runtime_discharge_only():
    assert abs(_r(current_a=-5.0, remaining_ah=104.0).runtime_h - 20.8) < 1e-6
    assert _r(current_a=1.0).runtime_h is None        # charging -> no ETA
    assert _r(current_a=0.0).runtime_h is None


def test_imbalance_mv():
    assert abs(_r(cells_v=(3.30, 3.31, 3.29, 3.30)).imbalance_mv - 20.0) < 1e-6


def test_states():
    assert _r(current_a=-5.0).state() == PackState.DISCHARGING
    assert _r(current_a=5.0, soc_pct=80).state() == PackState.CHARGING
    assert _r(current_a=1.0, soc_pct=100).state() == PackState.FLOAT
    assert _r(current_a=0.0).state() == PackState.IDLE


def test_runtime_str():
    assert runtime_str(None) == "—"
    assert runtime_str(20.5) == "20h 30m"


def test_temp_str():
    assert temp_str(25) == "25°C"
    assert temp_str(25, fahrenheit=True) == "77°F"
    assert temp_str(0, fahrenheit=True) == "32°F"
