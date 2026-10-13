# Changelog

Versions are `YYMM.minor.hotfix`.

## 2610.12.001 — 2026-10-13

### New
- **Channel change prompt** (Settings → *Ask for the channel at launch and after a
  channel change*, off by default). When it's on, a channel picker opens:
  - when the app starts;
  - each time you change channel in the game. The app spots the game's
    **CHANGE CHANNEL** and **CANCEL** buttons side by side, and asks once that window
    has closed, not while it's open.

  Pick a channel (1–100) or type it. **Keep chN** closes the picker unchanged, e.g.
  if you cancelled. It works while monitoring and while not; on Wayland only while
  monitoring.
- **Exports are timestamped**: every export's file name gets your local date and time,
  `YYYY-MM-DD HH-MM-SS`. That covers prices, the item and map lists, and the command
  line's `export`, `export-items`, `export-maps` and `report`. For example,
  `mfm market prices 2026-10-13 08-11-00.csv`.

### Fixed
- **Free Market map names read as junk** ("Hidden Streat Lz: Rem aihlea ned…",
  "Hidden Steet: ltl Ud*Cl U"). The minimap is as wide as the map's name, but its
  area was measured once and kept for as long as shops opened in the same spot, which
  they do on every map. Coming from a map with a longer name (Victoria Road), the area
  was too wide for the Free Market's minimap and took in the shop signs beside it.
  - The minimap is now measured again before every shop visit.
  - The map reader cuts its capture down to the minimap's name panel, so scenery
    beside or below it is never read.
- Listings already saved with a garbled map keep it; the right Free Market number
  can't be recovered from the junk.

## 2610.11.002 — 2026-10-13

### Fixed
- **meowdb couldn't be reached** from the apps built on GitHub ("certificate verify
  failed: unable to get local issuer certificate"). Their Python looked for trusted
  certificates where GitHub's build machine keeps them, not where your system does.
  The apps now carry their own certificate bundle and also use the system's
  certificates, wherever the system keeps them.
- Certificate errors get their own hint in the error window instead of "check your
  internet connection".

## 2610.11.001 — 2026-10-13

Changes since 2610.7.001.

### New
- **Items tab filters**, modelled on NiaMeowDB's item database:
  - name, category (Equip, Use, Etc, Setup, Cash) and the kind of item within it;
  - class (equipment only), with or without all-class items;
  - required level range and **Sold by NPCs**.
  - **Clear** resets them, a count shows how many items match, and the filter is
    remembered between sessions.
- **NPC buy** and **NPC sell** prices in the Items tab, right after Market: what an NPC
  shop charges (the cheapest shop, from NiaMeowDB's NPC Shop Database) and what an NPC
  pays you. They're downloaded with the item data on every **Update**.
- **Shop** and **Player** are separate columns in Deals, Items, Alerts and item
  history; the Live header and Recent shops show them apart too.
- **Full map names**: both minimap lines are read, so maps are saved as "Area: Zone",
  e.g. "Kerning City Subway: Line 1 <Area 1>" or "Hidden Street: Free Market <2>".
- Wide tables scroll sideways.

### Changed
- **A listing's price is the meso amount shown.** Whatever comes before "for" is
  ignored ("699 for 222,222 mesos" is 222,222), and a garbled quantity no longer stops
  a row from being read. Prices already logged are converted once.
- Column headers are now **Price** and **Max price** (no more "/ ea").
- The window opens a little wider (1300 px) so the new columns fit.

### Fixed
- The map area's icon was read as junk ("ies ||") and "<Area 1>" was cut to "<Area";
  the icon is now blanked out before reading and bracketed names are kept whole.
- Map names picked up the map count from meowdb's index ("Kerning City Subway ( 8 )").
  It's stripped now, and listings saved that way are corrected once.
- A required level of 0 was stored as unknown.
- Linux build on GitHub: the Tesseract build stopped when one of the library folders it
  looks in didn't exist.

### Upgrading
- Opening this version for the first time:
  - adds the area to map names logged before ("Free Market <2>" becomes
    "Hidden Street: Free Market <2>");
  - converts prices to the meso amount.
- The app offers to re-download the item and map lists once, for the filters and NPC
  prices (about 11 requests). Settings → Game data → **Update** does the same.

## 2610.7.001 — 2026-10-12

First release on GitHub: Windows, macOS (Apple silicon) and Linux apps.
