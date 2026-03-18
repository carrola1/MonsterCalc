from __future__ import annotations

from pathlib import Path

from MonsterCalc import SHEET_EXTENSION, _normalize_sheet_path, _sheet_preview
from MonsterCalc import autosave_sheet_text, list_autosaved_sheets


def test_sheet_preview_uses_first_non_blank_line():
    assert _sheet_preview("\n\n first line \nsecond line") == "first line"
    assert _sheet_preview("") == "(blank sheet)"


def test_normalize_sheet_path_prefers_monstercalc_extension():
    assert _normalize_sheet_path("sheet", "MonsterCalc Sheets (*.mcalc)") == Path("sheet.mcalc")
    assert _normalize_sheet_path("sheet", "Text files (*.txt)") == Path("sheet.txt")
    assert _normalize_sheet_path("sheet.txt", "MonsterCalc Sheets (*.mcalc)") == Path("sheet.txt")


def test_autosave_sheet_text_keeps_only_last_ten_sheets(tmp_path):
    for index in range(12):
        autosave_sheet_text(f"sheet {index}", tmp_path)

    sheets = list_autosaved_sheets(tmp_path)

    assert len(sheets) == 10
    assert all(sheet.path.suffix == SHEET_EXTENSION for sheet in sheets)
    assert sheets[0].preview == "sheet 11"
    assert sheets[-1].preview == "sheet 2"
