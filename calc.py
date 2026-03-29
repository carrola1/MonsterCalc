from __future__ import annotations

import re
import time
from dataclasses import dataclass

import toolButtons
import keywords

from app_paths import resource_path
from engine import CalculationEngine, EngineConfig, strip_inline_comment
from qt_compat import QColor, QFont, QGridLayout, QLabel, QMenu, QPainter, QPlainTextEdit
from qt_compat import QPixmap, QRect, QSignalBlocker, QSize, QSplitter, QToolButton, QToolTip
from qt_compat import Qt, QWidget
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

ACCENT_RED = "#ab2424"
ACCENT_RED_BRIGHT = "#bb2d2d"
WINDOW_BG = "#26292b"
PANEL_BG = "#26292b"
EDITOR_BG = "#1a1b1d"
RESULTS_BG = "#1a1b1d"
GUTTER_BG = "#141618"
BUTTON_BG = "#303338"
BUTTON_HOVER_BG = "#3a3e44"
BORDER_DARK = "#090909"
TEXT_PRIMARY = "#f2f3f4"
TEXT_SECONDARY = "#c8ccd1"
TEXT_MUTED = "#77808a"
RESULT_CLICK_MAX_SECONDS = 0.35
RESULT_CLICK_MAX_DISTANCE = 6
AUTOSPACED_TOKENS = {"+", "-", "*", "/", "<<", ">>", "&", "|", "^", "**", "=", "to"}

TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)$")
TOKEN_CONTINUATION_RE = re.compile(r"^[A-Za-z0-9_]")
HOVER_TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass(frozen=True)
class InlineCompletion:
    token: str
    ghost_text: str
    insert_text: str


def scale_scroll_value(
    source_min: int,
    source_max: int,
    source_value: int,
    target_min: int,
    target_max: int,
) -> int:
    del source_max
    return max(target_min, min(source_value, target_max))


def should_reserve_horizontal_scrollbar_space(*maximums: int) -> bool:
    return any(maximum > 0 for maximum in maximums)


def build_token_insert_text(
    line_text: str,
    cursor_column: int,
    token: str,
    *,
    trailing_parenthesis: bool = False,
) -> str:
    if trailing_parenthesis:
        return f"{token}("

    if token not in AUTOSPACED_TOKENS:
        return token

    before_char = line_text[cursor_column - 1] if cursor_column > 0 else ""
    after_char = line_text[cursor_column] if cursor_column < len(line_text) else ""
    leading_space = " " if before_char and not before_char.isspace() else ""
    trailing_space = " " if after_char == "" or not after_char.isspace() else ""
    return f"{leading_space}{token}{trailing_space}"


def token_at_column(line_text: str, column: int) -> str | None:
    for match in HOVER_TOKEN_RE.finditer(line_text):
        if match.start() <= column < match.end():
            return match.group(0)
    return None


def build_hover_previews(evaluations) -> dict[str, str]:
    previews: dict[str, str] = {}
    for line_number, evaluation in enumerate(evaluations, start=1):
        if evaluation.display:
            previews[f"line{line_number}"] = f"line{line_number} = {evaluation.display}"
        if evaluation.assignment_name and evaluation.display:
            previews[evaluation.assignment_name] = (
                f"{evaluation.assignment_name} = {evaluation.display}"
            )
    return previews


def build_result_hover_previews(evaluations) -> dict[int, str]:
    previews: dict[int, str] = {}
    for line_number, evaluation in enumerate(evaluations, start=1):
        value = evaluation.value
        if not isinstance(value, int) or isinstance(value, bool):
            continue
        if not evaluation.display:
            continue
        previews[line_number] = "\n".join(
            (
                f"default: {evaluation.display}",
                f"dec: {value}",
                f"hex: {hex(value)}",
                f"bin: {bin(value)}",
            )
        )
    return previews


def build_clickable_result_lines(evaluations) -> set[int]:
    return {
        line_number
        for line_number, evaluation in enumerate(evaluations, start=1)
        if evaluation.display
    }


