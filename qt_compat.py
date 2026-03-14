from __future__ import annotations

import os
from pathlib import Path


QT_API = ""

try:
    import PySide6 as _qt_package

    from PySide6.QtCore import QRegularExpression, QRect, QSize, QSettings, QSignalBlocker, Qt, QUrl
    from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QFont
    from PySide6.QtGui import QIcon, QKeySequence, QPainter, QPixmap, QSyntaxHighlighter, QTextCharFormat
    from PySide6.QtWidgets import QApplication, QCheckBox, QFileDialog, QGridLayout, QInputDialog
    from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QSplitter
    from PySide6.QtWidgets import QMenu, QToolButton, QToolTip, QWidget

    QT_API = "PySide6"
    _PLUGIN_ROOT = Path(_qt_package.__file__).resolve().parent / "Qt" / "plugins"
except ImportError:
    import PyQt6 as _qt_package

    from PyQt6.QtCore import QRegularExpression, QRect, QSize, QSettings, QSignalBlocker, Qt, QUrl
    from PyQt6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QFont
    from PyQt6.QtGui import QIcon, QKeySequence, QPainter, QPixmap, QSyntaxHighlighter, QTextCharFormat
    from PyQt6.QtWidgets import QApplication, QCheckBox, QFileDialog, QGridLayout, QInputDialog
    from PyQt6.QtWidgets import QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QSplitter
    from PyQt6.QtWidgets import QMenu, QToolButton, QToolTip, QWidget

    QT_API = "PyQt6"
    _PLUGIN_ROOT = Path(_qt_package.__file__).resolve().parent / "Qt6" / "plugins"


def configure_qt_environment(*, offscreen: bool = False) -> None:
    if QT_API == "PySide6":
        os.environ.setdefault("QT_PLUGIN_PATH", str(_PLUGIN_ROOT))
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(_PLUGIN_ROOT / "platforms"))
    if offscreen:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


configure_qt_environment()
