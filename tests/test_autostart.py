import sys

from ecoworthy_bms.autostart import apply_autostart, launch_command


def test_launch_command_mentions_executable():
    cmd = launch_command()
    assert sys.executable in cmd
    if not getattr(sys, "frozen", False):
        assert "-m ecoworthy_bms" in cmd


def test_apply_roundtrip(tmp_path, monkeypatch):
    if sys.platform == "win32":
        # don't mutate the real registry in tests; just confirm it returns a bool
        assert isinstance(apply_autostart(False), bool)
        return
    if sys.platform == "darwin":
        monkeypatch.setenv("HOME", str(tmp_path))
        target = tmp_path / "Library" / "LaunchAgents" / "com.ecoworthy.bmsmonitor.plist"
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        target = tmp_path / "autostart" / "ecoworthy-bms-monitor.desktop"
    assert apply_autostart(True) is True
    assert target.exists()
    assert apply_autostart(False) is True
    assert not target.exists()
