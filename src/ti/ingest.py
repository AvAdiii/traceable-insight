"""Read an assessment workbook (or CSV) into rows that keep every cell's address.

Each template sheet is found by its header row (anywhere in the first 15 rows). When one file has
several template sheets (e.g. "Sheet1" and "Revised Data"), the revised one is preferred and each
row is paired with its twin in the other sheet so disagreements can be shown.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

from ti import clean
from ti.template import ALL, is_template, map_headers, norm_class, norm_gender

PREFER = re.compile(r"revis|clean|final|updated|corrected", re.I)


@dataclass
class Row:
    sheet: str
    row: int                       # spreadsheet row number (1-based, as Excel shows it)
    school: str
    klass: str
    name: str
    parent: str
    gender: str
    dob: object                    # date | None
    dob_note: str
    cells: dict                    # field -> {col, raw, v, status, note}
    raw_row: list
    preferred: bool = True
    twin: int | None = None        # index of twin Row in the other sheet's list


@dataclass
class SheetRead:
    name: str
    header_row: int
    headers: list
    cols: dict                     # field -> column letter
    rows: list = field(default_factory=list)
    preferred: bool = True


def _sheets_from_xlsx(data: bytes):
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    for ws in wb.worksheets:
        yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]


def _sheets_from_csv(data: bytes):
    text = data.decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text[:2000], delimiters=",\t;") if text else csv.excel
    yield "Sheet1", [list(r) for r in csv.reader(io.StringIO(text), dialect)]


def read(data: bytes, filename: str) -> list[SheetRead]:
    src = _sheets_from_csv(data) if Path(filename).suffix.lower() in (".csv", ".tsv", ".txt") \
        else _sheets_from_xlsx(data)
    sheets = []
    for title, rows in src:
        hdr_i, cols = None, {}
        for i, r in enumerate(rows[:15]):
            c = map_headers(r)
            if is_template(c):
                hdr_i, cols = i, c
                break
        if hdr_i is None:
            continue
        width = max(cols.values()) + 1
        headers = [clean.raw_text(h) for h in rows[hdr_i][:width]]
        sr = SheetRead(title, hdr_i + 1, headers,
                       {f: get_column_letter(i + 1) for f, i in cols.items()})
        for j, r in enumerate(rows[hdr_i + 1:], start=hdr_i + 2):
            r = (r + [None] * width)[:width]
            name = clean.raw_text(r[cols["name"]])
            if not name:
                continue
            cells = {}
            for f, i in cols.items():
                cell = {"col": get_column_letter(i + 1), "raw": clean.raw_text(r[i])}
                if f in ALL:
                    c = clean.number(r[i], f)
                    cell.update(v=c.value, status=c.status, note=c.note)
                cells[f] = cell
            birth, note = clean.dob(r[cols["dob"]]) if "dob" in cols else (None, "No DOB column")
            sr.rows.append(Row(
                sheet=title, row=j,
                school=re.sub(r"\s+", " ", clean.raw_text(r[cols["school"]])),
                klass=norm_class(r[cols["klass"]]), name=re.sub(r"\s+", " ", name),
                parent=clean.raw_text(r[cols["parent"]]) if "parent" in cols else "",
                gender=norm_gender(r[cols["gender"]]) if "gender" in cols else "",
                dob=birth, dob_note=note, cells=cells,
                raw_row=[clean.raw_text(x) for x in r]))
        sheets.append(sr)
    _choose_preferred(sheets)
    return sheets


def _choose_preferred(sheets: list[SheetRead]) -> None:
    if len(sheets) < 2:
        return
    best = next((s for s in sheets if PREFER.search(s.name)), sheets[0])
    for s in sheets:
        s.preferred = s is best
        if s is best:
            continue
        for r in s.rows:
            r.preferred = False
        # Pair rows: same position when the sheets line up, else by school + class + name.
        by_key = {(r.school, r.klass, clean.name_key(r.name)): i for i, r in enumerate(best.rows)}
        for i, r in enumerate(s.rows):
            b = best.rows[i] if i < len(best.rows) else None
            if b is not None and clean.name_key(b.name) == clean.name_key(r.name):
                r.twin = i
            else:
                r.twin = by_key.get((r.school, r.klass, clean.name_key(r.name)))
