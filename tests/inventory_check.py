"""Checks inventory icon matching against the official icons (run by the
"Inventory icon check" workflow, which can reach meowdb):
  1. icons captured from shop rows (tests/fixtures/shop_icons/<item>.png) against
     every official icon: where the right item ranks, and how close it is;
  2. the inventory window in tests/fixtures/inventory.png: best matches per slot."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp()
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import mfm  # noqa: E402
from PIL import Image  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
res = mfm.update_items_meowdb(full=True, force=True)
print("item list:", getattr(res, "message", res))
con = mfm.db()
got, failed = mfm.download_all_icons(con, rate=10)
print(f"icons downloaded: {got}, failed: {failed}")
matcher = mfm.IconMatcher(con)
print(f"reference icons: {len(matcher.refs)}")

lines = []
true_d, wrong_d = [], []
import json  # noqa: E402

names = json.loads((FIX / "shop_icons" / "index.json").read_text(encoding="utf-8"))
for f in sorted((FIX / "shop_icons").glob("*.png")):
    item = names.get(f.name, f.stem)   # file names can't hold every character (":")
    if not mfm.is_known_item(item):
        continue
    top = matcher.match_slot(Image.open(f), top=200)
    rank = next((i for i, (n, _) in enumerate(top) if n == item), None)
    d_true = next((d for n, d in top if n == item), None)
    d_wrong = next((d for n, d in top if n != item), None)
    if d_true is not None:
        true_d.append(d_true)
    if d_wrong is not None:
        wrong_d.append(d_wrong)
    lines.append(f"{item}: rank {rank}, right {d_true if d_true is None else round(d_true, 3)}, "
                 f"best other {top[0][0] if top[0][0] != item else (top[1][0] if len(top) > 1 else '-')} "
                 f"{d_wrong if d_wrong is None else round(d_wrong, 3)}")
if true_d:
    lines.append(f"right-item distance: max {max(true_d):.3f}, avg {sum(true_d) / len(true_d):.3f}; "
                 f"best wrong item: min {min(wrong_d):.3f}")

inv = Image.open(FIX / "inventory.png").convert("RGB")
cfg = mfm.load_config()
for r in mfm.scan_inventory(inv, matcher, cfg):
    lines.append(f"slot {r['slot']}: " + ", ".join(f"{n} {d:.3f}" for n, d in matcher.match_slot(r["icon"], top=5))
                 + f" | qty {r['qty']}")
out = "\n".join(lines)
print(out)
Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")).write_text(out)
with open("result.txt", "w") as fh:
    fh.write(out)

# a few official icons, base64, for looking at them elsewhere (DUMP_ICONS="Name,Name")
dump = [n.strip() for n in os.environ.get("DUMP_ICONS", "").split(",") if n.strip()]
if dump:
    import base64
    keys = mfm._icon_keys()
    with open("dump.txt", "w") as fh:
        for name in dump:
            key = keys.get(name)
            row = con.execute("SELECT png FROM cache.meowdb_icons WHERE icon_key = ?", (str(key),)).fetchone() if key else None
            if row:
                fh.write(f"{name}\t{base64.b64encode(row[0]).decode()}\n")
