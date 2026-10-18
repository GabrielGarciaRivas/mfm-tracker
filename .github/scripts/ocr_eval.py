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
    """Every model in TESSDATA (and each with +eng) against the standard one; the best
    goes first in the report as "BEST <lang>" when it's clearly better."""
    ev, td = Path(sys.argv[1]), sys.argv[2]
    langs = [p.stem for p in sorted(Path(td).glob("*.traineddata")) if p.stem != "eng"]
    variants = [("standard", "eng", None)] + [(l, l, td) for l in langs] + [(l + "+eng", l + "+eng", td) for l in langs]
    lines = []
    for png in sorted(ev.glob("*.png")):
        truth = " ".join(png.with_suffix(".gt.txt").read_text(encoding="utf-8").split())
        lines.append((truth, {name: read(png, lang, d) for name, lang, d in variants}))
    chars = sum(len(t) for t, _ in lines) or 1
    res = {}
    for name, _, _ in variants:
        errs = sum(dist(r[name], t) for t, r in lines)
        exact = sum(r[name] == t for t, r in lines)
        res[name] = (errs, exact)
    std = res["standard"]
    best = min((n for n in res if n != "standard"), key=lambda n: (res[n][0], -res[n][1]), default=None)
    out = []
    if best and res[best][0] < std[0] * 0.9 and res[best][1] >= std[1]:
        lang = next(l for n, l, _ in variants if n == best)
        out.append(f"BEST {lang}")
    out.append(f"## OCR test on {len(lines)} lines it wasn't trained on\n")
    out.append("| Model | Wrong characters | Lines exactly right |")
    out.append("|---|---|---|")
    for name, (errs, exact) in res.items():
        out.append(f"| {name} | {errs} of {chars} ({100 * errs / chars:.1f}%) | {exact} of {len(lines)} |")
    out.append("")
    if best:
        out.append(f"<details><summary>Every line (standard vs {best})</summary>\n")
        out.append(f"| Truth | Standard | {best} |")
        out.append("|---|---|---|")
        esc = lambda s: s.replace("|", "\\|")
        for t, r in lines:
            out.append(f"| {esc(t)} | {esc(r['standard'])} | {esc(r[best])} |")
        out.append("\n</details>")
    print("\n".join(out))


if __name__ == "__main__":
    main()
