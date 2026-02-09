#!/usr/bin/env python3
import sys
import os
import shutil
import json
import subprocess
import platform
import requests
import re
import struct
import zlib
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QInputDialog, QProgressBar,
    QScrollArea, QFrame, QLineEdit, QLayout, QSizePolicy, QMenu, QStyle,
    QFileDialog, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QRect, QTimer, QUrl
from PyQt6.QtGui import QIcon, QColor, QBrush, QPixmap, QAction, QPainter, QPainterPath, QDesktopServices, QCursor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# --- CRITICAL CONFIGURATION ---
os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"

# --- CONSTANTS ---
def find_steam_root():
    candidates = [
        Path.home() / ".steam" / "steam",
        Path.home() / ".local" / "share" / "Steam",
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        Path.home() / "snap" / "steam" / "common" / ".steam" / "steam",
    ]

    for path in candidates:
        if path.exists() and (path / "steamapps" / "libraryfolders.vdf").exists():
            return path.resolve()
    return Path.home() / ".local" / "share" / "Steam"

STEAM_BASE = find_steam_root()
STEAM_APPS = STEAM_BASE / "steamapps"
COMPATDATA = STEAM_APPS / "compatdata"
STEAM_API_URL = "https://store.steampowered.com/api/appdetails"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/?term={term}&l=english&cc=US"
STEAM_IMG_URL = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
STEAMGRIDDB_SEARCH_URL = "https://www.steamgriddb.com/search/grids?term={term}"

CONFIG_DIR = Path.home() / ".config/PrefixHQ"
DB_FILE = CONFIG_DIR / "prefix_db.json"
IMG_CACHE_DIR = CONFIG_DIR / "cache"

IGNORE_APPIDS = {"0", "228980", "1070560", "1391110", "1628350"}

# --- STYLESHEET ---
DARK_THEME = """
QMainWindow {
    background-color: #1b2838;
}
QWidget {
    color: #c7d5e0;
    font-family: 'Segoe UI', sans-serif;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background: #171a21;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #3d4450;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QLineEdit {
    background-color: #2a475e;
    border: 1px solid #171a21;
    border-radius: 4px;
    padding: 8px;
    color: white;
    font-size: 14px;
}
QLineEdit:focus {
    border: 1px solid #66c0f4;
}
QPushButton {
    background-color: #2a475e;
    color: white;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #66c0f4;
    color: #171a21;
}
QPushButton:pressed {
    background-color: #193144;
}
QPushButton#DeleteBtn {
    background-color: #3b2020;
    color: #ff6666;
}
QPushButton#DeleteBtn:hover {
    background-color: #d9534f;
    color: white;
}
QPushButton#LinkBtn {
    background-color: transparent;
    color: #66c0f4;
    text-align: left;
    padding: 0px;
}
QPushButton#LinkBtn:hover {
    text-decoration: underline;
    background-color: transparent;
}
QPushButton#ExitBtn {
    background-color: #3b2020;
    color: #ff6666;
    padding: 6px 16px;
    font-weight: bold;
    min-width: 80px;
    border-radius: 4px;
}
QPushButton#ExitBtn:hover {
    background-color: #d9534f;
    color: white;
}
/* Game Card Styling (Grid) */
QFrame#GameCard {
    background-color: #171a21;
    border-radius: 8px;
}
QFrame#GameCard:hover {
    background-color: #222630;
}
/* Game List Item Styling (List) */
QFrame#GameListItem {
    background-color: #171a21;
    border-radius: 4px;
    margin-bottom: 2px;
}
QFrame#GameListItem:hover {
    background-color: #222630;
}
QLabel#CardTitle {
    font-size: 13px;
    font-weight: bold;
    color: white;
}
QLabel#CardStatus {
    font-size: 10px;
    color: #8f98a0;
}
QLabel#StatusFooter {
    font-size: 12px;
    color: #8f98a0;
    font-weight: bold;
}
/* Dialogs */
QDialog {
    background-color: #1b2838;
}
"""

