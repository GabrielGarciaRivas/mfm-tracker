# Maplestory Free Market Tracker — MapleStory Classic price tracker

Screenshots the shop window, reads item names and prices with OCR, logs them to a
local database, and tells you whether each listing is a **DEAL**, **fair**, or **HIGH**
compared with market rate. It only reads pixels from your screen; it never touches
the game client, memory, or network traffic.

## The app (no install)

**Windows:** `Free Market Tracker.exe`. **macOS:** `Free Market Tracker.app`. **Linux:**
`Free Market Tracker`. Each has Python, the window toolkit and Tesseract OCR built in;
nothing else needs to be installed. Put it anywhere and double-click it.

- **Windows:** the .exe isn't code-signed, so the first time SmartScreen may say "Windows
  protected your PC": click **More info → Run anyway**. Some antivirus tools are wary of
  single-file Python apps; it's a false positive, and building it yourself (below) gives
  you an identical file.
- **Linux:** extract it, then double-click (or run `./"Free Market Tracker"`). If your file
  manager opens it as text, make it executable: right-click → Properties → "Is executable",
  or `chmod +x "Free Market Tracker"`. To add it to your app menu, move it to
  `~/Applications/`, the `.desktop` file to `~/.local/share/applications/` and the `.png` to
  `~/.local/share/icons/`. On Wayland, `grim` / `spectacle` / `gnome-screenshot` from your
  desktop is still used for screenshots.
- **macOS:** build it on your Mac (below), then drag `Free Market Tracker.app` into
  Applications. The first time you press **Start monitoring**, macOS asks for **Screen
  Recording** permission: allow it in System Settings → Privacy & Security → Screen
  Recording, then quit and reopen the app. Without it the app only sees your desktop
  wallpaper and never finds a shop. (A rebuilt app counts as new to macOS, so after
  rebuilding you may need to switch the permission off and on again.)
- Starting takes a few seconds, since it unpacks itself to a temporary folder first.
- The app uses the Inter font (SIL Open Font License, `packaging/fonts/OFL.txt`), loaded
  privately by the app: nothing is installed on your system.
- The Linux app carries its own Tesseract 5.3.4, the version the OCR clean-up was tuned and
  tested on. (Newer Tesseract releases, like the one Arch currently ships, read some faded
  text and shop titles slightly differently.) It needs glibc 2.38 or newer, which any
  up-to-date Arch has.
- Your data (prices, alerts, settings) stays in the same data folder as before, so the app
  and the Python scripts share it.
- With arguments it works like `mfm.py`, e.g. `"Free Market Tracker" deals`.

### Building the apps yourself
- **Windows:** double-click `packaging/Build Windows App.bat`. It installs Python and
  Tesseract with winget if needed (for the build only), then writes
  `dist/Free Market Tracker.exe`.
- **macOS:** double-click `packaging/Build macOS App.command`. It installs Homebrew,
  Tesseract and Python with Tk if needed (for the build only), checks that OCR works from
  inside the finished app, then writes `dist/Free Market Tracker.app` and a
  `dist/Free Market Tracker (macOS).zip` for copying to another Mac. The app is built for
  your Mac's processor (Apple silicon or Intel). If macOS won't open the .command file
  because it was downloaded ("unidentified developer"), right-click it → **Open**, or
  allow it under System Settings → Privacy & Security → **Open Anyway**; or run it from
  Terminal: `bash "packaging/Build macOS App.command"`.
- **Linux:** `packaging/build_tesseract_static.sh` once (builds a self-contained Tesseract
  5.3.4; needs `base-devel cmake ninja libpng zlib`), then `packaging/build_linux.sh` (needs
  `python`, `tk`, `tesseract-data-eng`, and `pip install pyinstaller pillow pytesseract mss
  pyspellchecker`). Without the static Tesseract it bundles your system's tesseract and its
  libraries instead, which works but makes the file about three times bigger.
- **All three, on GitHub:** push this folder to a GitHub repository and run the "Build
  apps" workflow from the Actions tab (`.github/workflows/build.yml`); the files appear
  under the run's Artifacts (the Mac one is for Apple silicon). Pushing a tag like
  `v2610.1.000` also publishes them as a release. A Mac app downloaded this way isn't
  notarized by Apple, so the first time right-click it → **Open** (or run
  `xattr -cr "/Applications/Free Market Tracker.app"` once).
