"""Compare the standard English model with the trained one on held-out lines.

Usage: ocr_eval.py EVAL_DIR TESSDATA_DIR_WITH_mfm
Prints a Markdown report; its first line is "BETTER" when the trained model makes
clearly fewer mistakes (fewer wrong characters and at least as many lines exactly right).
"""
import subprocess
import sys
from pathlib import Path


def dist(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def read(png: Path, lang: str, tessdata: str | None) -> str:
    cmd = ["tesseract", str(png), "-", "--psm", "7", "-l", lang]
    if tessdata:
        cmd[1:1] = ["--tessdata-dir", tessdata]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return " ".join(out.split())


def main() -> None:
    ev, td = Path(sys.argv[1]), sys.argv[2]
    rows = []
    for png in sorted(ev.glob("*.png")):
        truth = " ".join(png.with_suffix(".gt.txt").read_text(encoding="utf-8").split())
        rows.append((truth, read(png, "eng", None), read(png, "mfm", td)))
    chars = sum(len(t) for t, _, _ in rows) or 1
    res = {}
    for k, name in ((1, "standard"), (2, "trained")):
        errs = sum(dist(r[k], r[0]) for r in rows)
        exact = sum(r[k] == r[0] for r in rows)
        res[name] = (errs, exact)
    better = res["trained"][0] < res["standard"][0] * 0.9 and res["trained"][1] >= res["standard"][1]
    out = []
    if better:
        out.append("BETTER")
    out.append(f"## OCR test on {len(rows)} lines it wasn't trained on\n")
    out.append("| Model | Wrong characters | Lines exactly right |")
    out.append("|---|---|---|")
    for name, (errs, exact) in res.items():
        out.append(f"| {name} | {errs} of {chars} ({100 * errs / chars:.1f}%) | {exact} of {len(rows)} |")
    out.append("")
    out.append("<details><summary>Every line</summary>\n")
    out.append("| Truth | Standard | Trained |")
    out.append("|---|---|---|")
    for t, a, b in rows:
        esc = lambda s: s.replace("|", "\\|")
        out.append(f"| {esc(t)} | {esc(a)} | {esc(b)} |")
    out.append("\n</details>")
    print("\n".join(out))


if __name__ == "__main__":
    main()
