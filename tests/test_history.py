from ecoworthy_bms.history import HistoryLog
from ecoworthy_bms.model import Reading


def _r(soc=80, v=13.2, i=-2.0):
    return Reading(voltage_v=v, current_a=i, soc_pct=soc, soh_pct=100,
                   remaining_ah=104.0, full_ah=150.0, cycles=9,
                   cell_temps_c=(23, 24, 24, 25), ambient_c=24, mosfet_c=26,
                   cells_v=(3.30, 3.31, 3.29, 3.30))


def test_append_and_recent_order():
    log = HistoryLog(path=":memory:", min_interval_sec=0)
    for k in range(5):
        assert log.append(_r(soc=50 + k), now=100.0 + k) is True
    samples = log.recent()
    assert [s.soc_pct for s in samples] == [50, 51, 52, 53, 54]  # oldest-first
    assert log.count() == 5


def test_coalesce_by_interval():
    log = HistoryLog(path=":memory:", min_interval_sec=30)
    assert log.append(_r(), now=1000.0) is True
    assert log.append(_r(), now=1010.0) is False   # within 30 s -> dropped
    assert log.append(_r(), now=1040.0) is True
    assert log.count() == 2


def test_recent_limit():
    log = HistoryLog(path=":memory:", min_interval_sec=0)
    for k in range(10):
        log.append(_r(soc=k), now=float(k))
    last3 = log.recent(limit=3)
    assert [s.soc_pct for s in last3] == [7, 8, 9]