- Any built app can check its own OCR: `"Free Market Tracker" selftest`
  (on a Mac: `"/Applications/Free Market Tracker.app/Contents/MacOS/Free Market Tracker" selftest`).

## Install (running from source)

### Arch Linux
```bash
sudo pacman -S python python-pip tesseract tesseract-data-eng tk   # tk = the GUI toolkit
# Wayland only: one screenshot tool for your desktop
sudo pacman -S grim            # Hyprland / Sway
#   or spectacle (KDE) / gnome-screenshot (GNOME)

cd mfm-tracker
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # works in bash, zsh and fish
```
Then run the tool with `.venv/bin/python mfm.py gui`, or activate the venv first
(`source .venv/bin/activate` in bash/zsh, `source .venv/bin/activate.fish` in fish)
and use plain `python`.

### Windows
1. Install Python 3.10+ from python.org (tick **Add to PATH**; Tk for the GUI is included).
2. Install Tesseract: the UB Mannheim build at
   https://github.com/UB-Mannheim/tesseract/wiki (default path
   `C:\Program Files\Tesseract-OCR\` is detected automatically).
3. In PowerShell:
```powershell
cd mfm-tracker
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Run the game in **windowed or borderless** mode; exclusive fullscreen can capture black.

### macOS
```bash
brew install tesseract python@3.12 python-tk@3.12
cd mfm-tracker
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python mfm.py gui
```
Give Terminal (or whichever app runs the script) Screen Recording permission.

## Use

### Live window (recommended)
```bash
.venv/bin/python mfm.py gui
```
1. On first start it offers to download the **MapleStory Classic item list** from
   NiaMeowDB (see below). Say yes: OCR'd names are snapped onto real
   item names, so a misread like "Mokhbi Throwing Stars" is logged as "Mokbi
   Throwing-Stars". Names that aren't in the list (e.g. Classic World's renamed scrolls)
   still get word-level fixes from a vocabulary of item words ("PetEquip Speed Scrall" ->
   "Pet Equip Speed Scroll"). Letters OCR commonly confuses (g/p, a/o, l/i, rn/m) are
   treated as near-equal when matching, while genuinely different items (Wolbi vs Mokbi,
   10% vs 60%) are never merged. You can also do this from Settings or with
   `.venv/bin/python mfm.py meowdb`.
2. Click **Start monitoring** and play normally. Open shops and scroll through them.
   There's nothing to set up. The store window is found automatically wherever it is, on
   any monitor, by its SELLER INFO / BUY ITEM / LEAVE STORE buttons (only shop windows
   have that stack), so sky, clouds or other white windows can't be mistaken for it. The
   map name is read from the minimap, found by its "MINI MAP" title strip and WORLD
   button at the game window's top-left, whatever size the current map makes it, and
   even if you've dragged the shop window somewhere else. The minimap shows the name on
   two lines, the area on top and the zone below, and both are read: the map is saved as
   **"Area: Zone"**, e.g. "Kerning City Subway: Line 1 <Area 1>" or "Hidden Street: Free
   Market <2>". The area's icon left of the name is blanked out before reading.
3. Pick your channel in **Channel** (1–100: choose it from the list or type it; nothing else
   can be entered). It stays set for every shop you open until you change it, and is saved
   with each listing, since the channel isn't shown anywhere the tool can read.

The panel on the right shows what it found ("Shop area: auto, found at …") and a preview
of exactly what's being read.

**Manual areas (only if auto-detection misses):** **Shop area** lets you drag a box
around the whole store window (title bar to the bottom of the item list), and **Map
area** around the minimap's street + map name. Do this if you play windowed with an
unusual window size or have moved the minimap away from the corner. **Settings → Auto
Detection** forgets the areas you drew and goes back to finding the shop and minimap
automatically.

Every listing is logged with **where** it is: shop title, seller, map and your channel,
e.g. `111 (liormm) · Free Market <2> · ch2`.

- Every item gets a **thumbnail**, captured from the store window the first time it's
  seen (and replaced if the first one came from a faded, sold row). Icons show in all
  tables and the history window, and are stored in the database.
- A listing's **Price** is the meso amount shown before "mesos". Whatever comes before
  "for" (a quantity) is ignored: "699 for 222,222 mesos" is a price of 222,222. Databases
  from older versions, which divided by the quantity, are converted once.
