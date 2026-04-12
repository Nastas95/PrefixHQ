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
    QFileDialog, QDialog, QDialogButtonBox, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QRect, QTimer, QUrl
from PyQt6.QtGui import QIcon, QColor, QBrush, QPixmap, QAction, QPainter, QPainterPath, QDesktopServices, QCursor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# SSL certificate path detection for Flatpak compatibility
ssl_paths = [
    "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt",    # Fedora/RHEL
    "/usr/share/ca-certificates/ca-bundle.crt",  # Common fallback
]
for cert_path in ssl_paths:
    if os.path.exists(cert_path):
        os.environ["REQUESTS_CA_BUNDLE"] = cert_path
        break

# --- UPDATE SYSTEM CONSTANTS ---
GITHUB_API_URL = "https://api.github.com/repos/Nastas95/PrefixHQ/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/Nastas95/PrefixHQ/releases"
CURRENT_VERSION = "2.5"

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

# --- THEME SYSTEM ---
THEME_TEMPLATE = """
QMainWindow, QWidget#MainWidget, QWidget#ScrollContent {{ background-color: {bg}; }}
QScrollArea::viewport {{ background-color: {bg}; }}
QWidget {{ color: {text}; font-family: 'Segoe UI', sans-serif; }}
QScrollArea {{ border: none; background-color: transparent; }}
QScrollBar:vertical {{ border: none; background: {dark_bg}; width: 10px; margin: 0px; }}
QScrollBar::handle:vertical {{ background: {scroll}; min-height: 20px; border-radius: 5px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QLineEdit {{ background-color: {input_bg}; border: 1px solid {dark_bg}; border-radius: 4px; padding: 8px; color: {input_text}; font-size: 14px; }}
QLineEdit:focus {{ border: 1px solid {accent}; }}
QPushButton {{ background-color: {btn_bg}; color: {btn_text}; border: none; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
QPushButton:hover {{ background-color: {accent}; color: {hover_text}; }}
QPushButton:pressed {{ background-color: {pressed_bg}; }}
QPushButton#DeleteBtn {{ background-color: {del_bg}; color: {del_text}; }}
QPushButton#DeleteBtn:hover {{ background-color: {del_hover}; color: {del_hover_text}; }}
QPushButton#LinkBtn {{ background-color: transparent; color: {accent}; text-align: left; padding: 0px; }}
QPushButton#LinkBtn:hover {{ text-decoration: underline; background-color: transparent; }}
QPushButton#ExitBtn {{ background-color: {exit_bg}; color: {exit_text}; padding: 6px 16px; font-weight: bold; min-width: 80px; border-radius: 4px; }}
QPushButton#ExitBtn:hover {{ background-color: {exit_hover}; color: {exit_hover_text}; }}
QPushButton#UpdateBtn {{ background-color: transparent; color: {accent}; border: 1px solid {accent}; padding: 4px 12px; border-radius: 4px; font-size: 12px; }}
QPushButton#UpdateBtn:hover {{ background-color: {accent}; color: {bg}; }}
QComboBox {{ background-color: {input_bg}; border: 1px solid {dark_bg}; border-radius: 4px; padding: 6px 8px; color: {input_text}; font-size: 13px; }}
QComboBox::drop-down {{ border: none; width: 20px; background: transparent; }}
QComboBox::down-arrow {{ width: 10px; height: 10px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid {text}; }}
QComboBox QAbstractItemView {{ background-color: {dark_bg}; border: 1px solid {dark_bg}; color: {text}; selection-background-color: {accent}; selection-color: {hover_text}; outline: 0; padding: 4px; }}
QFrame#GameCard {{ background-color: {card_bg}; border-radius: 8px; }}
QFrame#GameCard:hover {{ background-color: {card_hover}; }}
QFrame#GameListItem {{ background-color: {card_bg}; border-radius: 4px; margin-bottom: 2px; }}
QFrame#GameListItem:hover {{ background-color: {card_hover}; }}
QLabel#CardTitle {{ font-size: 13px; font-weight: bold; color: {title_text}; }}
QLabel#CardStatus {{ font-size: 10px; color: {status_text}; }}
QLabel#StatusFooter {{ font-size: 12px; color: {footer_text}; font-weight: bold; }}
QDialog {{ background-color: {bg}; }}
QProgressBar {{ height: 4px; border: none; background: {dark_bg}; }}
QProgressBar::chunk {{ background: {accent}; }}
QMessageBox {{ background-color: {bg}; }}
"""

