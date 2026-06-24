#!/usr/bin/env python3
"""Generate tests/fixtures/sample.pdf for the chunk.py smoke test.

Reproducible, no PII, no embedded metadata beyond defaults. The fixture contains a heading, a
paragraph, an invoice-style key/value line, and a small table — enough to exercise paragraph
and table chunking under the default `structure` mode. Key-value and formula chunking require
`--mode understand`; for richer key-value coverage, point the smoke test at a real form PDF.

Run:  uv run --with reportlab python tests/fixtures/make_sample.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).with_name("sample.pdf")


def build() -> None:
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Quarterly Revenue Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            "Total net revenue for Q4 2024 was 4.2 billion dollars, an increase over the prior "
            "quarter driven by subscription growth and reduced churn.",
            styles["BodyText"],
        ),
        Spacer(1, 12),
        Paragraph("Invoice Number: INV-2024-0042", styles["BodyText"]),
        Spacer(1, 12),
        Table(
            [["Segment", "Revenue", "Growth"],
             ["Cloud", "$2.1B", "+18%"],
             ["On-Prem", "$2.1B", "+4%"]],
            style=TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ]),
        ),
    ]
    SimpleDocTemplate(str(OUT), pagesize=LETTER).build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