def should_insert_line_reference_from_result_click(
    *,
    press_duration_seconds: float,
    move_distance: int,
    line_number: int | None,
    clickable_lines: set[int],
    has_selection: bool,
) -> bool:
    return (
        press_duration_seconds <= RESULT_CLICK_MAX_SECONDS
        and move_distance <= RESULT_CLICK_MAX_DISTANCE
        and line_number is not None
        and line_number in clickable_lines
        and not has_selection
    )


def find_inline_completion(
    line_text: str,
    cursor_column: int,
    signatures: dict[str, str],
) -> InlineCompletion | None:
    before_cursor = line_text[:cursor_column]
    after_cursor = line_text[cursor_column:]

    if after_cursor and TOKEN_CONTINUATION_RE.match(after_cursor):
        return None

    call_completion = _find_call_argument_hint(before_cursor, after_cursor, signatures)
    if call_completion is not None:
        return call_completion

    match = TOKEN_RE.search(before_cursor)
    if match is None:
        return None

    fragment = match.group(1)
    if len(fragment) < 3:
        return None

    matches = [token for token in signatures if token.startswith(fragment)]
    if len(matches) != 1:
        return None

    token = matches[0]
    signature = signatures[token]

    if fragment == token:
        return InlineCompletion(token=token, ghost_text=signature, insert_text="(")

    return InlineCompletion(
        token=token,
        ghost_text=f"{token[len(fragment):]}{signature}",
        insert_text=token[len(fragment):],
    )


def _find_call_argument_hint(
    before_cursor: str,
    after_cursor: str,
    signatures: dict[str, str],
) -> InlineCompletion | None:
    if after_cursor and not after_cursor.isspace():
        return None

    call_context = _find_open_call(before_cursor, signatures)
    if call_context is None:
        return None

    token, argument_text = call_context
    remaining_signature = _remaining_signature(signatures[token], argument_text)
    if remaining_signature is None:
        return None

    return InlineCompletion(
        token=token,
        ghost_text=remaining_signature,
        insert_text="",
    )


def _find_open_call(
    before_cursor: str,
    signatures: dict[str, str],
) -> tuple[str, str] | None:
    depth = 0
    for index in range(len(before_cursor) - 1, -1, -1):
        char = before_cursor[index]
        if char == ")":
            depth += 1
        elif char == "(":
            if depth > 0:
                depth -= 1
                continue

            token_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*$", before_cursor[:index])
            if token_match is None:
                return None

            token = token_match.group(1)
            if token not in signatures:
                return None

            return token, before_cursor[index + 1 :]
    return None


def _remaining_signature(signature: str, argument_text: str) -> str | None:
    params = _signature_params(signature)
    if params is None:
        return None
    if not params:
        return None

    arg_index, current_fragment = _argument_progress(argument_text)
    if arg_index >= len(params):
        return None
    if current_fragment:
        if arg_index + 1 >= len(params):
            return None
        return ", " + ", ".join(params[arg_index + 1 :]) + ")"

    return ", ".join(params[arg_index:]) + ")"


def _signature_params(signature: str) -> list[str] | None:
    params = [param.strip() for param in signature.strip()[1:-1].split(",") if param.strip()]
    if any("..." in param for param in params):
        return None
    if not params:
        return None
    return params


def _argument_progress(argument_text: str) -> tuple[int, str]:
    depth = 0
    arg_index = 0
    current_fragment_chars: list[str] = []

    for char in argument_text:
        if char == "," and depth == 0:
            arg_index += 1
            current_fragment_chars = []
            continue
        if char == "(":
            depth += 1
        elif char == ")" and depth > 0:
            depth -= 1
        current_fragment_chars.append(char)

    return arg_index, "".join(current_fragment_chars).strip()


def should_auto_insert_closing_paren(
    line_text: str,
    cursor_column: int,
    signatures: dict[str, str],
) -> bool:
    before_cursor = line_text[:cursor_column]
    after_cursor = line_text[cursor_column:]
    if after_cursor and not after_cursor.isspace():
        return False

    call_context = _find_open_call(before_cursor, signatures)
    if call_context is None:
        return False

    token, argument_text = call_context
    params = _signature_params(signatures[token])
    if not params:
        return False

    arg_index, current_fragment = _argument_progress(argument_text)
    if arg_index != len(params) - 1 or not current_fragment:
        return False

    return True


