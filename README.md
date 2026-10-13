# Free Market Tracker

**Free Market price tracker for MapleStory Classic World.**

Free Market Tracker reads the shop windows you open in the Free Market, logs every item and
price, and marks each listing as a **DEAL**, **fair** or **HIGH** compared with the market
price. It only looks at your screen; it never touches the game.

Technical name (command line, data folder, repository): `mfm-tracker`.
What's new: [CHANGELOG.md](CHANGELOG.md).

## Install

Download the app for your system from the
[Releases page](https://github.com/jayee88/mfm-tracker/releases). Nothing else needs to be
installed.

- **Windows:** run `Free Market Tracker.exe`. If Windows shows "Windows protected your
  PC", click **More info → Run anyway**.
- **macOS** (Apple silicon; on an Intel Mac, build it yourself, below): unzip it and drag
  **Free Market Tracker** into Applications. If macOS won't open it, go to System
  Settings → Privacy & Security and click **Open Anyway**. When you first press **Start
  monitoring**, allow **Screen Recording** (System Settings → Privacy & Security → Screen
  Recording), then reopen the app.
- **Linux:** extract it and double-click **Free Market Tracker** (if it opens as text:
  right-click → Properties → "Is executable"). Runs on 64-bit distros with glibc 2.35 or
  newer (Ubuntu 22.04+, Debian 12+, Fedora 36+, openSUSE, Arch and others). On Wayland, also
  install your desktop's screenshot tool: `grim` (Hyprland, Sway), `spectacle` (KDE) or
  `gnome-screenshot` (GNOME).

Play the game **windowed or borderless**, not exclusive fullscreen.

### Run from source (optional)

**Windows:** install [Python](https://www.python.org/downloads/) (tick **Add to PATH**)
and [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki), then in PowerShell:
```powershell
cd mfm-tracker
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python mfm-tracker gui
```

**macOS:**
```bash
brew install tesseract python@3.12 python-tk@3.12
cd mfm-tracker
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python mfm-tracker gui
```

**Linux:** install the packages for your distro, then run the same three commands as on
macOS with `python3`:

| Distro | Packages |
|---|---|
| Ubuntu, Debian, Mint, Pop!_OS | `sudo apt install python3 python3-venv python3-tk tesseract-ocr tesseract-ocr-eng` |
| Fedora | `sudo dnf install python3 python3-tkinter tesseract tesseract-langpack-eng` |
| openSUSE | `sudo zypper install python3 python3-tk tesseract-ocr tesseract-ocr-traineddata-english` |
| Arch, Manjaro, EndeavourOS | `sudo pacman -S python tk tesseract tesseract-data-eng` |
| Void | `sudo xbps-install python3 python3-tkinter tesseract-ocr tesseract-ocr-eng` |
| Alpine | `sudo apk add python3 python3-tkinter tesseract-ocr tesseract-ocr-data-eng` |
| RHEL, Rocky, AlmaLinux 10 | `sudo dnf install epel-release`, then `sudo dnf install python3 python3-tkinter tesseract tesseract-langpack-eng` |

### Build the app yourself (optional)
- **Windows:** double-click `packaging/Build Windows App.bat`.
- **macOS:** double-click `packaging/Build macOS App.command`.
- **Linux:** run `packaging/build_tesseract_static.sh`, then `packaging/build_linux.sh`.
- **All three on GitHub:** run the **Build apps** workflow from the Actions tab.

The finished app is in the `dist` folder.

## Getting started

1. Open Free Market Tracker. The first time, it offers to download the MapleStory Classic
   item and map lists. Say yes; they correct misread item and map names.
2. Pick your **Channel**.
3. Click **Start monitoring**, then play normally: open shops and scroll through them.

The shop window and the minimap are found automatically, on any monitor. Each listing is
saved with its item, price, shop, player, map, channel and time. The panel on the right
shows what's being read.

If the shop or map is ever not found, use **Shop area** / **Map area** to draw a box
around it. **Settings → Auto Detection** goes back to finding them automatically.

## Channel

Click the arrow on the **Channel** box to pick from the channel picker, or type the
number. The channel stays set until you change it.

The app also asks for your channel when it starts and each time you change channel in
the game (after the game's Change Channel window closes). Turn this off, or set how many
channels the picker shows, in **Settings**.

## Tabs

- **Live:** the shop you're in, filling in as you scroll. Green = DEAL, red = HIGH,
  grey = no market price yet, faded = sold.
- **Deals:** listings still for sale, best deals first. Tick **Include sold** to see sold
  ones.
- **Items:** every item you've seen: the cheapest listing still for sale and where it is,
  listed and sold prices, market price, and the NPC buy / sell prices. Filter by name,
  category, class, level or "Sold by NPCs" with the bar above it.
- **Review:** names that didn't match an item in the database. Press **Enter** to accept
  the suggested item, **M** to pick one yourself, **K** to keep the name, **Delete** to
  remove it.
- **Watched**, **Ignored** and **My Inventory:** see below.

Double-click any item for its **price history**: a chart and every sighting. Right-click a
sighting to change its price or channel, add a note, watch it, or delete it.

Right-click items in any table for more options: watch the item, add a note, watch the
listing, ignore, match to the right item, delete a bad read, or look the item up on meowdb.

## Notes

Add a note to a listing for anything the item name doesn't say, like **+5 ATK** or **7
slots**: right-click it in Live, Deals or an item's history → **Add note…**. Notes show in
the **Notes** column. The next time you see the same item from the same player at the same
price, it gets the note too.

### Selecting several rows
- **Alt + click** adds or removes a row; **Ctrl + Alt + drag** selects every row you pass
  over. Ctrl + click, Shift + click and Ctrl + A work too.
- On a Mac, use **Option** instead of Alt and **Cmd** instead of Ctrl.
- Right-click the selection to act on all of it, or press Delete.

## Watched

Watched items and listings get an **alert**: a sound, a green outline, and the app comes to
the front. The **Watched** tab has two lists.

**Watched items** (top): any listing of an item.
1. Type the item, optionally a **max price**, and click **Watch**. Or right-click any item →
   **Watch this item…**
2. When it's for sale in a shop you open, you get an alert, and the price, shop, player,
   map, channel and time are shown.

**Watched listings** (bottom): one player's listing, e.g. a Korean Fan with +5 ATK.
1. Right-click a listing in Live, Deals or an item's history → **Watch this listing…**, and
   enter a note for it.
2. When that listing is for sale again, you get an alert. Its latest price, place and time
   are shown, and it's marked sold once it sells.

Right-click a watched item or listing to see its history, change the max price or note, or
remove it. Pick your own alert sound with **Choose sound…**. Sound and "bring to front" can
each be turned off.

**Ignored:** items you don't care about. They never count as deals, but their prices are
still logged and watched items still get alerts. Right-click any item → **Ignore deals on…**

## My Inventory

Keep track of what the items you own are worth.

1. Click **Add items…**. A window opens that reads your **Item Inventory** in the game
   (open it with the I key). Your items show up as you switch between its tabs.
2. Icons that couldn't be matched are highlighted: press **Enter** to accept the suggested
   item, **M** to pick one yourself, or **Delete** to remove the row. Your choice is
   remembered next time.
3. Select the items you want and click **Add**. **Add by name…** puts any other item in
   the list by typing its name.

If your inventory isn't found, click **Inventory area** and draw a box around it.
**Settings → Auto Detection** goes back to finding it automatically.

For each item, the tab shows its market price, the range of prices seen, how many
sightings there are, how many sold in the last 24 hours, and the average of its last 3
sales. **Net worth** at the bottom adds them up:
- **Possible range:** the lowest and highest prices of all your items.
- **Estimated value (market prices)** and **(last 3 sales)**.

Right-click an item to see its history, change the quantity or remove it. Matching works
best with all item icons downloaded (Settings → Game data → Update).

## Market price

An item's market price is:
1. a reference price you imported, or
2. the median of the prices you've seen over the last 14 days (only sold prices, once it
   has sold at least twice).

Your own sightings only count once an item has been seen **5 times** (Settings →
**Required sightings before judging**). Until then it shows no DEAL or HIGH.

**Outliers:** troll prices and misreads far from an item's usual price are left out of its
market price. Very low ones still show as deals; very high ones show as **OUTLIER**. Adjust
or turn this off in Settings.

**Sold items:** listings that are faded in a shop are logged as sold. Coming back to the
same shop doesn't log the same listing twice.

## Import and export

- **Export prices…** saves a CSV of market prices (one row per item) or every sighting.
- **Import prices…** loads reference prices from a CSV with the columns `item,price`, for
  example prices you copied from meso.watch.
- **Settings → Game data:** **Update** downloads the latest item and map lists (and item
  icons) from NiaMeowDB, with OSMS Data Explorer as a backup. **Import…** / **Export…**
  saves or restores each list; an item list exported as **.zip** includes every icon.

Exported files get the date and time in their name, e.g.
`mfm-tracker market prices 2026-10-13 08-11-00.csv`.

## Settings

Rest the mouse on any setting for a short explanation.

| Setting | Default | What it does |
|---|---|---|
| Capture every (seconds) | 0.15 | how often the screen is read while monitoring |
| Frames to confirm a row | 2 | identical reads needed before a listing is saved |
| Extra reads for names not in database | 2 | extra reads before an unknown name is saved |
| Empty frames = shop closed | 3 | reads without a shop before it counts as closed |
| Market median window (days) | 14 | how many days of sightings make the market price |
| OCR upscale factor | 3 | raise it if small text is misread |
| Required sightings before judging | 5 | sightings needed before an item gets a market price, DEAL / HIGH, and outliers |
| Flag DEAL / HIGH at ± % | 15 | how far from the market price a listing must be |
| Outliers: ceiling / floor | 200% / 75% | how far above / below the usual price counts as an outlier |
| Ask for the channel at launch and after a channel change | on | the channel prompt |
| Channels in the channel picker | 18 | buttons in the channel picker |
| Data retention | 30 days, archive | see below |

**Data retention:** listings not seen for 30 days are copied to an archive file and then
removed (or just deleted, or kept forever). This runs at start, every 6 hours, and when you
click **Clean up now**. A red warning appears if the price database grows past 100 MB.

## Your data

Everything is kept in one folder: `%APPDATA%\mfm-tracker` (Windows),
`~/Library/Application Support/mfm-tracker` (macOS) or `~/.local/share/mfm-tracker`
(Linux). **Settings → Open data folder** opens it.

| Folder | Contents |
|---|---|
| `prices/` | your prices (`prices.db`) |
| `settings/` | settings, watched items and listings, my inventory, ignore list, manual matches |
| `cache/` | downloaded item and map lists, icons |
| `archives/` | old listings moved out by data retention |
| `backups/` | copies made before anything is cleared |

**Settings → Clear pricing data…** and **Reset personal settings…** ask twice and save a
backup first.

## Command line

The app and `mfm-tracker` (from source) also take commands:
```bash
mfm-tracker deals                   # recent listings ranked against the market price
mfm-tracker item "dark scroll"      # one item's price history
mfm-tracker watch --channel 5       # monitor in the terminal
mfm-tracker report                  # an HTML report
mfm-tracker export prices.csv       # export prices (--all for every sighting)
mfm-tracker import-ref prices.csv   # import reference prices
mfm-tracker meowdb                  # update the item and map lists
mfm-tracker where                   # show the data folder
mfm-tracker --help                  # every command
```
With the app, use `"Free Market Tracker" deals` and so on. From source:
`python mfm-tracker deals`.

## Credits

Also in the app: **Settings → About**.

**Created by**

- Jayee (Discord: @jayee88)

**Made with**

- [Claude Opus 5.5 (claude-opus-5-5) by Anthropic](https://www.anthropic.com/claude): AI model that wrote the code, tests and documentation, working with you in Claude

**Game data**

- [NiaMeowDB (meowdb.com) — the meowdb team](https://meowdb.com/msclassic/): Item and map lists, item ids and icons for MapleStory Classic World
- [OSMS Data Explorer (osmsdataexplorer.com) — @ohmi](https://osmsdataexplorer.com/): Backup item and map lists and icons, mined from MapleStory Classic World

**Open source**

- [Tesseract OCR 5.3.4](https://github.com/tesseract-ocr/tesseract): reads the text in shop windows · Apache-2.0
- [Tesseract English data (tessdata_fast)](https://github.com/tesseract-ocr/tessdata_fast): OCR language model · Apache-2.0
- [Leptonica 1.87.0](https://github.com/DanBloomberg/leptonica): image library used by Tesseract · BSD-2-Clause
- [libpng and zlib](https://github.com/pnggroup/libpng): image compression used by Leptonica · libpng and zlib licenses
- [Python 3.13](https://www.python.org/): the language the app is written in · PSF License
- [python-build-standalone](https://github.com/astral-sh/python-build-standalone): portable Python used to build the Linux app · MPL-2.0
- [Tcl/Tk 9.0.3](https://github.com/tcltk/tk): the window toolkit (tkinter) · Tcl/Tk license (BSD-style)
- [libXft 2.3.9](https://github.com/openbsd/xenocara): smooth fonts for Tk on Linux, from OpenBSD's xenocara · HPND (MIT-style)
- [Pillow](https://github.com/python-pillow/Pillow): image processing · MIT-CMU (HPND)
- [pytesseract](https://github.com/madmaze/pytesseract): Python bridge to Tesseract · Apache-2.0
- [python-mss](https://github.com/BoboTiG/python-mss): screen capture · MIT
- [pyspellchecker](https://github.com/barrust/pyspellchecker): English word list for shop titles · MIT
- [SQLite](https://www.sqlite.org/): the price database · public domain
- [Inter typeface](https://github.com/rsms/inter): the app's font · SIL Open Font License 1.1
- [PyInstaller 6.22 (with pyinstaller-hooks-contrib, altgraph)](https://github.com/pyinstaller/pyinstaller): packs everything into one app · GPL-2.0 with bootloader exception, Apache-2.0, MIT
- [pynput](https://github.com/moses-palmer/pynput): global hotkey for the command-line `hotkey` mode (not in the packaged app) · LGPL-3.0

MapleStory is a trademark of NEXON. This is an unofficial fan tool, not affiliated with or endorsed by NEXON, NiaMeowDB or OSMS Data Explorer.

## License

Free Market Tracker is free software under the [GNU General Public License v3.0](LICENSE). The open-source components listed above keep their own licenses.