class DataManager:
    @staticmethod
    def init_storage():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        IMG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not DB_FILE.exists():
            DataManager.save_db({"custom_names": {}, "custom_status": {}, "api_cache": {}})

    @staticmethod
    def load_db():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"custom_names": {}, "custom_status": {}, "api_cache": {}}

    @staticmethod
    def save_db(data):
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving DB: {e}")

    @staticmethod
    def get_steam_libraries():
        libraries = []
        if STEAM_BASE.exists():
            libraries.append(STEAM_BASE)

        vdf_path = STEAM_APPS / "libraryfolders.vdf"
        if vdf_path.exists():
            try:
                with open(vdf_path, "r", encoding="utf-8") as f:
                    content = f.read()
                matches = re.findall(r'"path"\s+"(.*?)"', content)
                for path_str in matches:
                    path_str = path_str.replace("\\\\", "\\")
                    lib_path = Path(path_str)

                    if lib_path.exists() and lib_path not in libraries:
                        libraries.append(lib_path)
            except Exception as e:
                print(f"Error parsing libraryfolders.vdf: {e}")

        return libraries

class NonSteamManager:
    @staticmethod
    def get_non_steam_ids(steam_root):
        mapping = {}
        userdata = steam_root / "userdata"
        if not userdata.exists():
            return mapping

        print(f"DEBUG: Checking userdata in {userdata}")

        for user_dir in userdata.iterdir():
            shortcuts_path = user_dir / "config" / "shortcuts.vdf"
            if shortcuts_path.exists():
                print(f"DEBUG: Found shortcuts.vdf at {shortcuts_path}")
                try:
                    with open(shortcuts_path, "rb") as f:
                        data = f.read()

                    items = NonSteamManager.parse_binary_vdf(data)
                    print(f"DEBUG: Parsed {len(items)} items from VDF")

                    for item in items:
                        app_name = item.get("AppName", "")
                        exe_path = item.get("Exe", "")

                        raw_id = item.get("appid")
                        if raw_id is not None:
                            generated_id = raw_id & 0xffffffff
                            mapping[str(generated_id)] = app_name
                            print(f"DEBUG: Mapped (Explicit) {generated_id} -> {app_name}")

                        if app_name and exe_path:
                            crc_input = (exe_path + app_name).encode("utf-8")
                            crc = zlib.crc32(crc_input) & 0xffffffff
                            gen_id = crc | 0x80000000
                            mapping[str(gen_id)] = app_name

                            print(f"DEBUG: Mapped (Calculated) {gen_id} -> {app_name}")

                except Exception as e:
                    print(f"Error parsing shortcuts.vdf at {shortcuts_path}: {e}")
        return mapping

    @staticmethod
    def parse_binary_vdf(data):

        def read_string(d, p):
            end = d.find(b'\x00', p)
            if end == -1: raise ValueError("Unterminated string")
            s = d[p:end].decode('utf-8', 'replace')
            return s, end + 1

        def parse_map(d, p):
            res = {}
            while p < len(d):
                type_byte = d[p]
                p += 1

                if type_byte == 0x08:
                    return res, p

                if p >= len(d): break

                try:
                    key, p = read_string(d, p)
                except ValueError:
                    break

                if type_byte == 0x00:
                    sub_map, p = parse_map(d, p)
                    res[key] = sub_map
                elif type_byte == 0x01:
                    val, p = read_string(d, p)
                    res[key] = val
                elif type_byte == 0x02:
                    if p + 4 > len(d): break
                    val = struct.unpack('<I', d[p:p+4])[0] # Unsigned
                    p += 4
                    res[key] = val
                else:
                    print(f"DEBUG: Unknown type {hex(type_byte)} at {p-1}")
                    break
            return res, p

        items = []
        ptr = 0

        if len(data) > 0:
            try:
                if data[ptr] == 0x00:
                    ptr += 1
                    key, ptr = read_string(data, ptr)
                    if key == "shortcuts":
                        root_map, ptr = parse_map(data, ptr)
                        for k, v in root_map.items():
                            if isinstance(v, dict):
                                items.append(v)
                        return items
            except:
                ptr = 0
            try:
                root_map, ptr = parse_map(data, 0)
                for k, v in root_map.items():
                    if isinstance(v, dict):
                        items.append(v)
            except Exception as e:
                print(f"DEBUG: Fallback parse failed: {e}")

        return items