- Where a listing is shows in four columns: **Shop** (the shop's name), **Player** (who's
  selling), **Map** and **Channel** (centered). The **Time** column shows your computer's local time as
  YYYY-MM-DD HH:MM; times are
  saved in UTC, so the database stays correct if you move it to another computer or time
  zone (older records are converted once, from this computer's time zone).
- **Live** shows the shop you're in, filling in as you scroll. Green = DEAL, red = HIGH,
  grey = no market price yet, shaded grey = SOLD. A deal only makes a sound when the item
  is on your Alerts list (see Alerts).
- **Deals** ranks listings still for sale by % vs market, with their location
  (tick **Include sold** to see sold ones too).
- **Items** shows, per item: the **cheapest listing still for sale and where it is**,
  the **listed median** vs. the **sold median** (what it actually sells for), and counts.
  Select a row and press Delete (or right-click) to remove a bad OCR read.
- Double-click any row for its price history (sold sightings drawn as grey squares)
  and every sighting with its status and location.
- In the history window, **right-click a sighting** to **change its price** (per item;
  `45000`, `45,000` and `45k` all work), **change its channel** (1–100, or empty for
  unknown), or **delete it**. Pick several with Alt+click (Option+click on a Mac) to
  change them together; double-click a sighting to change its price, Delete removes it.
  The chart, market rate and every table update right away.

### Alerts (watchlist)
Get a **ping** and a **green outline** around the item's icon when something you want
is for sale in a shop you open.

- **Alerts** tab: type an item (suggestions, with icons, come from the item database), optionally a
  **max price**, and click **Add alert**. Leave the max price empty to be alerted at
  any price. Or right-click any item in Live, Deals or Items → **Alert me when this is
  listed…**
- When a matching listing shows up while monitoring, the tracker plays a ping, shows
  the price and shop/map in the status bar, brings its window to the front, and
  records where it was: the Alerts tab shows each alert's **Last price**, **Shop**,
  **Player**, **Map**, **Channel** and **Time**. Several matches at once give one ping.
- Matching rows in Live, Deals and Items get a green outline on the icon and bold text.
- Sold (faded) listings and listings above your max price never alert.
- **Choose sound…** picks your own `.wav`; **Test sound** plays it. The sound is played
  with `winsound` on Windows and `pw-play`/`paplay`/`aplay` on Linux (PipeWire,
  PulseAudio or ALSA). If none of those exists you'll get the system bell instead.
  The ping sound and "bring window to front" can each be switched off in the tab.
- Double-click an item in the Alerts (or Ignored) tab for its price history, the same
  window as in the Items tab. Right-click an alert for **Show history**, **Change max
  price…** and **Remove item**; right-click an ignored item for **Show history** and
  **Remove item** (stop ignoring it). Both work on several selected rows at once.
- Alerts are saved in `watchlist.json` in the data folder (`mfm.py where`).

### Selecting several rows
Every table (Live, Deals, Items, Alerts, Ignored) lets you pick several rows at once:

| | |
|---|---|
| **Alt + click** | add or remove one row |
| **Ctrl + Alt + drag** | add every row the mouse passes over (scrolls at the top/bottom edge) |
| Ctrl + click / Shift + click | standard toggle / range select, also work |
| Ctrl + A, Esc | select all, clear |

On a Mac, Alt is the **Option** key: **Option + click**, and **Cmd + Option + drag** (or
Ctrl + Option + drag). Cmd + click / Shift + click and Cmd + A work too, and right-click is
also Ctrl + click or a two-finger click. Delete is the ⌫ key.

Right-click inside a selection to act on all of it: **Alert me when these are listed**
(one max price for all), **Ignore deals on** / **Stop ignoring**, and **Delete N listings**
(Live, Deals: just those shops' listings) or **Delete all listings of N items** (Items).
The Delete key does the same. A selection survives the tables' automatic refresh.

Linux note: many desktops use Alt+drag (KDE Plasma 5, some tiling WMs) or Alt+click to
move windows, which swallows the click before the tracker sees it. Use Ctrl+click /
Shift+click there, or change the window-move modifier to Super/Meta in your desktop
settings.

### Ignore list
Items you don't care about can be ignored for deals: right-click → **Ignore deals on…**,
or add them in the **Ignored** tab. Ignored items never ring the deal bell or get the
green DEAL highlight, and they're hidden from the Deals tab unless you tick **Show
ignored**. They're still logged (prices, history and market rates keep working), and an
alert you've set on an ignored item still fires. Stored in `ignorelist.json` in the data
folder; `mfm.py deals` skips them too.

### Outliers
Troll prices (69,420,420), fat-fingered listings and OCR slips (4 for 4,000) would drag an
item's market rate around. Once an item has **5 sightings** in the history window, any
price more than the **ceiling** above or the **floor** below the item's **median** is set
aside:

- it's left out of the market rate and the listed/sold medians;
- a price **below the floor** is still a **DEAL** (it's shown, highlighted, and counts for
  deal alerts like any other deal) and is marked "very low" in the item's history; it
  just doesn't move the market rate until prices around it make it normal;
- a price **above the ceiling** is shown as **OUTLIER** (orange), never a deal, and is left
  out of "cheapest listed"; the Deals tab hides those unless you tick **Show outliers**;
- in an item's history the chart scales to normal prices and outliers are drawn as hollow
  orange rings pinned to the edge, labelled with their price.

The median is the baseline because a single absurd price barely moves it, where it would
drag an average far enough to hide itself. Set the ceiling (default 200% = more than 3×
the median), the floor (default 75% = less than a quarter of it), the number of sightings
needed, or switch it off in **Settings**. Alerts you've set still fire on any price under
your cap.

### Sold items
Items drawn faded in a store have sold. They're logged as **sold**, and sold prices
are the preferred basis for the market rate:

1. a reference price you imported, else
2. the median **sold** price (once 2+ sales have been seen), else
3. the median of everything seen.

Coming back to a shop doesn't double-count. Before a listing is saved, it's checked
against the last 24 hours: if the same item and price was logged in a shop
with the same shop name, player name and map, it's shown in Live (marked
**already logged** in the Saved column, greyed) but not added again; only its "last
seen" time is updated. Small OCR slips in the shop or player name ("lynn" / "Iynn")
still count as the same shop. The **channel is not compared**, so forgetting to change
it when you move channels can't create duplicates. A price change, another seller or
another map is a new listing, and so is one last seen more than 24 hours ago.

If a listing was for sale on an earlier visit (within 7 days) and is faded now, that
row is marked as sold ("marked sold") instead of a second, sold copy being added.

How it follows you around the market:
- It only runs OCR when a store window is actually on screen (a ~7 ms colour check),
  so it stays light on CPU while you walk around.
- Item icons and their quantity badges are blanked out before reading, and faded rows
  get a second, contrast-boosted read so their prices come out right.
- Scrolling is handled automatically: each listing is logged once per shop visit.
  Rows cut off at the edge of the list are skipped until they scroll fully into view.
- A visit ends when you close the shop, or when the store header (title, avatar, seller)
  changes, i.e. you opened a different shop. Scrolling never changes the header, so it
  never starts a new visit. If it ever misses a switch, **Ctrl+N** ends the current visit.
- **The mouse cursor and item tooltips are ignored.** Rows under the glove cursor or under
  the pop-up item window are skipped for that frame (the panel shows "+N under cursor")
  and read as soon as you move the mouse off them, so the cursor can't turn "Toga" into
  "Topa" or glue "Orange Hooded…" from a tooltip onto the row below. Scrolling with the
  wheel while hovering the list is fine; just move the mouse off a row if it stays unread.
- Long names are truncated by the game (e.g. `Crossbow Attack Scroll: I…`) and are
  logged that way. If you import a reference price under the full name and only one
  item matches the prefix, it's matched to the full name automatically.

**Upgrading from the first version?** Its parser logged junk rows ("For", "1For"…).
Clear them out with `.venv/bin/python mfm.py purge-old`.

### Command line
```bash
python mfm.py calibrate          # manually set the store-window area (normally automatic)
python mfm.py calibrate --map    # manually set the minimap name area
python mfm.py calibrate --auto   # forget manual areas, go back to automatic
python mfm.py watch --channel 5  # same continuous monitoring, printed in the terminal
python mfm.py hotkey             # one capture per F8 press (Windows / X11)
python mfm.py deals              # last 24h of listings ranked by % vs market
python mfm.py item dark scroll gloves  # history for one item (fuzzy name match)
python mfm.py report             # report.html with trends, open in a browser
python mfm.py scan shot1.png     # OCR a screenshot of a store window
python mfm.py scan --full screen.png   # full-screen screenshot: finds the store automatically
python mfm.py forget "For"       # delete every listing of one (misread) item
```

Moving the game window or the store window is fine; it's re-found automatically.

**Wayland:** the GUI and `watch` both work (screenshots go through grim/spectacle/
gnome-screenshot). `hotkey` doesn't, since apps can't grab global keys there.
On KDE, spectacle may be slow at sub-second intervals; raise the capture interval in
Settings if the OCR time looks high.

## Item data from NiaMeowDB

Item names, ids and icons come from [NiaMeowDB](https://meowdb.com/msclassic/item-db)
(meowdb.com), used with permission. Thanks to the meowdb team.

**Backup source:** [OSMS Data Explorer](https://osmsdataexplorer.com/), game
data mined from MapleStory Classic World. It's used only where NiaMeowDB has nothing:
- **items** missing from meowdb's list (compared by the game's own item id, which meowdb
  uses as the icon key, and by name), so their names are spell-checked too, with their
  category;
- **maps** missing from meowdb's map list (it has every map, with street and region), so
  misread names on any map can be corrected;
- **icons** meowdb doesn't have: when meowdb answers "not found" for an icon, the backup
  source's picture of that item is used.

It's downloaded with **Update** (checked at most once a week, with conditional requests,
so unchanged files cost almost nothing; Full refresh checks it right away), and also when
meowdb can't be reached. A downloaded file that doesn't look like the expected format is
rejected and the previous copy kept. Settings → Game data shows what it adds. Command
line: `mfm.py osms [--force]`; `mfm.py meowdb` updates it too.

- On first start the GUI offers to download the Classic item and map lists; after that,
  **Settings → Game data → Update** (or `.venv/bin/python mfm.py meowdb`) only fetches
  what changed:
  - meowdb lists items in id order and new items get new ids, so an update re-checks just
    the page holding your newest item, plus any pages after it: usually **one request**,
    sent as a conditional request so an unchanged page comes back as "304 Not Modified".
  - The item list is checked at most once a day and the map list at most once a week;
    asking more often makes no requests at all.
  - A full re-download (one request per 500 items, one per second) happens the first time,
    after 30 days, if meowdb's list changed earlier in the list, or when you click **Full
    refresh** (`mfm.py meowdb --full`).
  - There's no fixed number of pages: each page from meowdb says whether more follow
    (`hasMore`) and how many there are (`totalPages`), and pages are read until there are no
    more, so a list that grows past 11 pages (5,500 items) is still read completely. An
    update starts at the page holding your newest item and continues onto any new pages.
  - `cache/meowdb_sync.json` is the bookkeeping for this: when the item list was last
    checked and fully downloaded, the version tag meowdb sent for each page (so an unchanged
    page costs a "304 Not Modified" instead of the whole page), and the same for the map
    list. It holds no item data; deleting it only makes the next update a full download.
- OCR'd names are snapped onto item names from the database ("Reppae Hat" -> "Reggae Hat"), and truncated
  names are expanded when only one item matches ("Claw Attack Scroll: Interm…" ->
  "Claw Attack Scroll: Intermediate").
- **Item icons:** Update and Full refresh also download every official item
  icon you don't have yet (Settings → Game data, on by default): up to **10 per second**
  in the background, so the first time takes roughly **10 minutes** for ~5,500 icons; the
  status bar shows progress and the time left.
  - **Automatic slow-down:** if meowdb answers "too many requests" (429) or "busy" (503),
    the speed halves and downloads pause for as long as meowdb asks (Retry-After, else 10
    s); slow answers (over 3 s) or errors reduce it by a quarter. After 50 good answers in a
    row it speeds back up by a quarter, never above 10 per second and never below one
    request per 2 seconds. The status bar says when meowdb has asked to slow down.
  - Four downloads are in flight at once, because one request on its own takes longer than
    a tenth of a second; the rate limit applies to all of them together. The speed is the
    `icon_rate` setting in `settings/config.json`.
  - Each icon is downloaded once, ever: later updates only fetch icons of new
  items (an item whose picture changes gets a new icon key, so that's caught too). Closing
  the app stops it; the next update continues where it left off. Icons meowdb doesn't have
  aren't asked for again for a month. Command line: `mfm.py meowdb --icons`.
- With that option off, icons are still fetched for the items you see in shops and in
  item search. Official icons replace the screen-captured thumbnails; items meowdb doesn't
  have keep the thumbnail cut from the screen. `mfm.py fetch-icons` fetches icons for
  everything you've logged.
- Items whose name doesn't exactly match anything in the item database get a small red
  **!** badge on their thumbnail (Live, Deals, Items and history). It usually means an OCR
  misread the item list couldn't fix, a name cut off too short to identify, or an item
  newer than your copy of the list. No badges are shown when no item list is installed.
- Look-alike names are guarded against: a short word can't gain or lose a letter ("Topa"
  is never snapped to "Topaz"), and when two different items are about equally close
  to what was read, the tracker doesn't guess. The row keeps its OCR text with a red **!**
  for you to match.
- **Fixing one bad read:** in Live or Deals, right-click → **Delete this listing (bad
  read)**, or **Match to database item…** with **Only this listing** ticked. That changes just
  that shop's listing, so a one-off misread of a real item (Toga logged as Topaz) can be
  fixed without renaming every genuine Topaz. For real item names this is the default,
  and "Remember" starts unticked.
- **Unmatched names get extra reads.** A row whose name doesn't match any item in the database isn't
  shown in Live or logged straight away: it's read on 2 more screen captures first (fresh
  reads, even if the screen hasn't moved). If one of those reads identifies the item, only
  the correct name is logged and the garbled read is dropped. Genuinely unknown items are
  logged after the extra reads, and one that scrolls out of view before then is still
  logged when you leave the shop, provided it was read at least twice. The number of
  extra reads is in Settings (0 turns this off).
- **Review tab:** every logged name that doesn't match an item in the database, most-seen first, with
  the closest database item, how alike they are, how many listings it has and what OCR read.
  Truncated scroll names are graded by their saved icon colour. Work through it from the
  keyboard (the next row is selected after each action, and several selected rows are
  handled at once):
  - **Enter**: accept the suggestion (renames the listings and, with "Remember" ticked,
    learns the reading for next time);
  - **M**: match by hand; **K**: keep the name as it is (an item newer than your list, say).
    Kept names lose their ! badge; tick "Show kept names" to see them or un-keep with K;
  - **Delete**: delete its listings (junk reads such as tooltip text);
  - **Accept all 90%+ alike** matches every confident suggestion at once, after showing you
    the list.
  The tab title shows how many names are waiting, e.g. "Review (7)". Command line:
  `mfm.py review` lists them, `mfm.py review --accept` accepts the 90%+ ones.
- **Manual matching:** right-click an item (Live, Deals or Items) → **Match to database
  item…**, type to search, and pick the right one. Its listings are renamed, and with
  "Remember" ticked the tracker learns that reading, so the next time your OCR produces
  the same misspelling it's logged correctly. Matches are stored in `aliases.json` in the
  data folder (`mfm.py where`); truncated scroll names are remembered per icon colour.
  Command line: `mfm.py match "Rennae Hat" "Reggae Hat"`.
- **Map names** are checked against meowdb's map list (downloaded with the items, one
  extra request) and the backup source's, so misreads like "Hidden Streat: Free Marker
  <8>" are logged as "Hidden Street: Free Market <8>". Room and area numbers must match
  exactly and are never changed. If the area line is misread, the zone alone decides
  when only one map has that zone. Map names already in your database are corrected
  when the list is downloaded, and names saved by versions before 2610.8 (zone only,
  "Free Market <2>") get their area added once.
