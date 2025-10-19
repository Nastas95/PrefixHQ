#!/usr/bin/env python3
import os
import re
import json
import shutil
import requests
os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QMessageBox, QInputDialog
)

# Paths
STEAM_APPS = Path.home() / ".local/share/Steam/steamapps"
COMPATDATA = STEAM_APPS / "compatdata"
STEAM_API = "https://store.steampowered.com/api/appdetails"

# Local DB
CONFIG_DIR = Path.home() / ".config/PrefixHQ"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = CONFIG_DIR / "games.json"

def load_local_db():
    if DB_FILE.exists():
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"installed_games": {}, "custom_names": {}}

def save_local_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Steam runtimes / redistributables to ignore
IGNORE_APPIDS = {
    "1070560", "228980", "1391110", "1628350", "0"
}

def get_installed_games():
    games = {}
    for acf_file in STEAM_APPS.glob("*.acf"):
        try:
            with open(acf_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                appid_match = re.search(r'"appid"\s+"(\d+)"', content)
                if appid_match:
                    appid = appid_match.group(1)
                    if appid in IGNORE_APPIDS:
                        continue
                    name_match = re.search(r'"name"\s+"([^"]+)"', content)
                    name = name_match.group(1) if name_match else f"(AppID {appid})"
                    games[appid] = name
        except Exception as e:
            print(f"Error reading {acf_file}: {e}")
    return games

def get_game_name(appid):
    try:
        appid_str = str(int(appid))
        resp = requests.get(STEAM_API, params={"appids": appid_str}, timeout=5)
        data = resp.json()
        info = data.get(appid_str)
        if info and info.get("success") and "data" in info:
            return info["data"].get("name", f"(AppID {appid_str})")
    except Exception:
        pass
    return f"(AppID {appid})"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrefixHQ")
        self.setGeometry(100, 100, 600, 800)

        central = QWidget()
        self.layout = QVBoxLayout()
        central.setLayout(self.layout)
        self.setCentralWidget(central)

        # Log area
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.layout.addWidget(self.log_window)

        # Table for orphan prefixes
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Prefix AppID", "Game Name"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        self.layout.addWidget(self.table)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_open = QPushButton("Open Directory")
        self.btn_open.clicked.connect(self.open_selected)
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_rename = QPushButton("Rename Game")
        self.btn_rename.clicked.connect(self.rename_game)
        self.btn_quit = QPushButton("Quit")
        self.btn_quit.clicked.connect(self.close)

        for btn in [self.btn_delete, self.btn_open, self.btn_refresh, self.btn_rename, self.btn_quit]:
            buttons_layout.addWidget(btn)
        self.layout.addLayout(buttons_layout)

        # Load DB
        self.db = load_local_db()
        self.installed_games = get_installed_games()
        self.db["installed_games"].update(self.installed_games)
        save_local_db(self.db)

        self.show_initial_state()

    def show_initial_state(self):
        self.log_window.clear()
        self.log(f"Found {len(self.installed_games)} installed Steam games:", color="green")
        for appid, name in self.installed_games.items():
            display_name = self.db["custom_names"].get(appid, name)
            self.log(f'<span style="color:yellow">{display_name}</span> (AppID {appid})')
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        if not COMPATDATA.exists():
            self.log(f"❌ Path not found: {COMPATDATA}", color="red")
            return
        row = 0
        for dir_entry in COMPATDATA.iterdir():
            if not dir_entry.is_dir():
                continue
            appid = dir_entry.name
            if not appid.isdigit():
                continue
            if appid in self.installed_games or appid in IGNORE_APPIDS:
                continue

            game_name = self.db["custom_names"].get(appid, get_game_name(appid))

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(appid))
            self.table.setItem(row, 1, QTableWidgetItem(game_name))
            row += 1
        self.log("")
        self.log(f"Found {row} orphaned prefixes:", color="red")

    def refresh(self):
        self.installed_games = get_installed_games()
        self.db["installed_games"].update(self.installed_games)
        save_local_db(self.db)
        self.show_initial_state()
        self.log("Refresh completed.", color="green")

    def get_selected_rows(self):
        return [index.row() for index in self.table.selectionModel().selectedRows()]

    def delete_selected(self):
        rows = self.get_selected_rows()
        if not rows:
            self.log("No prefixes selected.", color="red")
            return
        non_steam_selected = any(
            self.table.item(row, 0).text() not in self.installed_games
            for row in rows
        )
        if non_steam_selected:
            reply = QMessageBox.question(
                self,
                "⚠️⚠️⚠️ WARNING ⚠️⚠️⚠️",
                ("Some of the selected prefixes are associated with "
                "<b><span style='color:red'>non-Steam programs</span></b> and may contain "
                "<b>important files (like saves or configuration)</b>. "
                "These programs may still be installed on your system! "
                "Are you sure you want to <b>delete them?</b> <br> <br>"
                "⚠️⚠️⚠️ <b><span style='color:red'>This action is irreversible </span></b>⚠️⚠️⚠️"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self.log("Deletion cancelled by user.", color="yellow")
                return
        for row in reversed(rows):
            appid_item = self.table.item(row, 0)
            if not appid_item:
                continue
            appid = appid_item.text()
            path = COMPATDATA / appid
            try:
                shutil.rmtree(path)
                self.log(f"✅ Deleted: {path}", color="green")
                self.table.removeRow(row)
            except Exception as e:
                self.log(f"❌ Error deleting {path}: {e}", color="red")

    def open_selected(self):
        rows = self.get_selected_rows()
        if not rows:
            self.log("No prefixes selected to open.", color="yellow")
            return
        for row in rows:
            path = COMPATDATA / self.table.item(row, 0).text()
            subprocess.Popen(["xdg-open", str(path)])
            self.log(f"📂 Opened directory: {path}", color="yellow")

    def rename_game(self):
        rows = self.get_selected_rows()
        if len(rows) != 1:
            self.log("You can only rename one prefix at a time.", color="red")
            return
        row = rows[0]
        appid = self.table.item(row, 0).text()
        current_name = self.table.item(row, 1).text()
        new_name, ok = QInputDialog.getText(self, "Rename Game", f"Enter new name for {current_name}:", text=current_name)
        if ok and new_name.strip():
            self.db["custom_names"][appid] = new_name.strip()
            save_local_db(self.db)
            self.table.setItem(row, 1, QTableWidgetItem(new_name.strip()))
            self.log(f"Game {appid} renamed to '{new_name.strip()}'", color="green")

    def log(self, message, color=None):
        if color:
            self.log_window.append(f'<span style="color:{color}">{message}</span>')
            self.log_window.append("")
        else:
            self.log_window.append(message)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