class SystemUtils:
    @staticmethod
    def _get_clean_environment():
        clean_env = os.environ.copy()
        vars_to_remove = [
            "LD_LIBRARY_PATH", "OPENSSL_MODULES", "OPENSSL_CONF",
            "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
            "QML2_IMPORT_PATH", "QML_IMPORT_PATH", "PYTHONPATH",
            "XDG_DATA_DIRS", "XDG_CONFIG_DIRS"
        ]
        for var in vars_to_remove:
            clean_env.pop(var, None)

        if "_MEIPASS" in clean_env:
            meipass = clean_env["_MEIPASS"]
            keys_to_remove = [k for k, v in clean_env.items() if meipass in str(v)]
            for k in keys_to_remove:
                clean_env.pop(k, None)

        clean_env["QT_QPA_PLATFORM"] = "xcb"
        clean_env.pop("QTWEBENGINEPROCESS_PATH", None)
        return clean_env

    @staticmethod
    def get_default_file_manager():
        try:
            cmd = ["xdg-mime", "query", "default", "inode/directory"]
            result = subprocess.check_output(cmd).decode().strip()
            if result:
                if "nautilus" in result.lower(): return "nautilus"
                if "dolphin" in result.lower(): return "dolphin"
                if "nemo" in result.lower(): return "nemo"
                if "thunar" in result.lower(): return "thunar"
                if "pcmanfm" in result.lower(): return "pcmanfm"
        except Exception:
            pass
        common_fms = ["dolphin", "nautilus", "nemo", "thunar", "pcmanfm", "caja"]
        for fm in common_fms:
            if shutil.which(fm): return fm
        return None

    @staticmethod
    def open_with_file_manager(path):
        path = str(path)
        if not os.path.exists(path):
            return False

        clean_env = SystemUtils._get_clean_environment()
        fm = SystemUtils.get_default_file_manager()

        if fm:
            try:
                subprocess.Popen([fm, path], env=clean_env)
                return True
            except:
                pass

        try:
            subprocess.Popen(["xdg-open", path], env=clean_env)
            return True
        except:
            return False

    @staticmethod
    def open_url(url):
        if not getattr(sys, 'frozen', False):
            QDesktopServices.openUrl(QUrl(url))
            return True

        clean_env = SystemUtils._get_clean_environment()
        system = platform.system()

        try:
            if system == 'Linux':
                subprocess.Popen(['xdg-open', url], env=clean_env)
            elif system == 'Darwin':
                subprocess.Popen(['open', url], env=clean_env)
            elif system == 'Windows':
                subprocess.Popen(['cmd', '/c', 'start', '', url],
                               env=clean_env,
                               shell=False,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(['xdg-open', url], env=clean_env)
            return True
        except Exception as e:
            print(f"Error opening URL '{url}': {e}")
            return False

# --- CUSTOM LAYOUT ---
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, h_spacing=10, v_spacing=10):
        super().__init__(parent)
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.items = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        return size

    def do_layout(self, rect, test_only):
        x, y = rect.x(), rect.y()
        line_height = 0

        for item in self.items:
            wid = item.widget()
            space_x = self.h_spacing
            space_y = self.v_spacing

            if wid and not wid.isVisible():
                continue

            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

