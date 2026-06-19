"""Settings page: connection, units, thresholds, the safety gates, pluggable
automation actions, the optional ASCOM Alpaca SafetyMonitor, and window/tray QoL.
Scrollable. Binds to AppConfig and emits changes."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from ..config import AppConfig
from ..profiles import parse_profiles, profiles_to_config


class SettingsPage(QWidget):
    settingsApplied = Signal(object)   # emits a new AppConfig
    connectRequested = Signal()        # connect/disconnect button

    def __init__(self, cfg: AppConfig) -> None:
        super().__init__()
        self._cfg = cfg
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        root = QVBoxLayout(content)
        outer.addWidget(scroll)
        scroll.setWidget(content)

        root.addWidget(_section(self.tr("Settings")))
        form = QFormLayout()
        self._mac = QLineEdit(cfg.mac)
        self._mac.setPlaceholderText("battery BLE MAC, e.g. 52:EB:8C:7B:3A:FF")
        conn_row = QHBoxLayout()
        conn_row.addWidget(self._mac, 1)
        self.connectBtn = QPushButton(self.tr("Connect"))
        self.connectBtn.clicked.connect(self.connectRequested.emit)
        conn_row.addWidget(self.connectBtn)
        form.addRow(self.tr("Battery MAC"), _wrap(conn_row))

        self._poll = QDoubleSpinBox(); self._poll.setRange(1.0, 120.0); self._poll.setSuffix(" s")
        self._poll.setValue(cfg.poll_sec)
        form.addRow(self.tr("Poll interval"), self._poll)

        self._fahrenheit = QCheckBox(self.tr("Show temperatures in °F"))
        self._fahrenheit.setChecked(cfg.fahrenheit)
        form.addRow(self.tr("Units"), self._fahrenheit)

        self._low_soc = QSpinBox(); self._low_soc.setRange(1, 99); self._low_soc.setSuffix(" %")
        self._low_soc.setValue(cfg.low_soc_warn_pct)
        form.addRow(self.tr("Low-SOC warning"), self._low_soc)

        self._imb = QSpinBox(); self._imb.setRange(20, 1000); self._imb.setSuffix(" mV")
        self._imb.setValue(cfg.imbalance_warn_mv)
        form.addRow(self.tr("Imbalance warning"), self._imb)
        root.addLayout(form)

        root.addWidget(_section(self.tr("Batteries (one 'Name = MAC' per line)")))
        self._roster = QPlainTextEdit()
        self._roster.setPlaceholderText("Field pack = 52:EB:8C:7B:3A:FF")
        self._roster.setPlainText("\n".join(f"{n} = {m}" for n, m in (cfg.batteries or [])))
        self._roster.setMaximumHeight(96)
        root.addWidget(self._roster)

        # --- safety gates ---
        root.addWidget(_section(self.tr("Critical-reserve safety")))
        form2 = QFormLayout()
        self._crit_soc = QSpinBox(); self._crit_soc.setRange(5, 95); self._crit_soc.setSuffix(" %")
        self._crit_soc.setValue(cfg.critical_soc_pct)
        form2.addRow(self.tr("Critical-SOC"), self._crit_soc)
        self._failsafe = QSpinBox(); self._failsafe.setRange(30, 1800); self._failsafe.setSuffix(" s")
        self._failsafe.setValue(cfg.failsafe_timeout_sec)
        form2.addRow(self.tr("Fail-safe timeout"), self._failsafe)
        root.addLayout(form2)

        # --- pluggable automation actions ---
        root.addWidget(_section(self.tr("Automation (on safety change)")))
        form3 = QFormLayout()
        self._cmd = QLineEdit(cfg.on_transition_command)
        self._cmd.setPlaceholderText("shell command; tokens {state} {soc} {voltage} {reason}")
        form3.addRow(self.tr("Run command"), self._cmd)
        self._webhook = QLineEdit(cfg.webhook_url)
        self._webhook.setPlaceholderText("https://… (POST JSON)")
        form3.addRow(self.tr("Webhook URL"), self._webhook)
        self._mqtt_en = QCheckBox(self.tr("Publish to MQTT"))
        self._mqtt_en.setChecked(cfg.mqtt_enabled)
        form3.addRow(self.tr("MQTT"), self._mqtt_en)
        self._mqtt_host = QLineEdit(cfg.mqtt_host); self._mqtt_host.setPlaceholderText("broker host")
        form3.addRow(self.tr("MQTT host"), self._mqtt_host)
        self._mqtt_port = QSpinBox(); self._mqtt_port.setRange(1, 65535); self._mqtt_port.setValue(cfg.mqtt_port)
        form3.addRow(self.tr("MQTT port"), self._mqtt_port)
        self._mqtt_topic = QLineEdit(cfg.mqtt_topic)
        form3.addRow(self.tr("MQTT topic"), self._mqtt_topic)
        root.addLayout(form3)

        # --- astro (ASCOM Alpaca) ---
        root.addWidget(_section(self.tr("Astro (ASCOM Alpaca SafetyMonitor)")))
        form4 = QFormLayout()
        self._alpaca = QCheckBox(self.tr("Enable Alpaca SafetyMonitor (127.0.0.1)"))
        self._alpaca.setChecked(cfg.alpaca_enabled)
        form4.addRow(self.tr("ASCOM Alpaca"), self._alpaca)
        self._port = QSpinBox(); self._port.setRange(1024, 65535); self._port.setValue(cfg.alpaca_port)
        form4.addRow(self.tr("Alpaca port"), self._port)
        root.addLayout(form4)

        # --- window & tray ---
        root.addWidget(_section(self.tr("Window & tray")))
        form5 = QFormLayout()
        self._autostart = QCheckBox(self.tr("Start at login"))
        self._autostart.setChecked(cfg.start_with_os)
        form5.addRow(self.tr("Startup"), self._autostart)
        self._min_tray = QCheckBox(self.tr("Minimize/close to system tray"))
        self._min_tray.setChecked(cfg.minimize_to_tray)
        form5.addRow(self.tr("Tray"), self._min_tray)
        self._start_min = QCheckBox(self.tr("Start minimized to tray"))
        self._start_min.setChecked(cfg.start_minimized)
        form5.addRow("", self._start_min)
        self._notify = QCheckBox(self.tr("Notify on safety trips"))
        self._notify.setChecked(cfg.notifications_enabled)
        form5.addRow(self.tr("Notifications"), self._notify)
        root.addLayout(form5)

        save = QPushButton(self.tr("Apply && Save"))
        save.clicked.connect(self._apply)
        root.addWidget(save)
        root.addStretch(1)

    def set_connected(self, connected: bool) -> None:
        self.connectBtn.setText(self.tr("Disconnect") if connected else self.tr("Connect"))

    def _apply(self) -> None:
        self._cfg = replace(
            self._cfg,
            mac=self._mac.text().strip(),
            batteries=profiles_to_config(parse_profiles(self._roster.toPlainText())),
            poll_sec=float(self._poll.value()),
            fahrenheit=self._fahrenheit.isChecked(),
            low_soc_warn_pct=int(self._low_soc.value()),
            imbalance_warn_mv=int(self._imb.value()),
            critical_soc_pct=int(self._crit_soc.value()),
            failsafe_timeout_sec=int(self._failsafe.value()),
            on_transition_command=self._cmd.text().strip(),
            webhook_url=self._webhook.text().strip(),
            mqtt_enabled=self._mqtt_en.isChecked(),
            mqtt_host=self._mqtt_host.text().strip(),
            mqtt_port=int(self._mqtt_port.value()),
            mqtt_topic=self._mqtt_topic.text().strip(),
            alpaca_enabled=self._alpaca.isChecked(),
            alpaca_port=int(self._port.value()),
            start_with_os=self._autostart.isChecked(),
            minimize_to_tray=self._min_tray.isChecked(),
            start_minimized=self._start_min.isChecked(),
            notifications_enabled=self._notify.isChecked(),
        )
        try:
            self._cfg.save()
        except Exception:  # noqa: BLE001
            pass
        self.settingsApplied.emit(self._cfg)


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section")
    return lbl


def _wrap(layout) -> QWidget:
    w = QWidget()
    w.setLayout(layout)
    return w
