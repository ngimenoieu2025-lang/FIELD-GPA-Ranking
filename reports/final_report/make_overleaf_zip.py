"""Make a small zip of the report for Overleaf (the whole repository is too large).

Run from anywhere:  python reports/final_report/make_overleaf_zip.py
Output: reports/final_report/final_report_overleaf.zip (ignored by Git) with
reports/final_report/ and figures/final/ at their repository paths, so the
figure paths in main.tex keep working. In Overleaf: New Project -> Upload
Project, then Menu -> Main document = reports/final_report/main.tex.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "final_report" / "final_report_overleaf.zip"
SKIP_SUFFIXES = {".zip", ".pdf", ".log", ".aux", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"}


def files():
    for path in sorted((ROOT / "reports" / "final_report").rglob("*")):
        if path.is_file() and path.suffix not in SKIP_SUFFIXES:
            yield path
    yield from sorted((ROOT / "figures" / "final").glob("*.pdf"))


def main() -> None:
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files():
            z.write(path, path.relative_to(ROOT).as_posix())
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