# --- CUSTOM WIDGETS ---
class CoverDownloadDialog(QDialog):
    def __init__(self, game_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Cover Art")
        self.setFixedWidth(450)
        self.game_name = game_name

        layout = QVBoxLayout(self)

        # Instruction
        layout.addWidget(QLabel(f"Enter direct image URL for: <b>{game_name}</b>"))

        # Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/image.jpg")
        layout.addWidget(self.url_input)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_url(self):
        return self.url_input.text().strip()

# --- MIXIN FOR CONTEXT MENU (Shared between Grid and List) ---
class GameCardMixin:
    def show_context_menu_common(self, pos):
        menu = QMenu(self)

        action_sgdb = QAction("Search on SteamGridDB", self)
        action_sgdb.triggered.connect(
            lambda: SystemUtils.open_url(STEAMGRIDDB_SEARCH_URL.format(term=self.data["name"]))
        )

        action_local = QAction("Load Cover from File...", self)
        action_local.triggered.connect(lambda: self.window().action_set_cover_local(self.data))

        action_url = QAction("Load Cover from URL...", self)
        action_url.triggered.connect(lambda: self.window().action_set_cover_url(self.data))

        menu.addAction(action_sgdb)
        menu.addSeparator()
        menu.addAction(action_local)
        menu.addAction(action_url)
        menu.addSeparator()

        toggle_text = "Mark as Uninstalled" if self.data["is_installed"] else "Mark as Installed"
        action_toggle = QAction(toggle_text, self)
        action_toggle.triggered.connect(lambda: self.window().action_toggle_status(self.data))
        menu.addAction(action_toggle)

        menu.exec(self.mapToGlobal(pos))

class GameCard(QFrame, GameCardMixin):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setObjectName("GameCard")
        self.setFixedSize(220, 200)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu_common)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.img_label = QLabel()
        self.img_label.setFixedHeight(105)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background-color: #0d1015; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        self.img_label.setScaledContents(True)
        layout.addWidget(self.img_label)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 8, 10, 8)
        content_layout.setSpacing(4)

        self.title_lbl = QLabel(data["name"])
        self.title_lbl.setObjectName("CardTitle")
        self.title_lbl.setWordWrap(False)
        content_layout.addWidget(self.title_lbl)

        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("CardStatus")
        self.update_status_display()
        content_layout.addWidget(self.status_lbl)

        content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        self.setup_buttons(btn_layout)
        content_layout.addLayout(btn_layout)
        layout.addWidget(content_widget)

    def setup_buttons(self, layout):
        style = QApplication.style()

        btn_open = QPushButton()
        btn_open.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        btn_open.setToolTip("Open Directory")
        btn_open.clicked.connect(lambda: self.window().action_open(self.data))

        btn_rename = QPushButton()
        icon_edit = QIcon.fromTheme("document-edit")
        if icon_edit.isNull():
            icon_edit = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        btn_rename.setIcon(icon_edit)
        btn_rename.setToolTip("Rename")
        btn_rename.clicked.connect(lambda: self.window().action_rename(self.data))

        btn_delete = QPushButton()
        btn_delete.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        btn_delete.setObjectName("DeleteBtn")
        btn_delete.setToolTip("Delete Prefix")
        btn_delete.clicked.connect(lambda: self.window().action_delete(self.data))

        layout.addWidget(btn_open)
        layout.addWidget(btn_rename)
        layout.addWidget(btn_delete)

    def update_status_display(self):
        status_text = "Installed" if self.data["is_installed"] else "Uninstalled"
        status_color = "#a3cf06" if self.data["is_installed"] else "#d9534f"
        self.status_lbl.setText(f"{status_text} • ID: {self.data['appid']}")
        self.status_lbl.setStyleSheet(f"color: {status_color};")

    def update_image(self, pixmap):
        self.img_label.setPixmap(pixmap)

