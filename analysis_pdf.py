"""Generate a compact PDF brief for download (dataset + citation + summary stats)."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from fpdf import FPDF


def _ascii_safe(text: str) -> str:
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
    )


def _wrap_lines(text: str, width: int = 92) -> list[str]:
    """Split long paths/strings so fpdf can wrap (avoids 'not enough horizontal space')."""
    t = _ascii_safe(text)
    if len(t) <= width:
        return [t]
    return [t[i : i + width] for i in range(0, len(t), width)]


class _BriefPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def build_cmapss_brief_pdf(
    fd: str,
    root: str,
    df_train: Optional[pd.DataFrame],
    df_test: Optional[pd.DataFrame],
    rul: Optional[np.ndarray],
) -> bytes:
    """Return PDF bytes summarizing loaded C-MAPSS slices and the PHM08 reference."""
    pdf = _BriefPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(pdf.epw, 10, _ascii_safe("NASA C-MAPSS - Turbofan PHM brief"))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        pdf.epw,
        5,
        _ascii_safe(
            "Reference: A. Saxena, K. Goebel, D. Simon, and N. Eklund, "
            '"Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", '
            "PHM08, Denver CO, Oct 2008."
        ),
    )
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Data location", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Root:", ln=True)
    w = pdf.epw
    for line in _wrap_lines(root):
        pdf.multi_cell(w, 5, line)
    pdf.ln(1)
    pdf.multi_cell(pdf.epw, 5, _ascii_safe(f"Subset: {fd.upper()} (train/test/RUL as available)"))
    pdf.ln(2)

    def _summarize(name: str, df: Optional[pd.DataFrame]) -> None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, f"{name} summary", ln=True)
        pdf.set_font("Helvetica", "", 10)
        if df is None or len(df) == 0:
            pdf.multi_cell(pdf.epw, 5, "Not loaded.")
            pdf.ln(1)
            return
        nu = int(df["unit"].nunique())
        pdf.multi_cell(pdf.epw, 5, _ascii_safe(f"Rows: {len(df):,} | Engines: {nu}"))
        g = df.groupby("unit")["cycle"].max()
        pdf.multi_cell(
            pdf.epw,
            5,
            _ascii_safe(
                f"Cycles per engine (max): min={g.min():.0f}, max={g.max():.0f}, mean={g.mean():.1f}"
            ),
        )
        pdf.ln(1)

    _summarize("Training", df_train)
    _summarize("Test", df_test)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "RUL vector (test)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if rul is not None and len(rul):
        pdf.multi_cell(
            pdf.epw,
            5,
            _ascii_safe(
                f"Length: {len(rul)} | min={rul.min():.1f}, max={rul.max():.1f}, mean={rul.mean():.1f}"
            ),
        )
    else:
        pdf.multi_cell(pdf.epw, 5, "RUL file not loaded or empty.")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Column layout (26 fields)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        pdf.epw,
        5,
        _ascii_safe(
            "unit, cycle, 3 operational settings, 21 sensor measurements - see NASA readme for semantics."
        ),
    )

    # fpdf2 returns bytearray; Streamlit download_button requires bytes (not bytearray).
    raw = pdf.output()
    if isinstance(raw, str):
        return raw.encode("latin-1")
    return bytes(raw)
