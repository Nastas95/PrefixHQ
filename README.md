# PrefixHQ

**PrefixHQ** is a Linux GUI tool for managing Steam Proton/Wine prefixes. It helps identify and handle orphaned or leftover prefixes, making it easy to clean up your system and manage game configurations.

## Features

* **Scan Installed Games:** Automatically detects installed Steam games.
* **Orphan Prefix Management:** Lists prefixes in `~/.local/share/Steam/steamapps/compatdata` that no longer correspond to installed games.
* **Safe Deletion:** Delete selected prefixes with warnings for non-Steam programs to prevent accidental data loss.
* **Open Prefix Directory:** Quickly open a prefix folder in your file manager.
* **Rename Games:** Customize display names for games or prefixes.
* **Local Database:** Stores installed games and custom names in `~/.config/PrefixHQ/games.json` for faster access.

## Installation

1. Download the latest precompiled binary from the [Releases](https://github.com/Nastas95/PrefixHQ/releases) page.
2. Run it!

## Requirements

* Linux with Steam installed
* No need to install Python or dependencies — all required libraries are bundled in the binary
* - (*Optional*) Internet connection (**upon launch PrefixHQ tries to download the Steam appID from [this source](https://store.steampowered.com/api/appdetails) and save it to the config folder**)

## Notes

* Uses `~/.local/share/Steam/steamapps/compatdata` to detect Proton/Wine prefixes.
* Stores configuration in `~/.config/PrefixHQ/`.
* Safe for managing Steam prefixes, but deletion of non-Steam prefixes may remove important files — proceed with caution.
