from __future__ import annotations

import os

import pytest

from MonsterCalc import MainWindow
from calc import MainWidget


pytestmark = pytest.mark.skipif(
    os.environ.get("MONSTERCALC_RUN_QT_TESTS") != "1",
    reason="Qt smoke tests require a local GUI-capable Qt runtime",
)


def test_main_widget_updates_results_live(qtbot):
    widget = MainWidget()
    qtbot.addWidget(widget)

    widget.textEdit.setPlainText("x = 300\nans + 5\n50 mm to in")

    qtbot.waitUntil(
        lambda: widget.resDisp.toPlainText() == "300\n305\n1.9685 in",
        timeout=2000,
    )


def test_main_widget_respects_result_format_changes(qtbot):
    widget = MainWidget()
    qtbot.addWidget(widget)
    widget.textEdit.setPlainText("10000")

    widget.resFormat = "scientific"

    qtbot.waitUntil(lambda: widget.resDisp.toPlainText() == "1.0000e4", timeout=2000)


def test_main_widget_shows_hint_for_bare_builtin(qtbot):
    widget = MainWidget()
    qtbot.addWidget(widget)
    widget.textEdit.setPlainText("bin")

    qtbot.waitUntil(lambda: widget.resDisp.toPlainText() == "<Convert to bin>", timeout=2000)


def test_main_widget_uses_compact_placeholder_text(qtbot):
    widget = MainWidget()
    qtbot.addWidget(widget)

    assert widget.textEdit.placeholderText() == (
        "Type one expression per line.\n"
        "Examples:\n"
        "10k\n"
        "vdiv(5, 10k, 10k)\n"
        "50 mm to in\n"
        "x = 2*pi"
    )


def test_main_widget_can_insert_line_reference_token(qtbot):
    widget = MainWidget()
    qtbot.addWidget(widget)
    widget.textEdit.setPlainText("10\n20\n")
    cursor = widget.textEdit.textCursor()
    cursor.setPosition(len(widget.textEdit.toPlainText()))
    widget.textEdit.setTextCursor(cursor)

    widget.textEdit.insertLineReference(1)

    assert widget.textEdit.toPlainText().endswith("line1")


def test_main_window_new_sheet_button_autosaves_current_content(qtbot, tmp_path):
    window = MainWindow()
    window.autosave_dir = tmp_path
    qtbot.addWidget(window)
    window.editor.textEdit.setPlainText("current sheet")

    window.editor.newSheetTool.click()

    assert window.editor.textEdit.toPlainText() == ""
    assert len(list(tmp_path.glob("*.mcalc"))) == 1