class GameListItem(QFrame, GameCardMixin):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setObjectName("GameListItem")
        self.setFixedHeight(60)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu_common)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 10, 5)
        layout.setSpacing(15)

        # Image (Small on left)
        self.img_label = QLabel()
        self.img_label.setFixedSize(100, 50)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background-color: #0d1015; border-radius: 4px;")
        self.img_label.setScaledContents(True)
        layout.addWidget(self.img_label)

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 5, 0, 5)

        self.title_lbl = QLabel(data["name"])
        self.title_lbl.setObjectName("CardTitle")
        info_layout.addWidget(self.title_lbl)

        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("CardStatus")
        self.update_status_display()
        info_layout.addWidget(self.status_lbl)

        layout.addLayout(info_layout, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        self.setup_buttons(btn_layout)
        layout.addLayout(btn_layout)

    def setup_buttons(self, layout):
        style = QApplication.style()

        btn_open = QPushButton()
        btn_open.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        btn_open.setToolTip("Open Directory")
        btn_open.clicked.connect(lambda: self.window().action_open(self.data))

        btn_rename = QPushButton()
        icon_edit = QIcon.fromTheme("document-edit")
        if icon_edit.isNull():
            icon_edit = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        btn_rename.setIcon(icon_edit)
        btn_rename.setToolTip("Rename")
        btn_rename.clicked.connect(lambda: self.window().action_rename(self.data))

        btn_delete = QPushButton()
        btn_delete.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        btn_delete.setObjectName("DeleteBtn")
        btn_delete.setToolTip("Delete Prefix")
        btn_delete.clicked.connect(lambda: self.window().action_delete(self.data))

        layout.addWidget(btn_open)
        layout.addWidget(btn_rename)
        layout.addWidget(btn_delete)

    def update_status_display(self):
        status_text = "Installed" if self.data["is_installed"] else "Uninstalled"
        status_color = "#a3cf06" if self.data["is_installed"] else "#d9534f"
        self.status_lbl.setText(f"{status_text} • ID: {self.data['appid']}")
        self.status_lbl.setStyleSheet(f"color: {status_color};")

    def update_image(self, pixmap):
        self.img_label.setPixmap(pixmap)

class ScanWorker(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def run(self):
        self.progress.emit("Loading DB...")
        db = DataManager.load_db()
        custom_names = db.get("custom_names", {})
        custom_status = db.get("custom_status", {})
        api_cache = db.get("api_cache", {})

        installed_games = {}
        prefixes = []

        libraries = DataManager.get_steam_libraries()
        total_libs = len(libraries)

        # Pre-load non-steam games mapping
        self.progress.emit("Parsing Non-Steam shortcuts...")
        non_steam_games = NonSteamManager.get_non_steam_ids(STEAM_BASE)

        self.progress.emit("Scanning manifest files...")
        for lib_path in libraries:
            apps_path = lib_path / "steamapps"
            if apps_path.exists():
                for acf in apps_path.glob("*.acf"):
                    try:
                        content = acf.read_text(encoding="utf-8", errors="ignore")
                        aid_match = re.search(r'"appid"\s+"(\d+)"', content)
                        name_match = re.search(r'"name"\s+"([^"]+)"', content)
                        if aid_match:
                            appid = aid_match.group(1)
                            name = name_match.group(1) if name_match else f"AppID {appid}"
                            installed_games[appid] = name
                    except: continue

        for idx, lib_path in enumerate(libraries):
            self.progress.emit(f"Scanning Library {idx + 1}/{total_libs}: {lib_path.name}")

            compatdata_path = lib_path / "steamapps" / "compatdata"

            if not compatdata_path.exists():
                continue

            if not os.access(compatdata_path, os.R_OK | os.X_OK):
                continue

            try:
                dirs = [d for d in compatdata_path.iterdir() if d.is_dir() and d.name.isdigit()]

                for d in dirs:
                    appid = d.name
                    if appid in IGNORE_APPIDS: continue

                    if not os.access(d, os.R_OK):
                        continue

                    display_name = "Unknown"
                    is_installed = False

                    if appid in custom_status:
                        is_installed = custom_status[appid]
                    elif appid in installed_games:
                        is_installed = True
                    elif appid in non_steam_games:
                        is_installed = True

                    status = "Installed" if is_installed else "Uninstalled"

                    if appid in custom_names:
                        display_name = custom_names[appid]
                    elif appid in installed_games:
                        display_name = installed_games[appid]
                    elif appid in non_steam_games:
                        display_name = non_steam_games[appid]
                    elif appid in api_cache:
                        display_name = api_cache[appid]
                    else:
                        fetched = self.fetch_steam_name(appid)
                        display_name = fetched
                        if "AppID" not in fetched:
                            api_cache[appid] = fetched

                    prefixes.append({
                        "appid": appid,
                        "name": display_name,
                        "path": str(d),
                        "status": status,
                        "is_installed": is_installed
                    })
            except Exception as e:
                print(f"Error scanning {compatdata_path}: {e}")

        db["api_cache"] = api_cache
        DataManager.save_db(db)

        unique_prefixes = {}
        for p in prefixes:
            aid = p["appid"]
            if aid not in unique_prefixes:
                unique_prefixes[aid] = p
            else:
                if p["is_installed"] and not unique_prefixes[aid]["is_installed"]:
                    unique_prefixes[aid] = p

        final_list = list(unique_prefixes.values())
        final_list.sort(key=lambda x: (not x["is_installed"], x["name"].lower()))
        self.finished.emit(final_list)

    def fetch_steam_name(self, appid):
        try:
            resp = requests.get(STEAM_API_URL, params={"appids": appid}, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                if data.get(appid, {}).get("success"):
                    return data[appid]["data"]["name"]
        except: pass
        return f"AppID {appid}"

class MainWindow(QMainWindow):
    REQ_TYPE_IMAGE = 1
    REQ_TYPE_SEARCH = 2
    REQ_TYPE_FALLBACK = 3
    REQ_TYPE_MANUAL_URL = 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrefixHQ")
        self.resize(1000, 700)
        self.setStyleSheet(DARK_THEME)
        DataManager.init_storage()

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_network_finished)

        self.cards = {}
        self.all_prefixes = []

        # Load view mode preference
        db = DataManager.load_db()
        self.view_mode = db.get("view_mode", "grid") # Default to grid

        self.active_downloads = set()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 10)

        self.setup_header()

        # Scroll Area Placeholder
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area, 1)

        # Initial layout setup
        self.setup_view_container()

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { height: 4px; border: none; background: #171a21; } QProgressBar::chunk { background: #66c0f4; }")
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # --- FOOTER ---
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 5, 0, 0)
        footer_layout.setSpacing(10)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusFooter")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("ExitBtn")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(self.close_application)
        footer_layout.addWidget(self.exit_btn)
        self.main_layout.addWidget(footer_widget)

        self.refresh_data()

    def close_application(self):
        if self.active_downloads:
            reply = QMessageBox.question(
                self, "Confirm Exit", "Image downloads are still in progress. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No: return

        if hasattr(self, 'worker') and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit", "Prefix scan is still in progress. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No: return

        QApplication.quit()

    def setup_header(self):
        header = QHBoxLayout()

        title = QLabel("STEAM PREFIXES")
        title.setStyleSheet("font-size: 24px; font-weight: 900; letter-spacing: 1px; color: #66c0f4;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_grid)

        self.btn_toggle_view = QPushButton()
        self.btn_toggle_view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_toggle_btn_icon()
        self.btn_toggle_view.setToolTip("Toggle Grid/List View")
        self.btn_toggle_view.clicked.connect(self.toggle_view)

        self.btn_refresh = QPushButton("REFRESH")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)

        self.btn_open_config = QPushButton("OPEN CONFIG")
        self.btn_open_config.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_config.clicked.connect(lambda: SystemUtils.open_with_file_manager(CONFIG_DIR))

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.search_input)
        header.addWidget(self.btn_toggle_view)
        header.addWidget(self.btn_open_config)
        header.addWidget(self.btn_refresh)

        self.main_layout.addLayout(header)

    def update_toggle_btn_icon(self):
        style = QApplication.style()
        if self.view_mode == "grid":
            icon = QIcon.fromTheme("view-list")
            if icon.isNull():
                icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)
            self.btn_toggle_view.setIcon(icon)
        else:
            icon = QIcon.fromTheme("view-grid")
            if icon.isNull():
                icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
            self.btn_toggle_view.setIcon(icon)

    def toggle_view(self):
        self.view_mode = "list" if self.view_mode == "grid" else "grid"

        # Save view mode to DB
        db = DataManager.load_db()
        db["view_mode"] = self.view_mode
        DataManager.save_db(db)

        self.update_toggle_btn_icon()
        self.setup_view_container()
        self.populate_view()

    def setup_view_container(self):
        self.scroll_content = QWidget()

        if self.view_mode == "grid":
            self.layout_container = FlowLayout(self.scroll_content, margin=0, h_spacing=15, v_spacing=15)
        else:
            self.layout_container = QVBoxLayout(self.scroll_content)
            self.layout_container.setSpacing(5)
            self.layout_container.setContentsMargins(5, 5, 5, 5)
            self.layout_container.addStretch() # Push items to top

        self.scroll_content.setLayout(self.layout_container)
        self.scroll_area.setWidget(self.scroll_content)

    def refresh_data(self):
        self.btn_refresh.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.worker = ScanWorker()
        self.worker.progress.connect(lambda s: self.status_label.setText(s))
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()

    def on_scan_finished(self, prefixes):
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Found {len(prefixes)} prefixes.")
        self.all_prefixes = prefixes
        self.populate_view()

    def populate_view(self):
        self.cards = {}

        if self.layout_container:
            while self.layout_container.count():
                item = self.layout_container.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        for p in self.all_prefixes:
            if self.view_mode == "grid":
                widget = GameCard(p, self)
            else:
                widget = GameListItem(p, self)

            self.layout_container.addWidget(widget)
            self.cards[p["appid"]] = widget
            self.load_image(p["appid"], p["name"])

        if self.view_mode == "list":
            self.layout_container.addStretch()

        self.filter_grid(self.search_input.text())

    def filter_grid(self, text):
        text = text.lower()
        visible_count = 0
        for appid, card in self.cards.items():
            match = text in card.data["name"].lower() or text in str(appid)
            card.setVisible(match)
            if match: visible_count += 1

        if self.view_mode == "grid":
            self.scroll_content.adjustSize()

    # --- IMAGE HANDLING ---
    def load_image(self, appid, name):
        cache_path = IMG_CACHE_DIR / f"{appid}.jpg"

        if cache_path.exists():
            pix = QPixmap(str(cache_path))
            if not pix.isNull():
                if appid in self.cards:
                    self.cards[appid].update_image(pix)
                return

        if appid in self.active_downloads: return

        url = STEAM_IMG_URL.format(appid=appid)
        req = QNetworkRequest(QUrl(url))
        data = {
            "appid": appid,
            "name": name,
            "req_type": self.REQ_TYPE_IMAGE
        }
        req.setAttribute(QNetworkRequest.Attribute.User, data)
        self.nam.get(req)
        self.active_downloads.add(appid)

    def on_network_finished(self, reply):
        user_data = reply.request().attribute(QNetworkRequest.Attribute.User)
        if not isinstance(user_data, dict):
             reply.deleteLater()
             return

        appid = user_data.get("appid")
        name = user_data.get("name")
        req_type = user_data.get("req_type")

        if req_type == self.REQ_TYPE_IMAGE:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self.save_and_display_image(appid, reply.readAll())
            else:
                if name and "AppID" not in name:
                    self.start_fallback_search(appid, name)
                else:
                    self.active_downloads.discard(appid)

        elif req_type == self.REQ_TYPE_SEARCH:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode())
                    if data.get("total", 0) > 0 and data.get("items"):
                        found_id = data["items"][0]["id"]
                        self.start_fallback_download(appid, found_id)
                    else:
                        self.active_downloads.discard(appid)
                except:
                    self.active_downloads.discard(appid)
            else:
                self.active_downloads.discard(appid)

        elif req_type == self.REQ_TYPE_FALLBACK:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self.save_and_display_image(appid, reply.readAll())
            self.active_downloads.discard(appid)

        elif req_type == self.REQ_TYPE_MANUAL_URL:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self.save_and_display_image(appid, reply.readAll())
            else:
                QMessageBox.warning(self, "Download Error", "Could not download image from provided URL.")
            self.active_downloads.discard(appid)

        reply.deleteLater()

    def start_fallback_search(self, appid, name):
        url = STEAM_SEARCH_URL.format(term=name)
        req = QNetworkRequest(QUrl(url))
        data = {
            "appid": appid,
            "name": name,
            "req_type": self.REQ_TYPE_SEARCH
        }
        req.setAttribute(QNetworkRequest.Attribute.User, data)
        self.nam.get(req)

    def start_fallback_download(self, original_appid, found_appid):
        url = STEAM_IMG_URL.format(appid=found_appid)
        req = QNetworkRequest(QUrl(url))
        data = {
            "appid": original_appid,
            "req_type": self.REQ_TYPE_FALLBACK
        }
        req.setAttribute(QNetworkRequest.Attribute.User, data)
        self.nam.get(req)

    def save_and_display_image(self, appid, data):
        self.active_downloads.discard(appid)
        pix = QPixmap()
        pix.loadFromData(data)

        if not pix.isNull():
            try:
                with open(IMG_CACHE_DIR / f"{appid}.jpg", "wb") as f:
                    f.write(data)
            except: pass

            if appid in self.cards:
                self.cards[appid].update_image(pix)

    # --- ACTIONS ---
    def action_open(self, data):
        path = Path(data["path"])
        if path.exists():
            if not SystemUtils.open_with_file_manager(path):
                QMessageBox.warning(self, "Error", "Could not open file manager.")
        else:
            QMessageBox.critical(self, "Error", "Prefix path not found or is invalid.")

    def action_rename(self, data):
        path = Path(data["path"])

        if not path.exists():
            QMessageBox.critical(self, "Error", "Prefix folder does not exist.")
            return

        if not os.access(path, os.W_OK):
             QMessageBox.critical(self, "Permission Denied", "Cannot rename this prefix. Access denied.")
             return

        new_name, ok = QInputDialog.getText(self, "Rename", f"Rename {data['name']}:", text=data["name"])
        if ok and new_name.strip():
            new_name = new_name.strip()
            db = DataManager.load_db()
            db.setdefault("custom_names", {})[data["appid"]] = new_name
            DataManager.save_db(db)

            data["name"] = new_name
            if data["appid"] in self.cards:
                self.cards[data["appid"]].title_lbl.setText(new_name)
                self.load_image(data["appid"], new_name)

    def action_toggle_status(self, data):
        current_status = data["is_installed"]
        new_status = not current_status

        db = DataManager.load_db()
        db.setdefault("custom_status", {})[data["appid"]] = new_status
        DataManager.save_db(db)

        data["is_installed"] = new_status
        data["status"] = "Installed" if new_status else "Uninstalled"

        if data["appid"] in self.cards:
            self.cards[data["appid"]].update_status_display()

    def action_delete(self, data):
        path = Path(data["path"])

        if not path.exists():
             QMessageBox.critical(self, "Error", "Prefix path not found.")
             return

        if not os.access(path, os.W_OK):
             QMessageBox.critical(self, "Permission Denied", "Cannot delete this prefix. Access denied.")
             return

        msg = f"Delete prefix for:\n{data['name']} (ID: {data['appid']})?\n\nLocation: {path}\n\nIRREVERSIBLE."
        reply = QMessageBox.question(self, "Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(data["path"])
                if data["appid"] in self.cards:
                    card = self.cards.pop(data["appid"])
                    card.deleteLater()
                    QTimer.singleShot(10, lambda: self.scroll_content.adjustSize())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def action_set_cover_local(self, data):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Cover Art", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if fname:
            try:
                with open(fname, "rb") as f:
                    img_data = f.read()
                self.save_and_display_image(data["appid"], img_data)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load image: {e}")

    def action_set_cover_url(self, data):
        dlg = CoverDownloadDialog(data["name"], self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            url = dlg.get_url()
            if url:
                req = QNetworkRequest(QUrl(url))
                req_data = {
                    "appid": data["appid"],
                    "req_type": self.REQ_TYPE_MANUAL_URL
                }
                req.setAttribute(QNetworkRequest.Attribute.User, req_data)
                self.nam.get(req)
                self.active_downloads.add(data["appid"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if not STEAM_BASE.exists():
        print(f"Warning: Default steam base not found at {STEAM_BASE}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