THEME_PALETTES = {
    "Steam Dark": {"bg": "#1b2838", "text": "#c7d5e0", "dark_bg": "#171a21", "scroll": "#3d4450", "input_bg": "#2a475e", "input_text": "#ffffff", "btn_bg": "#2a475e", "btn_text": "#ffffff", "hover_text": "#171a21", "pressed_bg": "#193144", "accent": "#66c0f4", "del_bg": "#3b2020", "del_text": "#ff6666", "del_hover": "#d9534f", "del_hover_text": "#ffffff", "exit_bg": "#3b2020", "exit_text": "#ff6666", "exit_hover": "#d9534f", "exit_hover_text": "#ffffff", "card_bg": "#171a21", "card_hover": "#222630", "title_text": "#ffffff", "status_text": "#8f98a0", "footer_text": "#8f98a0"},
    "Catppuccin Mocha": {"bg": "#1e1e2e", "text": "#cdd6f4", "dark_bg": "#181825", "scroll": "#585b70", "input_bg": "#313244", "input_text": "#cdd6f4", "btn_bg": "#313244", "btn_text": "#cdd6f4", "hover_text": "#1e1e2e", "pressed_bg": "#11111b", "accent": "#89b4fa", "del_bg": "#f38ba8", "del_text": "#1e1e2e", "del_hover": "#eba0ac", "del_hover_text": "#1e1e2e", "exit_bg": "#f38ba8", "exit_text": "#1e1e2e", "exit_hover": "#eba0ac", "exit_hover_text": "#1e1e2e", "card_bg": "#181825", "card_hover": "#313244", "title_text": "#cdd6f4", "status_text": "#6c7086", "footer_text": "#6c7086"},
    "Dracula": {"bg": "#282a36", "text": "#f8f8f2", "dark_bg": "#44475a", "scroll": "#6272a4", "input_bg": "#44475a", "input_text": "#f8f8f2", "btn_bg": "#44475a", "btn_text": "#f8f8f2", "hover_text": "#f8f8f2", "pressed_bg": "#1e1f29", "accent": "#bd93f9", "del_bg": "#ff5555", "del_text": "#f8f8f2", "del_hover": "#ff6e6e", "del_hover_text": "#f8f8f2", "exit_bg": "#ff5555", "exit_text": "#f8f8f2", "exit_hover": "#ff6e6e", "exit_hover_text": "#f8f8f2", "card_bg": "#44475a", "card_hover": "#6272a4", "title_text": "#f8f8f2", "status_text": "#6272a4", "footer_text": "#6272a4"},
    "Nord": {"bg": "#2E3440", "text": "#D8DEE9", "dark_bg": "#3B4252", "scroll": "#4C566A", "input_bg": "#3B4252", "input_text": "#D8DEE9", "btn_bg": "#3B4252", "btn_text": "#D8DEE9", "hover_text": "#ECEFF4", "pressed_bg": "#2E3440", "accent": "#88C0D0", "del_bg": "#BF616A", "del_text": "#ECEFF4", "del_hover": "#D08770", "del_hover_text": "#ECEFF4", "exit_bg": "#BF616A", "exit_text": "#ECEFF4", "exit_hover": "#D08770", "exit_hover_text": "#ECEFF4", "card_bg": "#3B4252", "card_hover": "#4C566A", "title_text": "#ECEFF4", "status_text": "#8FBCBB", "footer_text": "#8FBCBB"},
    "Gruvbox": {"bg": "#282828", "text": "#ebdbb2", "dark_bg": "#32302f", "scroll": "#928374", "input_bg": "#3c3836", "input_text": "#ebdbb2", "btn_bg": "#3c3836", "btn_text": "#ebdbb2", "hover_text": "#ebdbb2", "pressed_bg": "#282828", "accent": "#b8bb26", "del_bg": "#cc241d", "del_text": "#ebdbb2", "del_hover": "#b2221a", "del_hover_text": "#ebdbb2", "exit_bg": "#cc241d", "exit_text": "#ebdbb2", "exit_hover": "#b2221a", "exit_hover_text": "#ebdbb2", "card_bg": "#32302f", "card_hover": "#504945", "title_text": "#ebdbb2", "status_text": "#928374", "footer_text": "#928374"},
}

