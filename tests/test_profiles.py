from ecoworthy_bms.profiles import (
    Profile, parse_profiles, profiles_from_config, profiles_to_config, aggregate_bank,
)
from ecoworthy_bms.model import Reading


def _r(soc, full=150.0, rem=None, i=-2.0, cells=(3.3, 3.3, 3.3, 3.3)):
    rem = rem if rem is not None else full * soc / 100.0
    return Reading(voltage_v=13.2, current_a=i, soc_pct=soc, soh_pct=100,
                   remaining_ah=rem, full_ah=full, cycles=9,
                   cell_temps_c=(23, 24, 24, 25), ambient_c=24, mosfet_c=26, cells_v=cells)


def test_parse_and_format_roundtrip():
    text = "Field pack = AA:BB:CC:DD:EE:01\n# note\n\nDD:EE:FF:00:11:22"
    ps = parse_profiles(text)
    assert ps == [Profile("Field pack", "AA:BB:CC:DD:EE:01"),
                  Profile("DD:EE:FF:00:11:22", "DD:EE:FF:00:11:22")]
    assert profiles_to_config(ps) == [["Field pack", "AA:BB:CC:DD:EE:01"],
                                      ["DD:EE:FF:00:11:22", "DD:EE:FF:00:11:22"]]
    assert profiles_from_config(profiles_to_config(ps)) == ps


def test_aggregate_bank_capacity_weighted():
    # 150Ah @100% + 100Ah @50% => 200Ah of 250Ah => 80%
    b = aggregate_bank([_r(100, full=150.0, rem=150.0, i=1.0),
                        _r(50, full=100.0, rem=50.0, i=-3.0)])
    assert b.n == 2 and b.soc_pct == 80
    assert b.remaining_ah == 200.0 and b.full_ah == 250.0
    assert b.current_a == -2.0


def test_aggregate_bank_empty():
    b = aggregate_bank([None, None])
    assert b.n == 0 and b.soc_pct == 0


def test_aggregate_bank_cell_spread():
    b = aggregate_bank([_r(80, cells=(3.30, 3.31, 3.29, 3.30)),
                        _r(80, cells=(3.40, 3.20, 3.35, 3.33))])
    assert abs(b.imbalance_mv - 200.0) < 1e-6   # 3.40 - 3.20
