"""
Generates ONE synthetic, text-layer prescription document for the P4 POC.

Per D7 (ARCHITECTURE_MVP_PLAN.md): digitally generated, text-layer PDFs only —
no scanned images, no OCR. This gives real, extractable text with exact
bounding-box coordinates, which is what makes D16 (original-document
verification) possible at all.

Per HACK-980 / PRIV-982: this persona and all values are entirely fictional.
No real patient, no real clinician, no real facility. The document is
visibly labelled as synthetic demo data both in its own content and in
downstream UI (F-X07 / PRIV-981 — enforced later, at the app layer).

Run: python3 scripts/generate_synthetic_prescription.py
Output: demo-data/documents/synthetic_prescription.pdf
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "demo-data" / "documents" / "synthetic_prescription.pdf"


def build_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=LETTER)
    width, height = LETTER

    y = height - 72

    def line(text: str, size: int = 11, bold: bool = False, gap: int = 18) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(72, y, text)
        y -= gap

    # --- Clearly marked as synthetic / demo data throughout ---
    line("*** SYNTHETIC DEMO DOCUMENT — NOT A REAL PRESCRIPTION ***", size=10, bold=True, gap=22)
    line("Fictional Community Clinic (synthetic facility)", size=9, gap=14)
    line("Prescription", size=16, bold=True, gap=28)

    line("Patient: Ramesh D. (synthetic persona)", gap=16)
    line("Date of issue: 12 Aug 2026", gap=16)
    line("Prescribing clinician: Dr. A. Fictional (synthetic)", gap=26)

    line("Medications:", bold=True, gap=20)
    line("1. Tablet A 5mg — take 1 tablet before breakfast", gap=16)
    line("2. Tablet B 10mg — take 1 tablet after lunch, with food", gap=16)
    line("3. Tablet C 2.5mg — take 1 tablet at night", gap=26)

    line("Instructions:", bold=True, gap=20)
    line("Take medications at the same time each day. Do not skip doses.", gap=16)
    line("Contact your care team if you are unsure about any instruction.", gap=26)

    line("*** END OF SYNTHETIC DEMO DOCUMENT ***", size=10, bold=True, gap=16)

    c.showPage()
    c.save()


if __name__ == "__main__":
    build_pdf(OUTPUT_PATH)
    print(f"Synthetic text-layer PDF written to: {OUTPUT_PATH}")
