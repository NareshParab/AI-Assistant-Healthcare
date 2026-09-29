# P4 Transfer Package — Apply Instructions

This package contains the P4 (backend/document/API foundation) proof-of-concept
implementation, prepared for manual transfer into your local
`AI-Assistant-Healthcare` repository. It was built from a read-only cloud
clone of the real GitHub repo (no push access was available from this
session), so this is a file transfer, not a git push.

## What's included (12 files)

1. `.gitignore` — the CORRECTED/MERGED version. This preserves every line of
   your original committed `.gitignore` (including `.claude/`,
   `firetv/captures/`, `*.iml`, `*credentials*.json`, `firetv/build_output.log`)
   and adds new patterns needed for the Python backend and P4 artifacts
   (`__pycache__/`, `.venv/`, `backend/*.db`, `backend/blobs/`, `*.apk`/`*.aab`
   broadened, `*.log`, `logs/`, `secrets/`, `credentials/`). Nothing from the
   original was removed — purely additive.
2. `.env.example`
3. `backend/requirements.txt`
4. `backend/app/__init__.py`
5. `backend/app/documents/__init__.py`
6. `backend/app/documents/extract.py`
7. `backend/app/documents/render.py`
8. `backend/app/main.py`
9. `backend/tests/__init__.py`
10. `backend/tests/test_p4_poc.py`
11. `demo-data/documents/synthetic_prescription.pdf`
12. `scripts/generate_synthetic_prescription.py`

**Deliberately excluded:** `backend/tests/output/p4_poc_highlighted_crop.png`
— this is a generated test artifact (pytest writes it when
`test_p4_poc.py` runs); it is not source and will regenerate locally the
first time you run the test suite.

## How to apply

From the root of your local `AI-Assistant-Healthcare` repository:

```bash
# 1. Copy every file in this package into your repo, preserving paths.
#    (Replace SOURCE with wherever you extracted this package.)
cp -r SOURCE/.gitignore SOURCE/.env.example SOURCE/backend SOURCE/demo-data SOURCE/scripts .

# 2. Review the diff before staging anything.
git status
git diff .gitignore

# 3. Install the new Python dependency set (P4 only).
pip install -r backend/requirements.txt --break-system-packages   # or use a venv

# 4. Regenerate the synthetic PDF locally if you want to confirm the script
#    (optional — the PDF is already included above, this just re-derives it):
python3 scripts/generate_synthetic_prescription.py

# 5. Run the P4 validation tests.
pytest backend/tests/ -v

# 6. Optional manual smoke test:
uvicorn backend.app.main:app --reload
# then in another shell:
curl "http://127.0.0.1:8000/v1/poc/p4/render?needle=Tablet%20A" --output /tmp/p4_check.png
```

Do not commit or push until you've reviewed the diff yourself — this
package was prepared with explicit instructions not to commit/push from
the session that built it.
