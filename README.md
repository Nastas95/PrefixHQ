# PrefixHQ

![Linux](https://img.shields.io/badge/Platform-Linux-%23FCC624?logo=linux)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg?logo=gnu)

A modern, visual manager for Steam CompatData (Proton/Wine prefixes) on Linux.  
Transform your folder structure into a beautiful game library with automatic cover art and multi-library awareness.

---

## ✨ Features

### 🖼️ Visual Game Library
- **Responsive Grid Layout** – Card-based interface with high-quality Steam cover art
- **Automatic Cover Downloads** – Fetches official header images from Steam API
- **Local Image Caching** – Saves covers to `~/.config/PrefixHQ/cache/` for instant reloads
- **Custom Cover Support** – Override covers via URL, local file, or SteamGridDB search

### 📚 Multi-Library Awareness
- **Automatic Library Detection** – Parses `libraryfolders.vdf` to discover *all* Steam libraries (primary + secondary drives, external SSDs)
- **Cross-Library Matching** – Correctly pairs prefixes with game names even when game files reside in a different library
- **Installation Status Tracking** – Visual indicators distinguish installed vs. orphaned prefixes:
  - ✅ **Green** = Game currently installed
  - ⚠️ **Red** = Prefix orphaned (game uninstalled)

### ⚙️ Universal Compatibility
- Works out-of-the-box with:
  - Native Steam (`~/.steam/steam`)
  - Flatpak (`~/.var/app/com.valvesoftware.Steam/`)
  - Snap (`~/snap/steam/common/`)

### ⚡ Performance & Safety
- **Background Scanning** – Async prefix detection via `QThread` (no UI freezing)
- **Smart Deduplication** – Handles edge cases where same AppID appears across libraries
- **Permission-Aware** – Skips unreadable directories gracefully
- **Safe Deletion** – Confirmation dialogs before removing prefixes

### 🖱️ Context Menu Actions (Right-Click)
- `Open Prefix Folder` – Jump directly to `compatdada` directory
- `Search on SteamGridDB` – Find community artwork alternatives
- `Load Cover from File...` – Use local image
- `Load Cover from URL...` – Fetch custom cover from web
- `Mark as Installed/Uninstalled` – Override detection status manually

---

## 🛠️ Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux |
| **Python** | 3.8+ |
| **Dependencies** | `PyQt6>=6.4.0`, `requests>=2.28.0` |

> 💡 All other dependencies (`os`, `sys`, `json`, `pathlib`, etc.) are part of Python's standard library.

---

## 🚀 Installation & Usage


### Option 1: Binary Releases
Download the latest Binary from the [Releases Page](https://github.com/yourusername/PrefixHQ/releases).


### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/Nastas95/PrefixHQ
cd PrefixHQ

# Install dependencies
pip install -r requirements.txt

# Launch the application
python PrefixHQ.py
```

---

## 🎮 How It Works

1. **Scanning**  
   On launch, PrefixHQ scans all Steam installations (Native/Flatpak/Snap) and parses `libraryfolders.vdf` to discover every library location.

2. **Matching**  
   Scans `steamapps/compatdata/` folders and matches AppID-named directories to installed games using:
   - Local `.acf` manifest files (primary method)
   - Steam API fallback (if needed)

3. **Visualizing**  
   Presents prefixes as visual cards with:
   - Game cover art
   - AppID and custom name
   - Status indicator (installed vs. uninstalled)

4. **Cleaning**  
   Safely delete orphaned prefixes to reclaim disk space — with confirmation dialogs to prevent accidents.

---

## ⚙️ Configuration & Data Storage

All data is stored locally under `~/.config/PrefixHQ/`:

| File/Folder | Purpose |
|-------------|---------|
| `prefix_db.json` | Database storing custom names, manual status overrides, and API cache |
| `cache/` | Local storage for downloaded cover art (avoids repeated API calls) |

> 🔁 First launch may take 10–30 seconds while cover art downloads. Subsequent launches are instant thanks to caching.

---

## ⚠️ Important Warning

> [!WARNING]
> **Deleting a prefix permanently removes all data inside that Proton container**, including:
> - Windows game saves
> - Configuration files
> - Installed mods and custom content
>
> **Always verify** a prefix is truly orphaned before deletion. When in doubt, back up the folder first.

---

## 📝 License

Distributed under the **GNU General Public License v3.0**

See [`LICENSE`](LICENSE) for the full license text.
