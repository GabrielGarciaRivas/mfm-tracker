"""
Live monitoring window for mfm. Run with:  python mfm.py gui   (or python mfm_gui.py)

Leave it running while you play. Every shop you open and scroll through is read
continuously; each listing appears in the Live tab the moment it's logged,
coloured by how it compares with market rate, along with which shop and map
it's in.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import mfm


# ---- fonts --------------------------------------------------------------------
# The app ships the Inter font (packaging/fonts, SIL Open Font License). Tk can only
# use installed fonts, so it's made available to this process alone: on Linux via
# a fontconfig file that adds our folder to the system's fonts, on Windows as a
# private font, on macOS through CoreText for this process only. Nothing is
# installed on the system.
UI_FAMILY = "Inter"


def _font_dir() -> Path | None:
    for d in (mfm.BUNDLE / "fonts", Path(__file__).resolve().parent / "packaging" / "fonts"):
        if d.is_dir() and any(d.glob("*.otf")):
            return d
    return None


def _register_fonts_macos(d: Path) -> None:
    import ctypes
    cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    ct = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreText.framework/CoreText")
    cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                          ctypes.c_long, ctypes.c_bool]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    ct.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    for f in d.glob("*.otf"):
        raw = str(f).encode("utf-8")
        url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
        if url:
            ct.CTFontManagerRegisterFontsForURL(url, 1, None)     # 1 = this process only
            cf.CFRelease(url)


MAC = mfm.sys.platform == "darwin"


def bind_right_click(widget, fn) -> None:
    """Context menus: right button everywhere; on a Mac also Control+click, and
    Button-2, which is the right button in older Tk versions there."""
    widget.bind("<Button-3>", fn)
    if MAC:
        widget.bind("<Button-2>", fn)
        widget.bind("<Control-Button-1>", fn)


def register_fonts() -> None:
    """Must run before the first tk.Tk() (fontconfig is read when Tk starts)."""
    d = _font_dir()
    if d is None:
        return
    try:
        if mfm.sys.platform == "win32":
            import ctypes
            for f in d.glob("*.otf"):
                ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)   # FR_PRIVATE
        elif mfm.sys.platform == "darwin":
            _register_fonts_macos(d)
        elif "FONTCONFIG_FILE" not in mfm.os.environ or mfm.FROZEN:
            conf = mfm.CACHE_DIR / "fonts.conf"
            system = "/etc/fonts/fonts.conf"
            conf.write_text(
                '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
                + (f'  <include ignore_missing="yes">{system}</include>\n' if Path(system).exists() else "")
                + f"  <dir>{d}</dir>\n</fontconfig>\n", encoding="utf-8")
            mfm.os.environ["FONTCONFIG_FILE"] = str(conf)
    except Exception:
        pass


register_fonts()


def apply_fonts(root) -> str:
    """Use Inter for every standard Tk font (falls back to the system font if it
    couldn't be loaded). Also defines MfmBold / MfmBig for emphasis and titles."""
    from tkinter import font as tkfont
    fams = set(tkfont.families(root))
    fam = UI_FAMILY if UI_FAMILY in fams else tkfont.nametofont("TkDefaultFont", root).actual("family")
    size = 9 if mfm.sys.platform == "win32" else 13 if MAC else 10
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                 "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
        try:
            f = tkfont.nametofont(name, root)
            f.configure(family=fam, size=size - (1 if name in ("TkSmallCaptionFont", "TkTooltipFont") else 0))
        except tk.TclError:
            pass
    tkfont.nametofont("TkHeadingFont", root).configure(weight="bold")
    keep = getattr(root, "_mfm_fonts", {})   # Tk deletes a named font when its object is freed
    for name, sz, wt in (("MfmBold", size, "bold"), ("MfmBig", size + 2, "bold")):
        try:
            keep[name] = tkfont.Font(root, name=name, family=fam, size=sz, weight=wt)
        except tk.TclError:   # already defined (second window / tests)
            tkfont.nametofont(name, root).configure(family=fam, size=sz, weight=wt)
    root._mfm_fonts = keep
    return fam

COLS = ("item", "each", "market", "diff", "verdict")
HEAD = {"item": "Item", "each": "Price", "market": "Market",
        "diff": "Diff", "verdict": "Verdict", "shop": "Shop", "player": "Player", "map": "Map",
        "channel": "Channel", "best_shop": "Shop", "best_player": "Player", "best_map": "Map",
        "best_channel": "Channel",
        "time": "Time", "low": "Low", "high": "High", "seen": "Seen",
        "source": "Source", "best": "Cheapest", "best_where": "Cheapest at",
        "status": "Status", "listed_med": "Listed med.", "sold_med": "Sold med.",
        "listed_n": "Listed", "sold_n": "Sold", "total": "Bundle price",
        "max_each": "Max price", "last_price": "Last price", "npc_buy": "NPC buy", "npc_sell": "NPC sell",
        "saved": "Saved",
        "suggest": "Suggested item", "score": "Alike", "count": "Listings", "raw": "What OCR read"}
WIDTH = {"item": 155, "each": 82, "market": 82, "diff": 52, "verdict": 62,
         "shop": 140, "player": 100, "map": 265, "channel": 72,
         "best_shop": 140, "best_player": 100, "best_map": 265, "best_channel": 72,
         "time": 126, "low": 95, "high": 95, "seen": 50, "source": 110,
         "best": 90, "best_where": 230, "status": 66, "listed_med": 95, "sold_med": 90,
         "listed_n": 60, "sold_n": 45, "total": 100, "max_each": 110, "last_price": 100, "npc_buy": 85, "npc_sell": 85,
         "saved": 110, "suggest": 260, "score": 60, "count": 65, "raw": 300}
NUMERIC = {"each", "market", "diff", "low", "high", "seen", "best", "listed_med",
           "sold_med", "listed_n", "sold_n", "total", "score", "count", "channel", "best_channel",
           "max_each", "last_price", "npc_buy", "npc_sell"}
CENTER = {"channel", "best_channel"}


def shop_text(shop, seller) -> str:
    """ "Title (Seller)", for one-line summaries (status bar, recent shops)."""
    return mfm.ShopFrame([], shop or "", seller or "").shop


def split_shop(text: str) -> tuple[str, str]:
    """ "Title (Seller)" (saved by older versions) -> ("Title", "Seller")."""
    m = re.fullmatch(r"(.*?)\s*\(([^()]*)\)\s*", text or "")
    return (m.group(1), m.group(2)) if m else (text or "", "")


def where_text(shop, seller, mp, channel) -> str:
    return mfm.location(mfm.ShopFrame([], shop or "", seller or "").shop, mp, channel)


def num(s: str) -> float:
    try:
        return float(str(s).replace(",", "").replace("%", "").replace("+", ""))
    except ValueError:
        return float("-inf")


class Tooltip:
    """Small help text that appears when the mouse rests on a widget for a moment.
    Only one is ever shown at a time."""
    DELAY_MS = 500
    active = None

    def __init__(self, widget, text: str, wrap: int = 340):
        self.widget, self.text, self.wrap = widget, text, wrap
        self.tip = self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _=None):
        self._cancel()
        self.job = self.widget.after(self.DELAY_MS, self._show)

    def _cancel(self):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None

    def _show(self):
        self.job = None
        if self.tip or not self.widget.winfo_exists():
            return
        if Tooltip.active is not None and Tooltip.active is not self:
            Tooltip.active._hide()
        Tooltip.active = self
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        try:
            tw.attributes("-topmost", True)
        except tk.TclError:
            pass
        tk.Label(tw, text=self.text, justify="left", wraplength=self.wrap, background="#fffbe6",
                 foreground="#222", relief="solid", borderwidth=1, padx=8, pady=5,
                 font="TkTooltipFont").pack()

    def _hide(self, _=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None
        if Tooltip.active is self:
            Tooltip.active = None


# Shown in Settings → About. (name, what it is / how it's used, link)
CREDITS = [
    ("Created by", [
        ("Jayee (Discord: @jayee88)", "", None),
    ]),
    ("Made with", [
        ("Claude Opus 5.5 (claude-opus-5-5) by Anthropic",
         "AI model that wrote the code, tests and documentation, working with you in Claude",
         "https://www.anthropic.com/claude"),
    ]),
    ("Game data", [
        ("NiaMeowDB (meowdb.com) — the meowdb team",
         "Item and map lists, item ids and icons for MapleStory Classic World",
         "https://meowdb.com/msclassic/"),
        ("OSMS Data Explorer (osmsdataexplorer.com) — @ohmi",
         "Backup item and map lists and icons, mined from MapleStory Classic World",
         "https://osmsdataexplorer.com/"),
    ]),
    ("Open source", [
        ("Tesseract OCR 5.3.4", "reads the text in shop windows · Apache-2.0",
         "https://github.com/tesseract-ocr/tesseract"),
        ("Tesseract English data (tessdata_fast)", "OCR language model · Apache-2.0",
         "https://github.com/tesseract-ocr/tessdata_fast"),
        ("Leptonica 1.87.0", "image library used by Tesseract · BSD-2-Clause",
         "https://github.com/DanBloomberg/leptonica"),
        ("libpng and zlib", "image compression used by Leptonica · libpng and zlib licenses",
         "https://github.com/pnggroup/libpng"),
        ("Python 3.13", "the language the app is written in · PSF License", "https://www.python.org/"),
        ("python-build-standalone", "portable Python used to build the Linux app · MPL-2.0",
         "https://github.com/astral-sh/python-build-standalone"),
        ("Tcl/Tk 9.0.3", "the window toolkit (tkinter) · Tcl/Tk license (BSD-style)",
         "https://github.com/tcltk/tk"),
        ("libXft 2.3.9", "smooth fonts for Tk on Linux, from OpenBSD's xenocara · HPND (MIT-style)",
         "https://github.com/openbsd/xenocara"),
        ("Pillow", "image processing · MIT-CMU (HPND)", "https://github.com/python-pillow/Pillow"),
        ("pytesseract", "Python bridge to Tesseract · Apache-2.0", "https://github.com/madmaze/pytesseract"),
        ("python-mss", "screen capture · MIT", "https://github.com/BoboTiG/python-mss"),
        ("pyspellchecker", "English word list for shop titles · MIT", "https://github.com/barrust/pyspellchecker"),
        ("SQLite", "the price database · public domain", "https://www.sqlite.org/"),
        ("Inter typeface", "the app's font · SIL Open Font License 1.1", "https://github.com/rsms/inter"),
        ("PyInstaller 6.22 (with pyinstaller-hooks-contrib, altgraph)",
         "packs everything into one app · GPL-2.0 with bootloader exception, Apache-2.0, MIT",
         "https://github.com/pyinstaller/pyinstaller"),
        ("pynput", "global hotkey for the command-line `hotkey` mode (not in the packaged app) · LGPL-3.0",
         "https://github.com/moses-palmer/pynput"),
    ]),
]


def tip(text: str, *widgets) -> None:
    for w in widgets:
        Tooltip(w, text)


def ask_value(parent, title, prompt, initial="", choices=None, check=None) -> str | None:
    """Small modal dialog with one text box (a dropdown that also takes typing when
    `choices` is given). Returns the text, or None if cancelled. OK stays disabled
    while `check(text)` is False."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.resizable(False, False)
    frm = ttk.Frame(win, padding=14)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text=prompt, wraplength=360, justify="left").pack(anchor="w")
    var = tk.StringVar(value=initial)
    box = (ttk.Combobox(frm, textvariable=var, values=choices, width=12, height=15) if choices
           else ttk.Entry(frm, textvariable=var, width=18))
    box.pack(anchor="w", pady=(8, 10))
    result = {"v": None}
    btns = ttk.Frame(frm)
    btns.pack(fill="x")

    def ok(_=None):
        if check is None or check(var.get()):
            result["v"] = var.get()
            win.destroy()

    ok_btn = ttk.Button(btns, text="OK", command=ok)
    ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
    ok_btn.pack(side="right", padx=6)

    def validate(*_):
        ok_btn.state(["!disabled"] if check is None or check(var.get()) else ["disabled"])
    var.trace_add("write", validate)
    validate()
    win.bind("<Return>", ok)
    win.bind("<KP_Enter>", ok)
    win.bind("<Escape>", lambda e: win.destroy())
    box.focus_set()
    box.select_range(0, "end")
    win.update_idletasks()
    try:
        win.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")
        win.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(win)
    return result["v"]


def make_tree(parent, cols) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    # "#0" (the tree column) holds the item's icon
    tree = ttk.Treeview(frame, columns=cols, show="tree headings", selectmode="extended")
    tree.column("#0", width=42, minwidth=42, stretch=False, anchor="center")
    tree.heading("#0", text="")
    for c in cols:
        tree.heading(c, text=HEAD[c], command=lambda c=c: sort_tree(tree, c, False))
        tree.column(c, width=WIDTH[c], anchor="center" if c in CENTER else "e" if c in NUMERIC else "w",
                    stretch=(c == "item"))
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sb.set)

    def xset(lo, hi):        # the horizontal bar only shows when the columns don't fit
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            hsb.pack_forget()
        elif not hsb.winfo_ismapped():
            hsb.pack(side="bottom", fill="x", before=tree)
        hsb.set(lo, hi)
    tree.configure(xscrollcommand=xset)
    sb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    tree.tag_configure("deal", background="#d5f2dc", foreground="#145c2c")
    tree.tag_configure("high", background="#fadad7", foreground="#8c1d16")
    tree.tag_configure("unknown", foreground="#8a8a8a")
    tree.tag_configure("sold", foreground="#9a9a9a", background="#f0f0f0")
    tree.tag_configure("watch", font="MfmBold")
    tree.tag_configure("ignored", foreground="#a0a0a0")
    tree.tag_configure("outlier", foreground="#a0661a", background="#fbf3e4")
    tree.frame = frame
    enable_multiselect(tree)
    return tree


def enable_multiselect(tree) -> None:
    """Picking several rows at once, on top of Tk's own Ctrl+click / Shift+click:
    - Alt+click adds or removes a single row
    - Ctrl+Alt+drag adds every row the mouse passes over (scrolls at the edges)
    - Ctrl+A selects all, Esc clears"""
    st = {"anchor": None, "base": set()}
    tree.dragging = False

    def toggle(e):
        r = tree.identify_row(e.y)
        if r:
            tree.selection_toggle(r)
            tree.focus(r)
            st["anchor"], st["base"] = r, set(tree.selection())
        return "break"

    def range_start(e):
        r = tree.identify_row(e.y)
        if r:
            st["anchor"], st["base"] = r, set(tree.selection())
            tree.selection_add(r)
            tree.focus(r)
            tree.dragging = True
        return "break"

    def range_drag(e):
        a = st["anchor"]
        if a is None or not tree.exists(a):
            return "break"
        h = tree.winfo_height()
        if e.y < 30:
            tree.yview_scroll(-1, "units")
        elif e.y > h - 6:
            tree.yview_scroll(1, "units")
        r = tree.identify_row(min(max(e.y, 30), h - 4))
        if r:
            kids = tree.get_children("")
            i, j = sorted((kids.index(a), kids.index(r)))
            tree.selection_set(list(st["base"] | set(kids[i:j + 1])))
        return "break"

    def release(_e):
        tree.dragging = False

    # on a Mac, Option is Alt; Ctrl+click is right-click there, so Cmd+Option+drag too
    alt = ("Alt", "Option") if MAC else ("Alt",)
    ctrl = ("Control", "Command") if MAC else ("Control",)
    for a in alt:
        tree.bind(f"<{a}-Button-1>", toggle)
        tree.bind(f"<{a}-B1-Motion>", lambda e: range_drag(e) if tree.dragging else "break")
        for c in ctrl:
            tree.bind(f"<{c}-{a}-Button-1>", range_start)
            tree.bind(f"<{c}-{a}-B1-Motion>", range_drag)
    tree.bind("<B1-Motion>", lambda e: range_drag(e) if tree.dragging else None, add="+")
    tree.bind("<ButtonRelease-1>", release, add="+")
    for c in (("Control", "Command") if MAC else ("Control",)):
        tree.bind(f"<{c}-a>", lambda e: (tree.selection_set(tree.get_children("")), "break")[1])
        tree.bind(f"<{c}-A>", lambda e: (tree.selection_set(tree.get_children("")), "break")[1])
    tree.bind("<Escape>", lambda e: tree.selection_set(()))


def sort_tree(tree, col, reverse):
    rows = [(tree.set(k, col), k) for k in tree.get_children("")]
    key = (lambda r: num(r[0])) if col in NUMERIC else (lambda r: r[0].lower())
    rows.sort(key=key, reverse=reverse)
    for i, (_, k) in enumerate(rows):
        tree.move(k, "", i)
    tree.heading(col, command=lambda: sort_tree(tree, col, not reverse))


def tag_for(v: str) -> str:
    return {"DEAL": "deal", "HIGH": "high", "?": "unknown", "SOLD": "sold", "OUTLIER": "outlier"}.get(v, "")


def diff_text(pct) -> str:
    return "" if pct is None else f"{pct:+.0f}%"


class IconList:
    """A list of item names with their icons (Treeview), for search results."""

    def __init__(self, parent, app, height=8, width=360):
        self.app = app
        self.tree = ttk.Treeview(parent, show="tree", selectmode="browse", style="Search.Treeview",
                                 height=height)
        self.tree.column("#0", width=width)
        self.names: dict[str, str] = {}
        app.icon_lists.append(self)

    def set_names(self, names):
        t = self.tree
        t.delete(*t.get_children())
        self.names = {}
        for n in names:
            iid = t.insert("", "end", text="  " + n, image=self.app.icon_for(n, 26))
            self.names[iid] = n
        kids = t.get_children()
        if kids:
            t.selection_set(kids[0])
            t.see(kids[0])
        self.app.request_icons(list(names)[:8])

    def selected(self) -> str:
        sel = self.tree.selection()
        return self.names.get(sel[0], "") if sel else ""

    def refresh_images(self):
        try:
            for iid, n in self.names.items():
                self.tree.item(iid, image=self.app.icon_for(n, 26))
        except tk.TclError:
            pass

    def alive(self) -> bool:
        try:
            return bool(self.tree.winfo_exists())
        except tk.TclError:
            return False


class ItemSearch(ttk.Frame):
    """Text box that suggests meowdb item names, with their icons, as you type.
    Arrow keys / mouse pick a suggestion; Enter with nothing picked calls on_return."""

    def __init__(self, parent, app, width=42, on_return=None):
        super().__init__(parent)
        self.app, self.on_return = app, on_return
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.pack(fill="x")
        self.popup = None
        self.list = None
        self._after = None
        self._quiet = False
        self._navigated = False
        self.var.trace_add("write", self._changed)
        self.entry.bind("<Down>", self._into_list)
        self.entry.bind("<Escape>", lambda e: self.hide())
        self.entry.bind("<Return>", self._enter)
        self.entry.bind("<KP_Enter>", self._enter)
        self.entry.bind("<FocusOut>", lambda e: self.after(200, self._maybe_hide))

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str) -> None:
        self._quiet = True
        self.var.set(value)
        self._quiet = False
        self.hide()

    def focus(self):
        self.entry.focus_set()

    def _changed(self, *_):
        if self._quiet:
            return
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(120, self._update)

    def _update(self):
        self._after = None
        text = self.var.get().strip()
        names = mfm.suggest_items(text, 12) if len(text) >= 2 else []
        if not names or (len(names) == 1 and names[0] == text):
            self.hide()
            return
        self._show(names)

    def _show(self, names):
        if self.popup is None:
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            self.popup.transient(self.winfo_toplevel())
            self.list = IconList(self.popup, self.app, height=8, width=max(self.entry.winfo_width(), 360))
            t = self.list.tree
            t.pack(fill="both", expand=True)
            t.bind("<ButtonRelease-1>", lambda e: self._pick())
            t.bind("<Return>", lambda e: self._pick())
            t.bind("<KP_Enter>", lambda e: self._pick())
            t.bind("<Escape>", lambda e: (self.hide(), self.entry.focus_set()))
            t.bind("<Up>", self._up)
            t.bind("<FocusOut>", lambda e: self.after(200, self._maybe_hide))
        self._navigated = False
        self.list.set_names(names)
        self.list.tree.configure(height=min(8, len(names)))
        x, y = self.entry.winfo_rootx(), self.entry.winfo_rooty() + self.entry.winfo_height()
        w = max(self.entry.winfo_width(), 360)
        self.list.tree.column("#0", width=w - 4)
        self.popup.geometry(f"{w}x{min(8, len(names)) * 30 + 4}+{x}+{y}")
        self.popup.deiconify()
        self.popup.lift()

    def hide(self):
        if self.popup is not None:
            self.popup.withdraw()

    def visible(self) -> bool:
        return self.popup is not None and self.popup.winfo_viewable()

    def _maybe_hide(self):
        f = self.focus_get()
        if self.popup is not None and f is not None and str(f).startswith(str(self.popup)):
            return
        if f is not self.entry:
            self.hide()

    def _into_list(self, _e=None):
        if self.visible():
            self._navigated = True
            self.list.tree.focus_set()
            kids = self.list.tree.get_children()
            if kids:
                self.list.tree.focus(self.list.tree.selection()[0] if self.list.tree.selection() else kids[0])
        return "break"

    def _up(self, _e=None):
        t = self.list.tree
        kids = t.get_children()
        if kids and t.selection() and t.selection()[0] == kids[0]:
            self.entry.focus_set()
            return "break"
        return None

    def _pick(self):
        name = self.list.selected() if self.list else ""
        if name:
            self.set(name)
            self.entry.focus_set()
            self.entry.icursor("end")

    def _enter(self, _e=None):
        if self.visible() and self._navigated:
            self._pick()
            return "break"
        self.hide()
        if self.on_return:
            self.on_return()
        return "break"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cfg = mfm.load_config()
        self.con = mfm.db()
        self.events: queue.Queue = queue.Queue()
        self.stop_event: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.monitor: mfm.Monitor | None = None
        self.preview_img = None
        self.last_map = ""
        self.found_at = None
        self.icons: dict[str, ImageTk.PhotoImage] = {}
        self.scopes: dict[tuple, dict] = {}   # (table, row) -> which logged listing it is
        self.icon_lists: list = []           # open search lists, refreshed when icons arrive
        self._icon_queue: queue.Queue = queue.Queue()
        self._icon_asked: set[str] = set()
        self._icon_worker = None
        self.watch = mfm.load_watchlist()
        self._error_times: dict = {}
        root.report_callback_exception = self._tk_error
        self.ignored = set(mfm.load_ignorelist())
        self.shops_today = 0
        self.logged_today = 0

        root.title("Free Market Tracker")
        root.geometry("1300x700")
        root.minsize(980, 500)
        self._build()
        self.refresh_tables()
        root.after(100, self.drain_events)
        if not mfm.ITEMS_PATH.exists():
            root.after(800, self.offer_item_list)
        elif mfm.needs_type_refresh() or mfm.needs_map_refresh():
            root.after(800, self.offer_type_refresh)
        root.after(5000, self.periodic_refresh)
        root.after(1500, self.check_db_size)
        root.after(2000, lambda: self.run_retention(quiet=True))   # every launch
        root.after(6 * 3600 * 1000, self.retention_tick)           # and every 6 hours
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ layout
    def _build(self):
        self.ui_font = apply_fonts(self.root)
        style = ttk.Style()
        if "clam" in style.theme_names() and mfm.sys.platform != "win32":
            style.theme_use("clam")
        style.configure("TButton", padding=(10, 3), width=-6)   # size to the label (min 6 chars)
        style.configure("Treeview", rowheight=34)
        style.configure("Search.Treeview", rowheight=30)
        style.configure("Status.TLabel", foreground="#555")
        style.configure("Big.TLabel", font="MfmBig")
        style.configure("Bold.TLabel", font="MfmBold")
        style.configure("Treeview.Heading", font="TkHeadingFont")

        bar = ttk.Frame(self.root, padding=(10, 8))
        bar.pack(fill="x")
        self.top_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Always on top", variable=self.top_var,
                        command=lambda: self.root.attributes("-topmost", self.top_var.get())
                        ).pack(side="right")
        ttk.Button(bar, text="Settings", command=self.settings).pack(side="right", padx=6)
        ttk.Button(bar, text="Import prices…", command=self.import_ref).pack(side="right")
        ttk.Button(bar, text="Export prices…", command=self.export_prices).pack(side="right", padx=(0, 6))
        self.start_btn = ttk.Button(bar, text="▶  Start monitoring", command=self.toggle, width=17)
        self.start_btn.pack(side="left")
        ttk.Button(bar, text="Shop area", command=self.calibrate).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Map area",
                   command=lambda: self.calibrate(key="map_region")).pack(side="left", padx=(6, 0))
        ttk.Label(bar, text="Channel:").pack(side="left", padx=(14, 4))
        # stays filled in for every shop until you change it (saved with each listing)
        self.channel_var = tk.StringVar()
        self.channel_var.trace_add("write", self._channel_changed)
        # pick 1-100 from the list or type it; anything else can't be entered
        ok = (self.root.register(lambda p: p == "" or (p.isdigit() and p[0] != "0" and int(p) <= 100)), "%P")
        self.channel_box = ttk.Combobox(bar, textvariable=self.channel_var, width=5, height=15,
                                        values=[str(n) for n in range(1, 101)],
                                        validate="key", validatecommand=ok)
        self.channel_box.pack(side="left")
        # rarely needed now that shop changes are detected on every frame
        self.root.bind_all("<Control-n>", lambda e: self.next_shop())
        if MAC:
            self.root.bind_all("<Command-n>", lambda e: self.next_shop())

        # red warning when prices.db gets big (shown by check_db_size)
        self.size_warn = tk.Label(self.root, background="#c62828", foreground="white", anchor="w",
                                  padx=10, pady=5, cursor="hand2", font="MfmBold", justify="left")
        self.size_warn.bind("<Button-1>", lambda e: self.settings())
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=10)

        # Live tab: current shop table + preview/stats panel
        live = ttk.Frame(self.nb, padding=6)
        self.nb.add(live, text="  Live  ")
        left = ttk.Frame(live)
        left.pack(side="left", fill="both", expand=True)
        self.shop_title = ttk.Label(left, text="Waiting for a shop…", style="Big.TLabel")
        self.shop_title.pack(anchor="w", pady=(0, 6))
        self.live = make_tree(left, COLS + ("saved",))
        self.live.tag_configure("dupe", foreground="#7a7a7a")
        self.live.frame.pack(fill="both", expand=True)
        self.live.bind("<Double-1>", lambda e: self.open_history(self.live))

        right = ttk.Frame(live, padding=(10, 0, 0, 0), width=300)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        ttk.Label(right, text="What the OCR sees").pack(anchor="w")
        self.preview = ttk.Label(right, relief="solid", anchor="center", text="no capture yet")
        self.preview.pack(fill="x", pady=(2, 8), ipady=4)
        self.stats = ttk.Label(right, justify="left")
        self.stats.pack(anchor="w")
        ttk.Label(right, text="Recent shops", style="Big.TLabel").pack(anchor="w", pady=(14, 4))
        self.recent = tk.Listbox(right, height=10, activestyle="none", borderwidth=0)
        self.recent.pack(fill="both", expand=True)

        # Deals tab
        deals = ttk.Frame(self.nb, padding=6)
        self.nb.add(deals, text="  Deals  ")
        top = ttk.Frame(deals)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Listings from the last").pack(side="left")
        self.hours_var = tk.IntVar(value=24)
        ttk.Spinbox(top, from_=1, to=720, width=5, textvariable=self.hours_var,
                    command=self.refresh_tables).pack(side="left", padx=4)
        ttk.Label(top, text="hours, best deals first.").pack(side="left")
        self.only_deals = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Deals only", variable=self.only_deals,
                        command=self.refresh_tables).pack(side="right")
        self.show_sold = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Include sold", variable=self.show_sold,
                        command=self.refresh_tables).pack(side="right", padx=10)
        self.show_ignored = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Show ignored", variable=self.show_ignored,
                        command=self.refresh_tables).pack(side="right")
        self.show_outliers = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Show outliers", variable=self.show_outliers,
                        command=self.refresh_tables).pack(side="right", padx=10)
        self.deals = make_tree(deals, COLS + ("status", "shop", "player", "map", "channel", "time"))
        self.deals.frame.pack(fill="both", expand=True)
        self.deals.bind("<Double-1>", lambda e: self.open_history(self.deals))

        # Items tab
        items = ttk.Frame(self.nb, padding=6)
        self.nb.add(items, text="  Items  ")
        ttk.Label(items, text="Cheapest listing still for sale (seen in the last 24 h) and where, "
                              "plus what items list for vs. actually sell for. "
                              "Delete removes a bad OCR read; "
                              + ("Option+click or Cmd+Option+drag" if MAC else "Alt+click or Ctrl+Alt+drag")
                              + " picks several rows."
                  ).pack(anchor="w")
        legend = ttk.Frame(items)
        legend.pack(anchor="w", pady=(2, 6))
        self.legend_icon = ImageTk.PhotoImage(self._legend_badge())
        ttk.Label(legend, image=self.legend_icon).pack(side="left")
        ttk.Label(legend, foreground="#666",
                  text=" = not matched to any item in the database (check the spelling, or it may be new). "
                       "The Review tab lists them all with suggested matches."
                  ).pack(side="left")
        self._build_item_filter(items)
        self.items = make_tree(items, ("item", "best", "best_shop", "best_player", "best_map", "best_channel",
                                       "listed_med", "listed_n",
                                       "sold_med", "sold_n", "market", "npc_buy", "npc_sell", "source"))
        self.items.frame.pack(fill="both", expand=True)
        self.items.bind("<Double-1>", lambda e: self.open_history(self.items))
        self.items.bind("<Delete>", lambda e: self.forget_selected())
        self.items.bind("<BackSpace>", lambda e: self.forget_selected())
        for tree in (self.live, self.deals):
            tree.bind("<Delete>", lambda e, t=tree: self.delete_listing(t))
            tree.bind("<BackSpace>", lambda e, t=tree: self.delete_listing(t))
        for tree in (self.live, self.deals, self.items):
            self._add_menu(tree)

        self._build_review_tab()
        self._build_alerts_tab()
        self._build_ignore_tab()

        self.status = ttk.Label(self.root, style="Status.TLabel", padding=(10, 4))
        self.status.pack(fill="x")
        self._set_status()
        self._update_stats(None, None)

    # ------------------------------------------------------------------ monitoring
    def toggle(self):
        if self.worker and self.worker.is_alive():
            self.stop()
        else:
            self.start()

    def start(self):
        if not mfm.mac_screen_access(ask=True):
            messagebox.showwarning(
                "Screen Recording permission needed",
                "macOS only lets Free Market Tracker see the game after you allow it:\n\n"
                "System Settings > Privacy & Security > Screen Recording > turn on "
                "Free Market Tracker.\n\nThen quit and reopen the app (macOS applies the "
                "permission on the next start).")
            return
        self.stop_event = threading.Event()
        self.monitor = mfm.Monitor(self.cfg, lambda k, p: self.events.put((k, p)),
                                   self.channel())
        self.worker = threading.Thread(target=self.monitor.run, args=(self.stop_event,), daemon=True)
        self.worker.start()
        self.start_btn.config(text="■  Stop monitoring")
        self._set_status("Monitoring — open shops and scroll through them normally.")

    def stop(self):
        if self.stop_event:
            self.stop_event.set()
        self.start_btn.config(text="▶  Start monitoring")
        self._set_status("Stopped.")

    def channel(self) -> str | None:
        """The channel in the box (1-100), as saved with listings; None when empty."""
        ch = mfm.parse_channel(self.channel_var.get())
        return ch if ch and ch.isdigit() else None

    def next_shop(self):
        """Manually split visits, for when you hop shops without the window closing."""
        if self.monitor:
            self.monitor.request_split()
            self._set_status("Next shop: the current visit was ended (Ctrl+N).")

    def _channel_changed(self, *_):
        if self.monitor:
            self.monitor.channel = self.channel()

    def drain_events(self):
        try:
            while True:
                kind, p = self.events.get_nowait()
                getattr(self, f"on_{kind.lstrip('_')}")(p)
        except queue.Empty:
            pass
        self.root.after(100, self.drain_events)

    def on_session(self, p):
        self.live.delete(*self.live.get_children())
        self.scopes = {k: v for k, v in self.scopes.items() if k[0] != str(self.live)}
        shop = (" · ".join(x for x in (p.get("title") and f"Shop: {p['title']}",
                                        p.get("seller") and f"Player: {p['seller']}") if x)
                or p["shop"])
        self.shop_title.config(text="  ·  ".join(x for x in (
            shop, p["map"], f"opened {p['started']:%H:%M:%S}") if x))
        self.last_map = p["map"] or self.last_map
        self._update_stats(None, None)
        self.shops_today += 1

    def on_new(self, s: mfm.SeenListing):
        verdict = s.verdict
        if s.status == "sold":
            verdict = "SOLD"   # was listed on an earlier visit, sold since
        hit = None if s.sold else mfm.watch_match(self.watch, s.item, s.each)
        if hit:
            self.alert(s, hit)
        self._forget_icon(s.item)  # an icon may have just been saved/upgraded
        ign = s.item in self.ignored
        iid = self.live.insert("", "end", image=self.icon_for(s.item, found=bool(hit)),
                         tags=(("ignored",) if ign and verdict != "SOLD" else (tag_for(verdict),))
                         + (("watch",) if hit else ()), values=(
            s.item, mfm.fmt(s.each), mfm.fmt(s.market),
            diff_text(s.pct), verdict,
            {"seen": "already logged", "sold": "marked sold"}.get(s.status, "new")))
        if s.status == "seen":   # same shop, same price, logged in the last 24 h: not added again
            self.live.item(iid, tags=tuple(self.live.item(iid, "tags")) + ("dupe",))
        self.scopes[(str(self.live), iid)] = {"price": s.price, "qty": s.qty, "label": s.shop}
        self.live.yview_moveto(1.0)
        if s.status != "seen":
            self.logged_today += 1
        # deals only make a sound for items on your alert list (a watched item under
        # its max price already pinged above)
        if verdict == "DEAL" and not hit and not ign and any(w["item"] == s.item for w in self.watch):
            self.root.bell()

    def alert(self, s, w):
        """A watched item is for sale here: ping, say where, remember it."""
        import time as _t
        if self.cfg.get("alert_sound_on", True) and _t.monotonic() - getattr(self, "_last_ping", 0) > 2:
            self._last_ping = _t.monotonic()   # one ping per burst of matches
            if not mfm.play_sound(self.cfg.get("alert_sound") or None):
                self.root.bell()
        where = " · ".join(x for x in (s.shop, s.map, mfm.channel_label(s.channel)) if x)
        self._set_status(f"Alert: {s.item} for {mfm.fmt(s.each)} each at {where}")
        title, player = (s.title, s.seller) if (s.title or s.seller) else split_shop(s.shop)
        w["last_found"] = {"each": s.each, "shop": title, "player": player, "map": s.map,
                           "channel": s.channel, "time": s.first_seen}
        mfm.save_watchlist(self.watch)
        self.refresh_alerts()
        if self.cfg.get("alert_raise", True):
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass

    def on_closed(self, p):
        n = p["count"]
        deals = sum(1 for k in self.live.get_children() if "deal" in self.live.item(k, "tags"))
        label = " · ".join(x for x in (p.get("title"), p.get("seller")) if x) or p["shop"]
        self.recent.insert(0, f"{datetime.now():%H:%M}  {label}"
                              + (f" @ {p['map']}" if p["map"] else "") + f"  — {n} items"
                              + (f", {p['sold']} sold" if p.get("sold") else "")
                              + (f", {deals} deal{'s' if deals != 1 else ''}" if deals else ""))
        if deals:
            self.recent.itemconfig(0, foreground="#145c2c")
        self.shop_title.config(text=self.shop_title.cget("text") + "  ·  closed")
        self.refresh_tables()
        self.fetch_icons_async([self.live.set(k, "item") for k in self.live.get_children()])

    def on_frame(self, p):
        img = p["image"].copy()
        img.thumbnail((280, 200))
        self.preview_img = ImageTk.PhotoImage(img)
        self.preview.config(image=self.preview_img, text="")
        n = len(p["listings"])
        self._update_stats(f"{n}  (+{p['hidden']} under cursor)" if p.get("hidden") else n,
                           p["ocr_ms"])

    def on_layout(self, layout):
        self.found_at = layout
        self._update_stats(None, None)

    def on_error(self, msg):
        self.report_error("Monitoring error", msg)

    def report_error(self, title: str, msg: str):
        """Errors go to the status bar and to an error window you can't miss. One
        window collects them (no pile of dialogs), and the same error repeating
        (e.g. on every frame) reopens it at most every 2 minutes."""
        import time as _t
        msg = str(msg).strip() or "Unknown error"
        self._set_status(f"Error: {title}: {msg}")
        hint = ""
        low = msg.lower()
        if "readonly" in low or "read-only" in low or "permission denied" in low:
            hint = ("The price database can't be written to. Check that the data folder isn't "
                    "read-only and that you have write permission:\n" + str(mfm.DATA))
        elif "disk" in low and ("full" in low or "space" in low):
            hint = "The disk is full: free some space so prices can be saved."
        elif "database is locked" in low:
            hint = "The price database is busy (another copy of the tracker open?). Close the other one."
        elif any(k in low for k in ("urlopen", "timed out", "name resolution", "connection", "http error")):
            hint = "Check your internet connection; you can retry later from Settings."
        key = (title, msg)
        now = _t.monotonic()
        last = self._error_times.get(key)
        self._error_times[key] = now
        if last is not None and now - last < 120:
            return
        line = f"{datetime.now():%H:%M:%S}  {title}\n{msg}" + (f"\n→ {hint}" if hint else "")
        win = getattr(self, "_error_win", None)
        if win is None or not win.winfo_exists():
            win = tk.Toplevel(self.root)
            win.title("Free Market Tracker: error")
            win.transient(self.root)
            win.geometry("620x300")
            head = ttk.Frame(win, padding=(14, 12, 14, 6))
            head.pack(fill="x")
            ttk.Label(head, text="⚠", foreground="#c8352b", font=("TkDefaultFont", 22)).pack(side="left")
            ttk.Label(head, text="  Something went wrong", style="Big.TLabel").pack(side="left")
            box = tk.Text(win, wrap="word", height=8, relief="flat", padx=10, pady=8,
                          background="#fbefee", font="TkDefaultFont")
            box.pack(fill="both", expand=True, padx=14)
            btns = ttk.Frame(win, padding=(14, 8, 14, 12))
            btns.pack(fill="x")
            ttk.Button(btns, text="OK", command=win.destroy).pack(side="right")
            ttk.Button(btns, text="Copy details", command=lambda: (
                self.root.clipboard_clear(), self.root.clipboard_append(box.get("1.0", "end")))
            ).pack(side="right", padx=6)
            ttk.Button(btns, text="Open data folder", command=self.open_data_folder).pack(side="left")
            win._box = box
            self._error_win = win
        box = win._box
        box.configure(state="normal")
        if box.get("1.0", "end").strip():
            box.insert("end", "\n\n")
        box.insert("end", line)
        box.see("end")
        box.configure(state="disabled")
        win.deiconify()
        win.lift()

    def _tk_error(self, exc, val, tb):
        """Any failing button / menu action (e.g. deleting from a write-protected
        database) is reported instead of failing silently."""
        import traceback
        detail = "".join(traceback.format_exception_only(exc, val)).strip()
        try:
            with open(mfm.DATA / "app.log", "a", encoding="utf-8") as f:
                f.write("".join(traceback.format_exception(exc, val, tb)))
        except Exception:
            pass
        self.report_error("Action failed", detail)

    def _update_stats(self, rows, ocr_ms):
        on_screen = "—" if rows is None else rows
        speed = "—" if ocr_ms is None else f"{ocr_ms} ms"
        region, mregion = self.cfg.get("region"), self.cfg.get("map_region")

        def area(r, auto_r):
            # a saved area covering most of the screen is ignored (auto is used)
            screen = tuple(mfm.LAST_SCREEN_SIZE) or (self.root.winfo_screenwidth(),
                                                     self.root.winfo_screenheight())
            if r and not mfm.is_auto(r, screen):
                return f"manual {r[2]}×{r[3]}"
            if auto_r:
                return f"auto, found at {auto_r[0]},{auto_r[1]}"
            return "auto (open a shop)"
        lay = self.found_at
        self.stats.config(text=(
            f"Rows read this frame:  {on_screen}\n"
            f"OCR time:  {speed}\n"
            f"Shops visited:  {self.shops_today}\n"
            f"Listings logged:  {self.logged_today}\n"
            f"Shop area:  {area(region, lay.store if lay else None)}\n"
            f"Map area:  {area(mregion, lay.map if lay else None)}\n"
            f"Current map:  {self.last_map or '—'}"))

    def _set_status(self, text=None):
        base = text or "Idle. Press Start, then play normally."
        self.status.config(text=f"{base}    ·    v{mfm.VERSION}    ·    data: {mfm.DATA}")

    # ------------------------------------------------------------------ tables
    def check_db_size(self, repeat: bool = True):
        try:
            size = mfm.db_size()
        except OSError:
            size = 0
        if size > mfm.DB_WARN_BYTES:
            self.size_warn.config(text=(
                f"⚠  Your price database is {size / 1048576:,.0f} MB and getting large. It's "
                "recommended to archive and/or delete some data (click here: Settings → Data "
                "retention)."))
            if not self.size_warn.winfo_ismapped():
                self.size_warn.pack(fill="x", padx=10, pady=(0, 6), before=self.nb)
        elif self.size_warn.winfo_ismapped():
            self.size_warn.pack_forget()
        if repeat:
            self.root.after(60000, self.check_db_size)

    def retention_tick(self):
        """Every 6 hours while the app is open. Skipped while monitoring (cleaning up
        briefly locks the database) and tried again 10 minutes later."""
        if self.worker and self.worker.is_alive():
            self.root.after(10 * 60 * 1000, self.retention_tick)
            return
        self.run_retention(quiet=True)
        self.root.after(6 * 3600 * 1000, self.retention_tick)

    def run_retention(self, quiet=False, cfg=None, done=None):
        cfg = cfg or self.cfg
        if cfg.get("retention", "archive") not in ("archive", "delete") or getattr(self, "_pruning", False):
            return
        self._pruning = True

        def work():
            try:
                con = mfm.db()
                n, path = mfm.apply_retention(con, cfg)
                con.close()
                if n or not quiet:
                    self.events.put(("status", (
                        f"Removed {mfm.plural(n, 'listing')} not seen for "
                        f"{mfm.plural(int(cfg.get('keep_days', 30)), 'day')}"
                        + (f"; archived to {path}" if path else "") + ".")
                        if n else "No listings old enough to remove."))
                if n:
                    self.events.put(("call", lambda: (self.refresh_tables(), self.check_db_size(False))))
            except Exception as e:
                msg = f"Cleaning up old listings failed: {e}"
                self.events.put(("call", lambda: self.report_error("Cleanup failed", msg)))
            finally:
                self._pruning = False
                if done:
                    self.events.put(("call", done))
        threading.Thread(target=work, daemon=True).start()

    def periodic_refresh(self):
        if self.nb.index("current") != 0:
            self.refresh_tables()
        self.root.after(5000, self.periodic_refresh)

    def _keep_selection(self, tree, key):
        """Remember which rows are selected (and the scroll position) so a refresh
        doesn't throw away a multi-selection; returns a function that restores it."""
        chosen = {key(tree, k) for k in tree.selection()}
        top = tree.yview()[0]

        def restore():
            again = [k for k in tree.get_children("") if key(tree, k) in chosen]
            if again:
                tree.selection_set(again)
            tree.yview_moveto(top)
        return restore

    def refresh_tables(self):
        cfg, con = self.cfg, self.con
        if any(getattr(t, "dragging", False) for t in (self.deals, self.items)):
            return   # mid-selection; the next refresh will catch up
        self.refresh_alerts()
        self.refresh_ignored()
        self.refresh_review()
        row_key = lambda t, k: tuple(t.set(k, c) for c in ("item", "each", "status", "shop", "player", "map",
                                                           "channel"))
        restore_deals = self._keep_selection(self.deals, row_key)
        restore_items = self._keep_selection(self.items, lambda t, k: t.set(k, "item"))
        try:
            hours = max(1, int(self.hours_var.get()))
        except (tk.TclError, ValueError):
            hours = 24
        since = mfm.utc_ago(hours=hours)
        sold_filter = "" if self.show_sold.get() else "AND COALESCE(sold, 0) = 0"
        rows = con.execute(
            "SELECT item, price, qty, shop, seller, map, channel, COALESCE(sold, 0), "
            "MAX(COALESCE(last_seen, ts)) FROM listings WHERE COALESCE(last_seen, ts) >= ? "
            f"{sold_filter} GROUP BY item, price, qty, shop, seller, map, sold",
            (since,)).fetchall()
        scored = []
        bounds: dict[str, object] = {}
        for item, price, qty, shop, seller, mp, channel, sold, ts in rows:
            each = price
            mkt, _ = mfm.market_rate(con, item, cfg)
            if item not in bounds:
                bounds[item] = mfm.outlier_bounds(con, item, cfg)
            v, pct = mfm.verdict(each, mkt, cfg["deal_threshold_pct"], bounds[item])
            if v == "OUTLIER" and not self.show_outliers.get():
                continue
            if self.only_deals.get() and (v != "DEAL" or sold):
                continue
            if item in self.ignored and not self.show_ignored.get():
                continue
            scored.append((sold, pct if pct is not None else 999, item, qty, each, mkt, v,
                           (shop or "", seller or "", mp or "", channel or ""), ts, price, shop, seller))
        scored.sort()
        self.deals.delete(*self.deals.get_children())
        self.scopes = {k: v for k, v in self.scopes.items() if k[0] != str(self.deals)}
        for sold, pct, item, qty, each, mkt, v, where, ts, price, shop, seller in scored:
            found = not sold and bool(mfm.watch_match(self.watch, item, each))
            tag = "sold" if sold else ("ignored" if item in self.ignored else tag_for(v))
            iid = self.deals.insert("", "end", image=self.icon_for(item, found=found),
                              tags=(tag,) + (("watch",) if found else ()), values=(
                item, mfm.fmt(each), mfm.fmt(mkt),
                diff_text(None if pct == 999 else pct),
                v, "sold" if sold else "for sale", *where, mfm.local_time(ts)))
            self.scopes[(str(self.deals), iid)] = {"price": price, "qty": qty, "shop": shop, "seller": seller}

        best = mfm.cheapest(con, 24, cfg)
        self.items.delete(*self.items.get_children())
        filt = self.item_filter() if hasattr(self, "f_name") else {}
        shown = total = 0
        for (item,) in con.execute(
                "SELECT DISTINCT item FROM listings ORDER BY item COLLATE NOCASE"):
            total += 1
            if filt and not mfm.item_matches(item, filt):
                continue
            shown += 1
            mkt, src = mfm.market_rate(con, item, cfg)
            info = mfm.item_info(item)
            st = mfm.price_stats(con, item, cfg, bounds.get(item, "auto"))
            b = best.get(item)
            tag = ""
            if item in self.ignored:
                tag = "ignored"
            elif b:
                v, _ = mfm.verdict(b[0], mkt, cfg["deal_threshold_pct"])
                tag = tag_for(v) if v == "DEAL" else ""
            found = bool(b) and bool(mfm.watch_match(self.watch, item, b[0]))
            self.items.insert("", "end", image=self.icon_for(item, found=found),
                              tags=(tag,) + (("watch",) if found else ()), values=(
                item, mfm.fmt(b[0]) if b else "-", (b[1] or "") if b else "", (b[2] or "") if b else "",
                (b[3] or "") if b else "", (b[4] or "") if b else "",
                mfm.fmt(st["listed_median"]), st["listed_n"],
                mfm.fmt(st["sold_median"]), st["sold_n"], mfm.fmt(mkt),
                mfm.fmt(info.get("npcBuy")) if info and info.get("npcBuy") else "-",
                mfm.fmt(info.get("npcSell")) if info and info.get("npcSell") else "-", src))
        if hasattr(self, "f_count"):
            self.f_count.config(text=f"{shown:,} of {total:,} items" if shown != total else
                                f"{total:,} items")
        restore_deals()
        restore_items()

    # ------------------------------------------------------------------ items filter
    ANY = "Any"

    def _build_item_filter(self, parent):
        """Filter bar for the Items tab, modelled on NiaMeowDB's item database: name,
        category and subtype, class (with or without all-class items), level range and
        sold by NPCs. Remembered between sessions."""
        saved = self.cfg.get("items_filter") or {}
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 6))
        self.f_name = tk.StringVar(value=saved.get("name", ""))
        self.f_type = tk.StringVar(value=saved.get("type") or self.ANY)
        self.f_sub = tk.StringVar(value=saved.get("subtype") or self.ANY)
        self.f_job = tk.StringVar(value=saved.get("job") or self.ANY)
        self.f_allclass = tk.BooleanVar(value=saved.get("all_class", True))
        self.f_lmin = tk.StringVar(value="" if saved.get("level_min") is None else str(saved["level_min"]))
        self.f_lmax = tk.StringVar(value="" if saved.get("level_max") is None else str(saved["level_max"]))
        self.f_npc = tk.BooleanVar(value=saved.get("npc", False))

        def lab(text, **kw):
            ttk.Label(bar, text=text).pack(side="left", **kw)
        lab("Filter:")
        e = ttk.Entry(bar, textvariable=self.f_name, width=16)
        e.pack(side="left", padx=(4, 10))
        tip("Show items whose name contains this text.", e)
        lab("Category")
        self.f_type_cb = ttk.Combobox(bar, textvariable=self.f_type, state="readonly", width=7)
        self.f_type_cb.pack(side="left", padx=(4, 6))
        tip("Equip, Use, Etc, Setup or Cash, as in NiaMeowDB's item database.", self.f_type_cb)
        self.f_sub_cb = ttk.Combobox(bar, textvariable=self.f_sub, state="readonly", width=14)
        self.f_sub_cb.pack(side="left", padx=(0, 10))
        tip("The kind of item within the category (Shoes, Scroll, Ore, ...).", self.f_sub_cb)
        lab("Class")
        self.f_job_cb = ttk.Combobox(bar, textvariable=self.f_job, state="readonly", width=9)
        self.f_job_cb.pack(side="left", padx=(4, 2))
        tip("Items that need this class.", self.f_job_cb)
        cb = ttk.Checkbutton(bar, text="+ all-class", variable=self.f_allclass)
        cb.pack(side="left", padx=(0, 10))
        tip("With a class picked, also show items any class can use.", cb)
        lab("Level")
        ok = (self.root.register(lambda v: v == "" or (v.isdigit() and int(v) <= 250)), "%P")
        for var, t in ((self.f_lmin, "Lowest required level"), (self.f_lmax, "Highest required level")):
            sp = ttk.Spinbox(bar, from_=0, to=200, increment=10, width=4, textvariable=var,
                             validate="key", validatecommand=ok)
            sp.pack(side="left", padx=(4, 0))
            tip(t + " (empty = no limit).", sp)
            if var is self.f_lmin:
                lab("–", padx=(3, 0))
        cb = ttk.Checkbutton(bar, text="Sold by NPCs", variable=self.f_npc)
        cb.pack(side="left", padx=(10, 0))
        tip("Only items an NPC shop sells (handy to spot overpriced listings).", cb)
        b = ttk.Button(bar, text="Clear", command=self.clear_item_filter)
        b.pack(side="left", padx=(10, 0))
        self.f_count = ttk.Label(bar, foreground="#666")
        self.f_count.pack(side="left", padx=(10, 0))
        self._filter_job = None

        def changed(*_):
            if self.f_type.get() == self.ANY and self.f_sub.get() != self.ANY:
                self.f_sub.set(self.ANY)
            self._update_filter_choices()
            if self._filter_job:
                self.root.after_cancel(self._filter_job)
            self._filter_job = self.root.after(250, self._apply_item_filter)   # after typing pauses
        for v in (self.f_name, self.f_type, self.f_sub, self.f_job, self.f_allclass,
                  self.f_lmin, self.f_lmax, self.f_npc):
            v.trace_add("write", changed)
        self._update_filter_choices()

    def item_filter(self) -> dict:
        def num(v):
            return int(v) if v.strip().isdigit() else None
        any_ = self.ANY
        return {"name": self.f_name.get().strip(),
                "type": None if self.f_type.get() == any_ else self.f_type.get(),
                "subtype": None if self.f_sub.get() == any_ else self.f_sub.get(),
                "job": None if self.f_job.get() == any_ else self.f_job.get(),
                "all_class": self.f_allclass.get(),
                "level_min": num(self.f_lmin.get()), "level_max": num(self.f_lmax.get()),
                "npc": self.f_npc.get()}

    def _update_filter_choices(self):
        names = [r[0] for r in self.con.execute("SELECT DISTINCT item FROM listings")]
        opts = mfm.item_filter_options(names)
        self.f_type_cb["values"] = [self.ANY] + opts["types"]
        t = self.f_type.get()
        subs = opts["subtypes"].get(t, []) if t != self.ANY else []
        self.f_sub_cb["values"] = [self.ANY] + subs
        self.f_sub_cb.state(["!disabled" if subs else "disabled"])
        self.f_job_cb["values"] = [self.ANY] + opts["jobs"]

    def _apply_item_filter(self):
        self._filter_job = None
        f = self.item_filter()
        self.cfg["items_filter"] = f
        mfm.save_config(self.cfg)
        self.refresh_tables()

    def clear_item_filter(self):
        for v in (self.f_name, self.f_lmin, self.f_lmax):
            v.set("")
        for v in (self.f_type, self.f_sub, self.f_job):
            v.set(self.ANY)
        self.f_allclass.set(True)
        self.f_npc.set(False)

    def _build_alerts_tab(self):
        tab = ttk.Frame(self.nb, padding=6)
        self.nb.add(tab, text="  Alerts  ")
        ttk.Label(tab, text="Get a ping, and a green outline on the icon, when one of these is for "
                            "sale in a shop you open. Leave the max price empty to be alerted at any price."
                  ).pack(anchor="w", pady=(0, 6))
        add = ttk.Frame(tab)
        add.pack(fill="x")
        ttk.Label(add, text="Item:").pack(side="left")
        self.alert_entry = ItemSearch(add, self, width=42, on_return=lambda: self.alert_max_entry.focus_set())
        self.alert_entry.pack(side="left", padx=4)
        self.alert_item = self.alert_entry.var
        ttk.Label(add, text="Max price:").pack(side="left", padx=(10, 0))
        self.alert_max = tk.StringVar()
        self.alert_max_entry = ttk.Entry(add, textvariable=self.alert_max, width=12)
        self.alert_max_entry.pack(side="left", padx=4)
        self.alert_max_entry.bind("<Return>", lambda e: self.add_alert_from_form())
        ttk.Button(add, text="Add alert", command=self.add_alert_from_form).pack(side="left", padx=4)

        self.alerts = make_tree(tab, ("item", "max_each", "last_price", "shop", "player", "map", "channel", "time"))
        self.alerts.frame.pack(fill="both", expand=True, pady=6)
        self.alerts.bind("<Double-1>", lambda e: self.open_history(self.alerts))
        self._list_menu(self.alerts, [
            ("Show history", self.open_history, True),
            ("Change max price…", lambda t: self.change_alert_max(), False),
            None,
            ("Remove item", lambda t: self.remove_alert(), False)])
        self.alerts.bind("<Delete>", lambda e: self.remove_alert())
        self.alerts.bind("<BackSpace>", lambda e: self.remove_alert())

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Remove selected", command=self.remove_alert).pack(side="left")
        self.sound_on = tk.BooleanVar(value=self.cfg.get("alert_sound_on", True))
        ttk.Checkbutton(bottom, text="Play sound", variable=self.sound_on,
                        command=self._save_sound_prefs).pack(side="left", padx=(16, 0))
        self.raise_on = tk.BooleanVar(value=self.cfg.get("alert_raise", True))
        ttk.Checkbutton(bottom, text="Bring this window to front", variable=self.raise_on,
                        command=self._save_sound_prefs).pack(side="left", padx=(10, 0))
        ttk.Button(bottom, text="Test sound", command=self.test_sound).pack(side="left", padx=(10, 0))
        ttk.Button(bottom, text="Choose sound…", command=self.choose_sound).pack(side="left", padx=4)
        self.sound_lbl = ttk.Label(bottom, foreground="#666")
        self.sound_lbl.pack(side="left", padx=6)
        self.refresh_alerts()

    def refresh_alerts(self):
        if not hasattr(self, "alerts"):
            return
        restore = self._keep_selection(self.alerts, lambda t, k: t.set(k, "item"))
        self.alerts.delete(*self.alerts.get_children())
        for w in self.watch:
            lf = w.get("last_found") or {}
            if lf and "where" in lf:        # saved by versions before 2610.5: "shop · map"
                parts = lf["where"].split(" · ")
                lf = {"each": lf.get("each"), "shop": parts[0] if parts else "",
                      "map": parts[1] if len(parts) > 1 else "", "channel": None, "time": lf.get("when")}
            self.alerts.insert("", "end", image=self.icon_for(w["item"], found=bool(lf)), values=(
                w["item"], mfm.fmt(w["max_each"]) if w.get("max_each") not in (None, "") else "any",
                mfm.fmt(lf["each"]) if lf else "not seen yet",
                *((lf.get("shop") or "", lf.get("player") or "") if "player" in lf
                  else split_shop(lf.get("shop") or "")),
                (lf.get("map") if ": " in (lf.get("map") or "") else mfm.snap_map(lf.get("map") or "")),
                lf.get("channel") or "",
                mfm.local_time(lf["time"]) if lf.get("time") else ""))
        restore()
        snd = self.cfg.get("alert_sound")
        self.sound_lbl.config(text=f"Sound: {Path(snd).name if snd else 'default ping'}")

    def add_alert(self, item, max_each=None):
        item = item.strip()
        if not item:
            return
        self.watch = [w for w in self.watch if w["item"] != item]
        self.watch.append({"item": item, "max_each": max_each, "last_found": None})
        mfm.save_watchlist(self.watch)
        self.refresh_alerts()
        self.refresh_tables()
        self._set_status(f"Alert added: {item}" + (f" at {mfm.fmt(max_each)} or less" if max_each else ""))

    def add_alert_from_form(self):
        raw = self.alert_max.get().strip()
        try:
            max_each = mfm.parse_price(raw) if raw else None
        except Exception:
            max_each = None
        name = self.alert_item.get()
        if mfm.has_item_list() and not mfm.is_known_item(name):
            sugg = mfm.suggest_items(name, 1)
            if sugg and messagebox.askyesno("Item name", f"'{name}' isn't in the item database.\n\n"
                                            f"Use '{sugg[0]}' instead?"):
                name = sugg[0]
        self.add_alert(name, max_each)
        self.alert_entry.set("")
        self.alert_max.set("")

    def _list_menu(self, tree, entries):
        """Right-click menu for a list of items. entries: (label, fn(tree), single_only)
        or None for a separator; labels get a count when several rows are selected."""
        menu = tk.Menu(tree, tearoff=False)

        def popup(e):
            row = tree.identify_row(e.y)
            if not row:
                return
            if row not in tree.selection():   # right-clicking inside a selection keeps it
                tree.selection_set(row)
                tree.focus(row)
            n = len(tree.selection())
            menu.delete(0, "end")
            for ent in entries:
                if ent is None:
                    menu.add_separator()
                    continue
                label, fn, single = ent
                if single:
                    menu.add_command(label=label, command=lambda fn=fn: fn(tree),
                                     state="normal" if n == 1 else "disabled")
                else:
                    menu.add_command(label=label if n == 1 else f"{label} ({n} items)",
                                     command=lambda fn=fn: fn(tree))
            menu.tk_popup(e.x_root, e.y_root)
        bind_right_click(tree, popup)

    def change_alert_max(self):
        items = [self.alerts.set(k, "item") for k in self.alerts.selection()]
        if not items:
            return
        cur = ""
        if len(items) == 1:
            w = next((w for w in self.watch if w["item"] == items[0]), None)
            cur = mfm.fmt(w["max_each"]) if w and w.get("max_each") not in (None, "") else ""
        raw = ask_value(self.root, "Max price",
                        (f"Alert me when '{items[0]}' is for sale at or below:" if len(items) == 1 else
                         f"Max price for these {len(items)} alerts:")
                        + "\n(e.g. 45000, 45,000 or 45k; empty = any price)", cur,
                        check=lambda t: not t.strip() or (mfm.parse_price(t) or 0) > 0)
        if raw is None:
            return
        cap = mfm.parse_price(raw) if raw.strip() else None
        for w in self.watch:
            if w["item"] in items:
                w["max_each"] = cap
        mfm.save_watchlist(self.watch)
        self.refresh_alerts()
        self.refresh_tables()
        self._set_status(f"Max price {'set to ' + mfm.fmt(cap) if cap else 'removed (any price)'} for "
                         + (f"'{items[0]}'." if len(items) == 1 else f"{len(items)} alerts."))

    def remove_alert(self):
        sel = self.alerts.selection()
        if not sel:
            return
        gone = {self.alerts.set(k, "item") for k in sel}
        self.watch = [w for w in self.watch if w["item"] not in gone]
        mfm.save_watchlist(self.watch)
        self.refresh_alerts()
        self.refresh_tables()

    def alert_from_table(self, tree):
        items = self._selected_items(tree)
        if not items:
            return
        from tkinter import simpledialog
        what = f"'{items[0]}'" if len(items) == 1 else f"any of these {len(items)} items"
        raw = simpledialog.askstring("Alert", f"Alert me when {what} is for sale.\n\n"
                                     "Max price (leave empty for any price"
                                     + (", applies to each" if len(items) > 1 else "") + "):",
                                     parent=self.root)
        if raw is None:
            return
        cap = mfm.parse_price(raw) if raw.strip() else None
        for item in items:
            self.add_alert(item, cap)
        if len(items) > 1:
            self._set_status(f"Alerts added for {len(items)} items"
                             + (f" at {mfm.fmt(cap)} or less each" if cap else "") + ".")

    # ------------------------------------------------------------------ review unmatched
    def _build_review_tab(self):
        tab = ttk.Frame(self.nb, padding=6)
        self.review_tab = tab
        self.nb.add(tab, text="  Review  ")
        ttk.Label(tab, wraplength=1040, justify="left", text=(
            "Item names that don't match anything in the item database (the red ! badge), with the "
            "closest database item. Enter = accept the suggestion · M = match by hand · "
            "K = keep the name as it is (e.g. an item newer than your list) · Delete = delete "
            "its listings (junk reads). Works on several selected rows at once; the next row is "
            "selected after each action.")).pack(anchor="w", pady=(0, 6))
        self.review = make_tree(tab, ("item", "suggest", "score", "count", "time", "raw"))
        self.review.frame.pack(fill="both", expand=True)
        self.review.tag_configure("good", foreground="#145c2c")
        self.review.tag_configure("weak", foreground="#8a6d1a")
        self.review.tag_configure("kept", foreground="#9a9a9a")
        t = self.review
        t.bind("<Return>", lambda e: self.review_accept())
        t.bind("<KP_Enter>", lambda e: self.review_accept())
        t.bind("<Delete>", lambda e: self.review_delete())
        t.bind("<BackSpace>", lambda e: self.review_delete())
        for k in ("m", "M"):
            t.bind(f"<KeyPress-{k}>", lambda e: self.match_dialog(self.review))
        for k in ("k", "K"):
            t.bind(f"<KeyPress-{k}>", lambda e: self.review_keep())
        t.bind("<Double-1>", lambda e: self.open_history(self.review))
        menu = tk.Menu(self.root, tearoff=0)

        def popup(e):
            row = t.identify_row(e.y)
            if not row:
                return
            if row not in t.selection():
                t.selection_set(row)
            n = len(t.selection())
            menu.delete(0, "end")
            menu.add_command(label="Accept suggested match" + (f" ({n})" if n > 1 else "") + "   Enter",
                             command=self.review_accept)
            menu.add_command(label="Match by hand…   M", state="normal" if n == 1 else "disabled",
                             command=lambda: self.match_dialog(t))
            menu.add_command(label="Keep name as is" + (f" ({n})" if n > 1 else "") + "   K",
                             command=self.review_keep)
            menu.add_command(label="Delete listings" + (f" ({n} items)" if n > 1 else "") + "   Del",
                             command=self.review_delete)
            menu.add_separator()
            menu.add_command(label="Show history", state="normal" if n == 1 else "disabled",
                             command=lambda: self.open_history(t))
            menu.add_command(label="Look up on meowdb", state="normal" if n == 1 else "disabled",
                             command=lambda: self.open_meowdb(t))
            menu.tk_popup(e.x_root, e.y_root)
        bind_right_click(t, popup)

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", pady=(6, 0))
        ttk.Button(bottom, text="Accept suggestion", command=self.review_accept).pack(side="left")
        ttk.Button(bottom, text="Match…", command=lambda: self.match_dialog(self.review)).pack(side="left", padx=4)
        ttk.Button(bottom, text="Keep as is", command=self.review_keep).pack(side="left")
        ttk.Button(bottom, text="Delete listings", command=self.review_delete).pack(side="left", padx=4)
        ttk.Button(bottom, text="Accept all 90%+ alike", command=self.review_accept_confident
                   ).pack(side="left", padx=(16, 0))
        self.review_remember = tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom, text="Remember matches for future reads", variable=self.review_remember
                        ).pack(side="left", padx=(16, 0))
        self.review_show_kept = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Show kept names", variable=self.review_show_kept,
                        command=self.refresh_review).pack(side="right")
        self.refresh_review()

    def refresh_review(self):
        if not hasattr(self, "review"):
            return
        t = self.review
        if getattr(t, "dragging", False):
            return
        restore = self._keep_selection(t, lambda tr, k: tr.set(k, "item"))
        rows = mfm.unmatched_items(self.con, include_kept=self.review_show_kept.get())
        t.delete(*t.get_children())
        self.review_rows = {}
        for r in rows:
            tag = "kept" if r["kept"] else "good" if r["score"] >= 0.9 else "weak" if r["suggest"] else ""
            iid = t.insert("", "end", image=self.icon_for(r["item"]), tags=(tag,), values=(
                r["item"], (r["suggest"] or "— no close match —") + ("   (kept as is)" if r["kept"] else ""),
                f"{r['score']:.0%}" if r["suggest"] else "", r["count"],
                mfm.local_time(r["last"]), r["raw"]))
            self.review_rows[iid] = r
        restore()
        n = sum(1 for r in rows if not r["kept"])
        self.nb.tab(self.review_tab, text=f"  Review ({n})  " if n else "  Review  ")

    def _review_selected(self):
        t = self.review
        sel = list(t.selection())
        kids = list(t.get_children())
        after = kids.index(sel[-1]) + 1 if sel else 0
        nxt = next((k for k in kids[after:] if k not in sel), None) or \
            next((k for k in reversed(kids[:kids.index(sel[0])]) if k not in sel), None) if sel else None
        nxt_item = t.set(nxt, "item") if nxt else None
        return [self.review_rows[k] for k in sel if k in self.review_rows], nxt_item

    def _review_select(self, item):
        """After acting on a row, move on to the next one."""
        t = self.review
        for k in t.get_children():
            if t.set(k, "item") == item:
                t.selection_set(k)
                t.focus(k)
                t.see(k)
                break
        t.focus_set()

    def _apply_match(self, old, pick, remember) -> int:
        n = mfm.rename_item(self.con, old, pick)
        if remember:
            mfm.add_alias(old, pick, mfm.load_icon(self.con, pick) if old.endswith("…") else None)
        self._forget_icon(old)
        self._forget_icon(pick)
        for k in self.live.get_children():
            if self.live.set(k, "item") == old:
                self.live.set(k, "item", pick)
                self.live.item(k, image=self.icon_for(pick))
        return n

    def review_accept(self, rows=None):
        rows, nxt = (rows, None) if rows is not None else self._review_selected()
        done = [(r["item"], r["suggest"]) for r in rows if r["suggest"]]
        if not done:
            self._set_status("No suggestion to accept; use Match… (M) to pick one by hand.")
            return
        n = sum(self._apply_match(old, pick, self.review_remember.get()) for old, pick in done)
        self.refresh_tables()
        self.fetch_icons_async([p for _, p in done])
        self._set_status(f"Matched {len(done)} name{'s' if len(done) != 1 else ''} ({n} listings)"
                         + (": " + ", ".join(f"{o} → {p}" for o, p in done[:3]) if len(done) <= 3 else "."))
        if nxt:
            self._review_select(nxt)

    def review_accept_confident(self):
        rows = [r for r in self.review_rows.values() if r["suggest"] and r["score"] >= 0.9 and not r["kept"]]
        if not rows:
            self._set_status("No suggestions are 90% alike or better.")
            return
        listing = "\n".join(f"{r['item']}  →  {r['suggest']}" for r in rows[:15]) + \
            (f"\n… and {len(rows) - 15} more" if len(rows) > 15 else "")
        if messagebox.askyesno("Accept matches", f"Match these {len(rows)} names?\n\n{listing}"):
            self.review_accept(rows)

    def review_keep(self):
        rows, nxt = self._review_selected()
        if not rows:
            return
        kept = set(mfm.load_kept())
        unkeep = all(r["kept"] for r in rows)
        for r in rows:
            (kept.discard if unkeep else kept.add)(r["item"])
            self._forget_icon(r["item"])
        mfm.save_kept(kept)
        self.refresh_tables()
        what = f"'{rows[0]['item']}'" if len(rows) == 1 else f"{len(rows)} names"
        self._set_status(f"{what} {'back in review' if unkeep else 'kept as is (no ! badge)'}.")
        if nxt:
            self._review_select(nxt)

    def review_delete(self):
        rows, nxt = self._review_selected()
        if not rows:
            return
        n_list = sum(r["count"] for r in rows)
        names = "\n".join(r["item"] for r in rows[:12]) + (f"\n… and {len(rows) - 12} more" if len(rows) > 12 else "")
        if not messagebox.askyesno("Delete listings", f"Delete all {n_list} listings of\n\n{names}?"):
            return
        for r in rows:
            mfm.forget_item(self.con, r["item"])
            self._forget_icon(r["item"])
        self.refresh_tables()
        self._set_status(f"Deleted {n_list} listings of {len(rows)} name{'s' if len(rows) != 1 else ''}.")
        if nxt:
            self._review_select(nxt)

    # ------------------------------------------------------------------ ignore list
    def _build_ignore_tab(self):
        tab = ttk.Frame(self.nb, padding=6)
        self.nb.add(tab, text="  Ignored  ")
        ttk.Label(tab, text="Items here never count as deals: no bell, no green highlight, and they're "
                            "hidden from the Deals tab (tick \"Show ignored\" there to see them). They're "
                            "still logged, and an alert you've set on one still fires."
                  , wraplength=1000, justify="left").pack(anchor="w", pady=(0, 6))
        add = ttk.Frame(tab)
        add.pack(fill="x")
        ttk.Label(add, text="Item:").pack(side="left")
        box = ItemSearch(add, self, width=42, on_return=self.add_ignore_from_form)
        self.ignore_box = box
        self.ignore_item = box.var
        box.pack(side="left", padx=4)
        ttk.Button(add, text="Ignore", command=self.add_ignore_from_form).pack(side="left", padx=4)
        self.ignore_tree = make_tree(tab, ("item",))
        self.ignore_tree.frame.pack(fill="both", expand=True, pady=6)
        self.ignore_tree.bind("<Double-1>", lambda e: self.open_history(self.ignore_tree))
        self._list_menu(self.ignore_tree, [
            ("Show history", self.open_history, True),
            None,
            ("Remove item", lambda t: self.unignore_selected(), False)])
        self.ignore_tree.bind("<Delete>", lambda e: self.unignore_selected())
        self.ignore_tree.bind("<BackSpace>", lambda e: self.unignore_selected())
        bottom = ttk.Frame(tab)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Stop ignoring selected", command=self.unignore_selected).pack(side="left")
        self.refresh_ignored()

    def refresh_ignored(self):
        if not hasattr(self, "ignore_tree"):
            return
        t = self.ignore_tree
        restore = self._keep_selection(t, lambda tr, k: tr.set(k, "item"))
        t.delete(*t.get_children())
        for item in sorted(self.ignored, key=str.lower):
            t.insert("", "end", image=self.icon_for(item), values=(item,))
        restore()

    def set_ignored(self, items, on: bool):
        items = [i for i in items if i]
        if on:
            self.ignored.update(items)
        else:
            self.ignored.difference_update(items)
        mfm.save_ignorelist(self.ignored)
        for k in self.live.get_children():   # re-tag the current shop's rows
            if self.live.set(k, "item") in items:
                tags = [t for t in self.live.item(k, "tags") if t not in ("ignored", "deal", "high", "unknown")]
                if on and "sold" not in tags:
                    tags.append("ignored")
                elif not on:
                    tags.append(tag_for(self.live.set(k, "verdict")))
                self.live.item(k, tags=tags)
        self.refresh_tables()
        what = f"'{items[0]}'" if len(items) == 1 else f"{len(items)} items"
        self._set_status(f"{'Ignoring deals on' if on else 'No longer ignoring'} {what}.")

    def add_ignore_from_form(self):
        name = self.ignore_item.get().strip()
        if not name:
            return
        if mfm.has_item_list() and not mfm.is_known_item(name):
            sugg = mfm.suggest_items(name, 1)
            if sugg and messagebox.askyesno("Item name", f"'{name}' isn't in the item database.\n\n"
                                            f"Use '{sugg[0]}' instead?"):
                name = sugg[0]
        self.set_ignored([name], True)
        self.ignore_box.set("")

    def unignore_selected(self):
        items = self._selected_items(self.ignore_tree)
        if items:
            self.set_ignored(items, False)

    def _save_sound_prefs(self):
        self.cfg["alert_sound_on"] = self.sound_on.get()
        self.cfg["alert_raise"] = self.raise_on.get()
        mfm.save_config(self.cfg)

    def test_sound(self):
        if not mfm.play_sound(self.cfg.get("alert_sound") or None):
            self.root.bell()
            self._set_status("No audio player found (pw-play / paplay / aplay); used the system bell.")

    def choose_sound(self):
        path = filedialog.askopenfilename(title="Alert sound (.wav)",
                                          filetypes=[("WAV audio", "*.wav"), ("All files", "*")])
        if path:
            self.cfg["alert_sound"] = path
        elif self.cfg.get("alert_sound") and messagebox.askyesno("Alert sound", "Go back to the default ping?"):
            self.cfg["alert_sound"] = None
        mfm.save_config(self.cfg)
        self.refresh_alerts()

    def _selected_items(self, tree) -> list[str]:
        """Distinct item names of the selected rows, in table order."""
        return list(dict.fromkeys(tree.set(k, "item") for k in tree.selection()))

    def _add_menu(self, tree):
        """Right-click menu for any item table; acts on every selected row."""
        menu = tk.Menu(self.root, tearoff=0)

        def build():
            menu.delete(0, "end")
            rows, items = tree.selection(), self._selected_items(tree)
            one = len(rows) == 1
            n_items = "this item" if len(items) == 1 else f"{len(items)} items"
            single = "normal" if one else "disabled"
            menu.add_command(label="Match to database item…", state=single,
                             command=lambda: self.match_dialog(tree))
            menu.add_command(label="Show history", state=single, command=lambda: self.open_history(tree))
            menu.add_command(label="Look up on meowdb", state=single, command=lambda: self.open_meowdb(tree))
            menu.add_separator()
            menu.add_command(label=f"Alert me when {n_items} {'is' if len(items) == 1 else 'are'} listed…",
                             command=lambda: self.alert_from_table(tree))
            if all(i in self.ignored for i in items):
                menu.add_command(label=f"Stop ignoring {n_items}",
                                 command=lambda: self.set_ignored(items, False))
            else:
                menu.add_command(label=f"Ignore deals on {n_items}",
                                 command=lambda: self.set_ignored(items, True))
            menu.add_separator()
            if tree is self.items:
                menu.add_command(label=f"Delete all listings of {n_items}", command=self.forget_selected)
            else:
                menu.add_command(label="Delete this listing (bad read)" if one
                                 else f"Delete {len(rows)} listings (bad reads)",
                                 command=lambda: self.delete_listing(tree))
            menu.add_separator()
            menu.add_command(label="Select all  (Ctrl+A)",
                             command=lambda: tree.selection_set(tree.get_children("")))

        def popup(e):
            row = tree.identify_row(e.y)
            if row:
                if row not in tree.selection():   # right-clicking inside a selection keeps it
                    tree.selection_set(row)
                build()
                menu.tk_popup(e.x_root, e.y_root)
        bind_right_click(tree, popup)

    def match_dialog(self, tree):
        """Pick the right meowdb item for a misread name. Renames its listings and
        remembers the match so future reads of the same text are corrected."""
        sel = tree.selection()
        if not sel:
            return
        old = tree.set(sel[0], "item")
        if not mfm.has_item_list():
            messagebox.showinfo("No item list", "Download the item list first "
                                "(Settings → Game data → Update).")
            return
        win = tk.Toplevel(self.root)
        win.title("Match to database item")
        win.transient(self.root)
        win.geometry("540x520")
        ttk.Label(win, text="Read as:", padding=(12, 10, 12, 0)).pack(anchor="w")
        ttk.Label(win, text="  " + old, image=self.icon_for(old, 48), compound="left",
                  style="Big.TLabel", padding=(12, 2)).pack(anchor="w")
        ttk.Label(win, text="Search database items (type to filter):", padding=(12, 8, 12, 2)).pack(anchor="w")
        q = tk.StringVar(value=old.rstrip("…").rstrip(": "))
        entry = ttk.Entry(win, textvariable=q)
        entry.pack(fill="x", padx=12)
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12, pady=6)
        results = IconList(frame, self, height=8, width=470)
        lb = results.tree
        sb = ttk.Scrollbar(frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        scope = self.scopes.get((str(tree), sel[0]))
        # a real item name that was wrong once (cursor, smudge) should only fix this
        # listing and not be remembered, or every genuine "Topaz" would be renamed too
        one_off = bool(scope) and mfm.is_known_item(old)
        only_this = tk.BooleanVar(value=one_off)
        if scope:
            where = scope.get("label") or " ".join(x for x in (scope.get("shop"), f"({scope.get('seller')})"
                                                              if scope.get("seller") else "") if x)
            ttk.Checkbutton(win, text=f"Only this listing ({mfm.fmt(scope['price'])} at {where or 'this shop'}),"
                                      " not every listing of this item", variable=only_this
                            ).pack(anchor="w", padx=12)
        remember = tk.BooleanVar(value=not one_off)
        ttk.Checkbutton(win, text="Remember: always read this text as the chosen item",
                        variable=remember).pack(anchor="w", padx=12)

        def refill(*_):
            results.set_names(mfm.suggest_items(q.get() or old))
        q.trace_add("write", refill)
        refill()

        def apply(*_):
            pick = results.selected()
            if not pick:
                return
            n = mfm.rename_item(self.con, old, pick, scope if only_this.get() else None)
            if remember.get():
                mfm.add_alias(old, pick, mfm.load_icon(self.con, pick) if old.endswith("…") else None)
            for k in list(self.icons):
                if k.startswith(old + "@") or k.startswith(pick + "@"):
                    self.icons.pop(k, None)
            for t in (self.live,):
                for k in t.get_children():
                    if t.set(k, "item") == old and (not only_this.get() or t is not tree or k == sel[0]):
                        t.set(k, "item", pick)
                        t.item(k, image=self.icon_for(pick))
            self.refresh_tables()
            self.fetch_icons_async([pick])   # its official icon, if not downloaded yet
            self._set_status(f"Matched '{old}' to '{pick}' ({n} listings)"
                             + ("; future reads will match automatically." if remember.get() else "."))
            win.destroy()
        lb.bind("<Double-1>", apply)
        lb.bind("<Return>", apply)
        entry.bind("<Return>", apply)

        def move(d):
            kids = lb.get_children()
            if not kids:
                return "break"
            cur = lb.selection()[0] if lb.selection() else kids[0]
            i = max(0, min(len(kids) - 1, kids.index(cur) + d))
            lb.selection_set(kids[i])
            lb.see(kids[i])
            return "break"
        entry.bind("<Down>", lambda e: move(1))
        entry.bind("<Up>", lambda e: move(-1))
        btns = ttk.Frame(win, padding=(12, 4, 12, 12))
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Match", command=apply).pack(side="right", padx=6)
        entry.focus_set()
        entry.select_range(0, "end")

    def delete_listing(self, tree):
        """Remove the selected shops' listings (bad reads) without touching other
        listings of the same items."""
        rows = [(k, tree.set(k, "item"), self.scopes.get((str(tree), k))) for k in tree.selection()]
        rows = [r for r in rows if r[2]]
        if not rows:
            return
        if len(rows) == 1:
            k, item, scope = rows[0]
            q = f"Delete this listing of '{item}' ({mfm.fmt(scope['price'])})?"
        else:
            names = sorted({r[1] for r in rows})
            q = (f"Delete these {len(rows)} listings?\n\n" + "\n".join(names[:12])
                 + (f"\n… and {len(names) - 12} more" if len(names) > 12 else ""))
        if not messagebox.askyesno("Delete listings", q + "\n\nOther listings of the same items are kept."):
            return
        n = 0
        for k, item, scope in rows:
            n += mfm.forget_item(self.con, item, scope)
            if tree is self.live:
                tree.delete(k)
            self._forget_icon(item)
        self.refresh_tables()
        self._set_status(f"Deleted {n} listing{'s' if n != 1 else ''}"
                         + (f" of '{rows[0][1]}'." if len(rows) == 1 else "."))

    def open_meowdb(self, tree):
        import webbrowser

        sel = tree.selection()
        if sel:
            webbrowser.open(mfm.meowdb_url(tree.set(sel[0], "item")))

    def import_item_list(self, parent=None):
        return self._import_game_data("items", parent)

    GAME_DATA = {
        "items": ("item list", "mfm item list", mfm.import_items, mfm.export_items),
        "maps": ("map list", "mfm map list", mfm.import_maps, mfm.export_maps),
    }

    def _import_game_data(self, kind, parent=None):
        what, _, do_import, _ = self.GAME_DATA[kind]
        path = filedialog.askopenfilename(
            parent=parent, title=f"Import {what}",
            filetypes=[(what.capitalize() + " files",
                        "*.zip *.json *.csv *.txt" if kind == "items" else "*.json *.csv *.txt"),
                       ("All files", "*")])
        if not path:
            return None
        try:
            n = do_import(path)
        except Exception as e:
            self.report_error(f"Importing the {what} failed", f"{path}\n\n{e}")
            return None
        if kind == "items":
            mfm._Dictionary.cache = None
            self.on_icons_ready(None)
        self._set_status(f"Imported a {what} of {n:,} {'names' if kind == 'items' else 'maps'} "
                         f"from {Path(path).name}.")
        return n

    def _export_game_data(self, kind, parent=None):
        what, default, _, do_export = self.GAME_DATA[kind]
        types = [("JSON: the whole list, can be imported again", "*.json"),
                 ("CSV: the whole list, opens in a spreadsheet", "*.csv"),
                 ("Text: names only", "*.txt")]
        if kind == "items":
            types.insert(0, ("ZIP: the whole list plus every item icon", "*.zip"))
        ext = types[0][1][1:]
        path = filedialog.asksaveasfilename(
            parent=parent, title=f"Export {what}", initialfile=default + ext,
            defaultextension=ext, filetypes=types)
        if not path:
            return
        try:
            n = do_export(path)
        except Exception as e:
            self.report_error(f"Exporting the {what} failed", f"{path}\n\n{e}")
            return
        self._set_status(f"Exported the {what} ({n:,}) to {path}")

    def _game_data_frame(self, parent):
        """Settings section for the reference lists the app reads the game with."""
        box = ttk.LabelFrame(parent, text=" Game data ", padding=(10, 6))
        wrap = 850
        grey = {"foreground": "#666", "wraplength": wrap, "justify": "left"}

        def status_items():
            i = mfm.items_info()
            if not i["names"]:
                return "Not installed: item names won't be spell-checked. Use Update."
            have, total = mfm.icon_status(self.con)
            return (f"{i['names']:,} item names  ·  {i['source'] or 'imported list'}"
                    + (f"  ·  icons {have:,} / {total:,}" if total else ""))

        def status_maps():
            m = mfm.maps_info()
            return (f"{m['maps']:,} maps  ·  {m['source']}" if m["maps"] else
                    "Not installed: misread map names won't be corrected. Use Update.")

        def status_osms():
            o = mfm.osms_info()
            if not o["items"] and not o["maps"]:
                return "OSMS Data Explorer: not downloaded yet (Update gets it)"
            return (f"OSMS Data Explorer  ·  adds {mfm.plural(o['extra_items'], 'item')} and "
                    f"{mfm.plural(o['extra_maps'], 'map')} meowdb doesn't have"
                    + (f"  ·  checked {o['checked']}" if o["checked"] else ""))

        rows = {}

        def refresh():
            for key, fn in (("items", status_items), ("maps", status_maps), ("osms", status_osms)):
                try:
                    rows[key].config(text=fn())
                except tk.TclError:
                    pass       # window closed

        top = ttk.Frame(box)
        top.pack(fill="x")
        b = ttk.Button(top, text="Update",
                       command=lambda: self.download_meowdb(rows["items"], force=True, then=refresh))
        b.pack(side="left")
        tip("Gets new items and map changes from NiaMeowDB (meowdb.com), and the backup lists from "
            "OSMS Data Explorer. Quick: only what changed is downloaded.", b)
        b = ttk.Button(top, text="Full refresh",
                       command=lambda: self.download_meowdb(rows["items"], full=True, force=True, then=refresh))
        b.pack(side="left", padx=6)
        tip("Downloads the whole item and map lists again. Only needed if something looks out "
            "of date or wrong.", b)
        ttk.Label(top, foreground="#666", wraplength=wrap - 300, justify="left", text=(
            "Both lists come from NiaMeowDB, with OSMS Data Explorer as a backup. Update only asks "
            "for what's new; Full refresh downloads everything again.")).pack(side="left", padx=(10, 0))
        search_icons = tk.BooleanVar(value=self.cfg.get("search_icons", True))

        def toggle_search_icons():
            self.cfg["search_icons"] = search_icons.get()
            mfm.save_config(self.cfg)
        all_icons = tk.BooleanVar(value=self.cfg.get("download_all_icons", True))

        def toggle_icons():
            self.cfg["download_all_icons"] = all_icons.get()
            mfm.save_config(self.cfg)
        cb = ttk.Checkbutton(box, variable=all_icons, command=toggle_icons, text=(
            "Update also downloads every item icon (the first time takes about 10 minutes in the "
            "background, then only new items' icons)"))
        cb.pack(anchor="w", pady=(2, 0))
        tip("With this off, icons are only downloaded for items you actually come across.", cb)
        sections = [
            ("items", "Item list", status_items,
             "Corrects the OCR's spelling of item names, lists the items you can pick in "
             "Alerts, Ignored, Match and the Review tab, links each item to its NiaMeowDB page, shows icons, "
             "and gives each item's category.",
             "Files: cache/items.txt (names), meowdb_items.json (database copy: id, name, "
             "category, icon), item_ids.json, item_types.json, item_icons.json; "
             "icons in cache/icons.db"),
            ("maps", "Map list", status_maps,
             "Corrects misread map names from the minimap, e.g. 'Free Marker <8>' → "
             "'Free Market <8>'.",
             "File: cache/maps.json (id, name, street)"),
        ]
        for i, (kind, title, fn, purpose, files) in enumerate(sections):
            f = ttk.Frame(box)
            f.pack(fill="x", pady=(10, 0))
            top = ttk.Frame(f)
            top.pack(fill="x")
            ttk.Label(top, text=title, style="Bold.TLabel").pack(side="left")
            rows[kind] = ttk.Label(top, text=fn(), foreground="#1f6f3a")
            rows[kind].pack(side="left", padx=(10, 0))
            b = ttk.Frame(top)
            b.pack(side="right")
            ttk.Label(f, text=purpose, wraplength=wrap, justify="left").pack(anchor="w", pady=(2, 0))
            ttk.Label(f, text=files, **grey).pack(anchor="w")
            if kind == "items":
                cb = ttk.Checkbutton(f, text="Show icons in item search", variable=search_icons,
                                     command=toggle_search_icons)
                cb.pack(anchor="w", pady=(2, 0))
                tip("Shows each item's picture next to its name when you search for items in "
                    "Alerts, Ignored and Match.", cb)

            def imp(kind=kind):
                if self._import_game_data(kind, parent):
                    refresh()
            bi = ttk.Button(b, text="Import…", command=imp)
            bi.pack(side="left")
            be = ttk.Button(b, text="Export…", command=lambda kind=kind: self._export_game_data(kind, parent))
            be.pack(side="left", padx=(6, 0))
            noun = "item list" if kind == "items" else "map list"
            tip(f"Replaces the {noun} with one from a file, e.g. an export from another PC.", bi)
            tip(f"Saves the {noun} to a file"
                + (" (choose .zip to include every icon)" if kind == "items" else "")
                + ", to back it up or copy it to another PC.", be)
        bk = ttk.Frame(box)
        bk.pack(fill="x", pady=(10, 0))
        bk_title = ttk.Label(bk, text="Backup source", style="Bold.TLabel")
        bk_title.pack(side="left")
        rows["osms"] = ttk.Label(bk, text=status_osms(), foreground="#1f6f3a")
        rows["osms"].pack(side="left", padx=(10, 0))
        tip("OSMS Data Explorer (osmsdataexplorer.com) is used only where NiaMeowDB has nothing: "
            "items and maps missing from its lists, and icons it can't supply. Updated with the "
            "Update button (checked weekly). Files: cache/osms_items.json, cache/osms_maps.json; "
            "included in an item .zip export.", bk_title, rows["osms"])
        ttk.Label(box, **grey, text=(
            "Export: .json/.csv restores all the files above exactly (here or on another PC), "
            "an item .zip adds every icon, .txt is names only.")).pack(anchor="w", pady=(10, 0))
        return box

    def offer_item_list(self):
        if messagebox.askyesno(
                "Item names",
                "Download the MapleStory Classic item list from NiaMeowDB (meowdb.com)?\n\n"
                "It's used to fix OCR misspellings ('Reppae Hat' -> 'Reggae Hat') and to show "
                "official item icons. About 11 small requests. You can do this later from "
                "Settings."):
            self.download_meowdb()

    def offer_type_refresh(self):
        if messagebox.askyesno(
                "Update item list",
                "Re-download the item and map lists from NiaMeowDB (meowdb.com)? This version also "
                "saves each item's category, required level and class (for the Items tab's filters) "
                "and the map list, which is used to correct misread map names like "
                "'Free Marker <8>'."):
            self.download_meowdb()

    def download_meowdb(self, label=None, full=False, force=False, then=None):
        """Fetch the item list in the background so the window stays responsive."""
        def say(text):
            self.events.put(("status", text))
            if label is not None:
                self.events.put(("label", (label, text)))

        def work():
            meow_error, meow_msg = None, ""
            try:
                r = mfm.update_items_meowdb(lambda k: say(f"Updating items from meowdb… {k:,}"),
                                            full=full, force=force)
                meow_msg = r.message + (" Map list updated." if r.maps_updated else "")
                say(meow_msg)
            except Exception as e:
                meow_error = e
            try:      # the backup source, also (especially) when meowdb failed
                say("Checking the backup source (OSMS Data Explorer)…")
                osms_msg = mfm.update_osms(force=force or full or meow_error is not None)
            except Exception as e:
                osms_msg = f"Backup source not updated: {e}"
            if meow_error is None:
                say(meow_msg + "   " + osms_msg)
            if then:
                self.events.put(("call", then))
            if meow_error is not None:
                say(f"meowdb download failed: {meow_error}   {osms_msg}")
                self.events.put(("download_error", str(meow_error) + (
                    "\n\nThe backup source (OSMS Data Explorer) was updated, so items and maps "
                    "meowdb is missing are still covered." if not osms_msg.startswith("Backup source not") else "")))
                return
            try:
                if self.cfg.get("download_all_icons", True):
                    self.download_all_icons(label, then)
                con = mfm.db()
                seen = [r[0] for r in con.execute("SELECT DISTINCT item FROM listings")]
                if seen and mfm.fetch_official_icons(con, seen):
                    self.events.put(("icons_ready", seen))
            except Exception as e:
                say(f"meowdb download failed: {e}")
                self.events.put(("download_error", str(e)))
        say("Checking meowdb for updates…")
        threading.Thread(target=work, daemon=True).start()

    def download_all_icons(self, label=None, then=None):
        """Every meowdb icon not downloaded yet, ~2 per second, in the background.
        Resumes where it stopped (closing the app stops it)."""
        if getattr(self, "_icons_busy", False):
            return
        self._icons_busy = True
        self._icons_stop = threading.Event()

        def say(text):
            self.events.put(("status", text))
            if label is not None:
                self.events.put(("label", (label, text)))

        def work():
            con = mfm.db()
            try:
                have, total = mfm.icon_status(con)
                if have >= total:
                    return

                full_rate = float(self.cfg.get("icon_rate", 10))

                def progress(i, n, rate):
                    if i % 20 == 0 or i == n:
                        left = (n - i) / max(rate, 0.1) / 60
                        say(f"Downloading item icons from meowdb… {have + i:,} / {total:,}"
                            + (f", about {left:.0f} min left" if left >= 1 else "")
                            + (f" (meowdb asked to slow down: {rate:.1f}/s)" if rate < full_rate * 0.95 else ""))
                    if i % 500 == 0:
                        self.events.put(("icons_ready", None))
                got, bad = mfm.download_all_icons(con, progress, self._icons_stop, rate=full_rate)
                if not self._icons_stop.is_set():
                    say(f"Item icons: downloaded {got:,}" + (f" ({bad} unavailable)" if bad else "")
                        + f"; {mfm.icon_status(con)[0]:,} of {total:,} here.")
            except Exception as e:
                say(f"Icon download stopped: {e}")
            finally:
                self._icons_busy = False
                self.events.put(("icons_ready", None))
                if then:
                    self.events.put(("call", then))
                con.close()
        threading.Thread(target=work, daemon=True).start()

    def on_download_error(self, msg):
        self.report_error("meowdb download failed", msg)

    def on_call(self, fn):
        fn()

    def on_status(self, text):
        self._set_status(text)

    def on_label(self, p):
        lbl, text = p
        try:
            lbl.config(text=text)
        except tk.TclError:
            pass  # settings window was closed

    def on_icons_ready(self, items):
        if items is None:           # many new icons: drop every cached thumbnail
            # (keep the old images alive: open windows may still be showing them)
            self._retired_icons = getattr(self, "_retired_icons", []) + list(self.icons.values())
            self.icons.clear()
        for item in items or ():
            self._forget_icon(item)
        self.icon_lists = [l for l in self.icon_lists if l.alive()]
        for l in self.icon_lists:
            l.refresh_images()
        for k in self.live.get_children():
            self.live.item(k, image=self.icon_for(self.live.set(k, "item")))
        self.refresh_tables()

    def request_icons(self, names):
        """Download meowdb icons for search suggestions that have none yet: one at a
        time, at most 2 per second, each item only once (and never again after)."""
        if not self.cfg.get("search_icons", True) or not mfm.ITEM_ICONS_PATH.exists():
            return
        for n in names:
            if n in self._icon_asked:
                continue
            self._icon_asked.add(n)
            if mfm.load_icon(self.con, n) is None:
                self._icon_queue.put(n)
        if self._icon_worker is None or not self._icon_worker.is_alive():
            def work():
                con = mfm.db()
                while True:
                    try:
                        n = self._icon_queue.get(timeout=5)
                    except queue.Empty:
                        return
                    try:
                        if mfm.fetch_official_icons(con, [n], delay=0.5):
                            self.events.put(("search_icon", n))
                    except Exception:
                        pass
            self._icon_worker = threading.Thread(target=work, daemon=True)
            self._icon_worker.start()

    def on_search_icon(self, item):
        self._forget_icon(item)
        self.icon_lists = [l for l in self.icon_lists if l.alive()]
        for l in self.icon_lists:
            l.refresh_images()

    def fetch_icons_async(self, items):
        if not mfm.ITEM_ICONS_PATH.exists() or not items:
            return

        def work():
            if mfm.fetch_official_icons(mfm.db(), items):
                self.events.put(("icons_ready", items))
        threading.Thread(target=work, daemon=True).start()

    def icon_for(self, item: str, size: int = 30, found: bool = False):
        """Thumbnail for a table row (cached). Items that don't match anything in the
        meowdb list get a small red "!" badge; watched items found for sale get a
        green outline; '' when there's nothing to show."""
        warn = mfm.needs_review(item)
        key = f"{item}@{size}{'!' if warn else ''}{'g' if found else ''}"
        if key not in self.icons:
            img = mfm.load_icon(self.con, item)
            if img is None and not warn and not found:
                return ""
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            if img is not None:
                img = img.convert("RGBA")
                img.thumbnail((size, size), Image.LANCZOS)
                canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
            if warn:
                self._draw_warning(canvas)
            if found:
                from PIL import ImageDraw
                d = ImageDraw.Draw(canvas)
                for i in range(2):   # 2 px green frame
                    d.rectangle((i, i, size - 1 - i, size - 1 - i), outline=(30, 190, 70, 255))
            photo = ImageTk.PhotoImage(canvas)
            if img is None:
                # No thumbnail saved yet (e.g. the alert fired before the icon was stored):
                # don't cache the empty frame, so the real icon shows on the next refresh.
                self._uncached = getattr(self, "_uncached", [])[-50:] + [photo]   # keep a ref for Tk
                return photo
            self.icons[key] = photo
        return self.icons[key]

    def _forget_icon(self, item):
        for k in list(self.icons):
            if k.startswith(item + "@"):
                self.icons.pop(k, None)

    @staticmethod
    def _draw_warning(canvas, r=None):
        """Red circle with a white "!" in the top-right corner."""
        from PIL import ImageDraw

        s = canvas.width
        r = r or max(6, s * 13 // 30)             # badge diameter
        x0, y0 = s - r, 0
        d = ImageDraw.Draw(canvas)
        d.ellipse((x0, y0, x0 + r - 1, y0 + r - 1), fill=(214, 40, 40, 255), outline=(255, 255, 255, 255))
        cx = x0 + r / 2
        bar_w = max(1.0, r / 7)
        d.rectangle((cx - bar_w / 2, y0 + r * 0.2, cx + bar_w / 2, y0 + r * 0.58), fill=(255, 255, 255, 255))
        d.rectangle((cx - bar_w / 2, y0 + r * 0.68, cx + bar_w / 2, y0 + r * 0.8), fill=(255, 255, 255, 255))

    def _legend_badge(self):
        canvas = Image.new("RGBA", (15, 15), (0, 0, 0, 0))
        self._draw_warning(canvas, r=15)
        return canvas

    def forget_selected(self):
        items = self._selected_items(self.items)
        if not items:
            return
        shown = "\n".join(items[:12]) + (f"\n… and {len(items) - 12} more" if len(items) > 12 else "")
        if messagebox.askyesno("Delete items", f"Delete all logged listings of\n\n{shown}?"):
            n = sum(mfm.forget_item(self.con, item) for item in items)
            for item in items:
                self._forget_icon(item)
            self.refresh_tables()
            self._set_status(f"Deleted {n} listings of {len(items)} item{'s' if len(items) != 1 else ''}.")

    # ------------------------------------------------------------------ dialogs
    def calibrate(self, then_start=False, key="region"):
        was_running = bool(self.worker and self.worker.is_alive())
        self.root.withdraw()
        self.root.update()

        def grab():
            try:
                shot = mfm.grab_full_screen()
            except SystemExit as e:  # missing Wayland screenshot tool
                self.root.deiconify()
                messagebox.showerror("Can't capture screen", str(e))
                return

            def done(region):
                self.root.deiconify()
                if region:
                    self.cfg[key] = region  # monitor shares this dict, picks it up next frame
                    self._update_stats(None, None)
                    label = "Map area" if key == "map_region" else "Shop area"
                    self._set_status(f"{label} set to {region}.")
                    if then_start and not was_running:
                        self.start()

            mfm.calibrate(parent=self.root, shot=shot, on_done=done, key=key)

        # give the window manager a moment to hide us so we're not in the screenshot
        self.root.after(600, grab)

    def import_ref(self):
        path = filedialog.askopenfilename(title="Reference prices CSV (item,price)",
                                          filetypes=[("CSV", "*.csv"), ("All files", "*")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                ok = {"item", "price"} <= set(csv.DictReader(f).fieldnames or [])
            if not ok:
                raise ValueError("The CSV needs 'item' and 'price' column headers.")
            mfm.import_ref(path)
            self.refresh_tables()
            self._set_status(f"Imported reference prices from {path}")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def export_prices(self):
        """Save prices as CSV: one row per item (re-importable) or every sighting."""
        win = tk.Toplevel(self.root)
        win.title("Export prices")
        win.transient(self.root)
        win.resizable(False, False)
        kind = tk.StringVar(value="market")
        ttk.Label(win, text="Export as a CSV file (opens in Excel, LibreOffice, Google Sheets):",
                  padding=(14, 12, 14, 6)).pack(anchor="w")
        ttk.Radiobutton(win, variable=kind, value="market", text=(
            "Market prices, one row per item: market price and where it came from, listed and "
            "sold medians, cheapest listing.\nThe first columns are item,price,source, so it can be "
            "imported again with Import prices.")).pack(anchor="w", padx=14, pady=2)
        ttk.Radiobutton(win, variable=kind, value="listings", text=(
            "Every sighting: date, item, price, sold or for sale, shop, player, map, channel."
        )).pack(anchor="w", padx=14, pady=2)

        def go():
            default = f"mfm-{'market-prices' if kind.get() == 'market' else 'sightings'}-" \
                      f"{datetime.now():%Y-%m-%d}.csv"
            path = filedialog.asksaveasfilename(parent=win, title="Export prices", defaultextension=".csv",
                                                initialfile=default, filetypes=[("CSV", "*.csv")])
            if not path:
                return
            try:
                n = mfm.export_prices(self.con, path, self.cfg, kind.get())
            except Exception as e:
                messagebox.showerror("Export failed", str(e), parent=win)
                return
            win.destroy()
            self._set_status(f"Exported {n} rows to {path}")
        btns = ttk.Frame(win, padding=(14, 10, 14, 12))
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Export…", command=go).pack(side="right", padx=6)

    def _confirm_twice(self, parent, title, first, second) -> bool:
        """Deleting anything takes two separate confirmations."""
        if not messagebox.askyesno(title, first, parent=parent, icon="warning", default="no"):
            return False
        return messagebox.askyesno(title, second, parent=parent, icon="warning", default="no")

    def clear_prices(self, parent):
        n = self.con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        r = self.con.execute("SELECT COUNT(*) FROM reference").fetchone()[0]
        if not self._confirm_twice(
                parent, "Clear pricing data",
                f"Delete ALL pricing data?\n\n• {n:,} logged listings (every shop, sold and for sale)\n"
                f"• {r:,} imported reference prices\n\nYour settings, alerts, ignore list, manual matches "
                "and item icons are kept.",
                "Are you sure? This is the second and last confirmation.\n\n"
                f"All {n + r:,} price records will be deleted. A backup copy is saved in the "
                "data folder's 'backups' folder first, but the app itself can't undo this."):
            return
        if self.stop_event and self.worker and self.worker.is_alive():
            self.stop()
        backup = mfm.clear_prices(self.con)
        self.live.delete(*self.live.get_children())
        self.icons.clear()
        self.refresh_tables()
        self._set_status(f"Pricing data cleared. Backup: {backup}")
        messagebox.showinfo("Pricing data cleared", f"Done. A backup was saved to:\n{backup}", parent=parent)

    def reset_personal(self, parent):
        win = tk.Toplevel(parent)
        win.title("Reset personal settings")
        win.transient(parent)
        win.resizable(False, False)
        ttk.Label(win, text="Reset these to how they were when the app was new:",
                  padding=(14, 12, 14, 6)).pack(anchor="w")
        picks = {}
        for key, (label, _) in mfm.SETTINGS_FILES.items():
            picks[key] = tk.BooleanVar(value=True)
            ttk.Checkbutton(win, text=label, variable=picks[key]).pack(anchor="w", padx=14, pady=1)
        ttk.Label(win, foreground="#777", padding=(14, 6, 14, 0), text=(
            "Pricing data and the item database are not affected.")).pack(anchor="w")

        def go():
            parts = [k for k, v in picks.items() if v.get()]
            if not parts:
                return
            names = "\n".join("• " + mfm.SETTINGS_FILES[k][0] for k in parts)
            if not self._confirm_twice(
                    win, "Reset personal settings", f"Reset and delete:\n\n{names}?",
                    "Are you sure? This is the second and last confirmation.\n\nA backup copy is "
                    "saved in the data folder's 'backups' folder first, but the app itself can't "
                    "undo this."):
                return
            backup = mfm.reset_settings(parts)
            self.cfg = mfm.load_config()
            self.watch = mfm.load_watchlist()
            self.ignored = set(mfm.load_ignorelist())
            self.sound_on.set(self.cfg.get("alert_sound_on", True))
            self.raise_on.set(self.cfg.get("alert_raise", True))
            if self.monitor:
                self.monitor.cfg = self.cfg
            self.found_at = None
            self.icons.clear()
            self._update_stats(None, None)
            self.refresh_tables()
            win.destroy()
            if isinstance(parent, tk.Toplevel):
                try:
                    parent.destroy()   # the open Settings window shows the old values
                except tk.TclError:
                    pass
            self._set_status(f"Personal settings reset. Backup: {backup}")
            messagebox.showinfo("Settings reset", f"Done. A backup was saved to:\n{backup}")
        btns = ttk.Frame(win, padding=(14, 10, 14, 12))
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Reset…", command=go).pack(side="right", padx=6)

    def settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.transient(self.root)
        win.resizable(False, False)
        fields = [
            ("deal_threshold_pct", "Flag DEAL / HIGH at ± %", 1, 90, 1),
            ("interval_seconds", "Capture every (seconds)", 0.25, 10, 0.25),
            ("confirm_frames", "Frames to confirm a row", 1, 5, 1),
            ("unmatched_extra_frames", "Extra reads for names not in database", 0, 5, 1),
            ("close_frames", "Empty frames = shop closed", 1, 20, 1),
            ("history_days", "Market median window (days)", 1, 90, 1),
            ("upscale", "OCR upscale factor", 1, 6, 1),
            ("outlier_min_n", "Outliers: judge after this many sightings", 3, 100, 1),
            ("outlier_ceiling_pct", "Outliers: ceiling, % above median", 10, 10000, 10),
            ("outlier_floor_pct", "Outliers: floor, % below median", 5, 99, 5),
        ]
        tips = {
            "deal_threshold_pct": "How far below the market price a listing must be to count as a "
                                  "DEAL (and how far above to count as HIGH).",
            "interval_seconds": "How often the screen is read while monitoring. Lower is quicker to "
                                "catch rows; higher uses less CPU.",
            "confirm_frames": "How many identical reads a row needs before it's saved. Higher "
                              "avoids misreads; lower saves rows faster while scrolling.",
            "unmatched_extra_frames": "Names that aren't in the item database are read this many "
                                      "more times before they're saved, to rule out a misread.",
            "close_frames": "How many reads in a row without a shop mean the shop was closed.",
            "history_days": "How many days of your own sightings make up an item's market price.",
            "upscale": "How much the screen text is enlarged before it's read. Raise it if small "
                       "text is misread; higher is slower.",
            "outlier_min_n": "An item needs this many sightings before unusual prices are set aside.",
            "outlier_ceiling_pct": "Prices this far above the item's usual price are ignored for "
                                   "its market price (troll listings, typos).",
            "outlier_floor_pct": "Prices this far below the item's usual price don't change its "
                                 "market price (they still show as deals).",
        }
        vars_ = {}
        for i, (key, label, lo, hi, step) in enumerate(fields):
            lbl = ttk.Label(win, text=label)
            lbl.grid(row=i, column=0, sticky="w", padx=12, pady=4)
            v = tk.StringVar(value=str(self.cfg.get(key, mfm.DEFAULT_CONFIG[key])))
            spin = ttk.Spinbox(win, from_=lo, to=hi, increment=step, width=8, textvariable=v)
            spin.grid(row=i, column=1, padx=12, pady=4)
            tip(tips[key], lbl, spin)
            vars_[key] = (v, type(mfm.DEFAULT_CONFIG[key]))
        # ---- data retention (top right)
        ret = ttk.LabelFrame(win, text=" Data retention ", padding=(10, 4, 10, 8))
        ret.grid(row=0, column=2, rowspan=7, sticky="nwe", padx=(0, 12), pady=(6, 0))
        r1 = ttk.Frame(ret)
        r1.pack(anchor="w", pady=(0, 4))
        keep_var = tk.StringVar(value=str(self.cfg.get("keep_days", 30)))
        lk = ttk.Label(r1, text="Keep listings for")
        lk.pack(side="left")
        sk = ttk.Spinbox(r1, from_=1, to=3650, increment=1, width=6, textvariable=keep_var)
        sk.pack(side="left", padx=6)
        ttk.Label(r1, text="days").pack(side="left")
        tip("Listings not seen for this many days are archived and/or deleted (see below). "
            "Items you still see in shops keep their listings.", lk, sk)
        mode_var = tk.StringVar(value=self.cfg.get("retention", "archive"))
        rm = ttk.Frame(ret)
        rm.pack(anchor="w", pady=(0, 4))
        ttk.Label(rm, text="Then:").pack(side="left")
        for val, text, t in (
                ("archive", "Archive, then delete",
                 "Copies old listings into the archive file first, then removes them from your "
                 "price database. Nothing is lost; the archive keeps growing."),
                ("delete", "Delete", "Removes old listings for good."),
                ("keep", "Keep everything", "Never removes anything (the database keeps growing).")):
            rb = ttk.Radiobutton(rm, text=text, value=val, variable=mode_var)
            rb.pack(side="left", padx=(8, 0))
            tip(t, rb)
        r2 = ttk.Frame(ret)
        r2.pack(fill="x")
        ttk.Label(r2, text="Archive to:").pack(side="left", padx=(0, 6))
        arch_var = tk.StringVar(value=str(mfm.archive_dir(self.cfg)))
        ea = ttk.Entry(r2, textvariable=arch_var, width=26)
        ea.pack(side="left", fill="x", expand=True)

        def browse():
            d = filedialog.askdirectory(parent=win, title="Archive folder",
                                        initialdir=arch_var.get() or str(mfm.DATA))
            if d:
                arch_var.set(d)
        bb = ttk.Button(r2, text="Browse…", command=browse)
        bb.pack(side="left", padx=(6, 0))
        tip(f"Where {mfm.ARCHIVE_NAME} is kept (one file, added to on every cleanup). "
            "Any folder works, e.g. another drive.", ea, bb)
        r3 = ttk.Frame(ret)
        r3.pack(fill="x", pady=(6, 0))
        size_lbl = ttk.Label(r3, foreground="#666")

        def ret_cfg():
            try:
                days = max(1, int(float(keep_var.get())))
            except ValueError:
                days = 30
            return {"keep_days": days, "retention": mode_var.get(),
                    "archive_dir": arch_var.get().strip() or None}

        def show_size():
            size = mfm.db_size()
            try:
                old = mfm.old_listing_count(self.con, ret_cfg()["keep_days"])
            except Exception:
                old = 0
            size_lbl.config(text=f"Database {size / 1048576:,.1f} MB  ·  {old:,} to clean up",
                            foreground="#c62828" if size > mfm.DB_WARN_BYTES else "#666")

        def clean_now():
            c = ret_cfg()
            if c["retention"] == "keep":
                c["retention"] = "archive"
            n = mfm.old_listing_count(self.con, c["keep_days"])
            if not n:
                messagebox.showinfo("Clean up now", f"No listings are older than {c['keep_days']} days.",
                                    parent=win)
                return
            where = (f"archived to {mfm.archive_dir(c) / mfm.ARCHIVE_NAME} and then deleted"
                     if c["retention"] == "archive" else "deleted for good")
            if messagebox.askyesno("Clean up now", f"{mfm.plural(n, 'listing')} not seen for "
                                   f"{c['keep_days']} days will be {where}.\n\nContinue?", parent=win):
                self.run_retention(cfg=c, done=show_size)
        bc = ttk.Button(r3, text="Clean up now", command=clean_now)
        bc.pack(side="left")
        tip("Archives and/or deletes listings older than the days above right away (uses this "
            "form's choices; with Keep everything selected it archives).", bc)
        size_lbl.pack(side="left", padx=(8, 0))
        keep_var.trace_add("write", lambda *a: show_size())
        show_size()

        save_caps = tk.BooleanVar(value=self.cfg.get("save_captures", False))
        cb = ttk.Checkbutton(win, text="Save every capture as PNG (for debugging OCR)", variable=save_caps)
        cb.grid(row=len(fields), column=0, columnspan=2, sticky="w", padx=12, pady=4)
        tip("Keeps a picture of every screen read in the data folder, to check what the app saw. "
            "Uses disk space; leave off normally.", cb)
        outliers_on = tk.BooleanVar(value=self.cfg.get("outliers_on", True))
        cb = ttk.Checkbutton(win, text="Ignore outliers in market rates",
                             variable=outliers_on)
        cb.grid(row=len(fields) - 3, column=2, sticky="w", padx=(0, 12))
        tip("Leaves out absurd prices when working out an item's market price, once it has enough "
            "sightings.", cb)
        ttk.Label(win, foreground="#777", justify="left", text=(
            "Measured from the item's median price.\n200% ceiling = more than 3x the median;\n"
            "75% floor = less than 1/4 of it.")).grid(row=len(fields) - 2, column=2, rowspan=2,
                                                       sticky="nw", padx=(0, 12))

        def save():
            try:
                for key, (v, typ) in vars_.items():
                    self.cfg[key] = typ(float(v.get())) if typ is int else float(v.get())
            except ValueError:
                messagebox.showerror("Invalid value", "Please enter numbers only.", parent=win)
                return
            c = ret_cfg()
            if c["retention"] != "keep" and c["keep_days"] < int(self.cfg.get("history_days", 14)):
                if not messagebox.askyesno(
                        "Data retention", f"Keeping listings for {c['keep_days']} days is shorter than "
                        f"the market price window ({self.cfg.get('history_days', 14)} days), so market "
                        "prices will use less data.\n\nSave anyway?", parent=win):
                    return
            self.cfg.update(c)
            self.cfg["save_captures"] = save_caps.get()
            self.cfg["outliers_on"] = outliers_on.get()
            mfm.save_config(self.cfg)
            self.refresh_tables()
            win.destroy()

        def reset_auto():
            self.cfg["region"] = self.cfg["map_region"] = None
            mfm.save_config(self.cfg)
            self.found_at = None
            self._update_stats(None, None)
            self._set_status("Shop and map areas will be found automatically.")
        b = ttk.Button(win, text="Auto Detection", command=reset_auto)
        b.grid(row=len(fields) + 1, column=0, sticky="w", padx=12, pady=(8, 0))
        tip("Go back to finding the shop and minimap automatically.", b)
        ttk.Label(win, foreground="#666", wraplength=620, justify="left", text=(
            "Forgets manually captured areas and uses auto detection for Shop and Map areas."
            )).grid(row=len(fields) + 1, column=1, columnspan=2, sticky="w", padx=(0, 12), pady=(8, 0))
        self._game_data_frame(win).grid(row=len(fields) + 2, column=0, columnspan=3, sticky="we",
                                        padx=12, pady=(12, 0))
        bottom = ttk.Frame(win)
        bottom.grid(row=len(fields) + 3, column=0, columnspan=3, sticky="we", padx=12, pady=(12, 12))
        danger = ttk.LabelFrame(bottom, text=" Your data (prices and personal settings) ", padding=(10, 6))
        danger.pack(side="left")
        b1 = ttk.Button(danger, text="Clear pricing data…", command=lambda: self.clear_prices(win))
        b1.pack(side="left")
        b2 = ttk.Button(danger, text="Reset personal settings…", command=lambda: self.reset_personal(win))
        b2.pack(side="left", padx=6)
        b3 = ttk.Button(danger, text="Open data folder", command=self.open_data_folder)
        b3.pack(side="left")
        tip("Deletes every price you've recorded (asks twice, and keeps a backup first).", b1)
        tip("Lets you pick what to clear: settings, alerts, ignore list, manual matches (asks "
            "twice, keeps a backup). Prices are kept.", b2)
        tip("Opens the folder with your prices, settings, backups and downloaded game data.", b3)
        b6 = ttk.Button(bottom, text="About", command=lambda: self.about(win))
        tip("Version and credits: the data sources and open-source software this app is built on.", b6)
        b4 = ttk.Button(bottom, text="Cancel", command=win.destroy)
        b4.pack(side="right", anchor="s")
        b5 = ttk.Button(bottom, text="Save", command=save)
        b5.pack(side="right", anchor="s", padx=6)
        b6.pack(side="right", anchor="s", padx=(0, 12))
        tip("Saves the numbers and checkboxes above. (Game data options take effect right away.)", b5)

    def about(self, parent=None):
        import webbrowser

        win = tk.Toplevel(parent or self.root)
        win.title("About Free Market Tracker")
        win.transient(parent or self.root)
        win.geometry("700x620")
        head = ttk.Frame(win, padding=(16, 14, 16, 4))
        head.pack(fill="x")
        try:
            for p in (mfm.BUNDLE / "icon.png", Path(__file__).resolve().parent / "packaging" / "icon.png"):
                if p.exists():
                    win._logo = ImageTk.PhotoImage(Image.open(p).resize((48, 48)))
                    ttk.Label(head, image=win._logo).pack(side="left", padx=(0, 12))
                    break
        except Exception:
            pass
        info = ttk.Frame(head)
        info.pack(side="left", fill="x")
        ttk.Label(info, text="Free Market Tracker", style="Big.TLabel").pack(anchor="w")
        ttk.Label(info, text=f"Version {mfm.VERSION}", foreground="#555").pack(anchor="w")
        ttk.Label(info, foreground="#555", text="Free Market price tracker for MapleStory Classic World"
                  ).pack(anchor="w")
        btns = ttk.Frame(win, padding=(16, 8, 16, 12))
        btns.pack(side="bottom", fill="x")          # packed first so it always keeps its room
        frame = ttk.Frame(win, padding=(16, 8, 16, 0))
        frame.pack(fill="both", expand=True)
        txt = tk.Text(frame, wrap="word", relief="flat", borderwidth=0, highlightthickness=0,
                      background=win.cget("background"), padx=2, pady=2, cursor="arrow",
                      font="TkDefaultFont", spacing1=1, spacing3=1)
        sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.tag_configure("h", font="MfmBold", spacing1=10, spacing3=4)
        txt.tag_configure("name", font="MfmBold")
        txt.tag_configure("note", foreground="#555")
        txt.tag_configure("link", foreground="#1a5fb4", underline=True)
        txt.tag_bind("link", "<Enter>", lambda e: txt.config(cursor="hand2"))
        txt.tag_bind("link", "<Leave>", lambda e: txt.config(cursor="arrow"))
        for i, (section, entries) in enumerate(CREDITS):
            txt.insert("end", section + "\n", ("h",))
            for name, what, url in entries:
                tag = f"url{id(url)}{name[:6]}"
                txt.insert("end", name, ("name",))
                txt.insert("end", "\n" + (what + "\n" if what else ""), ("note",))
                if url:
                    txt.insert("end", url, ("link", tag))
                    txt.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
                    txt.insert("end", "\n")
                txt.insert("end", "\n")
        txt.insert("end", "MapleStory is a trademark of NEXON. This is an unofficial fan tool, not "
                          "affiliated with or endorsed by NEXON, NiaMeowDB or OSMS Data Explorer.",
                   ("note",))
        txt.config(state="disabled")
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Copy credits", command=lambda: (
            win.clipboard_clear(), win.clipboard_append(
                f"Free Market Tracker {mfm.VERSION}\n\n" + "\n\n".join(
                    sec + "\n" + "\n".join(f"- {n}" + (f": {w}" if w else "") + (f" ({u})" if u else "") for n, w, u in ents)
                    for sec, ents in CREDITS)))).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())

    def open_data_folder(self):
        import subprocess
        path = str(mfm.DATA)
        try:
            if mfm.sys.platform == "win32":
                mfm.os.startfile(path)
            elif MAC:
                subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            messagebox.showinfo("Data folder", path)

    def open_history(self, tree):
        sel = tree.selection()
        if not sel:
            return
        item = tree.set(sel[0], "item")
        if not self.con.execute("SELECT 1 FROM listings WHERE item = ?", (item,)).fetchone():
            messagebox.showinfo(item, f"'{item}' hasn't been seen in any shop yet.", parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title(item)
        win.geometry("1000x660")
        head = ttk.Frame(win, padding=(12, 10, 12, 0))
        head.pack(fill="x")
        ttk.Label(head, text="  " + item, image=self.icon_for(item, 48), compound="left",
                  style="Big.TLabel").pack(side="left")

        def lookup():
            import webbrowser
            webbrowser.open(mfm.meowdb_url(item))
        ttk.Button(head, text="Look up on meowdb", command=lookup).pack(side="right")
        summary = ttk.Label(win, padding=(12, 0))
        summary.pack(anchor="w")
        legend = ttk.Label(win, padding=(12, 0), foreground="#777")
        legend.pack(anchor="w")
        c = tk.Canvas(win, background="white", highlightthickness=0, height=260)
        c.pack(fill="both", expand=True, padx=12, pady=10)
        hint = ttk.Label(win, padding=(12, 0), justify="left", text=(
            "Sightings, cheapest first. Right-click a listing to change its price or channel, "
            "or to delete it; pick several with " + ("Option+click" if MAC else "Alt+click")
            + " to change them together. Double-click changes the price."))
        hint.pack(anchor="w", fill="x")
        hint.bind("<Configure>", lambda e: hint.config(wraplength=max(e.width - 24, 200)))
        table = make_tree(win, ("each", "status", "shop", "player", "map", "channel", "time"))
        table.column("#0", width=0, minwidth=0)   # one item: no per-row icon needed
        table.column("status", width=130)
        table.frame.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        st = {"rows": [], "out": [], "mkt": None, "bounds": None}

        def load():
            """(Re)read the item's listings and refresh every part of the window."""
            rows = self.con.execute(
                "SELECT COALESCE(sold_ts, ts), price, shop, seller, map, channel, qty, "
                "COALESCE(sold, 0), id FROM listings WHERE item = ? ORDER BY COALESCE(sold_ts, ts)",
                (item,)).fetchall()
            if not rows:
                win.destroy()
                return
            mkt, src = mfm.market_rate(self.con, item, self.cfg)
            bounds = mfm.outlier_bounds(self.con, item, self.cfg)
            out = [mfm.is_outlier(r[1], bounds) for r in rows]
            st.update(rows=rows, out=out, mkt=mkt, bounds=bounds)
            ps = mfm.price_stats(self.con, item, self.cfg, bounds)
            summary.config(text=(
                f"Market {mfm.fmt(mkt)} ({src})   ·   listed median {mfm.fmt(ps['listed_median'])} "
                f"({ps['listed_n']})   ·   sold median {mfm.fmt(ps['sold_median'])} ({ps['sold_n']})"))
            legend.config(text="dots = for sale    grey squares = sold    dashed line = market"
                          + ("    hollow orange = outlier (ignored)" if any(out) else "")
                          + (f"\nnormal range {mfm.fmt(bounds[0])} – {mfm.fmt(bounds[1])}; "
                             "prices outside it are ignored for the market rate" if bounds else ""))
            keep = set(table.selection())
            table.delete(*table.get_children())
            for ts, each, shop, seller, mp, channel, qty, sold, lid in sorted(rows, key=lambda r: (r[7], r[1])):
                v, _ = mfm.verdict(each, mkt, self.cfg["deal_threshold_pct"], bounds)
                tag = "outlier" if v == "OUTLIER" else "sold" if sold else (tag_for(v) if v != "?" else "")
                low = mfm.is_outlier(each, bounds) and bounds and each < bounds[0]
                table.insert("", "end", iid=str(lid), tags=(tag,), values=(
                    mfm.fmt(each), "outlier" if v == "OUTLIER" else ("sold" if sold else "for sale")
                    + (" (very low)" if low else ""),
                    shop or "", seller or "", mp or "", channel or "", mfm.local_time(ts)))
            table.selection_set([k for k in keep if table.exists(k)])
            draw()

        def picked():
            return [int(k) for k in table.selection()]

        def changed(msg):
            load()
            self.refresh_tables()
            self._set_status(msg)

        def change_price():
            ids = picked()
            if not ids:
                return
            cur = table.set(str(ids[0]), "each") if len(ids) == 1 else ""
            raw = ask_value(win, "Change price",
                            ("New price for this listing" if len(ids) == 1 else
                             f"New price for these {len(ids)} listings")
                            + " (e.g. 45000, 45,000 or 45k):", cur,
                            check=lambda t: (mfm.parse_price(t) or 0) > 0)
            if raw is None:
                return
            each = mfm.parse_price(raw)
            n = mfm.set_listing_price(self.con, ids, each)
            changed(f"Changed the price of {n} listing{'s' if n != 1 else ''} of '{item}' to {mfm.fmt(each)}.")

        def change_channel():
            ids = picked()
            if not ids:
                return
            cur = table.set(str(ids[0]), "channel") if len(ids) == 1 else ""
            raw = ask_value(win, "Change channel",
                            ("Channel for this listing" if len(ids) == 1 else
                             f"Channel for these {len(ids)} listings") + " (1–100, empty = unknown):",
                            cur, choices=[str(n) for n in range(1, 101)],
                            check=lambda t: not t.strip() or (t.strip().isdigit() and 1 <= int(t) <= 100))
            if raw is None:
                return
            n = mfm.set_listing_channel(self.con, ids, raw.strip())
            changed(f"Set channel of {n} listing{'s' if n != 1 else ''} to "
                    + (mfm.channel_label(raw.strip()) if raw.strip() else "unknown") + ".")

        def delete():
            ids = picked()
            if not ids:
                return
            what = (f"this {table.set(str(ids[0]), 'each')} listing" if len(ids) == 1
                    else f"these {len(ids)} listings")
            if not messagebox.askyesno("Delete listings", f"Delete {what} of '{item}'?\n\n"
                                       "Other listings of the item are kept.", parent=win):
                return
            n = mfm.delete_listings(self.con, ids)
            if not self.con.execute("SELECT 1 FROM listings WHERE item = ?", (item,)).fetchone():
                self._forget_icon(item)
            changed(f"Deleted {n} listing{'s' if n != 1 else ''} of '{item}'.")

        menu = tk.Menu(win, tearoff=False)

        def popup(e):
            row = table.identify_row(e.y)
            if not row:
                return
            if row not in table.selection():   # right-clicking inside a selection keeps it
                table.selection_set(row)
            n = len(table.selection())
            menu.delete(0, "end")
            menu.add_command(label="Change price…" if n == 1 else f"Change price of {n} listings…",
                             command=change_price)
            menu.add_command(label="Change channel…" if n == 1 else f"Change channel of {n} listings…",
                             command=change_channel)
            menu.add_separator()
            menu.add_command(label="Delete listing" if n == 1 else f"Delete {n} listings", command=delete)
            menu.tk_popup(e.x_root, e.y_root)
        bind_right_click(table, popup)
        table.bind("<Delete>", lambda e: delete())
        table.bind("<BackSpace>", lambda e: delete())
        table.bind("<Double-1>", lambda e: change_price() if table.identify_row(e.y) else None)

        def draw(_=None):
            rows, out, mkt, bounds = st["rows"], st["out"], st["mkt"], st["bounds"]
            c.delete("all")
            if not rows:
                return
            w, h = c.winfo_width(), c.winfo_height()
            pad_l, pad_r, pad_t, pad_b = 80, 16, 14, 28
            # scale to the normal prices; outliers are pinned to the top/bottom edge
            vals = [r[1] for r, o in zip(rows, out) if not o] or [r[1] for r in rows]
            vals += [mkt] if mkt else []
            lo, hi = min(vals), max(vals)
            if hi == lo:
                lo, hi = lo * 0.9, hi * 1.1 + 1
            span = hi - lo

            def y(v):
                v = min(max(v, lo), hi)
                return pad_t + (hi - v) / span * (h - pad_t - pad_b)

            def x(i):
                return pad_l + i * (w - pad_l - pad_r) / max(len(rows) - 1, 1)

            for frac in (0, 0.5, 1):
                v = lo + span * frac
                c.create_line(pad_l, y(v), w - pad_r, y(v), fill="#eeeeee")
                c.create_text(pad_l - 8, y(v), text=mfm.fmt(v), anchor="e", fill="#777")
            if mkt:
                c.create_line(pad_l, y(mkt), w - pad_r, y(mkt), fill="#999", dash=(4, 3))
                c.create_text(w - pad_r, y(mkt) - 8, text="market", anchor="e", fill="#999")
            pts = [(x(i), y(r[1])) for i, r in enumerate(rows)]
            line = [p for p, o in zip(pts, out) if not o]
            if len(line) > 1:
                c.create_line(*[v for p in line for v in p], fill="#3b6fd1", width=2)
            for (px, py), r, o in zip(pts, rows, out):
                if o:     # outlier: hollow orange ring at the edge, labelled with its price
                    c.create_oval(px - 5, py - 5, px + 5, py + 5, outline="#d9822b", width=2)
                    c.create_text(px + 8, py + (10 if py < h / 2 else -10), text=mfm.fmt(r[1]),
                                  anchor="w", fill="#d9822b")
                    continue
                if r[7]:  # sold: grey square
                    c.create_rectangle(px - 4, py - 4, px + 4, py + 4, fill="#7a7a7a", outline="")
                    continue
                v, _ = mfm.verdict(r[1], mkt, self.cfg["deal_threshold_pct"], bounds)
                col = {"DEAL": "#1f9a4a", "HIGH": "#c8352b"}.get(v, "#3b6fd1")
                c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=col, outline="")
            c.create_text(pad_l, h - 10, text=mfm.local_time(rows[0][0]), anchor="w", fill="#777")
            c.create_text(w - pad_r, h - 10, text=mfm.local_time(rows[-1][0]), anchor="e", fill="#777")

        c.bind("<Configure>", draw)
        load()

    def on_close(self):
        self.stop()
        if getattr(self, "_icons_stop", None):
            self._icons_stop.set()
        self.root.after(200, self.root.destroy)


def set_window_icon(root) -> None:
    for p in (mfm.BUNDLE / "icon.png", Path(__file__).resolve().parent / "packaging" / "icon.png"):
        if p.exists():
            try:
                root._icon = ImageTk.PhotoImage(Image.open(p))
                root.iconphoto(True, root._icon)
            except Exception:
                pass
            return


def main():
    root = tk.Tk(className="free-market-tracker")
    set_window_icon(root)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