- **Look up on meowdb** (right-click in Items, or the button in an item's history window)
  opens the item's meowdb page.

### Scroll grades from icon colour
Long scroll names are cut off by the game ("Overall Armor LUK Scroll:…"), and the visible
part can match several grades. When it does, the scroll's icon colour picks the grade:

| Icon colour | Grade |
|---|---|
| yellow | Greater |
| red | Intermediate |
| blue | Lesser |
| black | Chaos |

Any partial grade that is visible ("Topwear DEF Scroll: Gre…") is still respected, and it
works for faded (sold) scrolls too.

The colour is checked for **every** scroll name that isn't an exact item, before anything
else decides: it doesn't matter whether OCR kept the "..." ("Overall Armor DEF Scroll",
"…Scroll: Inter..", "Two-handed Blunt Wea"), small misreads in the visible part are
tolerated ("Overal Armor LUK Scrol"), and grades you've logged before never decide it.
A name that could be more than one scroll ("Overall Armor D…" = DEF or DEX) is never
guessed; it waits in the Review tab. If the colour can't be read, a visible grade letter
("Scroll: G") is used instead. Without an item list, names ending in "Scroll:" are
completed the same way ("Overall Armor LUK Scroll: Greater").

### Shop titles
Shop titles are corrected for OCR letter swaps ("55 burpers" -> "55 burgers") using an
English word list (`pyspellchecker`, installed from requirements.txt) plus item words.
A word is only changed when it isn't a real word and undoing a commonly-confused letter
turns it into one, so slang and shorthand ("pwease", "S>Scolls", "nx") stay as typed.
**Seller names are never corrected**, since players pick unusual names.

