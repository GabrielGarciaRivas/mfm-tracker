# Changelog

## 2610.19.001 — 2026-10-19

### Changed
- **Nicknames are called aliases** now, everywhere in the app and its documentation.
  Your aliases are kept; they sync with servers before 2.6.0 too.
- **Review → Megaphones:** a **Type: Item / Words** button at the bottom, like the Type in
  Edit aliases: Accept suggestion and Match manually then teach an item or words.
- **The game window is read on its own** (Windows, macOS and Linux), so the app keeps
  reading while other windows cover the game (not while it's minimized). It's found by
  "MapleStory" in its title; **Settings → Window detection** can change that or turn it
  off (then the whole screen is read). Areas drawn on the whole screen before aren't used
  while the game window is read: draw them again if you need them.
- **Wayland:** reading the game's window from XWayland (where Wine runs it) takes a few
  milliseconds instead of about a second with a screenshot tool, with no prompt. Shops,
  megaphones and the Change Channel window are read as fast as on X11 or Windows, and the
  channel is noticed when you're not monitoring too. A screenshot tool is only used when
  the game window can't be read this way.

### Fixed
- **Wayland:** "CalledProcessError: Command '['grim', ...]' returned non-zero exit status 1"
  when starting monitoring on KDE or GNOME with grim installed. grim only works on Sway,
  Hyprland and other wlroots desktops. The app now uses your desktop's own tool first
  (spectacle on KDE, gnome-screenshot on GNOME), moves on to the next tool if one fails,
  and says which tool to install if none works.

### Server 2.6.0
- Nicknames are called aliases: `/api/v1/aliases` (the old `/api/v1/nicknames` still works
  for older apps), and `mfm-server purge aliases`. The stored ones are kept.

## 2610.18.005 — 2026-10-18

### Changed
- **Shared Database:** the window also counts aliases sent and received.
- **Megaphones:** a **Filter** box shows only megaphones whose message has every word
  typed in it.
- **OCR training (Settings):** the app can keep pictures of the megaphone lines it reads.
  Lines read the same way several times, or the same by the standard and the app's own
  model, get their text automatically. The rest wait in **Check lines** for you to fix
  or skip. Agreed and checked lines go to the Shared Database server, for training the
  OCR model.

### Server 2.5.0
- Keeps the OCR training lines the apps send. `mfm-server export-ocr FILE.zip` exports
  them, and `mfm-server purge ocr` deletes them.
- **Channel:** the channel read from the Change Channel window is set only when the
  screen fades to black within 3 seconds of the window closing (the game changing
  channel). CANCEL, Esc, and changes the game refuses (restricted maps, in combat) leave
  the channel as it was. This replaces watching for Esc and the mouse over CANCEL.
- **Watched items:** a listing with a watched item is shown in bold red text (the whole
  row) instead of an outline around its icon. Megaphones with a watched item are shown
  the same way.
- **Map:** the map you're on shows next to the channel ("Map: Hidden Street: Free Market
  <6>"), read from the minimap every few seconds while monitoring, with or without a shop
  open.

## 2610.18.004 — 2026-10-18

### Fixed
- "megaphone read failed: OverflowError: Python int too large to convert to SQLite
  INTEGER": a megaphone with a very long run of digits (a misread line) was taken as a
  price too big to save. Numbers above 10 billion aren't taken as prices any more.

## 2610.18.003 — 2026-10-18

### Changed
- **Shared Database:** when the server's admin deletes data (`mfm-server purge`), the app
  deletes the same prices, megaphones and aliases from its own data on its next sync.
  When the app and the server disagree, the server's copy wins. The Shared Database
  window shows how many prices, megaphones and aliases were purged this way.
- **Monitoring:** a green arrow left of the button while monitoring, a red square when
  stopped.
- **Settings → Window detection:** the Shop, Map, Chat and Inventory area buttons moved
  here, with a new one for the Change Channel window. Each area shows whether it's found
  automatically or drawn by hand, with the drawn area's coordinates, and can go back to
  automatic on its own.
- **Window:** opens wider (up to 1880 pixels, to fit your screen), so the Megaphones tab's
  Message column isn't cut off.
- **Downloads** are now a zip (Windows, macOS) or tar.gz (Linux) with the version in the
  file name. The app itself keeps its plain name.

### Server 2.4.0
- New command `mfm-server purge` deletes prices, megaphones or aliases: older than a time
  (`--older-than 1d`), from the past while (`--last 1h`), or all (`--all`). Connected apps
  delete the same from their own data.
- "Not an item" marks are stored with the aliases again (2.3.0 left them out). Apps
  send theirs again once.

## 2610.18.002 — 2026-10-18

### New
- **Better reading of megaphones and shops:** the app has its own OCR model, trained on
  1,197 lines from the game's chat and shops. On 154 lines it hadn't seen, it went from
  5.6% of characters wrong to 0.8% (lines read exactly right: 42 → 123). Reading a
  megaphone takes a bit longer.

### Changed
- **Channel:** when you change channel in the game, the app reads the highlighted channel
  in the Change Channel window and sets it. It only asks when it can't read it. The window
  is looked for as often as **Capture every (seconds)** (0.1 by default). Closing the
  window with **Esc** or **CANCEL** keeps the channel you had.
- **Review → Megaphones:** a **Delete megaphone** button deletes the megaphones the
  selected rows came from, without adding an alias. Deleted megaphones aren't copied
  back from the Shared Database.

### Fixed
- The window froze ("Not responding"), mostly on Windows with many megaphones from the
  Shared Database. The Megaphones tab is now worked out in the background and only
  redrawn when it's on screen, several new megaphones make one redraw, and background
  work pauses while a big table is redrawn.
- Review → Megaphones shows the 500 most-seen phrases (the count on the tab is still all
  of them), and their suggested items are only worked out for those.
- Bits of 1-2 letters ("CH") are no longer listed as megaphone items.
- A shop item's stack count is no longer read as part of its name ("4 Meba").
- Scrolls in megaphones match much more often: "att 60%" no longer loses its "60",
  "60 %" and "60%atk" are read as "60%", and common shorthand comes as word aliases
  ("att", "atk", "matk", "acc", "avoid", "ohs", "2h", "bw", "xbow", "overall", "top",
  "pants", "helm" and more). With your grade aliases, "60% glove att" matches Gloves
  Attack Scroll: Intermediate.

- Shop names are read more accurately: Tesseract is given every word of the item names, so
  when a letter is unclear it leans towards the real item word (in a test with blurrier
  text, 27 of 34 names were read exactly instead of 22).

### Changed
- **Shared Database:** the window shows "Connected to (server name) (version) as (you)",
  and how many megaphones were sent and received as well as prices.
- "Add manual aliases" is now "Edit aliases".

## 2610.18.001 — 2026-10-18

### New
- **Megaphone items and prices:** each item a megaphone sells or buys gets its own line in
  the Megaphones tab, with the item's icon, name, price and market price. The time is the
  first column; a megaphone's other items are the lines below it. Items are found
  from item links, names and learned aliases.
- **Aliases:** teach the app what players call items ("kumbis" = Kumbi Throwing-Stars)
  in the new **Review → Megaphones** tab. Enter accepts the suggestion, M picks an item,
  Delete marks it as not an item. Older megaphones are updated right away.
- **Edit aliases:** a sheet of aliases (Megaphone term, Alias) to
  type into, from the Megaphones tab or Review → Megaphones. **Refresh** next to it
  matches every megaphone again with the current aliases.
- **Word aliases:** an alias can stand for words instead of an item ("60%" =
  Intermediate, "att" = Attack), so "60% gloves att" matches Gloves Attack Scroll:
  Intermediate without an alias for each scroll. Switch an alias with its Type cell.
  Megaphone items also match when every word of the item's name is there, in any order.
- **Review** now has two tabs: **Shop listings** and **Megaphones**. The Megaphones tab has
  a Buying / Selling column. Shop listings shows the price, shop, player and channel in
  their own columns. "Match" is now "Match manually", and "In the megaphone" is now "Item".
- A megaphone that isn't matched to an item yet shows its message as it was read until
  you match it in Review.
- The Items tab shows the median megaphone selling and buying prices, and the price
  history window has a Megaphones tab.
- **Shared Database:** aliases are shared too, so new players don't have to teach them
  again (needs server 2.2.0).

### Changed
- Megaphones are kept for 72 hours by default (was 24).
- **Scroll as fast as you like.** The screen is captured continuously, like a recording,
  and read at the OCR's own pace, so rows aren't missed when you scroll or hop shops
  quickly. A new **Frames waiting** stat and the status bar show when it's catching up.
  Pressing **Stop** still reads the frames captured just before; press Stop again to
  discard them.

### Fixed
- "Monitoring error: TypeError: startswith…" when opening a shop whose quantity
  ("12 for") wasn't read on a price line.
- "Database is locked" errors while reviewing or scrolling megaphones: working out the
  items in megaphones no longer keeps the database busy while it searches the item list.
- The window no longer freezes while shops are being read or while you search in Items:
  the Deals, Items and Review tables are worked out in the background. The Deals
  checkboxes and the Items filter apply at once.
- Item name matching (Review suggestions, the item search box) is about 4× faster.

Thanks to @GabrielGarciaRivas for these.

## 2610.16.002 — 2026-10-17

### Changed
- **Shared Database:** each time the app connects (or reconnects after being offline),
  it catches up: prices and megaphones logged while you weren't connected are sent, and
  everything on the server is read again, so nothing missed is left out.

## 2610.16.001 — 2026-10-17

### New
- **Shared Database:** share prices with other players through a server one of you runs
  (a Docker container; see `server/README.md`). Everyone connected sees each other's
  sightings and megaphones as they're logged. Only items from the item list are shared.
  Each player signs in with their own user name and password; the app stays signed in.
  A green dot next to the button means it's connected and syncing; red means it isn't.

### Changed
- When a megaphone is read several times with slightly different names or letters, the
  clearest read is kept.

## 2610.15.003 — 2026-10-14

### Changed
- Megaphones with **C/O** count as selling.
- After you pick your channel when the app starts, channel changes aren't detected for
  15 seconds, so closing the game's Change Channel window doesn't ask again.

## 2610.15.002 — 2026-10-14

### Fixed
- Megaphones were listed again as the chat scrolled, when a name was read a little
  differently.
- Player names in megaphones are read more accurately, and match names the app has
  seen before.

### Changed
- Megaphones are kept for 24 hours, then deleted. Set how long in the Megaphones tab.

## 2610.15.001 — 2026-10-14

### New
- **Megaphones in every colour:** pink, teal and yellow megaphones, and the blue ones
  from your own channel (they get the channel from the Channel box).
- Megaphones show in their in-game colour.
- **What the OCR sees** in the Megaphones tab: the chat window, with the megaphones
  being read outlined.

### Fixed
- The chat window wasn't found while you were typing in the chat bar.

## 2610.14.001 — 2026-10-14

### New
- **Megaphones tab:** while monitoring, buying and selling megaphones are read from the
  chat window and listed with their time, player, channel and message: selling on top,
  buying below.
- **Chat area** button, for when the chat window isn't found by itself.
- The channel picker works with the keyboard: arrow keys to move, Enter to pick.

### Changed
- The channel picker shows 20 channels by default again.
- While the channel picker is open, channel changes in the game aren't detected.

## 2610.13.001 — 2026-10-13

### New
- **My Inventory:** a new tab at the far right of the tab row to keep track of the items
  you own and what they're worth.
  - Add items with **Add by name**, or let **Auto Detect (beta)** read your Item
    Inventory window in the game.
  - See each item's market price, price range, recent sales and more.
  - Set a **List price** and **Notes**: click a selected row's cell to edit it.
  - Mark items **Sold** when they sell (or **Unsell** to undo). Sales are added to your
    prices.
  - **Net worth** totals, including listed items value and realized profit, with the 3%
    meso tax taken off.
  - **Export**, **Import** and **Clear My Inventory**.
- **Notes on listings:** right-click a listing → **Add note** for things like +5 ATK.
- **Watched listings:** right-click a listing → **Watch this listing** to get an alert when
  that player's listing is for sale again.

### Changed
- The **Alerts** tab is now **Watched**, with watched items on top and watched listings
  below.
- The channel picker shows 18 channels by default.
- Buttons and menu items no longer end in "…".

## 2610.12.002 — 2026-10-13

### Fixed
- The map wasn't found on some maps, e.g. Victoria Road: Sunset Sky.

## 2610.12.001 — 2026-10-13

### New
- **Channel prompt:** the app asks for your channel when it starts and after you change
  channel in the game. On by default; turn it off in Settings.
- **Channel picker:** the Channel box's arrow opens a grid of channel buttons. Set how many
  it shows in Settings (default 20).
- **Exports include the date and time** in the file name, e.g.
  `mfm-tracker market prices 2026-10-13 08-11-00.csv`.
- Install instructions for the major Linux distributions.

### Changed
- The app is now called **Free Market Tracker**, "Free Market price tracker for MapleStory
  Classic World". Its technical name is `mfm-tracker`; from source, run
  `python mfm-tracker gui`.
- **Capture every** defaults to 0.15 seconds.
- **Required sightings before judging** (was "Outliers: judge after this many sightings")
  now also applies to DEAL / HIGH: an item needs 5 sightings before it gets a market price.
  **Flag DEAL / HIGH** moved under it in Settings.
- From source on Linux, `pynput` is only needed for the `hotkey` command.
- Simpler wording in the app, the README and the changelog.

### Fixed
- Free Market map names were sometimes read as junk.
- Tesseract wasn't found on Void Linux.

## 2610.11.002 — 2026-10-13

### Fixed
- The downloaded apps couldn't connect to meowdb ("certificate verify failed").

## 2610.11.001 — 2026-10-13

### New
- **Items tab filters:** name, category, class, level and "Sold by NPCs".
- **NPC buy** and **NPC sell** prices in the Items tab.
- **Shop** and **Player** are separate columns.
- Maps are saved with their full name, e.g. "Hidden Street: Free Market <2>".
- Wide tables scroll sideways.

### Changed
- A listing's price is the meso amount shown; "699 for" quantities are ignored.
- Column headers are **Price** and **Max price**.

### Fixed
- Some map names were misread or cut short.
- Required level 0 showed as unknown.

### Upgrading
The first start converts saved prices and map names, and offers to re-download the item
and map lists once.

## 2610.7.001 — 2026-10-12

First release: Windows, macOS (Apple silicon) and Linux apps.
