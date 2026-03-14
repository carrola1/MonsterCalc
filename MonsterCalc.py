from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from app_paths import resource_path
from calc import MainWidget
from qt_compat import QAction, QActionGroup, QApplication, QCheckBox, QDesktopServices
from qt_compat import QFileDialog, QIcon, QInputDialog, QKeySequence, QMainWindow
from qt_compat import QMessageBox, QPixmap, QSettings, Qt, QUrl, configure_qt_environment


APP_NAME = "MonsterCalc"
APP_VERSION = "2.0"
ORG_NAME = "Andrew Carroll"
LEGACY_SETTINGS = ("company", "MonsterCalc")
PACKAGED_WELCOME_KEY = "packaged_welcome_initialized"


def _coerce_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.editor = MainWidget()
        self.setCentralWidget(self.editor)

        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.legacy_settings = QSettings(*LEGACY_SETTINGS)
        self.save_path: Path | None = None
        self.welcome_on_startup = True

        self._configure_window()
        self._create_actions()
        self._create_menus()
        self._restore_settings()
        self._apply_window_style()

    def _configure_window(self) -> None:
        icon_path = resource_path("app_icon")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.monster_icon = self._scaled_dialog_icon(icon_path, 56)
        self.setWindowTitle(APP_NAME)
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            width = max(640, int(available.width() * 0.42))
            height = max(460, int(available.height() * 0.42))
            self.resize(width, height)
            self.move(
                available.x() + max(24, int(available.width() * 0.04)),
                available.y() + max(24, int(available.height() * 0.05)),
            )
        else:
            self.resize(760, 560)
        self.statusBar().showMessage("Ready")
        self._apply_native_dark_titlebar()

    def _scaled_dialog_icon(self, image_path: Path, logical_size: int) -> QPixmap:
        dpr = self.devicePixelRatioF()
        icon = QPixmap(str(image_path)).scaled(
            int(logical_size * dpr),
            int(logical_size * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        icon.setDevicePixelRatio(dpr)
        return icon

    def _apply_window_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #2f3032;
            }

            QMenuBar {
                background-color: #2f3032;
                color: #f2f2f2;
                border-bottom: 1px solid #111111;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 4px 10px;
            }

            QMenuBar::item:selected {
                background-color: #202020;
            }

            QMenu {
                background-color: #2f3032;
                color: #e0e0e0;
                border: 1px solid #111111;
            }

            QMenu::item:selected {
                background-color: #202020;
            }

            QStatusBar {
                background-color: #2f3032;
                color: #c2c4c7;
            }
            """
        )

    def _apply_native_dark_titlebar(self) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            dwmapi = ctypes.windll.dwmapi
            for attribute in (20, 19):
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attribute,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
        except Exception:
            pass

    def _create_actions(self) -> None:
        self.openAction = QAction("Open…", self)
        self.openAction.setShortcut(QKeySequence.StandardKey.Open)
        self.openAction.triggered.connect(self.openDialog)

        self.saveAction = QAction("Save", self)
        self.saveAction.setShortcut(QKeySequence.StandardKey.Save)
        self.saveAction.triggered.connect(self.checkSave)

        self.saveAsAction = QAction("Save As…", self)
        self.saveAsAction.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.saveAsAction.triggered.connect(self.saveDialog)

        self.exitAction = QAction("Exit", self)
        self.exitAction.setShortcut(QKeySequence.StandardKey.Quit)
        self.exitAction.triggered.connect(self.close)

        self.copyAction = QAction("Copy", self)
        self.copyAction.setShortcut(QKeySequence.StandardKey.Copy)
        self.copyAction.triggered.connect(self.copySelection)

        self.cutAction = QAction("Cut", self)
        self.cutAction.setShortcut(QKeySequence.StandardKey.Cut)
        self.cutAction.triggered.connect(self.cutSelection)

        self.pasteAction = QAction("Paste", self)
        self.pasteAction.setShortcut(QKeySequence.StandardKey.Paste)
        self.pasteAction.triggered.connect(self.pasteClipboard)

        self.clearAction = QAction("Clear All", self)
        self.clearAction.setShortcut("Ctrl+Shift+C")
        self.clearAction.triggered.connect(self.clearAll)

        self.sigFigAction = QAction("Significant Figures…", self)
        self.sigFigAction.triggered.connect(self.setSigFigs)

        self.resultFormatGroup = QActionGroup(self)
        self.resultFormatGroup.setExclusive(True)
        self.sciFormatAction = QAction("Scientific (1.0e4)", self, checkable=True)
        self.engFormatAction = QAction("Engineering (10.0e3)", self, checkable=True)
        self.siFormatAction = QAction("SI Unit (10.0k)", self, checkable=True)
        self.resultFormatGroup.addAction(self.sciFormatAction)
        self.resultFormatGroup.addAction(self.engFormatAction)
        self.resultFormatGroup.addAction(self.siFormatAction)
        self.sciFormatAction.triggered.connect(lambda: self.setResFormat("scientific"))
        self.engFormatAction.triggered.connect(lambda: self.setResFormat("engineering"))
        self.siFormatAction.triggered.connect(lambda: self.setResFormat("si"))

        self.convXorToExpAction = QAction("Convert ^ to **", self, checkable=True)
        self.convXorToExpAction.triggered.connect(self.setConvXorToExp)

        self.aboutAction = QAction("About", self)
        self.aboutAction.triggered.connect(self.about)

        self.demoAction = QAction("Load Demo", self)
        self.demoAction.triggered.connect(lambda: self.welcome(force_load_demo=True))

        self.userGuideAction = QAction("User Guide", self)
        self.userGuideAction.triggered.connect(self.user_guide)

        self.releaseAction = QAction("Release Notes", self)
        self.releaseAction.triggered.connect(self.release_notes)

    def _create_menus(self) -> None:
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.saveAsAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAction)

        editMenu = menubar.addMenu("&Edit")
        editMenu.addAction(self.copyAction)
        editMenu.addAction(self.cutAction)
        editMenu.addAction(self.pasteAction)
        editMenu.addSeparator()
        editMenu.addAction(self.clearAction)

        settingsMenu = menubar.addMenu("&Settings")
        settingsMenu.addAction(self.sigFigAction)
        resultFormatMenu = settingsMenu.addMenu("Results Format")
        resultFormatMenu.addAction(self.sciFormatAction)
        resultFormatMenu.addAction(self.engFormatAction)
        resultFormatMenu.addAction(self.siFormatAction)
        settingsMenu.addSeparator()
        settingsMenu.addAction(self.convXorToExpAction)

        helpMenu = menubar.addMenu("&Help")
        helpMenu.addAction(self.aboutAction)
        helpMenu.addAction(self.userGuideAction)
        helpMenu.addAction(self.demoAction)
        helpMenu.addAction(self.releaseAction)

    def _restore_settings(self) -> None:
        sig_figs = self._setting_value("sig_figs")
        if sig_figs is not None:
            self.editor.sigFigs = _coerce_int(sig_figs, self.editor.sigFigs)

        result_format = self._setting_value("res_format")
        if result_format in {"scientific", "engineering", "si"}:
            self.editor.resFormat = str(result_format)

        conv_xor = self._setting_value("conv_xor_to_exp")
        if conv_xor is not None:
            self.editor.convXorToExp = _coerce_bool(conv_xor, True)

        self.welcome_on_startup = _coerce_bool(
            self._setting_value("welcome_on_startup"),
            True,
        )
        if getattr(sys, "frozen", False) and not _coerce_bool(
            self.settings.value(PACKAGED_WELCOME_KEY),
            False,
        ):
            self.welcome_on_startup = True

        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        self._sync_action_state()

    def _setting_value(self, key: str):
        current = self.settings.value(key)
        if current is not None:
            return current
        return self.legacy_settings.value(key)

    def _sync_action_state(self) -> None:
        self.sciFormatAction.setChecked(self.editor.resFormat == "scientific")
        self.engFormatAction.setChecked(self.editor.resFormat == "engineering")
        self.siFormatAction.setChecked(self.editor.resFormat == "si")
        self.convXorToExpAction.setChecked(self.editor.convXorToExp)

    def openDialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open file",
            str(Path.home()),
            "Text files (*.txt);;All files (*)",
        )
        if not filename:
            return

        try:
            file_path = Path(filename)
            self.editor.textEdit.setPlainText(file_path.read_text(encoding="utf-8"))
            self.save_path = file_path
            self.statusBar().showMessage(f"Opened {file_path.name}", 3000)
        except OSError as exc:
            self._show_error("Open Failed", f"Could not open file.\n\n{exc}")

    def saveDialog(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save file",
            str(self.save_path or Path.home()),
            "Text files (*.txt);;All files (*)",
        )
        if not filename:
            return

        self._save_to_path(Path(filename))

    def checkSave(self) -> None:
        if self.save_path is None:
            self.saveDialog()
            return
        self._save_to_path(self.save_path)

    def _save_to_path(self, file_path: Path) -> None:
        try:
            file_path.write_text(self.editor.textEdit.toPlainText(), encoding="utf-8")
            self.save_path = file_path
            self.statusBar().showMessage(f"Saved {file_path.name}", 3000)
        except OSError as exc:
            self._show_error("Save Failed", f"Could not save file.\n\n{exc}")

    def clearAll(self) -> None:
        self.editor.clear()
        self.statusBar().showMessage("Cleared", 2000)

    def _active_text_widget(self):
        focus_widget = self.focusWidget()
        if focus_widget in (self.editor.textEdit, self.editor.resDisp):
            return focus_widget
        return self.editor.textEdit

    def copySelection(self) -> None:
        self._active_text_widget().copy()

    def cutSelection(self) -> None:
        widget = self._active_text_widget()
        if widget.isReadOnly():
            return
        widget.cut()

    def pasteClipboard(self) -> None:
        widget = self._active_text_widget()
        if widget.isReadOnly():
            widget = self.editor.textEdit
        widget.paste()

    def setSigFigs(self) -> None:
        value, ok = QInputDialog.getInt(
            self,
            "Significant Figures",
            "Set the number of significant figures to display:",
            self.editor.sigFigs,
            1,
            15,
        )
        if ok:
            self.editor.sigFigs = value
            self.saveSettings()

    def setConvXorToExp(self) -> None:
        self.editor.convXorToExp = self.convXorToExpAction.isChecked()
        self.saveSettings()

    def setResFormat(self, format_name: str) -> None:
        self.editor.resFormat = format_name
        self._sync_action_state()
        self.saveSettings()

    def saveSettings(self) -> None:
        self.settings.setValue("sig_figs", self.editor.sigFigs)
        self.settings.setValue("res_format", self.editor.resFormat)
        self.settings.setValue("conv_xor_to_exp", self.editor.convXorToExp)
        self.settings.setValue("welcome_on_startup", self.welcome_on_startup)
        if getattr(sys, "frozen", False):
            self.settings.setValue(PACKAGED_WELCOME_KEY, True)
        self.settings.setValue("window_geometry", self.saveGeometry())

    def about(self) -> None:
        msgBox = QMessageBox(self)
        msgBox.setIconPixmap(self.monster_icon)
        msgBox.setWindowTitle("About")
        msgBox.setText(
            f"MonsterCalc {APP_VERSION}\n\n"
            "A fast scratchpad calculator for math, units, electronics, and programming.\n"
            "Created by Andrew Carroll."
        )
        msgBox.exec()

    def welcome(self, force_load_demo: bool = False) -> None:
        if force_load_demo:
            self._load_demo()

        msgBox = QMessageBox(self)
        msgBox.setIconPixmap(self.monster_icon)
        msgBox.setWindowTitle("Welcome")
        msgBox.setText(
            "MonsterCalc is ready.\n\n"
            "A demo sheet has been loaded to help you get started."
        )
        checkBox = QCheckBox("Do not show demo again")
        checkBox.setChecked(False)
        msgBox.setCheckBox(checkBox)
        msgBox.exec()

        self.welcome_on_startup = not checkBox.isChecked()
        self.saveSettings()

    def _load_demo(self) -> None:
        demo_path = resource_path("demo")
        self.editor.textEdit.setPlainText(demo_path.read_text(encoding="utf-8"))
        self.statusBar().showMessage("Demo loaded", 3000)

    def release_notes(self) -> None:
        release_path = resource_path("release_notes")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(release_path)))

    def user_guide(self) -> None:
        guide_path = resource_path("user_guide")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(guide_path)))

    def closeEvent(self, event) -> None:
        self.saveSettings()
        super().closeEvent(event)

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)


def main() -> int:
    configure_qt_environment()
    app = QApplication(sys.argv)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setStyle("Fusion")

    window = MainWindow()
    if sys.platform.startswith("win"):
        app_id = "MonsterCalc.MonsterCalc"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    window.show()
    window.editor.textEdit.setFocus()

    if window.welcome_on_startup:
        window._load_demo()
        window.welcome()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