### Game data in Settings: what each file is for
**Settings → Game data** shows the two reference lists the app reads the game with (they
aren't your prices), how many entries each has and where it came from:

| list | used for | files (in the data folder's `cache/`) |
|---|---|---|
| **Item list** | spelling correction of item names; the item search in Alerts, Ignored, Match and Review; meowdb links and icons; item categories | `items.txt` (names), `meowdb_items.json` (meowdb copy: id, name, category, icon), `item_ids.json`, `item_types.json`, `item_icons.json` |
| **Map list** | correcting misread minimap names (`Free Marker <8>` → `Free Market <8>`) | `maps.json` (id, name, street) |
| **Backup source** | items, maps and icons meowdb doesn't have (OSMS Data Explorer) | `osms_items.json`, `osms_maps.json` (included in an item .zip export) |

Each has **Import…** and **Export…** (command line: `import-items`, `export-items`,
`import-maps`, `export-maps`):
- **Update** / **Full refresh** (at the top of the section) update both lists.
- Export as **.json** or **.csv** saves each list as one file. It doesn't look like the
  files in `cache/` because it's the source they're made from: the item export holds
  every item's meowdb id, name, display name, category and icon key (= `meowdb_items.json`),
  and `items.txt`, `item_ids.json`, `item_types.json` and `item_icons.json` are rebuilt
  from it on import, byte for byte the same; the map export holds everything in
  `maps.json`. So importing it restores the lists exactly, here or on another PC, and the
  next **Update** only asks for newer items. Not included: icons (use .zip)
  and the record of when meowdb was last checked.
- Export the item list as **.zip** to include **every icon** too: `items.json` (the same as
  a .json export), `icons/meowdb/<icon key>.png` for official icons and
  `icons/captured/` for thumbnails cut from the screen (items meowdb doesn't have, with
  their names in `index.json`). Importing the .zip restores the list and all icons, so
  another PC doesn't need the icon download. A map .csv saved by Excel loses the leading zeros of map ids; they're restored
  on import.
- **.txt** is names only, one per line. Importing a names-only item list uses just those
  names for spelling.
- **Update** replaces an imported list with meowdb's again.
- Your prices have their own **Export prices / Import prices** buttons in the main window.

## Market rate and meso.watch

For each item, "market" is:
1. your imported reference price, if you have one, otherwise
2. the median price of your own logs over the last 14 days (needs 3+ sightings).

meso.watch's robots.txt disallows automated access, so this tool doesn't scrape it.
To use its numbers, copy the prices you care about into a CSV like
`reference_prices.csv` and run:

```bash
python mfm.py import-ref reference_prices.csv
```

Re-import whenever you refresh it; existing items are overwritten. If meso.watch
ever offers an API or data export, that would be the clean way to automate this —
worth asking the site owner.

### Exporting prices
**Export prices…** (next to Import prices, or `mfm.py export FILE.csv [--all]`) saves a CSV:
- **Market prices**: one row per item with its market price and where that came from,
  listed and sold medians, outliers ignored, and the cheapest listing still for sale.
  Its first columns are `item,price,source`, so it can be imported again (on another
  computer, or after clearing your data) as reference prices.
- **Every sighting**: date, item, price, sold or for sale, shop, seller (player), map, channel.
  Its times are UTC (`first_seen_utc`, `last_seen_utc`, `sold_at_utc`).

## Errors

Errors are shown in the status bar and in an error window (one window that collects them,
with a hint when the cause is clear: no internet for a meowdb download, a write-protected
or full disk for the price database). The same error repeating, e.g. on every frame while
monitoring, reopens the window at most every 2 minutes. Details also go to `app.log` in
the data folder.

## Version

The version shown in the status bar is `YYMM.minor.hotfix`, e.g. `2610.1.000`.

## Data retention
**Settings → Data retention** keeps the price database from growing forever:

- **Keep listings for N days** (default **30**): a listing that hasn't been seen (or sold)
  for that long is old. Listings you keep seeing in shops stay, however old the first
  sighting is.
- **Then:** **Archive, then delete** (default): old listings are first copied into
  `prices-archive.db` in the **Archive to** folder (default `archives/` in the data folder;
  **Browse…** picks any folder, e.g. another drive), and only removed from your price
  database once the copy is complete. The archive has the same columns as `prices.db`
  (plus a log of each cleanup) and is added to every time, never overwritten.
  **Delete** removes them for good. **Keep everything** never removes anything.
- It runs automatically every time the app starts, every 6 hours while it's open (if
  you're monitoring at that moment it waits until you stop, checking every 10 minutes,
  since cleaning up briefly locks the database), and whenever you press **Clean up now**
  (which uses what's in the form). The database file is compacted afterwards so it
  actually shrinks. The line next to it shows the database size and how many listings are due.
- If the retention is shorter than the market price window (14 days), Save asks first,
  since market prices would have less data.
- When `prices.db` grows past **100 MB**, a **red warning** appears at the top of the main
  window recommending to archive and/or delete some data; clicking it opens Settings.
- Command line: `mfm.py prune [--days N] [--delete | --archive DIR]`.

## Your data

Everything lives in one data folder (`%APPDATA%\mfm-tracker` on Windows,
`~/Library/Application Support/mfm-tracker` on macOS, `~/.local/share/mfm-tracker` on Linux; `mfm.py where` or **Settings → Open data folder**
shows it), split three ways so each part can be backed up or cleared on its own:

| folder | what's in it |
|---|---|
| `prices/` | `prices.db`: every listing you've seen, and imported reference prices |
| `settings/` | `config.json` (settings and capture areas), `watchlist.json` (alerts), `ignorelist.json`, `aliases.json` (manual matches), `kept_names.json` |
| `cache/` | downloaded or rebuildable: item and map database, item icons (`icons.db`), the ping sound |
| `backups/` | copies made before anything is cleared |

Older versions kept everything in the top folder; files are moved into place the first
time this version starts.

**Settings → Your data:**
- **Clear pricing data…** deletes every listing and reference price (settings, alerts, the
  item list and icons are kept).
- **Reset personal settings…** lets you tick what to reset: settings and capture areas,
  alerts, ignore list, manual matches, kept names.

Both ask twice before deleting anything, and save a backup copy to `backups/` first
(`prices-<date>.db` / `settings-<date>/`). To undo, close the app and copy the backup back.

## Settings

Change these in the GUI's **Settings** (rest the mouse on any setting or button there for a
short explanation), or edit `settings/config.json`:

| key | default | meaning |
|---|---|---|
| `deal_threshold_pct` | 15 | % below/above market to flag DEAL/HIGH |
| `interval_seconds` | 0.75 | how often the screen is read while monitoring |
| `confirm_frames` | 2 | identical reads needed before a row is logged |
| `unmatched_extra_frames` | 2 | extra reads for a name not in the item database before it's logged |
| `close_frames` | 3 | empty frames in a row that mean the shop closed |
| `hotkey` | `f8` | any pynput key name (`f9`, `home`, …) |
| `upscale` | 3 | OCR upscaling; raise to 4 if small text misreads |
| `save_captures` | false | keep every capture PNG to debug OCR |
| `tesseract_cmd` | null | full path to tesseract.exe if not auto-found |
| `search_icons` | true | show item icons in item search (Settings → Game data → Item list) |
| `download_all_icons` | true | Update also downloads every item icon not here yet |
| `icon_rate` | 10 | icon downloads per second (slows down by itself if meowdb asks) |
| `keep_days` | 30 | listings not seen for this many days are archived and/or deleted |
| `retention` | `archive` | `archive` (copy to the archive, then delete), `delete`, or `keep` (never remove) |
| `archive_dir` | null | archive folder (null = `archives/` in the data folder) |
| `outliers_on` | true | ignore outlier prices once an item has enough sightings |
| `outlier_min_n` | 5 | sightings needed before outliers are judged |
| `outlier_ceiling_pct` | 200 | more than this % above the median is an outlier |
| `outlier_floor_pct` | 75 | more than this % below the median is an outlier |

## Tips for good OCR
- Icons and their number badges, buttons and the scrollbar are ignored automatically.
- If names come out garbled, set `save_captures: true` and look at what's being read.
- The first sighting of an item locks in its spelling; later OCR typos snap to it.
  Importing reference prices with the correct names gives a clean starting list.

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