def get_theme_qss(theme_name):
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Steam Dark"])
    return THEME_TEMPLATE.format(**palette)


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

        def get_ci(d, key, default=""):
            key_lower = key.lower()
            for k, v in d.items():
                if k.lower() == key_lower:
                    return v
            return default

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
                        app_name = get_ci(item, "appname", "")
                        exe_path = get_ci(item, "exe", "")
                        raw_id = get_ci(item, "appid")
                        if raw_id is not None:
                            try:
                                id_32 = int(raw_id) & 0xffffffff
                                mapping[str(id_32)] = app_name
                                id_64 = (id_32 << 32) | 0x02000000
                                mapping[str(id_64)] = app_name
                                id_signed = struct.unpack('<i', struct.pack('<I', id_32))[0]
                                mapping[str(id_signed)] = app_name
                                print(f"DEBUG: Mapped (Explicit) {id_32} -> {app_name}")
                            except (ValueError, TypeError):
                                pass
                        if app_name and exe_path:
                            crc_input = (exe_path + app_name).encode("utf-8")
                            crc = zlib.crc32(crc_input) & 0xffffffff
                            gen_id = crc | 0x80000000
                            mapping[str(gen_id)] = app_name
                            if not exe_path.startswith('"'):
                                crc_input_q = (f'"{exe_path}"' + app_name).encode("utf-8")
                                crc_q = zlib.crc32(crc_input_q) & 0xffffffff
                                gen_id_q = crc_q | 0x80000000
                                mapping[str(gen_id_q)] = app_name
                except Exception as e:
                    print(f"Error parsing shortcuts.vdf at {shortcuts_path}: {e}")
        return mapping

    @staticmethod
    def parse_binary_vdf(data):
        def read_string(d, p):
            end = d.find(b'\x00', p)
            if end == -1:
                raise ValueError("Unterminated string")
            s = d[p:end].decode('utf-8', 'replace')
            return s, end + 1

        def parse_map(d, p):
            res = {}
            while p < len(d):
                type_byte = d[p]
                p += 1
                if type_byte == 0x08:
                    return res, p
                if p >= len(d):
                    break
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
                    if p + 4 > len(d):
                        break
                    val = struct.unpack('<I', d[p:p+4])[0]
                    p += 4
                    res[key] = val
                elif type_byte == 0x03:
                    if p + 4 > len(d):
                        break
                    p += 4
                elif type_byte == 0x07:
                    if p + 8 > len(d):
                        break
                    p += 8
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
                    if key.lower() == "shortcuts":
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
        # Only force X11 if not already set (respects Wayland and user preferences)
        if "QT_QPA_PLATFORM" not in os.environ:
            clean_env["QT_QPA_PLATFORM"] = "xcb"
        clean_env.pop("QTWEBENGINEPROCESS_PATH", None)
        return clean_env

    @staticmethod
    def get_default_file_manager():
        try:
            cmd = ["xdg-mime", "query", "default", "inode/directory"]
            result = subprocess.check_output(cmd).decode().strip()
            if result:
                if "nautilus" in result.lower():
                    return "nautilus"
                if "dolphin" in result.lower():
                    return "dolphin"
                if "nemo" in result.lower():
                    return "nemo"
                if "thunar" in result.lower():
                    return "thunar"
                if "pcmanfm" in result.lower():
                    return "pcmanfm"
        except Exception:
            pass
        common_fms = ["dolphin", "nautilus", "nemo", "thunar", "pcmanfm", "caja"]
        for fm in common_fms:
            if shutil.which(fm):
                return fm
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
                # Flatpak compatibility: escape sandbox to launch file manager on host
                if os.path.exists("/.flatpak-info"):
                    subprocess.Popen(["flatpak-spawn", "--host", fm, path], env=clean_env)
                else:
                    subprocess.Popen([fm, path], env=clean_env)
                return True
            except:
                pass
        try:
            # Flatpak compatibility: escape sandbox for xdg-open as well
            if os.path.exists("/.flatpak-info"):
                subprocess.Popen(["flatpak-spawn", "--host", "xdg-open", path], env=clean_env)
            else:
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
                               env=clean_env, shell=False,
                               creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
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
        layout.addWidget(QLabel(f"Enter direct image URL for: <b>{game_name}</b>"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/image.jpg")
        layout.addWidget(self.url_input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_url(self):
        return self.url_input.text().strip()


class GameCardMixin:
    def show_context_menu_common(self, pos):
        menu = QMenu(self)
        action_copy_id = QAction("Copy ID", self)
        action_copy_id.triggered.connect(lambda: QApplication.clipboard().setText(str(self.data["appid"])))
        menu.addAction(action_copy_id)
        menu.addSeparator()
        action_sgdb = QAction("Search on SteamGridDB", self)
        action_sgdb.triggered.connect(
            lambda: SystemUtils.open_url(STEAMGRIDDB_SEARCH_URL.format(term=self.data["name"])))
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
        self.img_label = QLabel()
        self.img_label.setFixedSize(100, 50)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background-color: #0d1015; border-radius: 4px;")
        self.img_label.setScaledContents(True)
        layout.addWidget(self.img_label)
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
                    except:
                        continue
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
                    if appid in IGNORE_APPIDS:
                        continue
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
        except:
            pass
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
        DataManager.init_storage()
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_network_finished)
        self.cards = {}
        self.all_prefixes = []
        # Load preferences
        db = DataManager.load_db()
        self.view_mode = db.get("view_mode", "grid")
        self.current_theme = db.get("current_theme", "Steam Dark")
        self.setStyleSheet(get_theme_qss(self.current_theme))
        self.active_downloads = set()
        self.download_attempts = {}
        main_widget = QWidget()
        main_widget.setObjectName("MainWidget")
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 10)
        self.setup_header()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area, 1)
        self.setup_view_container()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 5, 0, 0)
        footer_layout.setSpacing(10)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusFooter")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        # Check for Updates button (discreet, in footer)
        self.btn_check_update = QPushButton("Check Updates")
        self.btn_check_update.setObjectName("UpdateBtn")
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.setFixedWidth(120)
        self.btn_check_update.setToolTip(f"Current version: {CURRENT_VERSION}")
        self.btn_check_update.clicked.connect(lambda: self.perform_update_check(show_message=True))

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("ExitBtn")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(self.close_application)

        footer_layout.addWidget(self.btn_check_update)
        footer_layout.addWidget(self.exit_btn)
        self.main_layout.addWidget(footer_widget)
        self.refresh_data()
        # Auto-check for updates (delayed to not block UI, silent)
        QTimer.singleShot(3000, lambda: self.perform_update_check(show_message=False))

    def close_application(self):
        if self.active_downloads:
            reply = QMessageBox.question(
                self, "Confirm Exit", "Image downloads are still in progress. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        if hasattr(self, 'worker') and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit", "Prefix scan is still in progress. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        QApplication.quit()

    def setup_header(self):
        header = QHBoxLayout()
        title = QLabel("STEAM PREFIXES")
        title.setStyleSheet("font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_grid)
        # Theme Selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_PALETTES.keys())
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.theme_combo.setFixedWidth(160)
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
        header.addWidget(self.theme_combo)
        header.addWidget(self.btn_toggle_view)
        header.addWidget(self.btn_open_config)
        header.addWidget(self.btn_refresh)
        self.main_layout.addLayout(header)

    def on_theme_changed(self, theme_name):
        self.current_theme = theme_name
        db = DataManager.load_db()
        db["current_theme"] = theme_name
        DataManager.save_db(db)
        self.setStyleSheet(get_theme_qss(theme_name))

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
        db = DataManager.load_db()
        db["view_mode"] = self.view_mode
        DataManager.save_db(db)
        self.update_toggle_btn_icon()
        self.setup_view_container()
        self.populate_view()

    def setup_view_container(self):
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        if self.view_mode == "grid":
            self.layout_container = FlowLayout(self.scroll_content, margin=0, h_spacing=15, v_spacing=15)
        else:
            self.layout_container = QVBoxLayout(self.scroll_content)
            self.layout_container.setSpacing(5)
            self.layout_container.setContentsMargins(5, 5, 5, 5)
            self.layout_container.addStretch()
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
            if match:
                visible_count += 1
        if self.view_mode == "grid":
            self.scroll_content.adjustSize()

    # --- UPDATE METHODS ---
    def perform_update_check(self, show_message=True):
        release_info = self.get_latest_release_from_github()
        if not release_info:
            if show_message:
                QMessageBox.warning(self, "Update Check Failed",
                    "Could not fetch release information. Please check your internet connection.")
            return None

        latest_version = release_info['version']
        if self._is_newer_version(latest_version, CURRENT_VERSION):
            self.prompt_update(latest_version, release_info['changelog'], release_info['html_url'])
            return release_info
        elif show_message:
            QMessageBox.information(self, "No Updates Available",
                f"You are already using the latest version ({CURRENT_VERSION}).")
        return None

        latest_version = release_info['version']
        if self._is_newer_version(latest_version, CURRENT_VERSION):
            if show_message:
                self.prompt_update(latest_version, release_info['changelog'], release_info['html_url'])
            return release_info
        elif show_message:
            QMessageBox.information(self, "No Updates Available",
                f"You are already using the latest version ({CURRENT_VERSION}).")
        return None

    @staticmethod
    def get_latest_release_from_github():
        """Fetch latest release info from GitHub API"""
        try:
            headers = {'User-Agent': 'PrefixHQ-App'}
            response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            return {
                'version': release_data.get('tag_name', 'Unknown').lstrip('v'),
                'changelog': release_data.get('body', 'No changelog available'),
                'html_url': release_data.get('html_url', '')
            }
        except requests.exceptions.RequestException as exc:
            print(f"Error fetching release info: {exc}")
            return None
        except Exception as exc:
            print(f"Error parsing release info: {exc}")
            return None

    @staticmethod
    def _is_newer_version(latest: str, current: str) -> bool:
        """Compare version strings (simple semver-like comparison)"""
        def parse_version(v):
            return [int(x) for x in v.split('.') if x.isdigit()]
        try:
            latest_parts = parse_version(latest)
            current_parts = parse_version(current)
            return latest_parts > current_parts
        except:
            return False

    def prompt_update(self, latest_version, changelog, release_url):
        """Show update available dialog"""
        message_box = QMessageBox(QMessageBox.Icon.Question, "Update Available",
            f"A new update ({latest_version}) is available!\n\nView changelog?")
        changelog_button = message_box.addButton("View Changelog", QMessageBox.ButtonRole.ActionRole)
        download_button = message_box.addButton("Download Update", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = message_box.addButton("Maybe Later", QMessageBox.ButtonRole.RejectRole)
        message_box.exec()

        clicked = message_box.clickedButton()
        if clicked == changelog_button:
            self.show_changelog(latest_version, changelog, release_url)
        elif clicked == download_button:
            self.open_download_page(release_url)

    def show_changelog(self, latest_version, changelog_text, release_url):
        """Show changelog in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Changelog - v{latest_version}")
        dialog.setFixedSize(500, 400)
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        # Simple markdown-like formatting for changelog
        formatted = changelog_text.replace('# ', '### ').replace('## ', '#### ')
        text_edit.setPlainText(formatted)
        layout.addWidget(text_edit)

        button_layout = QHBoxLayout()
        download_btn = QPushButton("Go to Download Page")
        download_btn.clicked.connect(lambda: self.open_download_page(release_url))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        button_layout.addWidget(download_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        dialog.exec()

    def open_download_page(self, url=None):
        """Open GitHub releases page in default browser"""
        target_url = url or GITHUB_RELEASES_URL
        clean_env = os.environ.copy()
        # Clean environment variables that might interfere with subprocess
        for var in ["LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
                    "QML2_IMPORT_PATH", "QML_IMPORT_PATH", "PYTHONPATH"]:
            clean_env.pop(var, None)
        if "_MEIPASS" in clean_env:
            meipass = clean_env["_MEIPASS"]
            for key in list(clean_env.keys()):
                if meipass in str(clean_env[key]):
                    clean_env.pop(key, None)

        try:
            if sys.platform.startswith('linux'):
                subprocess.Popen(['xdg-open', target_url], env=clean_env)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', target_url], env=clean_env)
            elif sys.platform == 'win32':
                subprocess.Popen(['cmd', '/c', 'start', '', target_url],
                               env=clean_env, shell=False,
                               creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            print(f"Opened download page: {target_url}")
        except Exception as e:
            print(f"Failed to open browser: {e}")
            QMessageBox.warning(self, "Open URL",
                f"Could not open your browser. Please visit:\n{target_url}")

    # --- IMAGE HANDLING ---
    def load_image(self, appid, name):
        cache_path = IMG_CACHE_DIR / f"{appid}.jpg"
        if cache_path.exists():
            pix = QPixmap(str(cache_path))
            if not pix.isNull():
                if appid in self.cards:
                    self.cards[appid].update_image(pix)
                return
        if appid in self.active_downloads:
            return
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

            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.download_attempts[appid] = self.download_attempts.get(appid, 0) + 1
                if self.download_attempts[appid] >= 5:
                    print(f"[PrefixHQ] Max retries (5) reached for AppID {appid}. Giving up.")
                    self.active_downloads.discard(appid)
                    reply.deleteLater()
                    return

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
                else:
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
        self.download_attempts.pop(appid, None)
        pix = QPixmap()
        pix.loadFromData(data)
        if not pix.isNull():
            try:
                with open(IMG_CACHE_DIR / f"{appid}.jpg", "wb") as f:
                    f.write(data)
            except:
                pass
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
        msg = f"Delete prefix for:\n{data['name']} (ID: {data['appid']})?\nLocation: {path}\nIRREVERSIBLE."
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
QFileDialog, QDialog, QDialogButtonBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QRect, QTimer, QUrl
from PyQt6.QtGui import QIcon, QColor, QBrush, QPixmap, QAction, QPainter, QPainterPath, QDesktopServices, QCursor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
# SSL certificate path detection for Flatpak compatibility
ssl_paths = [
    "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt",    # Fedora/RHEL
    "/usr/share/ca-certificates/ca-bundle.crt",  # Common fallback
]
for cert_path in ssl_paths:
    if os.path.exists(cert_path):
        os.environ["REQUESTS_CA_BUNDLE"] = cert_path
        break

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

# --- THEME SYSTEM  ---
THEME_TEMPLATE = """
QMainWindow, QWidget#MainWidget, QWidget#ScrollContent {{ background-color: {bg}; }}
QScrollArea::viewport {{ background-color: {bg}; }}
QWidget {{ color: {text}; font-family: 'Segoe UI', sans-serif; }}
QScrollArea {{ border: none; background-color: transparent; }}
QScrollBar:vertical {{ border: none; background: {dark_bg}; width: 10px; margin: 0px; }}
QScrollBar::handle:vertical {{ background: {scroll}; min-height: 20px; border-radius: 5px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QLineEdit {{ background-color: {input_bg}; border: 1px solid {dark_bg}; border-radius: 4px; padding: 8px; color: {input_text}; font-size: 14px; }}
QLineEdit:focus {{ border: 1px solid {accent}; }}
QPushButton {{ background-color: {btn_bg}; color: {btn_text}; border: none; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
QPushButton:hover {{ background-color: {accent}; color: {hover_text}; }}
QPushButton:pressed {{ background-color: {pressed_bg}; }}
QPushButton#DeleteBtn {{ background-color: {del_bg}; color: {del_text}; }}
QPushButton#DeleteBtn:hover {{ background-color: {del_hover}; color: {del_hover_text}; }}
QPushButton#LinkBtn {{ background-color: transparent; color: {accent}; text-align: left; padding: 0px; }}
QPushButton#LinkBtn:hover {{ text-decoration: underline; background-color: transparent; }}
QPushButton#ExitBtn {{ background-color: {exit_bg}; color: {exit_text}; padding: 6px 16px; font-weight: bold; min-width: 80px; border-radius: 4px; }}
QPushButton#ExitBtn:hover {{ background-color: {exit_hover}; color: {exit_hover_text}; }}
QComboBox {{ background-color: {input_bg}; border: 1px solid {dark_bg}; border-radius: 4px; padding: 6px 8px; color: {input_text}; font-size: 13px; }}
QComboBox::drop-down {{ border: none; width: 20px; background: transparent; }}
QComboBox::down-arrow {{ width: 10px; height: 10px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid {text}; }}
QComboBox QAbstractItemView {{ background-color: {dark_bg}; border: 1px solid {dark_bg}; color: {text}; selection-background-color: {accent}; selection-color: {hover_text}; outline: 0; padding: 4px; }}
QFrame#GameCard {{ background-color: {card_bg}; border-radius: 8px; }}
QFrame#GameCard:hover {{ background-color: {card_hover}; }}
QFrame#GameListItem {{ background-color: {card_bg}; border-radius: 4px; margin-bottom: 2px; }}
QFrame#GameListItem:hover {{ background-color: {card_hover}; }}
QLabel#CardTitle {{ font-size: 13px; font-weight: bold; color: {title_text}; }}
QLabel#CardStatus {{ font-size: 10px; color: {status_text}; }}
QLabel#StatusFooter {{ font-size: 12px; color: {footer_text}; font-weight: bold; }}
QDialog {{ background-color: {bg}; }}
QProgressBar {{ height: 4px; border: none; background: {dark_bg}; }}
QProgressBar::chunk {{ background: {accent}; }}
QMessageBox {{ background-color: {bg}; }}
"""

THEME_PALETTES = {
    "Steam Dark": {"bg": "#1b2838", "text": "#c7d5e0", "dark_bg": "#171a21", "scroll": "#3d4450", "input_bg": "#2a475e", "input_text": "#ffffff", "btn_bg": "#2a475e", "btn_text": "#ffffff", "hover_text": "#171a21", "pressed_bg": "#193144", "accent": "#66c0f4", "del_bg": "#3b2020", "del_text": "#ff6666", "del_hover": "#d9534f", "del_hover_text": "#ffffff", "exit_bg": "#3b2020", "exit_text": "#ff6666", "exit_hover": "#d9534f", "exit_hover_text": "#ffffff", "card_bg": "#171a21", "card_hover": "#222630", "title_text": "#ffffff", "status_text": "#8f98a0", "footer_text": "#8f98a0"},
    "Catppuccin Mocha": {"bg": "#1e1e2e", "text": "#cdd6f4", "dark_bg": "#181825", "scroll": "#585b70", "input_bg": "#313244", "input_text": "#cdd6f4", "btn_bg": "#313244", "btn_text": "#cdd6f4", "hover_text": "#1e1e2e", "pressed_bg": "#11111b", "accent": "#89b4fa", "del_bg": "#f38ba8", "del_text": "#1e1e2e", "del_hover": "#eba0ac", "del_hover_text": "#1e1e2e", "exit_bg": "#f38ba8", "exit_text": "#1e1e2e", "exit_hover": "#eba0ac", "exit_hover_text": "#1e1e2e", "card_bg": "#181825", "card_hover": "#313244", "title_text": "#cdd6f4", "status_text": "#6c7086", "footer_text": "#6c7086"},
    "Dracula": {"bg": "#282a36", "text": "#f8f8f2", "dark_bg": "#44475a", "scroll": "#6272a4", "input_bg": "#44475a", "input_text": "#f8f8f2", "btn_bg": "#44475a", "btn_text": "#f8f8f2", "hover_text": "#f8f8f2", "pressed_bg": "#1e1f29", "accent": "#bd93f9", "del_bg": "#ff5555", "del_text": "#f8f8f2", "del_hover": "#ff6e6e", "del_hover_text": "#f8f8f2", "exit_bg": "#ff5555", "exit_text": "#f8f8f2", "exit_hover": "#ff6e6e", "exit_hover_text": "#f8f8f2", "card_bg": "#44475a", "card_hover": "#6272a4", "title_text": "#f8f8f2", "status_text": "#6272a4", "footer_text": "#6272a4"},
    "Nord": {"bg": "#2E3440", "text": "#D8DEE9", "dark_bg": "#3B4252", "scroll": "#4C566A", "input_bg": "#3B4252", "input_text": "#D8DEE9", "btn_bg": "#3B4252", "btn_text": "#D8DEE9", "hover_text": "#ECEFF4", "pressed_bg": "#2E3440", "accent": "#88C0D0", "del_bg": "#BF616A", "del_text": "#ECEFF4", "del_hover": "#D08770", "del_hover_text": "#ECEFF4", "exit_bg": "#BF616A", "exit_text": "#ECEFF4", "exit_hover": "#D08770", "exit_hover_text": "#ECEFF4", "card_bg": "#3B4252", "card_hover": "#4C566A", "title_text": "#ECEFF4", "status_text": "#8FBCBB", "footer_text": "#8FBCBB"},
    "Gruvbox": {"bg": "#282828", "text": "#ebdbb2", "dark_bg": "#32302f", "scroll": "#928374", "input_bg": "#3c3836", "input_text": "#ebdbb2", "btn_bg": "#3c3836", "btn_text": "#ebdbb2", "hover_text": "#ebdbb2", "pressed_bg": "#282828", "accent": "#b8bb26", "del_bg": "#cc241d", "del_text": "#ebdbb2", "del_hover": "#b2221a", "del_hover_text": "#ebdbb2", "exit_bg": "#cc241d", "exit_text": "#ebdbb2", "exit_hover": "#b2221a", "exit_hover_text": "#ebdbb2", "card_bg": "#32302f", "card_hover": "#504945", "title_text": "#ebdbb2", "status_text": "#928374", "footer_text": "#928374"},
}

def get_theme_qss(theme_name):
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Steam Dark"])
    return THEME_TEMPLATE.format(**palette)

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
        def get_ci(d, key, default=""):
            key_lower = key.lower()
            for k, v in d.items():
                if k.lower() == key_lower:
                    return v
            return default
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
                        app_name = get_ci(item, "appname", "")
                        exe_path = get_ci(item, "exe", "")
                        raw_id = get_ci(item, "appid")
                        if raw_id is not None:
                            try:
                                id_32 = int(raw_id) & 0xffffffff
                                mapping[str(id_32)] = app_name
                                id_64 = (id_32 << 32) | 0x02000000
                                mapping[str(id_64)] = app_name
                                id_signed = struct.unpack('<i', struct.pack('<I', id_32))[0]
                                mapping[str(id_signed)] = app_name
                                print(f"DEBUG: Mapped (Explicit) {id_32} -> {app_name}")
                            except (ValueError, TypeError):
                                pass
                        if app_name and exe_path:
                            crc_input = (exe_path + app_name).encode("utf-8")
                            crc = zlib.crc32(crc_input) & 0xffffffff
                            gen_id = crc | 0x80000000
                            mapping[str(gen_id)] = app_name
                            if not exe_path.startswith('"'):
                                crc_input_q = (f'"{exe_path}"' + app_name).encode("utf-8")
                                crc_q = zlib.crc32(crc_input_q) & 0xffffffff
                                gen_id_q = crc_q | 0x80000000
                                mapping[str(gen_id_q)] = app_name
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
                    val = struct.unpack('<I', d[p:p+4])[0]
                    p += 4
                    res[key] = val
                elif type_byte == 0x03:
                    if p + 4 > len(d): break
                    p += 4
                elif type_byte == 0x07:
                    if p + 8 > len(d): break
                    p += 8
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
                    if key.lower() == "shortcuts":
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
        # Only force X11 if not already set (respects Wayland and user preferences)
        if "QT_QPA_PLATFORM" not in os.environ:
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
                # Flatpak compatibility: escape sandbox to launch file manager on host
                if os.path.exists("/.flatpak-info"):
                    subprocess.Popen(["flatpak-spawn", "--host", fm, path], env=clean_env)
                else:
                    subprocess.Popen([fm, path], env=clean_env)
                return True
            except:
                pass
        try:
            # Flatpak compatibility: escape sandbox for xdg-open as well
            if os.path.exists("/.flatpak-info"):
                subprocess.Popen(["flatpak-spawn", "--host", "xdg-open", path], env=clean_env)
            else:
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
        layout.addWidget(QLabel(f"Enter direct image URL for: <b>{game_name}</b>"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/image.jpg")
        layout.addWidget(self.url_input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
    def get_url(self):
        return self.url_input.text().strip()

class GameCardMixin:
    def show_context_menu_common(self, pos):
        menu = QMenu(self)
        action_copy_id = QAction("Copy ID", self)
        action_copy_id.triggered.connect(lambda: QApplication.clipboard().setText(str(self.data["appid"])))
        menu.addAction(action_copy_id)
        menu.addSeparator()
        action_sgdb = QAction("Search on SteamGridDB", self)
        action_sgdb.triggered.connect(
            lambda: SystemUtils.open_url(STEAMGRIDDB_SEARCH_URL.format(term=self.data["name"])))
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
        self.img_label = QLabel()
        self.img_label.setFixedSize(100, 50)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background-color: #0d1015; border-radius: 4px;")
        self.img_label.setScaledContents(True)
        layout.addWidget(self.img_label)
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
        DataManager.init_storage()
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_network_finished)
        self.cards = {}
        self.all_prefixes = []

        # Load preferences
        db = DataManager.load_db()
        self.view_mode = db.get("view_mode", "grid")
        self.current_theme = db.get("current_theme", "Steam Dark")
        self.setStyleSheet(get_theme_qss(self.current_theme))

        self.active_downloads = set()
        self.download_attempts = {}
        main_widget = QWidget()
        main_widget.setObjectName("MainWidget")
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 10)
        self.setup_header()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area, 1)
        self.setup_view_container()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
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
        title.setStyleSheet("font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_grid)

        # Theme Selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_PALETTES.keys())
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.theme_combo.setFixedWidth(160)

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
        header.addWidget(self.theme_combo)
        header.addWidget(self.btn_toggle_view)
        header.addWidget(self.btn_open_config)
        header.addWidget(self.btn_refresh)
        self.main_layout.addLayout(header)

    def on_theme_changed(self, theme_name):
        self.current_theme = theme_name
        db = DataManager.load_db()
        db["current_theme"] = theme_name
        DataManager.save_db(db)
        self.setStyleSheet(get_theme_qss(theme_name))

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
        db = DataManager.load_db()
        db["view_mode"] = self.view_mode
        DataManager.save_db(db)
        self.update_toggle_btn_icon()
        self.setup_view_container()
        self.populate_view()

    def setup_view_container(self):
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        if self.view_mode == "grid":
            self.layout_container = FlowLayout(self.scroll_content, margin=0, h_spacing=15, v_spacing=15)
        else:
            self.layout_container = QVBoxLayout(self.scroll_content)
            self.layout_container.setSpacing(5)
            self.layout_container.setContentsMargins(5, 5, 5, 5)
            self.layout_container.addStretch()
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

        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.download_attempts[appid] = self.download_attempts.get(appid, 0) + 1
            if self.download_attempts[appid] >= 5:
                print(f"[PrefixHQ] Max retries (5) reached for AppID {appid}. Giving up.")
                self.active_downloads.discard(appid)
                reply.deleteLater()
                return

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
            else:
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
        self.download_attempts.pop(appid, None)
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
        msg = f"Delete prefix for:\n{data['name']} (ID: {data['appid']})?\nLocation: {path}\nIRREVERSIBLE."
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
