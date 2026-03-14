from __future__ import annotations

import toolButtons
import keywords

from app_paths import resource_path
from engine import CalculationEngine, EngineConfig, strip_inline_comment
from qt_compat import QFont, QGridLayout, QLabel, QMenu, QPlainTextEdit, QPixmap
from qt_compat import QSignalBlocker, QSplitter, QToolButton, Qt, QWidget
from syntaxhighlighter import KeywordHighlighter, ResultHighlighter


EDITOR_FONT_FAMILIES = [
    "SF Mono",
    "Menlo",
    "Consolas",
    "Monaco",
    "Courier New",
]

TITLE_FONT_FAMILIES = [
    "Cochin",
    "Palatino",
    "Baskerville",
    "Times New Roman",
]


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.engine = CalculationEngine(EngineConfig())
        self.last_evaluations = []

        self.textEdit = QPlainTextEdit()
        self.resDisp = QPlainTextEdit()
        self.headerIcon = QLabel()
        self.headerTitle = QLabel("MONSTER CALC")
        self.eeTool = QToolButton()
        self.funcTool = QToolButton()
        self.symTool = QToolButton()
        self.unitTool = QToolButton()
        self.splitEdit = QSplitter(Qt.Orientation.Horizontal)

        self.funcs = keywords.funcs
        self.operators = keywords.operators
        self.prefix = keywords.prefix
        self.suffix = keywords.suffix
        self.tweener = keywords.tweener
        self.symbols = keywords.symbols
        self.unusual_syms = keywords.unusual_syms
        self.units = keywords.unitsList
        self.unitKeys = keywords.unitKeys

        self.highlight = KeywordHighlighter(
            self.textEdit.document(),
            self.funcs,
            self.operators,
            self.symbols,
            self.suffix,
            self.prefix,
            self.tweener,
            self.unitKeys,
            self.unusual_syms,
        )
        self.resultHighlight = ResultHighlighter(self.resDisp.document())

        self.initUI()

    @property
    def sigFigs(self) -> int:
        return self.engine.config.sig_figs

    @sigFigs.setter
    def sigFigs(self, value: int) -> None:
        self.engine.config.sig_figs = max(1, int(value))
        self.updateResults()

    @property
    def resFormat(self) -> str:
        return self.engine.config.res_format

    @resFormat.setter
    def resFormat(self, value: str) -> None:
        self.engine.config.res_format = value
        self.updateResults()

    @property
    def convXorToExp(self) -> bool:
        return self.engine.config.conv_xor_to_exp

    @convXorToExp.setter
    def convXorToExp(self, value: bool) -> None:
        self.engine.config.conv_xor_to_exp = bool(value)
        self.updateResults()

    def initUI(self) -> None:
        self._configure_editors()
        self._configure_header()
        self._configure_tool_buttons()
        self._build_layout()

        self.textEdit.textChanged.connect(self.updateResults)
        self.textEdit.verticalScrollBar().valueChanged.connect(
            self.resDisp.verticalScrollBar().setValue
        )
        self.resDisp.verticalScrollBar().valueChanged.connect(
            self.textEdit.verticalScrollBar().setValue
        )

        self.updateResults()

    def _configure_editors(self) -> None:
        editor_font = QFont()
        editor_font.setFamilies(EDITOR_FONT_FAMILIES)
        editor_font.setPointSize(14)
        editor_font.setStyleHint(QFont.StyleHint.Monospace)

        self.textEdit.setFont(editor_font)
        self.textEdit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.textEdit.setTabStopDistance(32)
        self.textEdit.setPlaceholderText(
            "Type one expression per line.\n"
            "Examples: 10k, vdiv(5, 10k, 10k), 50 mm to in, x = 2*pi"
        )

        self.resDisp.setFont(editor_font)
        self.resDisp.setReadOnly(True)
        self.resDisp.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.resDisp.setTabStopDistance(32)

        self.splitEdit.setChildrenCollapsible(False)
        self.splitEdit.setHandleWidth(2)
        self.splitEdit.addWidget(self.textEdit)
        self.splitEdit.addWidget(self.resDisp)
        self.splitEdit.setStretchFactor(0, 3)
        self.splitEdit.setStretchFactor(1, 2)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #2f3032;
                color: #f0f0f0;
            }

            QLabel#headerIcon {
                background-color: #d7d9dd;
                border: 1px solid #171717;
                border-radius: 9px;
                padding: 2px;
            }

            QLabel#headerTitle {
                color: #a7c53f;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.16em;
            }

            QPlainTextEdit {
                border: 1px solid #121212;
                border-radius: 6px;
                padding: 10px;
                selection-color: #111111;
                selection-background-color: #98ad43;
            }

            QPlainTextEdit:focus {
                border: 1px solid #8ea53a;
            }

            QToolButton {
                background-color: #47484b;
                border: 1px solid #1b1b1b;
                border-radius: 6px;
                color: #f0f0f0;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 24px 6px 12px;
            }

            QToolButton:hover {
                background-color: #54565a;
                border: 1px solid #98b63a;
            }

            QToolButton::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 8px;
            }

            QToolButton::menu-button {
                border: none;
                width: 16px;
            }

            QMenu {
                background-color: #2f3032;
                border: 1px solid #1b1b1b;
                color: #e6e6e6;
                padding: 5px;
            }

            QMenu::item {
                border-radius: 6px;
                padding: 5px 10px;
            }

            QMenu::item:selected {
                background-color: #4b512f;
                color: #f7f7f7;
            }

            QMenu::item:disabled {
                color: #8b8b8b;
                background-color: transparent;
            }

            QSplitter::handle {
                background-color: #111111;
            }
            """
        )

        self.textEdit.setStyleSheet("background-color: #242527; color: #f4f4f4;")
        self.resDisp.setStyleSheet("background-color: #c1c3c7; color: #1d1d1d;")

    def _configure_header(self) -> None:
        icon = QPixmap(str(resource_path("header_icon")))
        self.headerIcon.setPixmap(icon.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.headerIcon.setFixedSize(42, 42)
        self.headerIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.headerIcon.setObjectName("headerIcon")
        self.headerTitle.setObjectName("headerTitle")
        title_font = QFont()
        title_font.setFamilies(TITLE_FONT_FAMILIES)
        title_font.setPointSize(17)
        title_font.setBold(True)
        self.headerTitle.setFont(title_font)
        self.headerTitle.setContentsMargins(14, 0, 0, 0)

    def _configure_tool_buttons(self) -> None:
        self.eeTool.setText("EE")
        self.funcTool.setText("Math")
        self.symTool.setText("Symbols")
        self.unitTool.setText("Units")

        self._populate_button(self.funcTool, toolButtons.populateFuncButton(self.funcTool), self.funcTriggered)
        self._populate_button(self.eeTool, toolButtons.populateEEButton(self.eeTool), self.eeTriggered)
        self._populate_button(self.symTool, toolButtons.populateSymButton(self.symTool), self.symTriggered)
        self._populate_button(self.unitTool, toolButtons.populateUnitButton(self.unitTool), self.unitTriggered)

    def _populate_button(self, button: QToolButton, menu: QMenu, callback) -> None:
        self._connect_menu_actions(menu, callback)
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def _connect_menu_actions(self, menu: QMenu, callback) -> None:
        for action in menu.actions():
            submenu = action.menu()
            if submenu is not None:
                self._connect_menu_actions(submenu, callback)
            elif action.isEnabled():
                action.triggered.connect(callback)

    def _build_layout(self) -> None:
        grid = QGridLayout()
        grid.setContentsMargins(10, 8, 10, 10)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        self.setLayout(grid)

        self.funcTool.setFixedWidth(90)
        self.symTool.setFixedWidth(104)
        self.unitTool.setFixedWidth(88)
        self.eeTool.setFixedWidth(68)
        self.funcTool.setMinimumHeight(34)
        self.symTool.setMinimumHeight(34)
        self.unitTool.setMinimumHeight(34)
        self.eeTool.setMinimumHeight(34)

        grid.addWidget(self.headerIcon, 0, 0, 1, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.headerTitle, 0, 1, 1, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.unitTool, 0, 2, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.symTool, 0, 3, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.funcTool, 0, 4, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.eeTool, 0, 5, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.splitEdit, 1, 0, 1, 6)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(1, 1)

    def updateResults(self) -> None:
        text = self.textEdit.toPlainText()
        self.last_evaluations = self.engine.evaluate_document(text)
        result_text = "\n".join(self._display_text_for_line(evaluation) for evaluation in self.last_evaluations)
        with QSignalBlocker(self.resDisp):
            self.resDisp.setPlainText(result_text)

    def _display_text_for_line(self, evaluation) -> str:
        if evaluation.display:
            return evaluation.display

        clean_line = strip_inline_comment(evaluation.source).strip()
        if not clean_line or clean_line in {"e", "pi"}:
            return ""

        hint = toolButtons.TOKEN_HINTS.get(clean_line)
        if hint is None:
            return ""

        return f"<{hint}>"

    def funcTriggered(self) -> None:
        self._insert_token(self.sender().text(), trailing_parenthesis=True)

    def eeTriggered(self) -> None:
        self._insert_token(self.sender().text(), trailing_parenthesis=True)

    def symTriggered(self) -> None:
        self._insert_token(self.sender().text())

    def unitTriggered(self) -> None:
        self._insert_token(self.sender().text())

    def _insert_token(self, action_text: str, trailing_parenthesis: bool = False) -> None:
        sender = self.sender()
        token = sender.data() if sender is not None and hasattr(sender, "data") else action_text.split(":", maxsplit=1)[0]
        self.textEdit.insertPlainText(f"{token}(" if trailing_parenthesis else token)
        self.textEdit.setFocus()

    def clear(self) -> None:
        self.textEdit.clear()
        self.resDisp.clear()

    def setSigFigs(self, digits: int) -> None:
        self.sigFigs = digits