def closing_paren_suffix_span(line_text: str, cursor_column: int) -> int | None:
    suffix = line_text[cursor_column:]
    stripped = suffix.strip()
    if stripped != ")":
        return None
    return suffix.index(")") + 1


def should_consume_existing_closing_paren(line_text: str, cursor_column: int) -> bool:
    return 0 <= cursor_column < len(line_text) and line_text[cursor_column] == ")"


class ScratchpadTextEdit(QPlainTextEdit):
    def __init__(self, signatures: dict[str, str]):
        super().__init__()
        self.signatures = signatures
        self.hoverPreviews: dict[str, str] = {}
        self.inline_completion: InlineCompletion | None = None
        self._lastInsertionPosition = 0
        self.lineNumberArea = LineNumberArea(self)
        self.completionLabel = QLabel(self.viewport())
        self.completionLabel.hide()
        self.completionLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.completionLabel.setStyleSheet(
            f"color: {TEXT_MUTED}; background-color: transparent; padding: 0px;"
        )

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.textChanged.connect(self._refresh_completion)
        self.cursorPositionChanged.connect(self._refresh_completion)
        self.cursorPositionChanged.connect(self._remember_cursor_position)
        self.verticalScrollBar().valueChanged.connect(self._refresh_completion)
        self.horizontalScrollBar().valueChanged.connect(self._refresh_completion)

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.updateLineNumberAreaWidth(0)
        self._remember_cursor_position()

    def lineNumberAreaWidth(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def updateLineNumberAreaWidth(self, _block_count: int) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy: int) -> None:
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def keyPressEvent(self, event) -> None:
        if (
            event.key() == Qt.Key.Key_Tab
            and self.inline_completion is not None
            and self.inline_completion.insert_text
            and self.textCursor().hasSelection() is False
        ):
            self.insertPlainText(self.inline_completion.insert_text)
            self._refresh_completion()
            return
        if event.text() == ")":
            cursor = self.textCursor()
            if not cursor.hasSelection():
                block_text = cursor.block().text()
                if should_consume_existing_closing_paren(
                    block_text,
                    cursor.positionInBlock(),
                ):
                    cursor.movePosition(cursor.MoveOperation.Right)
                    self.setTextCursor(cursor)
                    self._refresh_completion()
                    return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            if not cursor.hasSelection():
                block_text = cursor.block().text()
                suffix_span = closing_paren_suffix_span(block_text, cursor.positionInBlock())
                if suffix_span is not None:
                    cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, suffix_span)
                    cursor.insertBlock()
                    self.setTextCursor(cursor)
                    self._refresh_completion()
                    return
        super().keyPressEvent(event)
        if event.text() and not event.text().isspace() and len(event.text()) == 1:
            self._maybe_auto_insert_closing_paren()

    def _maybe_auto_insert_closing_paren(self) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return
        block = cursor.block()
        if not should_auto_insert_closing_paren(
            block.text(),
            cursor.positionInBlock(),
            self.signatures,
        ):
            return
        cursor.insertText(")")
        cursor.movePosition(cursor.MoveOperation.Left)
        self.setTextCursor(cursor)
        self._refresh_completion()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.rect()
        self.lineNumberArea.setGeometry(QRect(0, 0, self.lineNumberAreaWidth() + 1, rect.height()))
        self.lineNumberArea.raise_()
        self._refresh_completion()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.completionLabel.hide()
        QToolTip.hideText()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        QToolTip.hideText()

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        self._update_hover_preview(event)

    def lineNumberAreaPaintEvent(self, event) -> None:
        painter = QPainter(self.lineNumberArea)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        gutter_rect = self.lineNumberArea.rect().adjusted(0, 0, -1, -1)
        painter.setBrush(QColor(GUTTER_BG))
        painter.drawRoundedRect(gutter_rect, 6, 6)
        painter.fillRect(
            self.lineNumberArea.width() - 1,
            6,
            1,
            max(0, self.lineNumberArea.height() - 12),
            QColor("#23262a"),
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        vertical_offset = self.contentsRect().top()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top()) + vertical_offset
        bottom = top + int(self.blockBoundingRect(block).height())

        active_line = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                color = QColor(ACCENT_RED) if block_number == active_line else QColor(TEXT_MUTED)
                painter.setPen(color)
                painter.drawText(
                    0,
                    top,
                    self.lineNumberArea.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def lineNumberForY(self, y_pos: int) -> int | None:
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top()) + self.contentsRect().top()
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid():
            if block.isVisible() and top <= y_pos <= bottom:
                return block_number + 1
            if top > y_pos:
                return None

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

        return None

    def insertLineReference(self, line_number: int) -> None:
        cursor = self.textCursor()
        if not self.hasFocus():
            max_position = len(self.toPlainText())
            cursor.setPosition(min(self._lastInsertionPosition, max_position))
            self.setTextCursor(cursor)
        self.insertPlainText(f"line{line_number}")
        self.setFocus()
        self._remember_cursor_position()

    def setHoverPreviews(self, previews: dict[str, str]) -> None:
        self.hoverPreviews = previews

    def _refresh_completion(self, *_args) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            self.inline_completion = None
            self.completionLabel.hide()
            return

        block = cursor.block()
        completion = find_inline_completion(
            block.text(),
            cursor.positionInBlock(),
            self.signatures,
        )
        self.inline_completion = completion
        if completion is None:
            self.completionLabel.hide()
            return

        cursor_rect = self.cursorRect(cursor)
        if cursor_rect.isNull():
            self.completionLabel.hide()
            return

        self.completionLabel.setFont(self.font())
        self.completionLabel.setText(completion.ghost_text)
        self.completionLabel.adjustSize()
        label_pos = cursor_rect.topLeft()
        self.completionLabel.move(label_pos.x(), label_pos.y())
        if label_pos.x() >= self.viewport().width() or label_pos.y() >= self.viewport().height():
            self.completionLabel.hide()
            return
        self.completionLabel.show()

    def _remember_cursor_position(self) -> None:
        self._lastInsertionPosition = self.textCursor().position()

    def _update_hover_preview(self, event) -> None:
        cursor = self.cursorForPosition(event.position().toPoint())
        token = token_at_column(cursor.block().text(), cursor.positionInBlock())
        if token is None:
            QToolTip.hideText()
            return

        preview = self.hoverPreviews.get(token)
        if preview is None:
            QToolTip.hideText()
            return

        QToolTip.showText(event.globalPosition().toPoint(), preview, self)


