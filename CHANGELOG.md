# Changelog

Versions are `YYMM.minor.hotfix`.

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
