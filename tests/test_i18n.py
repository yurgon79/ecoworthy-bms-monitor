import os
import pytest
pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from ecoworthy_bms.i18n import install_translator

_app = QApplication.instance() or QApplication([])


def test_install_translator_graceful_when_missing():
    # no catalog for this locale -> returns None, English source used, no crash
    assert install_translator(_app, locale="zz_ZZ") is None
