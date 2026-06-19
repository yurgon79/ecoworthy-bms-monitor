import sys

from ecoworthy_bms.config import AppConfig, data_dir, APP_DIRNAME


def test_data_dir_is_under_app_name():
    d = data_dir()
    assert d.name == APP_DIRNAME


def test_roundtrip_save_load(tmp_path):
    p = tmp_path / "config.json"
    cfg = AppConfig(mac="AA:BB:CC:DD:EE:FF", critical_soc_pct=30, notifications_enabled=False)
    cfg.save(p)
    back = AppConfig.load(p)
    assert back.mac == "AA:BB:CC:DD:EE:FF"
    assert back.critical_soc_pct == 30 and back.notifications_enabled is False


def test_load_missing_returns_defaults(tmp_path):
    back = AppConfig.load(tmp_path / "nope.json")
    assert back.mac == "" and back.minimize_to_tray is True
