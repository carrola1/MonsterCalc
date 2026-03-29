from __future__ import annotations

import re

from qt_compat import QColor, QFont, QRegularExpression, QSyntaxHighlighter, QTextCharFormat


class KeywordHighlighter(QSyntaxHighlighter):
    def __init__(self, document, funcs, operators, syms, suffix, prefix, tweener, units, unusual_syms):
        super().__init__(document)

        self.funcs = funcs
        self.operators = operators
        self.syms = syms
        self.suffix = suffix
        self.prefix = prefix
        self.units = units
        self.tweener = tweener
        self.unusual_syms = unusual_syms
        self.assignment_regex = re.compile(r"^\s*([A-Za-z_]\w*)\s*=")

        self.styles = {
            "funcs": self.style_format("#ffd166", "bold"),
            "operators": self.style_format("#7bdff2"),
            "userSyms": self.style_format("#ff9f68", "bold"),
            "symbols": self.style_format("#ff6b8a"),
            "comments": self.style_format("#9099a4", "italic"),
            "units": self.style_format("#9be564", "bold"),
        }

        base_rules = []
        base_rules += [(rf"\b{re.escape(word)}\b", self.styles["funcs"], 0) for word in self.funcs]
        base_rules += [(pattern, self.styles["operators"], 0) for pattern in self.operators]
        base_rules += [(rf"\b{re.escape(symbol)}\b", self.styles["symbols"], 0) for symbol in self.syms]
        base_rules += [(rf"(\d)({re.escape(symbol)}\b)", self.styles["symbols"], 2) for symbol in self.suffix]
        base_rules += [(rf"\b{re.escape(prefix)}", self.styles["symbols"], 0) for prefix in self.prefix]
        base_rules += [(rf"(?<=\d){re.escape(token)}(?=[+-]?\d)", self.styles["symbols"], 0) for token in self.tweener]
        base_rules += [(rf"\b{re.escape(unit)}\b", self.styles["units"], 0) for unit in self.units]
        base_rules += [(rf"\b{re.escape(token)}\b", self.styles["operators"], 0) for token in self.unusual_syms]
        base_rules += [(r"#.*", self.styles["comments"], 0)]

        self.base_rules = [
            (QRegularExpression(pattern), text_format, capture_group)
            for pattern, text_format, capture_group in base_rules
        ]

    def style_format(self, color: str, style: str = "") -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if "bold" in style:
            text_format.setFontWeight(QFont.Weight.Bold)
        if "italic" in style:
            text_format.setFontItalic(True)
        return text_format

    def highlightBlock(self, text: str) -> None:
        rules = list(self.base_rules)

        for variable_name in self._assignment_names():
            rules.append(
                (
                    QRegularExpression(rf"\b{re.escape(variable_name)}\b"),
                    self.styles["userSyms"],
                )
            )

        rules.append((QRegularExpression(r"\bline\d+\b"), self.styles["userSyms"]))

        for expression, text_format, capture_group in self.base_rules:
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart(capture_group)
                length = match.capturedLength(capture_group)
                if start >= 0 and length > 0:
                    self.setFormat(start, length, text_format)

        for expression, text_format in rules[len(self.base_rules) :]:
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)

    def _assignment_names(self) -> set[str]:
        document = self.document()
        if document is None:
            return set()
        text = document.toPlainText()
        return {
            match.group(1)
            for line in text.splitlines()
            for match in [self.assignment_regex.match(line)]
            if match
        }


class ResultHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.hint_style = QTextCharFormat()
        self.hint_style.setForeground(QColor("#6e7882"))
        self.hint_style.setFontItalic(True)

    def highlightBlock(self, text: str) -> None:
        stripped = text.strip()
        if stripped.startswith("<") and stripped.endswith(">"):
            self.setFormat(0, len(text), self.hint_style)