class LineNumberArea(QWidget):
    def __init__(self, editor: ScratchpadTextEdit):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event) -> None:
        self.editor.lineNumberAreaPaintEvent(event)

    def mousePressEvent(self, event) -> None:
        line_number = self.editor.lineNumberForY(int(event.position().y()))
        if line_number is not None:
            self.editor.insertLineReference(line_number)
        super().mousePressEvent(event)


class ResultTextEdit(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineHoverPreviews: dict[int, str] = {}
        self.clickableLineNumbers: set[int] = set()
        self._lineReferenceCallback = None
        self._pressStartTime = 0.0
        self._pressPosition = None
        self._pressLineNumber: int | None = None
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def setLineHoverPreviews(self, previews: dict[int, str]) -> None:
        self.lineHoverPreviews = previews

    def setClickableLineNumbers(self, line_numbers: set[int]) -> None:
        self.clickableLineNumbers = set(line_numbers)

    def setLineReferenceCallback(self, callback) -> None:
        self._lineReferenceCallback = callback

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressStartTime = time.monotonic()
            self._pressPosition = event.position().toPoint()
            self._pressLineNumber = self.cursorForPosition(self._pressPosition).blockNumber() + 1
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        press_position = self._pressPosition
        press_line_number = self._pressLineNumber
        press_duration = time.monotonic() - self._pressStartTime
        super().mouseReleaseEvent(event)
        self._pressPosition = None
        self._pressLineNumber = None

        if event.button() != Qt.MouseButton.LeftButton:
            return
        if press_position is None or self._lineReferenceCallback is None:
            return

        release_position = event.position().toPoint()
        should_insert = should_insert_line_reference_from_result_click(
            press_duration_seconds=press_duration,
            move_distance=(release_position - press_position).manhattanLength(),
            line_number=press_line_number,
            clickable_lines=self.clickableLineNumbers,
            has_selection=self.textCursor().hasSelection(),
        )
        if should_insert:
            self._lineReferenceCallback(press_line_number)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        line_number = self.cursorForPosition(event.position().toPoint()).blockNumber() + 1
        preview = self.lineHoverPreviews.get(line_number)
        if preview is None:
            QToolTip.hideText()
            return
        QToolTip.showText(event.globalPosition().toPoint(), preview, self)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        QToolTip.hideText()


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.engine = CalculationEngine(EngineConfig())
        self.last_evaluations = []
        self._syncing_scrollbars = False

        self.textEdit = ScratchpadTextEdit(toolButtons.TOKEN_SIGNATURES)
        self.resDisp = ResultTextEdit()
        self.headerIcon = QLabel()
        self.headerTitle = QLabel("MONSTER CALC")
        self.newSheetTool = QToolButton()
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

    @property
    def editorFontSize(self) -> int:
        return self.textEdit.font().pointSize()

    @editorFontSize.setter
    def editorFontSize(self, value: int) -> None:
        clamped = max(16, min(20, int(value)))
        self._apply_editor_font_size(clamped)

    def initUI(self) -> None:
        self._configure_editors()
        self._configure_header()
        self._configure_tool_buttons()
        self._build_layout()

        self.textEdit.textChanged.connect(self.updateResults)
        self._connect_vertical_scrollbars()
        self._connect_horizontal_scrollbar_policies()

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
            "Examples:\n"
            "10k\n"
            "vdiv(5, 10k, 10k)\n"
            "50 mm to in\n"
            "x = 2*pi"
        )

        self.resDisp.setFont(editor_font)
        self.resDisp.setReadOnly(True)
        self.resDisp.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.resDisp.setTabStopDistance(32)
        self.resDisp.setLineReferenceCallback(self.textEdit.insertLineReference)

        self.splitEdit.setChildrenCollapsible(False)
        self.splitEdit.setHandleWidth(2)
        self.splitEdit.addWidget(self.textEdit)
        self.splitEdit.addWidget(self.resDisp)
        self.splitEdit.setStretchFactor(0, 3)
        self.splitEdit.setStretchFactor(1, 2)

        self.setStyleSheet(
            """
            QWidget {
                background-color: """
            + WINDOW_BG
            + """;
                color: """
            + TEXT_PRIMARY
            + """;
            }

            QLabel#headerIcon {
                background-color: transparent;
                border: none;
                padding: 0px;
            }

            QLabel#headerTitle {
                color: """
            + ACCENT_RED
            + """;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.16em;
            }

            QPlainTextEdit {
                border: 1px solid """
            + BORDER_DARK
            + """;
                border-radius: 6px;
                padding: 10px;
                selection-color: #111111;
                selection-background-color: """
            + ACCENT_RED
            + """;
            }

            QPlainTextEdit:focus {
                border: 1px solid #2a2d31;
            }

            QToolButton {
                background-color: """
            + BUTTON_BG
            + """;
                border: 1px solid """
            + BORDER_DARK
            + """;
                border-radius: 6px;
                color: """
            + TEXT_PRIMARY
            + """;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 24px 6px 12px;
            }

            QToolButton:hover {
                background-color: """
            + BUTTON_HOVER_BG
            + """;
                border: 1px solid """
            + ACCENT_RED_BRIGHT
            + """;
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

            QToolButton#newSheetTool {
                background-color: """
            + BUTTON_BG
            + """;
                border: 1px solid """
            + BORDER_DARK
            + """;
                border-radius: 10px;
                font-size: 24px;
                font-weight: 700;
                padding: 0px 0px 4px 0px;
            }

            QToolButton#newSheetTool:hover {
                background-color: """
            + BUTTON_HOVER_BG
            + """;
                border: 1px solid """
            + ACCENT_RED_BRIGHT
            + """;
            }

            QMenu {
                background-color: """
            + PANEL_BG
            + """;
                border: 1px solid """
            + BORDER_DARK
            + """;
                color: """
            + TEXT_PRIMARY
            + """;
                padding: 5px;
            }

            QMenu::item {
                border-radius: 6px;
                padding: 5px 10px;
            }

            QMenu::item:selected {
                background-color: #381b1b;
                color: #f7f7f7;
            }

            QMenu::item:disabled {
                color: """
            + TEXT_MUTED
            + """;
                background-color: transparent;
            }

            QSplitter::handle {
                background-color: """
            + BORDER_DARK
            + """;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 2px 2px 2px 0px;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 8px;
                margin: 0px 2px 2px 2px;
            }

            QScrollBar::handle:vertical,
            QScrollBar::handle:horizontal {
                background: #6f7781;
                border-radius: 4px;
                min-height: 28px;
                min-width: 28px;
            }

            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:horizontal:hover {
                background: #8a949f;
            }

            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {
                background: transparent;
                border: none;
            }
            """
        )

        self.textEdit.setStyleSheet(
            f"background-color: {EDITOR_BG}; color: {TEXT_PRIMARY};"
        )
        self.resDisp.setStyleSheet(
            f"background-color: {RESULTS_BG}; color: {TEXT_SECONDARY};"
        )
        self._apply_editor_font_size(16)

    def _apply_editor_font_size(self, point_size: int) -> None:
        editor_font = QFont(self.textEdit.font())
        editor_font.setPointSize(point_size)
        self.textEdit.setFont(editor_font)
        self.textEdit.completionLabel.setFont(editor_font)
        self.textEdit.updateLineNumberAreaWidth(0)
        self.textEdit.lineNumberArea.update()

        result_font = QFont(self.resDisp.font())
        result_font.setPointSize(point_size)
        self.resDisp.setFont(result_font)

    def _configure_header(self) -> None:
        icon = self._scaled_icon_pixmap(40)
        self.headerIcon.setPixmap(icon)
        self.headerIcon.setFixedSize(44, 44)
        self.headerIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.headerIcon.setObjectName("headerIcon")
        self.headerTitle.setObjectName("headerTitle")
        title_font = QFont()
        title_font.setFamilies(TITLE_FONT_FAMILIES)
        title_font.setPointSize(17)
        title_font.setBold(True)
        self.headerTitle.setFont(title_font)
        self.headerTitle.setContentsMargins(14, 0, 0, 0)

    def _scaled_icon_pixmap(self, logical_size: int) -> QPixmap:
        source = QPixmap(str(resource_path("app_icon")))
        dpr = self.devicePixelRatioF()
        scaled = source.scaled(
            int(logical_size * dpr),
            int(logical_size * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        return scaled

    def _configure_tool_buttons(self) -> None:
        self.newSheetTool.setText("+")
        self.newSheetTool.setObjectName("newSheetTool")
        self.newSheetTool.setToolTip("New Sheet")
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
        self.newSheetTool.setFixedSize(42, 34)
        self.eeTool.setFixedWidth(68)
        self.funcTool.setMinimumHeight(34)
        self.symTool.setMinimumHeight(34)
        self.unitTool.setMinimumHeight(34)
        self.eeTool.setMinimumHeight(34)

        grid.addWidget(self.headerIcon, 0, 0, 1, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.headerTitle, 0, 1, 1, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.newSheetTool, 0, 2, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.unitTool, 0, 3, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.symTool, 0, 4, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.funcTool, 0, 5, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.eeTool, 0, 6, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.splitEdit, 1, 0, 1, 7)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(1, 1)

    def _connect_vertical_scrollbars(self) -> None:
        editor_scrollbar = self.textEdit.verticalScrollBar()
        result_scrollbar = self.resDisp.verticalScrollBar()
        editor_scrollbar.valueChanged.connect(self._sync_results_scroll_from_editor)
        result_scrollbar.valueChanged.connect(self._sync_editor_scroll_from_results)

    def _connect_horizontal_scrollbar_policies(self) -> None:
        self.textEdit.horizontalScrollBar().rangeChanged.connect(
            self._sync_horizontal_scrollbar_policies
        )
        self.resDisp.horizontalScrollBar().rangeChanged.connect(
            self._sync_horizontal_scrollbar_policies
        )

    def _sync_horizontal_scrollbar_policies(self, *_args) -> None:
        reserve_space = should_reserve_horizontal_scrollbar_space(
            self.textEdit.horizontalScrollBar().maximum(),
            self.resDisp.horizontalScrollBar().maximum(),
        )
        policy = (
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
            if reserve_space
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        if self.textEdit.horizontalScrollBarPolicy() != policy:
            self.textEdit.setHorizontalScrollBarPolicy(policy)
        if self.resDisp.horizontalScrollBarPolicy() != policy:
            self.resDisp.setHorizontalScrollBarPolicy(policy)

    def _sync_results_scroll_from_editor(self, source_value: int) -> None:
        self._sync_scrollbar_value(
            self.textEdit.verticalScrollBar(),
            self.resDisp.verticalScrollBar(),
            source_value,
        )

    def _sync_editor_scroll_from_results(self, source_value: int) -> None:
        self._sync_scrollbar_value(
            self.resDisp.verticalScrollBar(),
            self.textEdit.verticalScrollBar(),
            source_value,
        )

    def _sync_scrollbar_value(self, source_scrollbar, target_scrollbar, source_value: int) -> None:
        if self._syncing_scrollbars:
            return
        source_value = max(source_scrollbar.minimum(), min(source_value, source_scrollbar.maximum()))
        target_value = scale_scroll_value(
            source_scrollbar.minimum(),
            source_scrollbar.maximum(),
            source_value,
            target_scrollbar.minimum(),
            target_scrollbar.maximum(),
        )
        source_needs_update = source_scrollbar.value() != source_value
        target_needs_update = target_scrollbar.value() != target_value
        if not source_needs_update and not target_needs_update:
            return
        self._syncing_scrollbars = True
        try:
            if source_needs_update:
                source_scrollbar.setValue(source_value)
            if target_needs_update:
                target_scrollbar.setValue(target_value)
        finally:
            self._syncing_scrollbars = False

    def updateResults(self) -> None:
        text = self.textEdit.toPlainText()
        self.last_evaluations = self.engine.evaluate_document(text)
        self.textEdit.setHoverPreviews(build_hover_previews(self.last_evaluations))
        self.resDisp.setLineHoverPreviews(build_result_hover_previews(self.last_evaluations))
        self.resDisp.setClickableLineNumbers(build_clickable_result_lines(self.last_evaluations))
        result_text = "\n".join(self._display_text_for_line(evaluation) for evaluation in self.last_evaluations)
        with QSignalBlocker(self.resDisp):
            self.resDisp.setPlainText(result_text)
        self._sync_horizontal_scrollbar_policies()
        self._sync_scrollbar_value(
            self.textEdit.verticalScrollBar(),
            self.resDisp.verticalScrollBar(),
            self.textEdit.verticalScrollBar().value(),
        )

    def _display_text_for_line(self, evaluation) -> str:
        if evaluation.display:
            return evaluation.display

        clean_line = strip_inline_comment(evaluation.source).strip()
        if not clean_line or clean_line in {"e", "pi"}:
            return ""

        hint = toolButtons.TOKEN_RESULT_HINTS.get(clean_line)
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
        cursor = self.textEdit.textCursor()
        insert_text = build_token_insert_text(
            cursor.block().text(),
            cursor.positionInBlock(),
            token,
            trailing_parenthesis=trailing_parenthesis,
        )
        self.textEdit.insertPlainText(insert_text)
        self.textEdit.setFocus()

    def clear(self) -> None:
        self.textEdit.clear()
        self.resDisp.clear()

    def setSigFigs(self, digits: int) -> None:
        self.sigFigs = digits
