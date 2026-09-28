"""Synthetic demo document generation — P4 checkpoint.

Generates a single-page, text-layer PDF that stands in for a doctor-provided
prescription (ARCHITECTURE_MVP_PLAN.md D7/D27). All content is fabricated.

PRIV-982: no real name, identifier, date of birth or document scan is used
or referenced anywhere in this module.
"""

from __future__ import annotations

import pymupdf as fitz

SYNTHETIC_MARKER = "SYNTHETIC DATA -- NOT A REAL PATIENT"
# Footer marker, added so the synthetic label is visible at both the top and
# bottom of the rendered page (a reviewer scrolled/cropped to any region of
# the page still sees a synthetic-data marker nearby). Content below is
# otherwise unchanged from the original P4 checkpoint.
SYNTHETIC_FOOTER_MARKER = "*** END OF SYNTHETIC DEMO DOCUMENT -- NOT A REAL PATIENT ***"

# Each line: (text, y_position_pt, fontsize_pt)
_LINES: list[tuple[str, float, float]] = [
    (SYNTHETIC_MARKER, 40, 10),
    ("Demo Care Clinic", 70, 14),
    ("Prescription", 92, 12),
    ("Patient: Synthetic Demo Patient", 130, 11),
    ("Date: 12 Aug 2026", 150, 11),
    ("Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast", 190, 11),
    ("Medication: Tab. Atorvastatin 10mg -- 1 tablet at night", 212, 11),
    ("Exercise: Gentle 10 minute walk, morning, if not fatigued", 250, 11),
    ("Precaution: Avoid heavy lifting for 6 weeks", 272, 11),
    ("Follow-up: Cardiology checkup in 4 weeks", 310, 11),
    (SYNTHETIC_FOOTER_MARKER, 750, 9),
]

PAGE_WIDTH = 612.0  # US Letter, points
PAGE_HEIGHT = 792.0


def generate_synthetic_prescription() -> bytes:
    """Build the demo prescription PDF in memory and return its bytes."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    for text, y, size in _LINES:
        page.insert_text((40, y), text, fontsize=size, fontname="helv")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def write_synthetic_prescription(path: str) -> None:
    with open(path, "wb") as f:
        f.write(generate_synthetic_prescription())


if __name__ == "__main__":
    import pathlib

    out_dir = pathlib.Path(__file__).resolve().parents[2] / "demo-data" / "documents"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "synthetic_prescription.pdf"
    write_synthetic_prescription(str(out_path))
    print(f"Wrote {out_path}")
