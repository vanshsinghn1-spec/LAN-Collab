import os
import platform
# --- FIX: Set High DPI Scaling ---
if platform.system() == "Windows":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

import socket
import threading
import sys
import cv2
import pyaudio
import numpy as np

import struct
from PIL import Image
import io
import mss
import hashlib
import time
import pygetwindow as gw
import json      # For safe data serialization
import base64    # To encode/decode binary data for json
import ssl
import math
import av        
import fractions

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QStackedLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QProgressBar, QTabWidget, QScrollArea, QFrame, QSplitter,
    QInputDialog, QMessageBox, QFileDialog, QSizePolicy, QSpacerItem, QDialog,
    QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import (
    pyqtSignal, pyqtSlot, QObject, QThread, Qt, QEvent, QSize, QTimer,
    QPointF, QEasingCurve, QPropertyAnimation, QRect, QRectF
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QBrush, QFont, QIcon, QGuiApplication,
    QMovie, QPainterPath
)

# LAN Collab imports
from shared_utils import lin2ulaw_numpy, ulaw2lin_numpy, safe_serialize, safe_deserialize, setup_logging
import config

# --- Configuration (imported from config module) ---
TCP_PORT = config.TCP_PORT
UDP_PORT = config.UDP_PORT
FILE_TCP_PORT = config.FILE_TCP_PORT
DISCOVERY_PORT = config.DISCOVERY_PORT
CHUNK = config.AUDIO_CHUNK_SIZE
FORMAT = config.AUDIO_FORMAT
CHANNELS = config.AUDIO_CHANNELS
RATE = config.AUDIO_SAMPLE_RATE
CAPTURE_FPS = config.VIDEO_CAPTURE_FPS
VIDEO_RENDER_FPS = config.VIDEO_RENDER_FPS
VIDEO_WIDTH = config.VIDEO_WIDTH
VIDEO_HEIGHT = config.VIDEO_HEIGHT
VIDEO_CRF = config.VIDEO_CRF
VIDEO_KEYFRAME_INTERVAL = config.VIDEO_KEYFRAME_INTERVAL
VIDEO_MAX_BITRATE_KBPS = config.VIDEO_MAX_BITRATE_KBPS
VIDEO_BUFFER_KBPS = config.VIDEO_BUFFER_KBPS
VIDEO_ENCODER_PRESET = config.VIDEO_ENCODER_PRESET
VIDEO_FRAGMENT_CHUNK_BYTES = config.VIDEO_FRAGMENT_CHUNK_BYTES

# --- UI Theme Configuration (imported from config module) ---
BG_COLOR = config.BG_COLOR
FRAME_BG = config.FRAME_BG
CHAT_BG = config.CHAT_BG
LIST_BG = config.LIST_BG
FG_COLOR = config.FG_COLOR
FG_DARKER = config.FG_DARKER
ACCENT_COLOR = config.ACCENT_COLOR
ACCENT_DARK = config.ACCENT_DARK
BTN_SUCCESS = config.BTN_SUCCESS
BTN_DANGER = config.BTN_DANGER
BTN_DANGER_ACTIVE = config.BTN_DANGER_ACTIVE
BTN_BG = config.BTN_BG
BTN_BG_ACTIVE = config.BTN_BG_ACTIVE
AVATAR_COLORS = config.AVATAR_COLORS

# --- Global Stylesheet (QSS) ---
STYLESHEET = f"""
    QWidget {{
        background-color: {BG_COLOR};
        color: {FG_COLOR};
        font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
        font-size: 10pt;
    }}
    QDialog {{
        background-color: {BG_COLOR};
    }}
    
    /* --- Frames & Panels --- */
    QFrame {{
        background-color: transparent;
        border: none;
    }}
    QFrame#MainScreen {{
        background-color: {BG_COLOR};
    }}
    QFrame#BottomBar {{
        background-color: {FRAME_BG};
        border-top: 1px solid {BTN_BG};
    }}
    QFrame#SidePanel {{
        background-color: {FRAME_BG};
        border-left: 1px solid {BTN_BG};
    }}
    
    /* --- NEW: Active Speaker Border --- */
    QFrame#ActiveSpeakerBorder {{
        background-color: transparent;
        border: 3px solid {ACCENT_COLOR};
        border-radius: 12px;
    }}
    
    /* --- Labels --- */
    QLabel {{
        background-color: transparent;
        padding: 2px;
    }}
    QLabel#AvatarName {{
        font-weight: 500;
        padding: 4px;
        color: {FG_COLOR};
        background-color: rgba(0, 0, 0, 0.4);
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
        margin: 0px;
    }}
    QLabel#VideoFeed {{
        background-color: {LIST_BG};
        border-radius: 8px; /* Rounded video */
    }}
    QLabel#AvatarCircle {{
        background-color: {LIST_BG};
        border-radius: 8px; /* Avatars are now rounded tiles */
    }}
    QLabel#PageIndicator {{
        background-color: {BTN_BG};
        border: none;
        border-radius: 4px;
        width: 8px;
        height: 8px;
    }}
    QLabel#PageIndicatorActive {{
        background-color: {ACCENT_COLOR};
        border: none;
        border-radius: 4px;
        width: 8px;
        height: 8px;
    }}

    /* --- Buttons --- */
    QPushButton {{
        background-color: {BTN_BG};
        color: {FG_COLOR};
        border: none;
        padding: 10px 16px;
        font-weight: 600; /* Bolder */
        border-radius: 6px; /* More rounded */
    }}
    QPushButton:hover {{
        background-color: {BTN_BG_ACTIVE};
    }}
    QPushButton:pressed {{
        background-color: {ACCENT_DARK};
    }}
    QPushButton:disabled {{
        background-color: {FRAME_BG};
        color: {FG_DARKER};
    }}

    /* Special Buttons */
    QPushButton#RedButton {{
        background-color: {BTN_DANGER};
        color: white;
    }}
    QPushButton#RedButton:hover {{
        background-color: {BTN_DANGER_ACTIVE};
        color: black;
    }}
    QPushButton#GreenButton {{
        background-color: {BTN_SUCCESS};
        color: white;
    }}
    QPushButton#GreenButton:hover {{
        background-color: #5cb85c;
    }}
    QPushButton#BlueButton {{
        background-color: {ACCENT_COLOR};
        color: white;
    }}
    QPushButton#BlueButton:hover {{
        background-color: {ACCENT_DARK};
    }}
    
    QPushButton#SidePanelCloseButton {{
        background-color: transparent;
        border: none;
        color: {FG_DARKER};
        font-weight: bold;
        font-size: 12pt;
        padding: 4px 8px;
    }}
    QPushButton#SidePanelCloseButton:hover {{
        background-color: {BTN_BG_ACTIVE};
        color: {FG_COLOR};
        border-radius: 4px;
    }}
    
    /* Bottom Bar Control Buttons */
    QPushButton#ControlButton {{
        background-color: {BTN_BG};
        color: {FG_COLOR};
        border: none;
        font-weight: 600;
        font-size: 11pt;
        border-radius: 20px; /* Circular */
        min-width: 40px;
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
    }}
    QPushButton#ControlButton:hover {{
        background-color: {BTN_BG_ACTIVE};
    }}
    QPushButton#ControlButton:pressed {{
        background-color: {ACCENT_DARK};
    }}
    QPushButton#ControlButtonRed {{
        background-color: {BTN_DANGER};
        color: white;
        border: none;
        font-weight: 600;
        font-size: 11pt;
        border-radius: 20px;
        min-width: 40px;
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
    }}
    QPushButton#ControlButtonRed:hover {{
        background-color: {BTN_DANGER_ACTIVE};
        color: black;
    }}
    /* Sidebar nav arrows */
    QPushButton#NavArrow {{
        background-color: {BTN_BG_ACTIVE};
        color: {FG_COLOR};
        font-size: 14pt;
        font-weight: bold;
        border-radius: 15px;
        width: 30px;
        height: 30px;
    }}
    QPushButton#NavArrow:hover {{
        background-color: {ACCENT_COLOR};
    }}
    
    QPushButton#CancelButton {{
        background-color: transparent;
        color: {BTN_DANGER};
        font-size: 14pt;
        font-weight: bold;
        padding: 0px 5px;
        margin-left: 5px;
        border: none;
        min-width: 20px;
        max-width: 20px;
    }}
    QPushButton#CancelButton:hover {{
        background-color: {BTN_BG_ACTIVE};
    }}

    /* --- Input Fields --- */
    QLineEdit {{
        background-color: {CHAT_BG};
        border: 1px solid {BTN_BG};
        padding: 10px;
        border-radius: 6px;
        color: {FG_COLOR};
        font-size: 10pt;
    }}
    QLineEdit:focus {{
        border: 1px solid {ACCENT_COLOR};
    }}
    
    /* --- Text/List Areas --- */
    QTextEdit, QListWidget {{
        background-color: {LIST_BG};
        border: 1px solid {BTN_BG};
        border-radius: 6px;
        color: {FG_COLOR};
        padding: 4px;
    }}
    QTextEdit {{
        font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    }}
    QListWidget::item {{
        padding: 8px;
        border-radius: 4px;
    }}
    QListWidget::item:hover {{
        background-color: {BTN_BG_ACTIVE};
    }}
    QListWidget::item:selected {{
        background-color: {ACCENT_COLOR};
        color: white;
    }}

    /* --- Tab Widget --- */
    QTabWidget::pane {{
        border: none;
        background-color: {FRAME_BG};
    }}
    QTabWidget::tab-bar {{
        alignment: left;
    }}
    QTabBar::tab {{
        background-color: {FRAME_BG};
        color: {FG_DARKER};
        padding: 10px 14px;
        font-weight: 600;
        border-radius: 0px;
        border-bottom: 2px solid {FRAME_BG};
    }}
    QTabBar::tab:hover {{
        background-color: {BTN_BG_ACTIVE};
        color: {FG_COLOR};
    }}
    QTabBar::tab:selected {{
        background-color: {FRAME_BG};
        color: {ACCENT_COLOR};
        border-bottom: 2px solid {ACCENT_COLOR};
    }}

    /* --- Progress Bar --- */
    QProgressBar {{
        border: 1px solid {BTN_BG};
        border-radius: 6px;
        text-align: center;
        color: {FG_COLOR};
        background-color: {FRAME_BG};
        font-weight: 600;
        height: 22px; /* Set fixed height */
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT_COLOR};
        border-radius: 5px;
    }}
    
    /* --- Scrollbars --- */
    QScrollArea {{
        border: none;
        background-color: {BG_COLOR};
    }}
    QScrollBar:vertical {{
        background-color: {BG_COLOR};
        width: 12px;
        margin: 0;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {BTN_BG_ACTIVE};
        min-height: 20px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {ACCENT_COLOR};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QScrollBar:horizontal {{
        background-color: {BG_COLOR};
        height: 12px;
        margin: 0;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {BTN_BG_ACTIVE};
        min-width: 20px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {ACCENT_COLOR};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}

    /* --- Splitter --- */
    QSplitter::handle {{
        background-color: {BTN_BG};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
"""


# --- Window Filter Configuration (imported from config module) ---
JUNK_WINDOW_TITLES = config.JUNK_WINDOW_TITLES

class ClientGUISignals(QObject):
     
    signal_add_chat = pyqtSignal(str, str)
    signal_handle_tcp = pyqtSignal(dict)
    signal_update_video = pyqtSignal(object, QPixmap)
    signal_update_grid = pyqtSignal()
    signal_update_member_list = pyqtSignal(list)
    signal_update_visibility = pyqtSignal(str, bool)
    signal_handle_camera_fail = pyqtSignal(str)
    signal_trigger_shutdown = pyqtSignal()
    signal_update_file_progress = pyqtSignal(int, str)
    signal_show_file_progress = pyqtSignal(str, str)
    signal_hide_file_progress = pyqtSignal()
    signal_update_file_log = pyqtSignal()
    signal_set_button_state = pyqtSignal(QPushButton, dict)
    signal_update_screen_share = pyqtSignal(QPixmap)
    signal_show_black_screen = pyqtSignal(bool)
    signal_open_side_panel = pyqtSignal(str)
    signal_ask_yes_no = pyqtSignal(str, str, str)
    signal_select_save_file = pyqtSignal(str, str, str)
    signal_set_active_speaker = pyqtSignal(str)
    signal_discovery_failed = pyqtSignal()

class WorkerThread(QThread):
     
    def __init__(self, target_func, parent=None):
        super().__init__(parent)
        self.target_func = target_func

    def run(self):
        if self.target_func:
            self.target_func()

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        """
        [LoginDialog] Initializes the login modal window.
        """
        super().__init__(parent)
        self.setWindowTitle("Join LAN Collab")
        self.setWindowIcon(QIcon(self.create_icon_pixmap()))
        self.setMinimumWidth(350)
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(15)
        root_layout.setContentsMargins(20, 20, 20, 20)
        title_label = QLabel("Join Meeting")
        title_label.setObjectName("Header")
        title_label.setStyleSheet("font-size: 16pt; font-weight: 600; padding-bottom: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(title_label)
        self.username_edit = QLineEdit(self)
        self.username_edit.setPlaceholderText("Your Name")
        self.code_edit = QLineEdit(self)
        self.code_edit.setPlaceholderText("e.g., 123-456-789")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.addRow(QLabel("Username:"), self.username_edit)
        form_layout.addRow(QLabel("Meet Code:"), self.code_edit)
        root_layout.addLayout(form_layout)
        root_layout.addSpacing(10)
        button_box = QDialogButtonBox()
        join_btn = QPushButton("Join")
        join_btn.setObjectName("BlueButton")
        join_btn.setDefault(True)
        cancel_btn = QPushButton("Cancel")
        button_box.addButton(join_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root_layout.addWidget(button_box)
        self.setLayout(root_layout)

    def create_icon_pixmap(self):
        """
        [LoginDialog] Generates the 'LC' application icon dynamically.
        
        Creates a 64x64 QPixmap, draws a rounded rectangle with the
        accent color, and centers the text 'LC' on it.
        """
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(ACCENT_COLOR)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 64, 64, 12, 12)
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "LC")
        painter.end()
        return pixmap

    def getValues(self):
        """
        [LoginDialog] Returns the entered (username, code) if 'Join' was
        clicked, or (None, None) if 'Cancel' was clicked.
        """
        if self.result() == QDialog.DialogCode.Accepted:
            username = self.username_edit.text().strip()
            code = self.code_edit.text().strip()
            if username and code:
                return username, code
        return None, None
    
class ClientGUI(QWidget):

    def __init__(self, username, code):
        """
        [ClientGUI] Initializes the main client application window.
        
        Sets up all state variables, networking components, media devices
        (PyAudio, OpenCV), and Qt signals. It then starts the initial
        'connect_to_server' thread.
        """
        super().__init__()
        self.username = username
        self.meet_code = code
        self.server_host = None 

        # --- State Variables (Identical) ---
        self.video_enabled = False 
        self.audio_enabled = True  
        self.screen_sharing_active = threading.Event()
        self.is_presenting = False
        self.share_target = None 
        self.is_side_panel_open = False
        self._file_log_entries = []
        self._temp_filepath_store = {}
        self._pending_file_offers = {}
        self.screen_presenter_name = "No one is presenting"
        self.video_frames = {}
        self.my_video_label = None
        self.is_connected = threading.Event()
        self.active_speaker_username = None
        self.last_speaker_timestamp = {self.username: time.time()}
        self.current_file_transfer_id = None

        # --- Networking ---
        self.tcp_socket = None
        self.udp_socket = None
        self.server_udp_addr = None
        self.tcp_lock = threading.Lock()

        # --- Media Devices ---
        self.camera = None
        self.p_audio = pyaudio.PyAudio()
        self.audio_stream_in = None
        self.audio_stream_out = None
        self._camera_lock = threading.Lock()
        
        # --- NEW: Video/Performance State ---
        self.video_encoder = None
        self.video_frame_count = 0
        self.screen_decoder = None
        self.last_local_video_update = 0
        self.last_video_update_times = {}
        self.video_fragment_buffers = {}
        
        # --- PyQt Specific ---
        self.signals = ClientGUISignals()
        self._dialog_callbacks = {} 
        
        # --- Scrolling Grid (Identical) ---
        self.video_grid_scroll_area = None
        self.video_grid_widget = None
        self.video_grid_layout = None
        
        self.setup_gui()
        self.connect_signals()

        self.connect_thread = WorkerThread(target_func=self.connect_to_server)
        self.connect_thread.start()

    def setup_gui(self):
        """
        Builds the entire PyQt6 user interface.
        
        This function constructs all widgets (buttons, labels, layouts,
        the side panel, the video grid) and connects their local
        click/change events to handler functions (like on_toggle_audio_click).
        """
        self.setWindowTitle(f"LAN Collab - {self.username}")
        self.setGeometry(100, 100, 1100, 750)
        self.setMinimumSize(900, 600)
        self.setWindowIcon(QIcon(LoginDialog().create_icon_pixmap()))
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.main_content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_screen_widget = QFrame(self)
        main_screen_widget.setObjectName("MainScreen")
        main_screen_layout = QHBoxLayout(main_screen_widget)
        main_screen_layout.setContentsMargins(0, 0, 0, 0)
        main_screen_layout.setSpacing(5)
        self.center_stack = QStackedLayout()
        self.video_grid_scroll_area = QScrollArea(self)
        self.video_grid_scroll_area.setWidgetResizable(True)
        self.video_grid_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.video_grid_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.video_grid_widget = QWidget(self)
        self.video_grid_layout = QGridLayout(self.video_grid_widget)
        self.video_grid_layout.setSpacing(10)
        self.video_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.video_grid_scroll_area.setWidget(self.video_grid_widget)
        self.screen_share_widget = QWidget()
        screen_share_layout = QStackedLayout(self.screen_share_widget)
        screen_share_layout.setContentsMargins(0,0,0,0)
        self.screen_share_label = QLabel(self)
        self.screen_share_label.setScaledContents(True)
        self.screen_share_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.screen_share_label.setStyleSheet("background-color: black;")
        screen_share_layout.addWidget(self.screen_share_label)
        self.center_stack.addWidget(self.video_grid_scroll_area)
        self.center_stack.addWidget(self.screen_share_widget)
        center_stack_widget = QWidget()
        center_stack_widget.setLayout(self.center_stack)
        sidebar_container_widget = QWidget()
        sidebar_container_layout = QVBoxLayout(sidebar_container_widget)
        sidebar_container_layout.setContentsMargins(0, 5, 5, 5)
        sidebar_container_layout.setSpacing(5)
        sidebar_container_widget.setFixedWidth(180)
        self.sidebar_nav_up = QPushButton("▲")
        self.sidebar_nav_up.setObjectName("NavArrow")
        self.sidebar_nav_up.clicked.connect(self.scroll_sidebar_up)
        sidebar_container_layout.addWidget(self.sidebar_nav_up, 0, Qt.AlignmentFlag.AlignCenter)
        self.right_video_sidebar_scroll_area = QScrollArea(self)
        self.right_video_sidebar_scroll_area.setWidgetResizable(True)
        self.right_video_sidebar_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.right_video_sidebar_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.right_video_sidebar_widget = QWidget()
        self.right_video_sidebar_layout = QVBoxLayout(self.right_video_sidebar_widget)
        self.right_video_sidebar_layout.setSpacing(10)
        self.right_video_sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.right_video_sidebar_scroll_area.setWidget(self.right_video_sidebar_widget)
        sidebar_container_layout.addWidget(self.right_video_sidebar_scroll_area, 1)
        self.sidebar_nav_down = QPushButton("▼")
        self.sidebar_nav_down.setObjectName("NavArrow")
        self.sidebar_nav_down.clicked.connect(self.scroll_sidebar_down)
        sidebar_container_layout.addWidget(self.sidebar_nav_down, 0, Qt.AlignmentFlag.AlignCenter)
        sidebar_container_widget.hide()
        self.right_video_sidebar_container = sidebar_container_widget
        main_screen_layout.addWidget(center_stack_widget, 1)
        main_screen_layout.addWidget(self.right_video_sidebar_container)
        self.side_panel = QFrame(self)
        self.side_panel.setObjectName("SidePanel")
        self.side_panel.setMinimumWidth(300)
        side_panel_layout = QVBoxLayout(self.side_panel)
        side_panel_layout.setContentsMargins(0, 0, 0, 0)
        side_panel_layout.setSpacing(0)
        close_btn_layout = QHBoxLayout()
        close_btn_layout.setContentsMargins(5, 5, 5, 5)
        close_btn_layout.addStretch(1)
        self.side_panel_close_btn = QPushButton("✕")
        self.side_panel_close_btn.setObjectName("SidePanelCloseButton")
        self.side_panel_close_btn.setFixedSize(28, 28)
        self.side_panel_close_btn.clicked.connect(lambda: self.toggle_side_panel(None))
        close_btn_layout.addWidget(self.side_panel_close_btn)
        side_panel_layout.addLayout(close_btn_layout)
        self.notebook = QTabWidget(self.side_panel)
        chat_tab = QWidget()
        chat_layout = QVBoxLayout(chat_tab)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_area = QTextEdit(self)
        self.chat_area.setReadOnly(True)
        chat_layout.addWidget(self.chat_area, 1)
        chat_entry_layout = QHBoxLayout()
        self.chat_entry = QLineEdit(self)
        self.chat_entry.setPlaceholderText("Send a message...")
        self.chat_entry.returnPressed.connect(self.send_chat_message_event)
        chat_entry_layout.addWidget(self.chat_entry, 1)
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("BlueButton")
        self.send_btn.clicked.connect(self.send_chat_message_event)
        chat_entry_layout.addWidget(self.send_btn)
        chat_layout.addLayout(chat_entry_layout)
        self.notebook.addTab(chat_tab, "Chat")
        member_tab = QWidget()
        member_layout = QVBoxLayout(member_tab)
        member_layout.setContentsMargins(10, 10, 10, 10)
        self.member_listbox = QListWidget(self)
        self.member_listbox.setStyleSheet("QListWidget::item { padding: 10px; }")
        member_layout.addWidget(self.member_listbox)
        self.notebook.addTab(member_tab, "Members")
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(10)
        self.file_send_btn = QPushButton("Upload File")
        self.file_send_btn.setObjectName("BlueButton")
        self.file_send_btn.clicked.connect(self.select_file_to_send)
        file_layout.addWidget(self.file_send_btn)
        self.file_progress_widget = QWidget(self)
        file_progress_layout = QHBoxLayout(self.file_progress_widget)
        file_progress_layout.setContentsMargins(0,0,0,0)
        file_progress_layout.setSpacing(5)
        self.file_progress_label = QLabel("Transfer Progress")
        self.file_progress_label.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        self.file_progress_bar = QProgressBar(self)
        self.file_progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.file_cancel_btn = QPushButton("✕")
        self.file_cancel_btn.setObjectName("CancelButton")
        self.file_cancel_btn.setToolTip("Cancel Transfer")
        self.file_cancel_btn.clicked.connect(self.on_cancel_file_transfer)
        file_progress_layout.addWidget(self.file_progress_label)
        file_progress_layout.addWidget(self.file_progress_bar, 1)
        file_progress_layout.addWidget(self.file_cancel_btn)
        file_layout.addWidget(self.file_progress_widget)
        file_layout.addWidget(QLabel("Available Files"))
        self.available_files_list = QListWidget(self) 
        self.available_files_list.setAlternatingRowColors(True)
        file_layout.addWidget(self.available_files_list, 1)
        self.file_download_btn = QPushButton("Download Selected File")
        self.file_download_btn.setObjectName("GreenButton")
        self.file_download_btn.clicked.connect(self.on_download_file_click) 
        file_layout.addWidget(self.file_download_btn)
        self.hide_file_progress()
        self.notebook.addTab(file_tab, "Files")
        side_panel_layout.addWidget(self.notebook, 1)
        self.main_content_splitter.addWidget(main_screen_widget)
        self.main_content_splitter.addWidget(self.side_panel)
        self.main_content_splitter.setSizes([750, 350])
        self.side_panel.hide()
        self.is_side_panel_open = False
        root_layout.addWidget(self.main_content_splitter, 1)
        self.bottom_control_bar = QFrame(self)
        self.bottom_control_bar.setObjectName("BottomBar")
        self.bottom_control_bar.setFixedHeight(70)
        bottom_bar_layout = QHBoxLayout(self.bottom_control_bar)
        bottom_bar_layout.setContentsMargins(20, 10, 20, 10)
        bottom_bar_layout.setSpacing(10)
        bottom_bar_layout.addWidget(QLabel(f"Code: {self.meet_code}"), 0, Qt.AlignmentFlag.AlignLeft)
        center_controls_layout = QHBoxLayout()
        center_controls_layout.setSpacing(10)
        self.audio_btn = QPushButton("Mic")
        self.audio_btn.setObjectName("ControlButton")
        self.audio_btn.setToolTip("Toggle Microphone")
        self.audio_btn.clicked.connect(self.on_toggle_audio_click)
        center_controls_layout.addWidget(self.audio_btn)
        self.video_btn = QPushButton("Cam")
        self.video_btn.setObjectName("ControlButtonRed")
        self.video_btn.setToolTip("Toggle Camera")
        self.video_btn.clicked.connect(self.on_toggle_video_click)
        center_controls_layout.addWidget(self.video_btn)
        self.share_btn = QPushButton("Share")
        self.share_btn.setObjectName("ControlButton")
        self.share_btn.setToolTip("Share Screen or Window")
        self.share_btn.clicked.connect(self.start_screen_share)
        center_controls_layout.addWidget(self.share_btn)
        self.end_call_btn = QPushButton("End")
        self.end_call_btn.setObjectName("ControlButtonRed")
        self.end_call_btn.setToolTip("Leave Meeting")
        self.end_call_btn.setFixedSize(60, 40)
        self.end_call_btn.setStyleSheet("border-radius: 20px;")
        self.end_call_btn.clicked.connect(lambda: self.close())
        center_controls_layout.addWidget(self.end_call_btn)
        right_controls_layout = QHBoxLayout()
        right_controls_layout.setSpacing(10)
        self.members_btn = QPushButton("Members")
        self.members_btn.setToolTip("Show Participants")
        self.members_btn.clicked.connect(lambda: self.toggle_side_panel('members'))
        right_controls_layout.addWidget(self.members_btn)
        self.chat_btn = QPushButton("Chat")
        self.chat_btn.setToolTip("Show Chat")
        self.chat_btn.clicked.connect(lambda: self.toggle_side_panel('chat'))
        right_controls_layout.addWidget(self.chat_btn)
        self.file_btn = QPushButton("Files")
        self.file_btn.setToolTip("Show File Transfers")
        self.file_btn.clicked.connect(lambda: self.toggle_side_panel('files'))
        right_controls_layout.addWidget(self.file_btn)
        bottom_bar_layout.addStretch(1)
        bottom_bar_layout.addLayout(center_controls_layout)
        bottom_bar_layout.addStretch(1)
        bottom_bar_layout.addLayout(right_controls_layout)
        root_layout.addWidget(self.bottom_control_bar)
        self.add_video_feed(self.username, is_local=True)

    def connect_signals(self):
        """
        Connects all custom Qt signals from the 'ClientGUISignals' class
        to their corresponding @pyqtSlot functions in the main thread.
        
        This is the core mechanism that allows background threads to safely
        trigger UI updates (e.g., 'signal_add_chat' from a network thread
        connects to '_slot_add_chat' in the GUI thread).
        """
        self.signals.signal_add_chat.connect(self._slot_add_chat)
        self.signals.signal_handle_tcp.connect(self.handle_tcp_message)
        self.signals.signal_update_video.connect(self._slot_update_video)
        self.signals.signal_update_grid.connect(self.update_grid_layout)
        self.signals.signal_update_member_list.connect(self._slot_update_member_list)
        self.signals.signal_update_visibility.connect(self.update_video_frame_visibility)
        self.signals.signal_handle_camera_fail.connect(self._slot_handle_camera_fail)
        self.signals.signal_trigger_shutdown.connect(self._slot_trigger_full_shutdown)
        self.signals.signal_update_file_progress.connect(self.update_file_progress)
        self.signals.signal_show_file_progress.connect(self.show_file_progress)
        self.signals.signal_hide_file_progress.connect(self.hide_file_progress)
        self.signals.signal_update_file_log.connect(self._update_file_log_display)
        self.signals.signal_set_button_state.connect(self._slot_set_button_state)
        self.signals.signal_update_screen_share.connect(self._slot_update_screen_share)
        self.signals.signal_show_black_screen.connect(self._slot_show_black_screen)
        self.signals.signal_open_side_panel.connect(self.open_side_panel_to)
        self.signals.signal_ask_yes_no.connect(self._slot_ask_yes_no)
        self.signals.signal_select_save_file.connect(self._slot_select_save_file)
        self.signals.signal_set_active_speaker.connect(self._slot_set_active_speaker)
        self.signals.signal_discovery_failed.connect(self._slot_on_discovery_failed)

    # --- Core Logic (Networking, Media) ---
    def connect_to_server(self):
        """
        [Thread Target]
        Handles the initial server discovery process.
        
        It broadcasts a UDP "discover" message with the meet code. It then
        listens for 2 seconds for a direct reply from the server.
        - On Success: It sets 'self.server_host' and starts the
        'connect_directly' thread.
        - On Failure: It emits 'signal_discovery_failed' to ask the user
        for the IP manually.
        """
        self.signals.signal_add_chat.emit("--- Discovering server... ---", "system")
        discover_socket = None
        try:
            discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = safe_serialize({'type': 'discover', 'code': self.meet_code})
            discover_socket.sendto(msg, ('<broadcast>', DISCOVERY_PORT))
            self.signals.signal_add_chat.emit(f"--- Searching for code '{self.meet_code}'... ---", "system")
            found_servers = []
            discover_socket.setblocking(False)
            start_time = time.time()
            while (time.time() - start_time) < 2.0:
                try:
                    data, addr = discover_socket.recvfrom(1024)
                    reply = safe_deserialize(data)
                    if reply.get('type') == 'discover_reply' and reply.get('ip') not in found_servers:
                        found_servers.append(reply.get('ip'))
                        self.signals.signal_add_chat.emit(f"--- Found server at {reply.get('ip')}... ---", "system")
                except (BlockingIOError, InterruptedError):
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Discovery listen error: {e}")
            
            if len(found_servers) == 0:
                raise socket.timeout("No server found with that code")
            else:
                self.server_host = found_servers[0]
                self.server_udp_addr = (self.server_host, UDP_PORT)
                self.signals.signal_add_chat.emit(f"--- Server found at {self.server_host}. Connecting... ---", "system")
                
                # --- START CHANGE: Discovery SUCCEEDED ---
                # Start the direct connection thread
                self.connect_thread_2 = WorkerThread(target_func=self.connect_directly)
                self.connect_thread_2.start()
                # --- END CHANGE ---

        except socket.timeout:
            # --- START CHANGE: Discovery FAILED ---
            # Signal the main thread to ask for an IP
            self.signals.signal_discovery_failed.emit()
            
        except Exception as e:
            self.signals.signal_handle_tcp.emit({'type': '_show_error_and_quit', 'title': 'Discovery Failed', 'message': f'An error occurred: {e}'})
            return
        
        finally:
            if discover_socket:
                discover_socket.setblocking(True)
                discover_socket.close()
        
    def connect_directly(self):
        """
        This is the second part of the connection
        """
        try:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            unencrypted_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket = self.ssl_context.wrap_socket(unencrypted_socket, server_hostname=self.server_host)
            self.tcp_socket.connect((self.server_host, TCP_PORT))
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, config.VIDEO_UDP_RCVBUF_BYTES)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, config.VIDEO_UDP_SNDBUF_BYTES)
            self.udp_socket.bind(('', 0))
            my_udp_port = self.udp_socket.getsockname()[1]
            join_message = f"JOIN:{self.username}:{my_udp_port}:{self.meet_code}"
            self.tcp_socket.send(join_message.encode('utf-8'))
            self.is_connected.set()
            self.signals.signal_add_chat.emit(f"--- Connected to {self.server_host} as '{self.username}' ---", "system")
            self.start_media_devices()
            threading.Thread(target=self.receive_tcp_data, daemon=True, name="TCP-Recv").start()
            threading.Thread(target=self.receive_udp_data, daemon=True, name="UDP-Recv").start()
            threading.Thread(target=self.send_video, daemon=True, name="Vid-Send").start()
            threading.Thread(target=self.send_audio, daemon=True, name="Aud-Send").start()
        except Exception as e:
            self.signals.signal_handle_tcp.emit({'type': '_show_error_and_quit', 'title': 'Connection Failed', 'message': f"Could not connect to server at {self.server_host}:{TCP_PORT}\n{e}"})
    
    def start_media_devices(self):
        """
        Initializes PyAudio input/output streams and checks for a camera.
        
        This function is called once the TCP connection is successful.
        It attempts to open the microphone and speaker streams.
        If any device fails, it logs the error, disables the corresponding
        feature, and updates the UI button state.
        """
        try:
            self.audio_stream_in = self.p_audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            self.audio_stream_out = self.p_audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
            self.audio_enabled = True
            self.signals.signal_add_chat.emit("--- Audio devices started. ---", "system")
            self.signals.signal_set_button_state.emit(self.audio_btn, {"text": "Mic", "objectName": "ControlButton", "toolTip": "Mute Microphone"})
        except Exception as e:
            self.signals.signal_add_chat.emit(f"--- [WARNING] Audio failed ({e}). You will be muted. ---", "system")
            self.audio_enabled = False
            self.signals.signal_set_button_state.emit(self.audio_btn, {"text": "Mic", "objectName": "ControlButtonRed", "enabled": False, "toolTip": "Audio failed"})
        try:
            test_cam = cv2.VideoCapture(0)
            if not test_cam.isOpened(): raise Exception("Camera not found")
            test_cam.release()
            self.signals.signal_add_chat.emit("--- Camera found. Video is ready. ---", "system")
            self.video_enabled = False
            self.signals.signal_set_button_state.emit(self.video_btn, {"text": "Cam", "objectName": "ControlButtonRed", "enabled": True, "toolTip": "Start Camera"})
        except Exception as e:
            self.signals.signal_add_chat.emit(f"--- [WARNING] No camera found ({e}). Video disabled. ---", "system")
            self.video_enabled = False
            self.camera = None
            self.signals.signal_set_button_state.emit(self.video_btn, {"text": "Cam", "objectName": "ControlButtonRed", "enabled": False, "toolTip": "No camera found"})
            self.signals.signal_update_visibility.emit(self.username, False)

    def send_video(self):
        """
        --- !!! MODIFIED for H.264 ENCODING !!! ---
        """
        try:
            while self.is_connected.is_set():
                frame_to_send = None
                frame_to_display = None
                
                with self._camera_lock:
                    if self.video_enabled and self.camera is not None and self.camera.isOpened() and self.video_encoder is not None:
                        try:
                            ret, frame = self.camera.read()
                            if not ret:
                                print("Camera read failed, cleaning up in-thread...")
                                try: self.camera.release()
                                except Exception: pass
                                self.camera = None
                                self.video_enabled = False # Set state
                                self.signals.signal_handle_camera_fail.emit("Camera read failed")
                                continue # Stop processing
                            
                            frame_resized = cv2.resize(frame, (self.video_encoder.width, self.video_encoder.height))
                            frame_to_send = frame_resized
                            frame_to_display = frame.copy()
                            
                        except Exception as e:
                            # --- FIX: Clean up HERE, inside the lock ---
                            print(f"Camera read error {e}, cleaning up in-thread...")
                            try: self.camera.release()
                            except Exception: pass
                            self.camera = None
                            self.video_enabled = False # Set state
                            self.signals.signal_handle_camera_fail.emit(f"Camera read error: {e}")
                            continue # Stop processing
                
                if frame_to_send is not None:
                    try:
                        av_frame = av.VideoFrame.from_ndarray(frame_to_send, format="bgr24")
                        av_frame.pts = self.video_frame_count
                        self.video_frame_count += 1
                        
                        packets = self.video_encoder.encode(av_frame)
                        
                        for packet in packets:
                            packet_bytes = bytes(packet)
                            if not self.udp_socket:
                                continue

                            # Split large encoded packets so motion-heavy frames do not get dropped.
                            if len(packet_bytes) <= VIDEO_FRAGMENT_CHUNK_BYTES:
                                payload = {
                                    'type': 'video_packet',
                                    'from': self.username,
                                    'data': packet_bytes
                                }
                                self.udp_socket.sendto(safe_serialize(payload), self.server_udp_addr)
                            else:
                                total_chunks = math.ceil(len(packet_bytes) / VIDEO_FRAGMENT_CHUNK_BYTES)
                                packet_id = f"{self.username}-{self.video_frame_count}-{time.time_ns()}"
                                for chunk_index in range(total_chunks):
                                    start = chunk_index * VIDEO_FRAGMENT_CHUNK_BYTES
                                    end = start + VIDEO_FRAGMENT_CHUNK_BYTES
                                    frag_payload = {
                                        'type': 'video_frag',
                                        'from': self.username,
                                        'packet_id': packet_id,
                                        'chunk_index': chunk_index,
                                        'total_chunks': total_chunks,
                                        'chunk': packet_bytes[start:end]
                                    }
                                    self.udp_socket.sendto(safe_serialize(frag_payload), self.server_udp_addr)
                                
                    except (OSError, socket.error) as e:
                        if self.is_connected.is_set(): print(f"UDP send error: {e}")
                    except Exception as e:
                        print(f"Video encoding/send error: {e}")

                # Local video display logic
                if frame_to_display is not None and self.my_video_label:
                    now = time.time()
                    if (now - self.last_local_video_update) > (1 / VIDEO_RENDER_FPS):
                        self.last_local_video_update = now
                        try:
                            label_w = self.my_video_label.width()
                            label_h = self.my_video_label.height()
                            
                            if label_w < 10 or label_h < 10:
                                target_size = (120, 90) if self.is_presenting else (240, 180)
                            else:
                               h, w, _ = frame_to_display.shape 
                               aspect = w / h if h > 0 else 1.0 
                               if label_w / aspect <= label_h: target_size = (label_w, int(label_w / aspect)) if aspect > 0 else (label_w, label_h)
                               else: target_size = (int(label_h * aspect), label_h) if aspect > 0 else (label_w, label_h)
                            
                            target_w = max(1, target_size[0])
                            target_h = max(1, target_size[1])
                            local_frame_resized = cv2.resize(frame_to_display, (target_w, target_h), interpolation=cv2.INTER_AREA)
                            frame_rgb = cv2.cvtColor(local_frame_resized, cv2.COLOR_BGR2RGB)
                            h, w, ch = frame_rgb.shape
                            bytes_per_line = ch * w
                            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                            q_pixmap = QPixmap.fromImage(q_img)
                            self.signals.signal_update_video.emit(self.my_video_label, q_pixmap)
                        except Exception as e: 
                            print(f"Error in local video render: {e}")
                
                time.sleep(1 / CAPTURE_FPS)

        except Exception as e:
            if self.is_connected.is_set(): print(f"Video send thread crashed: {e}")
        finally:
            self.stop_camera()
            print("Video send thread stopped.")

    def send_audio(self):
        """
        [Thread Target: Aud-Send]
        Captures, compresses, and sends audio packets.
        
        This loop runs on a high-precision timer. It reads a chunk of
        PCM audio from the microphone, checks if 'self.audio_enabled'
        is True, compresses the data using Mu-law, and sends it to the
        server via UDP.
        """
        perf_counter = time.perf_counter
        interval = float(CHUNK) / RATE
        next_wake_time = perf_counter()
        while self.is_connected.is_set():
            try:
                sleep_duration = next_wake_time - perf_counter()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                next_wake_time += interval
                if self.audio_enabled and self.audio_stream_in:
                    data_pcm = self.audio_stream_in.read(CHUNK, exception_on_overflow=False)
                    data_pcm_array = np.frombuffer(data_pcm, dtype=np.int16)
                    data_compressed = lin2ulaw_numpy(data_pcm_array)
                    data_payload = safe_serialize({"type": "audio", "from": self.username, "data": data_compressed})
                    if self.udp_socket: 
                        self.udp_socket.sendto(data_payload, self.server_udp_addr)
            except (IOError, OSError) as e:
                self.signals.signal_add_chat.emit(f"--- [ERROR] Audio input failed: {e} ---", "system")
                self.audio_enabled = False
                self.signals.signal_set_button_state.emit(self.audio_btn, {"text": "Mic", "objectName": "ControlButtonRed", "enabled": False, "toolTip": "Audio failed"})
                break
            except Exception as e: 
                if self.is_connected.is_set(): 
                    print(f"Audio send error: {e}")
    
    def receive_udp_data(self):
        """
        --- !!! MODIFIED for H.264 DECODING !!! ---
        Decodes H.264 packets from UDP.
        """
        while self.is_connected.is_set():
            try:
                if not self.udp_socket: break
                packet, _ = self.udp_socket.recvfrom(65536)
                payload = safe_deserialize(packet)
                sender = payload.get("from", "Unknown")
                if sender == self.username: continue
                msg_type = payload.get("type")

                # Periodic cleanup of stale/incomplete video fragment assemblies.
                if self.video_fragment_buffers:
                    now_cleanup = time.time()
                    stale_keys = []
                    for key, entry in self.video_fragment_buffers.items():
                        if now_cleanup - entry.get('timestamp', now_cleanup) > config.VIDEO_BUFFER_TIMEOUT_SEC:
                            stale_keys.append(key)
                    for key in stale_keys:
                        del self.video_fragment_buffers[key]
                
                if msg_type == "audio":
                    if self.audio_stream_out:
                        compressed_data = payload["data"]
                        pcm_data = ulaw2lin_numpy(compressed_data)
                        self.audio_stream_out.write(pcm_data)
                        
                elif msg_type == "video_packet":
                    details = self.video_frames.get(sender)

                    if details:
                        with details['decode_lock']:
                            # We must get the decoder *inside* the lock
                            decoder = details.get('decoder')
                            label = details.get('label')
                            
                            if decoder and label:
                                try:
                                    av_packet = av.Packet(payload['data'])
                                    frames = decoder.decode(av_packet)
                                    if frames:
                                        now = time.time()
                                        last_ts = self.last_video_update_times.get(sender, 0.0)
                                        min_interval = 1.0 / max(1, VIDEO_RENDER_FPS)
                                        if (now - last_ts) >= min_interval:
                                            self.last_video_update_times[sender] = now
                                            # Render only the latest decoded frame to minimize lag buildup.
                                            q_pixmap = self.av_frame_to_qpixmap(frames[-1], label)
                                            self.signals.signal_update_video.emit(label, q_pixmap)
                                        
                                # --- *** Catch generic av.AVError *** ---
                                except av.error.AVError:
                                    # Don't recreate decoder on every error — it loses all state.
                                    # Just skip this packet; the next keyframe will fix it.
                                    pass

                elif msg_type == "video_frag":
                    packet_id = payload.get('packet_id')
                    chunk_index = payload.get('chunk_index')
                    total_chunks = payload.get('total_chunks')
                    chunk = payload.get('chunk')

                    if (
                        not packet_id
                        or not isinstance(chunk_index, int)
                        or not isinstance(total_chunks, int)
                        or total_chunks <= 0
                        or chunk_index < 0
                        or chunk_index >= total_chunks
                        or not isinstance(chunk, bytes)
                    ):
                        continue

                    frag_key = (sender, packet_id)
                    entry = self.video_fragment_buffers.get(frag_key)
                    if entry is None:
                        entry = {
                            'timestamp': time.time(),
                            'total': total_chunks,
                            'chunks': {}
                        }
                        self.video_fragment_buffers[frag_key] = entry

                    # Ignore inconsistent fragment sets for the same packet_id.
                    if entry['total'] != total_chunks:
                        del self.video_fragment_buffers[frag_key]
                        continue

                    entry['chunks'][chunk_index] = chunk
                    entry['timestamp'] = time.time()

                    if len(entry['chunks']) == entry['total']:
                        try:
                            packet_bytes = b"".join(entry['chunks'][i] for i in range(entry['total']))
                        except KeyError:
                            del self.video_fragment_buffers[frag_key]
                            continue

                        del self.video_fragment_buffers[frag_key]

                        details = self.video_frames.get(sender)
                        if details:
                            with details['decode_lock']:
                                decoder = details.get('decoder')
                                label = details.get('label')

                                if decoder and label:
                                    try:
                                        av_packet = av.Packet(packet_bytes)
                                        frames = decoder.decode(av_packet)
                                        if frames:
                                            now = time.time()
                                            last_ts = self.last_video_update_times.get(sender, 0.0)
                                            min_interval = 1.0 / max(1, VIDEO_RENDER_FPS)
                                            if (now - last_ts) >= min_interval:
                                                self.last_video_update_times[sender] = now
                                                q_pixmap = self.av_frame_to_qpixmap(frames[-1], label)
                                                self.signals.signal_update_video.emit(label, q_pixmap)
                                    except av.error.AVError:
                                        # Don't recreate decoder — just skip and wait for next keyframe
                                        pass
                    
            except (KeyError, IndexError): pass
            except ValueError as e:
                print(f"AUDIO DECODE (ValueError): {e}")
            except AttributeError as e:
                pass
                # print(f"VIDEO/DEVICE (AttributeError): {e}")
            except OSError: 
                if self.is_connected.is_set(): print("UDP Socket closed.")
                break
            except Exception as e:
                if self.is_connected.is_set(): print(f"UDP Receive Error: {e}")
                pass
    
    def receive_tcp_data(self):
        """
        [Thread Target: TCP-Recv]
        Listens for all incoming TCP data from the server.
        
        This loop reads the 8-byte length prefix, then reads that many
        bytes to get the complete JSON message. It de-serializes the
        message and emits 'signal_handle_tcp' to pass the resulting
        dictionary to the main thread for processing.
        """
        try:
            while self.is_connected.is_set():
                if not self.tcp_socket: break
                prefix_data = self.tcp_socket.recv(8)
                if not prefix_data:
                    self.signals.signal_add_chat.emit("--- Server closed the connection. ---", "system")
                    break 
                payload_size = struct.unpack("Q", prefix_data)[0]
                payload_data = b""
                while len(payload_data) < payload_size:
                    chunk_size = min(4096, payload_size - len(payload_data))
                    chunk = self.tcp_socket.recv(chunk_size)
                    if not chunk: raise ConnectionError("Server disconnected mid-payload")
                    payload_data += chunk
                message = safe_deserialize(payload_data)
                self.signals.signal_handle_tcp.emit(message)
        except (ConnectionResetError, ConnectionError, struct.error, EOFError, OSError) as e:
            if self.is_connected.is_set():
                 self.signals.signal_add_chat.emit(f"--- Connection lost to server: {e} ---", "system")
        except Exception as e:
            if self.is_connected.is_set():
                 self.signals.signal_add_chat.emit(f"[ERROR] TCP Connection lost: {e}", "system")
        finally:
            if self.is_connected.is_set():
                self.signals.signal_add_chat.emit("--- Disconnected. Cleaning up... ---", "system")
                self.is_connected.clear() 
                self.signals.signal_trigger_shutdown.emit()
    
    def send_tcp_message(self, message_dict):
        """
        Serializes, packs, and sends a message to the server's TCP socket.
        
        This is the client-side counterpart to the server's 'pack_and_send'.
        It uses the same (Length-Prefix) + (Data) format to send
        JSON messages securely over the SSL/TLS-wrapped TCP socket.
        """
        if not self.tcp_socket or not self.is_connected.is_set(): return
        try:
            data = safe_serialize(message_dict)
            prefix = struct.pack("Q", len(data))
            with self.tcp_lock:
                self.tcp_socket.sendall(prefix + data)
        except (OSError, ConnectionError) as e:
            if self.is_connected.is_set():
                print(f"Failed to send TCP message: {e}")
        except Exception as e:
            print(f"Error packing TCP message: {e}")

    def screen_share_loop(self):
        """
        --- !!! MODIFIED for H.264 ENCODING !!! ---
        """
        screen_encoder = None
        last_size = (0, 0)
        screen_frame_count = 0
        
        try:
            with mss.mss() as sct:
                while self.screen_sharing_active.is_set() and self.is_connected.is_set():
                    try:
                        bbox = None
                        if self.share_target['type'] == 'screen':
                            bbox = sct.monitors[1]
                        
                        elif self.share_target['type'] == 'window':
                            windows = gw.getWindowsWithTitle(self.share_target['title'])
                            if not windows:
                                raise Exception("Window not found")
                            w = windows[0]
                            if not w.visible or w.isMinimized or w.area == 0:
                                raise Exception("Window not visible or minimized")
                            bbox = {'top': w.top, 'left': w.left, 'width': w.width, 'height': w.height}
                        
                        if not bbox or bbox['width'] <= 0 or bbox['height'] <= 0:
                            raise Exception("Invalid share target or size")
                        
                        img_shot = sct.grab(bbox)
                        img_pil = Image.frombytes("RGB", img_shot.size, img_shot.rgb)
                        base_width = 960
                        w_percent = (base_width / float(img_pil.size[0])) if img_pil.size[0] > 0 else 0
                        h_size = int((float(img_pil.size[1]) * float(w_percent)))
                        h_size = (h_size // 2) * 2
                        target_w = max(1, base_width)
                        target_h = max(1, h_size)
                        img_resized = img_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        current_size = img_resized.size
                        
                        if current_size[0] == 0 or current_size[1] == 0:
                            raise Exception("Invalid resize")

                        if current_size != last_size or screen_encoder is None:
                            # --- No .close() method, flush with None ---
                            if screen_encoder: 
                                for packet in screen_encoder.encode(None): # Flush old
                                    msg = {'type': 'screen_packet', 'from': self.username, 'data': bytes(packet)}
                                    self.send_tcp_message(msg)
                                
                            print(f"Initializing screen encoder to {current_size}")
                            screen_encoder = av.CodecContext.create("libx264", "w")
                            screen_encoder.width = current_size[0]
                            screen_encoder.height = current_size[1]
                            screen_encoder.pix_fmt = "yuv420p"
                            screen_encoder.time_base = fractions.Fraction(1, 15)
                            screen_encoder.framerate = 15
                            screen_encoder.gop_size = 30
                            screen_encoder.max_b_frames = 0
                            screen_encoder.options = {
                                "preset": "ultrafast", 
                                "tune": "zerolatency", 
                                "crf": "25",
                            }
                            last_size = current_size
                            screen_frame_count = 0
                        
                        frame_data = np.array(img_resized)
                        frame = av.VideoFrame.from_ndarray(frame_data, format="rgb24")
                        frame.pts = screen_frame_count
                        screen_frame_count += 1

                        packets = screen_encoder.encode(frame)
                        for packet in packets:
                            # --- *** Use bytes(packet) *** ---
                            msg = {'type': 'screen_packet', 'from': self.username, 'data': bytes(packet)}
                            self.send_tcp_message(msg)

                    except Exception as e:
                        print(f"Share loop error (will retry): {e}")
                        # --- Send 'screen_black' to avoid deserialization error ---
                        msg = {'type': 'screen_black', 'from': self.username}
                        self.send_tcp_message(msg)
                        threading.Event().wait(0.5)
                    
                    threading.Event().wait(0.066) # ~15 FPS
                    
        except Exception as e:
            self.signals.signal_add_chat.emit(f"Could not initialize screen capture: {e}", "system")
            if self.is_connected.is_set():
                self.signals.signal_handle_tcp.emit({'type': '_stop_screen_share_ui'})
        finally:
            if screen_encoder:
                try:
                    # --- Flush encoder with None ---
                    packets = screen_encoder.encode(None)
                    for packet in packets:
                        # --- *** Use bytes(packet) *** ---
                        msg = {'type': 'screen_packet', 'from': self.username, 'data': bytes(packet)}
                        self.send_tcp_message(msg)
                except Exception as e:
                    print(f"Error flushing screen encoder: {e}")
                
    def client_upload_file(self, filepath, transfer_id, port):
        """
        [Thread Target: File-Upload]
        Handles the data streaming for a single file upload.
        
        It connects to the server's file port (9100), performs the
        'UPLOAD' handshake, and then reads the local file in chunks,
        sending each chunk over the secure TCP socket. It also
        emits progress signals to update the UI.
        """
        file_socket = None
        try:
            self.signals.signal_set_button_state.emit(self.file_send_btn, {"enabled": False, "text": "Uploading..."})
            self.signals.signal_show_file_progress.emit(transfer_id, f"Uploading {os.path.basename(filepath)}...")
            filesize = os.path.getsize(filepath)
            total_sent = 0
            unencrypted_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            file_socket = self.ssl_context.wrap_socket(unencrypted_file_socket, server_hostname=self.server_host)
            file_socket.connect((self.server_host, port))
            self._temp_filepath_store[transfer_id] = {'socket': file_socket}
            handshake = f"UPLOAD:{transfer_id}\n"
            file_socket.sendall(handshake.encode('utf-8'))
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk: break
                    file_socket.sendall(chunk)
                    total_sent += len(chunk)
                    percent = (total_sent / filesize) * 100
                    self.signals.signal_update_file_progress.emit(int(percent), "Uploading")
            self.signals.signal_add_chat.emit(f"--- File {os.path.basename(filepath)} uploaded to server. ---", "system")
            self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'uploaded'})
        except (OSError, ConnectionError) as e:
            if self.current_file_transfer_id != transfer_id:
                self.signals.signal_add_chat.emit(f"--- Upload {os.path.basename(filepath)} cancelled. ---", "system")
            else:
                self.signals.signal_add_chat.emit(f"[ERROR] File upload failed: {e}", "system")
                self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'failed'})
        except Exception as e:
            self.signals.signal_add_chat.emit(f"[ERROR] File upload failed: {e}", "system")
            self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'failed'})
        finally:
            if transfer_id in self._temp_filepath_store:
                del self._temp_filepath_store[transfer_id]
            if file_socket: file_socket.close()
            self.signals.signal_hide_file_progress.emit()
            self.signals.signal_set_button_state.emit(self.file_send_btn, {"enabled": True, "text": "Upload File"})

    def client_download_file(self, save_path, filename, transfer_id, port, filesize, file_hash):
        """
        [Thread Target: File-Download]
        Handles the data streaming for a single file download.
        
        It connects to the server's file port (9100), performs the
        'DOWNLOAD' handshake, and then reads data from the socket,
        writing it in chunks to the 'save_path'. After, it performs
        an MD5 hash check to verify file integrity.
        """
        file_socket = None
        try:
            self.signals.signal_show_file_progress.emit(transfer_id, f"Downloading {filename}...")
            total_received = 0
            unencrypted_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            file_socket = self.ssl_context.wrap_socket(unencrypted_file_socket, server_hostname=self.server_host)
            file_socket.connect((self.server_host, port))
            
            self._temp_filepath_store[transfer_id] = {'socket': file_socket}

            handshake = f"DOWNLOAD:{transfer_id}\n"
            file_socket.sendall(handshake.encode('utf-8'))
            
            with open(save_path, 'wb') as f:
                while True:
                    chunk = file_socket.recv(4096)
                    if not chunk:
                        break 
                    f.write(chunk)
                    total_received += len(chunk)

                    if filesize > 0:
                        percent = (total_received / filesize) * 100
                        self.signals.signal_update_file_progress.emit(int(min(percent, 100)), "Downloading")
            
            self.signals.signal_add_chat.emit(f"--- Verifying {filename}... ---", "system")
            
            # --- *** Use chunked hashing for verification *** ---
            local_hash = self.hash_file_md5(save_path)
            if local_hash is None:
                raise Exception("Failed to hash downloaded file.")
            # ---

            if file_hash and local_hash == file_hash:
                self.signals.signal_add_chat.emit(f"--- File {filename} received successfully and verified! ---", "system")
                self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'complete'})
            elif not file_hash:
                self.signals.signal_add_chat.emit(f"--- File {filename} received (no hash to verify). ---", "system")
                self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'complete'})
            else:
                if total_received != filesize:
                     raise Exception(f"File size mismatch! Got {total_received} expected {filesize}. File is corrupt.")
                raise Exception(f"Hash mismatch! File is corrupt. Local: {local_hash[:10]}... Remote: {file_hash[:10]}...")

        except (OSError, ConnectionError) as e:
            if self.current_file_transfer_id != transfer_id:
                self.signals.signal_add_chat.emit(f"--- Download {filename} cancelled. ---", "system")
            else:
                self.signals.signal_add_chat.emit(f"[ERROR] File download failed: {e}", "system")
                self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'failed'})
            
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
                    self.signals.signal_add_chat.emit(f"--- Deleted incomplete file {filename} ---", "system")
            except Exception as e_del:
                self.signals.signal_add_chat.emit(f"--- [CRITICAL] Could not delete corrupt file: {e_del} ---", "system")
        except Exception as e:
            self.signals.signal_add_chat.emit(f"[ERROR] File download failed: {e}", "system")
            self.signals.signal_handle_tcp.emit({'type': '_update_file_log', 'id': transfer_id, 'status': 'failed'})
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
                    self.signals.signal_add_chat.emit(f"--- Deleted corrupt file {filename} ---", "system")
            except Exception as e_del:
                self.signals.signal_add_chat.emit(f"--- [CRITICAL] Could not delete corrupt file: {e_del} ---", "system")
        finally:
            if transfer_id in self._temp_filepath_store:
                del self._temp_filepath_store[transfer_id]
            if file_socket: file_socket.close()
            self.signals.signal_hide_file_progress.emit()
    # --- PyQt Slots (Receive signals from threads) ---

    @pyqtSlot(str, str)
    def _slot_add_chat(self, message, tag):
        """
        [Qt Slot]
        Appends a formatted message to the chat QTextEdit.
        
        'tag' (e.g., "system", "local_user", "remote_user") is used
        to apply different CSS styling (color, italics) to the message.
        """
        if tag == "local_user":
            self.chat_area.append(f'<div style="color: {BTN_SUCCESS}; font-weight: 600;">{message}</div>')
        elif tag == "remote_user":
            self.chat_area.append(f'<div style="color: {ACCENT_COLOR};">{message}</div>')
        elif tag == "system":
            self.chat_area.append(f'<div style="color: {FG_DARKER}; font-style: italic;">{message}</div>')
        else:
            self.chat_area.append(message)
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())

    @pyqtSlot(object, QPixmap)
    def _slot_update_video(self, label_widget, q_pixmap):
        """
        [Qt Slot]
        Sets the QPixmap on a specific QLabel widget for a video feed.
        
        This is the final step in the video render pipeline. It receives
        the decoded, resized, and rounded QPixmap and applies it to the
        target QLabel (either a grid tile or the sidebar).
        """
        try:
            if label_widget and self.is_connected.is_set():
                rounded_pixmap = self.round_pixmap(q_pixmap)
                label_widget.setPixmap(rounded_pixmap)
        except RuntimeError as e:
            if "has been deleted" in str(e):
                pass 
            else:
                print(f"Unhandled RuntimeError in _slot_update_video: {e}")
        except Exception as e:
            print(f"Unexpected error in _slot_update_video: {e}")
            
    def round_pixmap(self, pixmap, radius=8):
        """
        Helper function to create rounded corners for a QPixmap.
        
        This uses QPainter to clip the pixmap to a rounded rectangle
        path, making the video feeds match the UI's rounded-corner aesthetic.
        """
        if pixmap.isNull():
            return pixmap
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(pixmap.rect()), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    @pyqtSlot(list)
    def _slot_update_member_list(self, users):
        """
        [Qt Slot]
        Rebuilds the 'Members' tab in the side panel.
        
        It clears the existing list and re-populates it with the 'users'
        list. It applies special styling for "(You)" and the
        current active speaker (prefixing with '►').
        """
        self.member_listbox.clear()
        def sort_key(user):
            if user == self.username:
                return (0, 0)
            if user == self.active_speaker_username:
                return (1, 0)
            return (2, -self.last_speaker_timestamp.get(user, 0)) 
        sorted_users = sorted(users, key=sort_key)
        for i, user in enumerate(sorted_users):
            display_name = f"{user}"
            if user == self.username: 
                display_name += " (You)"
            if user == self.active_speaker_username:
                display_name = f"► {display_name}"
            item = QListWidgetItem(display_name)
            if user == self.username:
                item.setForeground(QColor(BTN_SUCCESS))
                item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            elif user == self.active_speaker_username:
                item.setForeground(QColor(ACCENT_COLOR))
                item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            else:
                item.setForeground(QColor(FG_COLOR))
            self.member_listbox.addItem(item)
            
    @pyqtSlot(str)
    def _slot_handle_camera_fail(self, error_msg):
        """
        [Qt Slot]
        Handles a camera failure detected in a background thread.
        
        This logs the error to the chat, ensures the video state is
        set to 'off', and updates the camera button to its 'disabled'
        state.
        """
        if not self.video_enabled: # Check the state set by the worker thread
            self.signals.signal_add_chat.emit(f"--- [ERROR] Camera failed: {error_msg}. Disabling video. ---", "system")
            # self.video_enabled is already False
            # self.camera is already None
            self._slot_set_button_state(self.video_btn, {"text": "Cam", "objectName": "ControlButtonRed", "toolTip": "Start Camera"})
            self.update_video_frame_visibility(self.username, show_video=False)
            self.send_tcp_message({'type': 'video_toggle', 'status': False})

    @pyqtSlot()
    def _slot_trigger_full_shutdown(self):
        """
        [Qt Slot]
        Triggers a clean shutdown from a background thread.
        
        This is called by the TCP receive thread when the server
        disconnects. It invokes 'self.close()', which properly
        triggers the 'closeEvent' handler.
        """ 
        self.close()

    @pyqtSlot(QPushButton, dict)
    def _slot_set_button_state(self, button, properties):
        """
        [Qt Slot]
        A thread-safe way to change the properties of a QPushButton.
        
        Allows background threads (e.g., media init) to change a
        button's text, objectName (for styling), and enabled status.
        """
        if "text" in properties:
            button.setText(properties["text"])
        if "objectName" in properties:
            button.setObjectName(properties["objectName"])
        if "enabled" in properties:
            button.setEnabled(properties["enabled"])
        if "toolTip" in properties:
            button.setToolTip(properties["toolTip"])
        button.style().polish(button)
        
    @pyqtSlot(QPixmap)
    def _slot_update_screen_share(self, q_pixmap):
        """
        [Qt Slot]
        Updates the main screen-sharing view with a new frame.
        
        This is only active when another user is presenting.
        """
        if not self.is_presenting: return
        self.screen_share_label.setPixmap(q_pixmap)
        
    @pyqtSlot(bool)
    def _slot_show_black_screen(self, show_black):
        """
        [Qt Slot]
        Shows or hides a black screen in the screen-share view.
        
        Used when the presenter's window is minimized or hidden
        to avoid showing a stale frame.
        """
        if not self.is_presenting: return
        if show_black:
            self.screen_share_label.setPixmap(QPixmap())
            self.screen_share_label.setStyleSheet("background-color: black;")
        else:
            self.screen_share_label.setStyleSheet("background-color: black;")
        
    @pyqtSlot(str, str, str)
    def _slot_ask_yes_no(self, title, question, callback_id):
        """
        [Qt Slot]
        Thread-safe way to show a Yes/No confirmation dialog.
        
        The 'callback_id' is used to find the correct callback function
        (which lives in a background thread) to send the (True/False)
        result to.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(question)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(STYLESHEET)
        reply = msg_box.exec()
        callback = self._dialog_callbacks.pop(callback_id, None)
        if callback:
            callback(reply == QMessageBox.StandardButton.Yes)

    @pyqtSlot(str, str, str)
    def _slot_select_save_file(self, title, filename, callback_id):
        """
        [Qt Slot]
        Thread-safe way to show a 'Save As...' file dialog.
        
        The 'callback_id' is used to find the correct callback function
        (which lives in a background thread) to send the 'save_path'
        result to.
        """
        save_path, _ = QFileDialog.getSaveFileName(self, title, filename)
        callback = self._dialog_callbacks.pop(callback_id, None)
        if callback:
            callback(save_path)
            
    @pyqtSlot(str)
    def _slot_set_active_speaker(self, username):
        """
    [Qt Slot]
    Highlights the video frame of the active speaker.
    
    It removes the "ActiveSpeakerBorder" from the previous speaker
    and applies it to the new speaker, then triggers a grid and
    member list update.
    """
        if username == self.active_speaker_username:
            return
        if self.active_speaker_username in self.video_frames:
            details = self.video_frames[self.active_speaker_username]
            details['border_frame'].setObjectName("")
            details['border_frame'].style().polish(details['border_frame'])
        self.active_speaker_username = username
        if self.active_speaker_username in self.video_frames:
            details = self.video_frames[self.active_speaker_username]
            details['border_frame'].setObjectName("ActiveSpeakerBorder")
            details['border_frame'].style().polish(details['border_frame'])
        self.signals.signal_update_grid.emit()
        self._slot_update_member_list([user for user in self.video_frames.keys()])

    # --- UI-Thread Functions (Slots) ---

    @pyqtSlot()
    def _slot_on_discovery_failed(self):
        """
        Called when the 2-second broadcast discovery fails.
        Asks the user for the IP manually.
        """
        self.signals.signal_add_chat.emit("--- Server not found automatically. ---", "system")
        
        # This runs on the main thread, so it can show a dialog
        ip, ok = QInputDialog.getText(self, 
                                     "Server Not Found", 
                                     "Could not find server. Please enter the Server IP Address:")
        
        if ok and ip:
            # User gave us an IP
            self.server_host = ip.strip()
            self.server_udp_addr = (self.server_host, UDP_PORT) # Set the UDP addr too
            self.signals.signal_add_chat.emit(f"--- Manually connecting to {self.server_host}... ---", "system")
            
            # Now start the direct connection thread
            self.connect_thread_2 = WorkerThread(target_func=self.connect_directly)
            self.connect_thread_2.start()
        else:
            # User clicked "Cancel"
            self.signals.signal_add_chat.emit("--- Connection cancelled. ---", "system")
            self.close() # Close the app
            
    @pyqtSlot(dict)
    def handle_tcp_message(self, msg):
        """
        --- !!! MODIFIED for H.264 DECODING !!! ---
        """
        try:
            msg_type = msg.get('type')
            sender = msg.get('from', 'System')
            
            if msg_type == 'auth_fail':
                 
                self.signals.signal_add_chat.emit(f"--- [ERROR] {msg['content']} ---", "system")
                if not hasattr(self, '_rejection_shown'):
                    self._rejection_shown = True
                    QMessageBox.critical(self, "Connection Failed", msg['content'])
                    self.on_closing(force=True)
                return
            
            if msg_type == 'chat':
                 
                self.add_chat_message(f"{sender}: {msg['content']}", "remote_user")
                self.open_side_panel_to('chat')
                
            elif msg_type == 'user_list':
                 
                current_users_data = msg['users']
                new_user_list_usernames = {user_data['username'] for user_data in current_users_data}
                current_video_frame_users = set(self.video_frames.keys())
                users_to_add = new_user_list_usernames - current_video_frame_users
                for user in users_to_add:
                    if user != self.username: 
                        self.add_video_feed(user, is_local=False)
                        self.last_speaker_timestamp[user] = time.time()
                users_to_remove = current_video_frame_users - new_user_list_usernames - {self.username}
                for user in users_to_remove:
                    self.remove_video_feed(user)
                    if user in self.last_speaker_timestamp:
                        del self.last_speaker_timestamp[user]
                for user_data in current_users_data:
                    username = user_data['username']
                    if username != self.username and username in self.video_frames:
                        if self.video_frames[username].get('container'):
                            status = user_data['video_on']
                            if self.video_frames[username]['remote_video_status'] != status:
                                self.video_frames[username]['remote_video_status'] = status
                                self.update_video_frame_visibility(username, show_video=status)
                self._slot_update_member_list([user_data['username'] for user_data in current_users_data])
                self.update_grid_layout() 

            elif msg_type == 'system':
                 
                sys_msg = msg['content']
                self.add_chat_message(f"--- {sys_msg} ---", "system")
                if sys_msg == 'Username already taken.':
                    if not hasattr(self, '_rejection_shown'):
                        self._rejection_shown = True
                        QMessageBox.critical(self, "Connection Failed", "That username is already in use.")
                        self.on_closing(force=True) 
                        
            elif msg_type == 'screen_start':
                # --- *** Use 'h264' not 'libx264' for decoder *** ---
                self.is_presenting = True
                self.screen_presenter_name = f"{sender} is presenting"
                
                if self.screen_decoder:
                    self.screen_decoder = None
                try:
                    self.screen_decoder = av.CodecContext.create("h264", "r")
                except Exception as e:
                    print(f"Failed to create screen decoder: {e}")
                
                if sender != self.username:
                    self.share_btn.setEnabled(False)
                self.update_grid_layout()
                
            # --- *** New message type for black screen *** ---
            elif msg_type == 'screen_black':
                self.signals.signal_show_black_screen.emit(True)
                
            elif msg_type == 'screen_packet':
                self.signals.signal_show_black_screen.emit(False)
                self.handle_screen_packet(msg)
                
            elif msg_type == 'screen_stop':
                # --- *** No .close() method *** ---
                presenter_name = self.screen_presenter_name.split(" ")[0]
                if sender == presenter_name or not presenter_name or presenter_name == "No": 
                    self.is_presenting = False
                    self.screen_sharing_active.clear() 
                    self.screen_presenter_name = "No one is presenting"
                    
                    self.screen_decoder = None # Clear decoder
                        
                    self.share_btn.clicked.disconnect()
                    self.share_btn.clicked.connect(self.start_screen_share)
                    self._slot_set_button_state(self.share_btn, {"text": "Share", "objectName": "ControlButton", "enabled": True, "toolTip": "Share Screen or Window"})
                    self.update_grid_layout()
                    self.signals.signal_show_black_screen.emit(False)
                    
            elif msg_type == 'video_toggle':
                 
                if sender in self.video_frames:
                    status = msg['status']
                    self.video_frames[sender]['remote_video_status'] = status
                    self.update_video_frame_visibility(sender, show_video=status)
                    self.add_chat_message(f"--- {sender} turned video {'on' if status else 'off'} ---", "system")
            
            elif msg_type == 'active_speaker':
                 
                speaker = msg.get('username')
                if speaker:
                    self.last_speaker_timestamp[speaker] = time.time()
                self.signals.signal_set_active_speaker.emit(speaker)
            
            # --- All File Logic ---
            elif msg_type == 'file_start_upload':
                self.handle_file_upload_start(msg)
            elif msg_type == 'file_available':
                self.add_chat_message(f"--- File shared: {msg['filename']} (from {msg['from_user']}) ---", "system")
                self.open_side_panel_to('files')
                item_text = f"{msg['filename']} ({msg['filesize']//1024} KB) - from {msg['from_user']}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, msg)
                self.available_files_list.addItem(item)
            elif msg_type == 'file_transfer_cancelled':
                transfer_id = msg.get('transfer_id')
                if transfer_id and self.current_file_transfer_id == transfer_id:
                    self.hide_file_progress()
                    self.add_chat_message(f"--- File transfer was cancelled. ---", "system")
                for i in range(self.available_files_list.count()):
                    item = self.available_files_list.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole).get('transfer_id') == transfer_id:
                        self.available_files_list.takeItem(i)
                        break

            # --- Internal signal-driven events ---
            elif msg_type == '_show_error_and_quit':
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(msg['title'])
                msg_box.setText(msg['message'])
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setStyleSheet(STYLESHEET)
                msg_box.exec()
                self.on_closing(force=True)
            elif msg_type == '_stop_screen_share_ui':
                self.stop_screen_share()
            elif msg_type == '_update_file_log':
                self.update_file_log_status(msg['id'], msg['status'])
                
        except KeyError as e:
            print(f"CRITICAL: KeyError handling TCP message: {e}. Message was: {msg}")
        except Exception as e:
            print(f"Error handling TCP message: {e}")

    # --- UI Helper Functions (implemented for PyQt) ---
    
    def clear_layout(self, layout):
        """
    Recursively clears all widgets and sub-layouts from a QLayout.
    
    This is crucial for dynamically rebuilding the video grid
    to prevent widget duplication and memory leaks.
    """
        if layout is None: return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None) 
            elif child.layout():
                self.clear_layout(child.layout())

    def open_side_panel_to(self, tab_name):
        """
    Opens the side panel (if closed) and switches to the specified tab.
    
    (e.g., 'chat', 'files', 'members')
    """
        try:
            if tab_name == 'chat': self.notebook.setCurrentIndex(0)
            elif tab_name == 'files': self.notebook.setCurrentIndex(2)
            elif tab_name == 'members': self.notebook.setCurrentIndex(1)
        except Exception:
            pass
        if not self.is_side_panel_open:
            self.side_panel.show()
            self.is_side_panel_open = True
            self.main_content_splitter.setSizes([self.width() - 300, 300])

    def toggle_side_panel(self, tab_to_open):
        """
    Handles the logic for the side panel buttons (Chat, Members, Files).
    
    - If the panel is closed, it opens to 'tab_to_open'.
    - If the panel is *open* and the user clicks the *same* tab button,
      it closes the panel.
    - If the panel is *open* and the user clicks a *different* tab button,
      it just switches tabs.
    """
        current_tab_index = -1
        if self.is_side_panel_open:
            current_tab_index = self.notebook.currentIndex()
        should_close = False
        if self.is_side_panel_open:
            if not tab_to_open:
                should_close = True
            elif (tab_to_open == 'chat' and current_tab_index == 0) or \
                 (tab_to_open == 'members' and current_tab_index == 1) or \
                 (tab_to_open == 'files' and current_tab_index == 2):
                should_close = True
        if should_close:
            self.side_panel.hide()
            self.is_side_panel_open = False
            self.main_content_splitter.setSizes([self.width(), 0])
        else:
            try:
                if tab_to_open == 'chat': self.notebook.setCurrentIndex(0)
                elif tab_to_open == 'members': self.notebook.setCurrentIndex(1)
                elif tab_to_open == 'files': self.notebook.setCurrentIndex(2)
            except Exception:
                pass
            if not self.is_side_panel_open:
                self.side_panel.show()
                self.is_side_panel_open = True
                self.main_content_splitter.setSizes([self.width() - 300, 300])

    def generate_avatar(self, username, size):
        """
    Generates a QPixmap avatar for a user.
    
    It creates a colored circle (based on a hash of the username)
    and draws the user's first initial in the center. This is used
    as the placeholder when their video is off.
    """
        container = QLabel()
        container.setObjectName("AvatarCircle")
        container.setFixedSize(size[0], size[1])
        container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(size[0], size[1])
        pixmap.fill(QColor(LIST_BG))
        hash_val = int(hashlib.md5(username.encode()).hexdigest(), 16)
        color = AVATAR_COLORS[hash_val % len(AVATAR_COLORS)]
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        initial = username[0].upper() if username else "?"
        font_size = int(min(size[0], size[1]) * 0.4)
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initial)
        painter.end()
        container.setPixmap(pixmap)
        return container

    @pyqtSlot(str, bool)
    def update_video_frame_visibility(self, username, show_video):
        """
    Switches a user's video widget between the video feed and the avatar.
    
    It finds the user's 'stack' (QStackedLayout) and sets the
    current widget to either the video 'label' (index 1) or the
    'avatar' (index 0).
    """
        if username not in self.video_frames: return
        widgets = self.video_frames[username]
        stack = widgets.get('stack')
        if not stack or not widgets.get('container'):
            return
        label = widgets.get('label')
        avatar = widgets.get('avatar')
        if show_video:
            stack.setCurrentWidget(label)
        else:
            stack.setCurrentWidget(avatar)

    @pyqtSlot()
    def update_grid_layout(self):
        """
    [Qt Slot]
    Dynamically recalculates and rebuilds the main video grid.
    
    This complex function determines the optimal number of rows/columns
    to fit all participants. It also handles the special "presentation mode"
    layout (one large screen, with participants in a sidebar).
    
    It is called whenever a user joins/leaves or the window is resized.
    """
        self.clear_layout(self.video_grid_layout)
        self.clear_layout(self.right_video_sidebar_layout)
        user_list = list(self.video_frames.keys())
        presenter_is_us = self.screen_presenter_name.startswith(self.username)
        def sort_key(user):
            if user == self.username:
                return (0, 0)
            if user == self.active_speaker_username:
                return (1, 0)
            return (2, -self.last_speaker_timestamp.get(user, 0)) 
        sorted_user_list = sorted(user_list, key=sort_key)
        if self.is_presenting and not presenter_is_us:
            self.center_stack.setCurrentIndex(1)
            self.right_video_sidebar_container.show()
            avatar_size = (160, 120)
            for username in sorted_user_list:
                details = self.video_frames[username]
                if not details.get('container'):
                    print(f"Warning: Skipping {username} in layout, container missing.")
                    continue
                self.right_video_sidebar_layout.addWidget(details['container'])
                details['border_frame'].setFixedSize(avatar_size[0] + 6, avatar_size[1] + 6)
                details['avatar'].setFixedSize(avatar_size[0], avatar_size[1])
                details['label'].setFixedSize(avatar_size[0], avatar_size[1])
                details['name_label'].setFixedWidth(avatar_size[0])
                new_avatar_pixmap = self.generate_avatar(username, avatar_size).pixmap()
                details['avatar'].setPixmap(new_avatar_pixmap)
            self.right_video_sidebar_layout.addStretch(1)
        else:
            self.center_stack.setCurrentIndex(0)
            self.right_video_sidebar_container.hide()
            if not sorted_user_list:
                return
            num_users = len(sorted_user_list)
            frame_width = self.video_grid_scroll_area.width() - 20
            frame_height = self.video_grid_scroll_area.height() - 20
            if frame_width < 100 or frame_height < 100:
                return
            best_layout = {'cols': 0, 'rows': 0, 'tile_w': 0, 'tile_h': 0}
            for cols in range(1, num_users + 1):
                rows = math.ceil(num_users / cols)
                tile_w = (frame_width - (cols - 1) * 10) // cols
                tile_h = int(tile_w * 0.75)
                total_h = (tile_h * rows) + ((rows - 1) * 10)
                if total_h <= frame_height:
                    if tile_w > best_layout['tile_w']:
                        best_layout = {'cols': cols, 'rows': rows, 'tile_w': tile_w, 'tile_h': tile_h}
                else:
                    tile_h = (frame_height - (rows - 1) * 10) // rows
                    tile_w = int(tile_h * (4/3))
                    total_w = (tile_w * cols) + ((cols - 1) * 10)
                    if total_w <= frame_width:
                        if tile_w > best_layout['tile_w']:
                            best_layout = {'cols': cols, 'rows': rows, 'tile_w': tile_w, 'tile_h': tile_w}
            if num_users == 1:
                tile_h = frame_height
                tile_w = int(tile_h * (4/3))
                if tile_w > frame_width:
                    tile_w = frame_width
                    tile_h = int(tile_w * 0.75)
                best_layout = {'cols': 1, 'rows': 1, 'tile_w': tile_w, 'tile_h': tile_h}
            cols = best_layout['cols']
            tile_size = (best_layout['tile_w'], best_layout['tile_h'])
            for i, username in enumerate(sorted_user_list):
                details = self.video_frames[username]
                if not details.get('container'):
                    print(f"Warning: Skipping {username} in layout, container missing.")
                    continue
                row = i // cols
                col = i % cols
                self.video_grid_layout.addWidget(details['container'], row, col, Qt.AlignmentFlag.AlignCenter)
                details['border_frame'].setFixedSize(tile_size[0] + 6, tile_size[1] + 6)
                details['avatar'].setFixedSize(tile_size[0], tile_size[1])
                details['label'].setFixedSize(tile_size[0], tile_size[1])
                details['name_label'].setFixedWidth(tile_size[0])
                new_avatar_pixmap = self.generate_avatar(username, tile_size).pixmap()
                details['avatar'].setPixmap(new_avatar_pixmap)
            total_rows = (num_users + cols - 1) // cols
            self.video_grid_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), total_rows, 0, 1, cols)
            self.video_grid_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), 0, cols, total_rows, 1)
    
    def add_video_feed(self, username, is_local=False):
        """
        --- !!! MODIFIED to add H.264 DECODER !!! ---
        """
        if username in self.video_frames: return
        print(f"Adding video feed for {username}")

        # 1. Overall container (This IS the border_frame)
        container = QFrame()
        container.setObjectName("") # No border by default
        container_layout = QStackedLayout(container)
        container_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        container_layout.setContentsMargins(3,3,3,3) 

        # 2. Media Stack (switches avatar and video) - BOTTOM LAYER
        media_stack = QStackedLayout()
        avatar_canvas = self.generate_avatar(username, (240, 180)) 
        video_label = QLabel()
        video_label.setObjectName("VideoFeed")
        media_stack.addWidget(avatar_canvas) # Index 0
        media_stack.addWidget(video_label)   # Index 1
        
        media_stack_widget = QWidget()
        media_stack_widget.setLayout(media_stack)

        # 3. Name Label (the overlay) - TOP LAYER
        name_text = f"{username}" + (" (You)" if is_local else "")
        name_label = QLabel(name_text)
        name_label.setObjectName("AvatarName")
        name_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        name_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 4. Add layers to the overlay stack
        container_layout.addWidget(media_stack_widget) # Index 0 - Base
        container_layout.addWidget(name_label)         # Index 1 - Top
        
        # --- *** Use 'h264' not 'libx264' for decoder *** ---
        decoder = None
        if not is_local:
            try:
                decoder = av.CodecContext.create("h264", "r")
            except Exception as e:
                print(f"Failed to create decoder for {username}: {e}")
        # ---
        
        # 5. Store references
        self.video_frames[username] = {
            'container': container,
            'border_frame': container,
            'stack': media_stack,
            'avatar': avatar_canvas,
            'label': video_label, 
            'name_label': name_label,
            'is_local': is_local, 
            'remote_video_status': False,
            'decoder': decoder, # <-- NEW
            'decode_lock': threading.Lock()
        }
        
        if is_local:
            self.my_video_label = video_label
            
        if username not in self.last_speaker_timestamp:
            self.last_speaker_timestamp[username] = time.time()
        
        # 6. Trigger layout update
        self.signals.signal_update_grid.emit()

    def remove_video_feed(self, username):
        """
        --- !!! MODIFIED to close DECODER !!! ---
        """
        if username in self.video_frames:
            print(f"Removing video feed for {username}")
            
            details = self.video_frames.pop(username)
            
            # --- No .close() method, just clear reference ---
            with details['decode_lock']:
                if 'decoder' in details and details['decoder']:
                    details['decoder'] = None # Now it's safe to nullify
            # ---
            
            if username in self.last_speaker_timestamp:
                del self.last_speaker_timestamp[username]
            
            details['container'].deleteLater()
            
            self.signals.signal_update_grid.emit()
            
    def add_chat_message(self, message, tag):
         
        self.signals.signal_add_chat.emit(message, tag)

    # --- File Log Functions ---
    def add_file_log(self, transfer_id, timestamp, sender, filename, status, receiver=None):
        pass
    def update_file_log_status(self, transfer_id, new_status, receiver=None):
        pass
    @pyqtSlot()
    def _update_file_log_display(self):
        pass
    @pyqtSlot(str, str)
    def show_file_progress(self, transfer_id, text):
        """
    [Qt Slot]
    Makes the file progress bar visible and sets its initial text.
    """
        self.current_file_transfer_id = transfer_id
        self.file_progress_widget.show()
        self.file_progress_label.setText(text)
        self.file_progress_bar.setValue(0)
    @pyqtSlot(int, str)
    def update_file_progress(self, percent, text):
        """
    [Qt Slot]
    Updates the file progress bar's percentage and text label.
    """
        self.file_progress_label.setText(f"{text} {int(percent)}%")
        self.file_progress_bar.setValue(percent)
    @pyqtSlot()
    def hide_file_progress(self):
        """
    [Qt Slot]
    Hides the file progress bar after a short delay.
    
    Resets the transfer ID and re-enables the download button.
    """
        self.current_file_transfer_id = None
        self.file_download_btn.setEnabled(True)
        self.file_download_btn.setText("Download Selected File")
        QTimer.singleShot(1500, self._internal_hide_progress)
    def _internal_hide_progress(self):
        """
    The actual function to hide the progress bar, called by the
    QTimer in 'hide_file_progress' to create a 1.5s delay.
    """
        if self.current_file_transfer_id is None:
            self.file_progress_widget.hide()
            self.file_progress_label.setText("Transfer Progress")
            self.file_progress_bar.setValue(0)

    # --- UI Event Handlers (Slots) ---

    def on_toggle_audio_click(self):
        self.audio_enabled = not self.audio_enabled
        is_enabled = self.audio_enabled
        self.add_chat_message(f"--- Audio {'enabled' if is_enabled else 'muted'} ---", "system")
        if is_enabled:
            self._slot_set_button_state(self.audio_btn, {"text": "Mic", "objectName": "ControlButton", "toolTip": "Mute Microphone"})
        else:
            self._slot_set_button_state(self.audio_btn, {"text": "Mic", "objectName": "ControlButtonRed", "toolTip": "Unmute Microphone"})

    def on_toggle_video_click(self):
        """
    [Qt Slot]
    Toggles the user's camera state (on/off).
    
    This slot is connected to the 'Cam' button. It calls
    'start_camera()' or 'stop_camera()' and sends the new
    'video_toggle' status to the server via TCP.
    """
        # --- *** Remove threading *** ---
        is_enabled = not self.video_enabled
        self.video_enabled = is_enabled
        
        if is_enabled:
            self.start_camera()
        else:
            self.stop_camera() 
            self._slot_set_button_state(self.video_btn, {"text": "Cam", "objectName": "ControlButtonRed", "toolTip": "Start Camera"})
            if self.username in self.video_frames:
                self.update_video_frame_visibility(self.username, show_video=False)
            if self.is_connected.is_set():
                self.send_tcp_message({'type': 'video_toggle', 'status': False})

    def start_camera(self):
        """
        --- !!! MODIFIED for H.264 ENCODER !!! ---
        """
        with self._camera_lock:
            if self.camera is not None: return
            try:
                self.camera = cv2.VideoCapture(0)
                if not self.camera.isOpened(): raise Exception("Camera failed to open")
                # Ask camera for higher-quality capture before encoding.
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
                self.camera.set(cv2.CAP_PROP_FPS, CAPTURE_FPS)
                try:
                    self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                except Exception:
                    pass
                
                print("Initializing video encoder...")
                self.video_encoder = av.CodecContext.create("libx264", "w")
                self.video_encoder.width = VIDEO_WIDTH
                self.video_encoder.height = VIDEO_HEIGHT
                self.video_encoder.pix_fmt = "yuv420p"
                self.video_encoder.gop_size = VIDEO_KEYFRAME_INTERVAL
                self.video_encoder.max_b_frames = 0
                # --- *** Use fractions.Fraction *** ---
                self.video_encoder.time_base = fractions.Fraction(1, CAPTURE_FPS)
                self.video_encoder.framerate = CAPTURE_FPS
                self.video_encoder.options = {
                    "preset": VIDEO_ENCODER_PRESET,
                    "tune": "zerolatency",
                    "crf": str(VIDEO_CRF),
                    "maxrate": f"{VIDEO_MAX_BITRATE_KBPS}k",
                    "bufsize": f"{VIDEO_BUFFER_KBPS}k",
                    "x264-params": f"keyint={VIDEO_KEYFRAME_INTERVAL}:min-keyint={VIDEO_KEYFRAME_INTERVAL}:scenecut=40:ref=1:bframes=0:intra-refresh=1"
                }
                self.video_frame_count = 0
                
                self.signals.signal_add_chat.emit(f"--- Video enabled ---", "system")
                self.signals.signal_set_button_state.emit(self.video_btn, {"text": "Cam", "objectName": "ControlButton", "toolTip": "Stop Camera"})
                self.send_tcp_message({'type': 'video_toggle', 'status': True})
                self.signals.signal_update_visibility.emit(self.username, True)
            except Exception as e:
                self.signals.signal_handle_camera_fail.emit(str(e))

    def stop_camera(self):
        """
        --- !!! MODIFIED to flush H.264 ENCODER !!! ---
        """
        with self._camera_lock:
            if self.camera is not None:
                try: self.camera.release()
                except Exception as e: print(f"Error releasing camera: {e}")
                self.camera = None
                self.signals.signal_add_chat.emit(f"--- Video disabled ---", "system")

            if self.video_encoder is not None:
                try:
                    # --- *** Flush encoder with None *** ---
                    packets = self.video_encoder.encode(None)
                except Exception as e:
                    print(f"Error flushing video encoder: {e}")
                self.video_encoder = None
            # ---

    def send_chat_message_event(self):
         
        message = self.chat_entry.text().strip()
        if message and self.is_connected.is_set():
            self.add_chat_message(f"You: {message}", "local_user")
            self.send_tcp_message({'type': 'chat', 'content': message})
            self.chat_entry.clear()

    def start_screen_share(self):
        """
    [Qt Slot]
    Opens the screen/window selection dialog.
    """
        self.show_share_selection_dialog()

    def show_share_selection_dialog(self):
        if self.screen_sharing_active.is_set():
            self.add_chat_message("--- You are already sharing. ---", "system")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Select what to share")
        dialog.setStyleSheet(STYLESHEET)
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        listbox = QListWidget(dialog)
        listbox.setAlternatingRowColors(True)
        listbox.setStyleSheet("QListWidget::item { padding: 10px; }")
        screen_item = QListWidgetItem("Entire Screen (Monitor 1)")
        screen_item.setData(Qt.ItemDataRole.UserRole, {'type': 'screen'})
        listbox.addItem(screen_item)
        current_window_title = self.windowTitle()
        temp_junk_list = JUNK_WINDOW_TITLES.copy()
        temp_junk_list.add(current_window_title)
        try:
            windows = gw.getWindowsWithTitle('')
            for w in windows:
                if w.title and w.visible and not w.isMinimized and w.area > 0 and w.title not in temp_junk_list:
                    item = QListWidgetItem(w.title)
                    item.setData(Qt.ItemDataRole.UserRole, {'type': 'window', 'title': w.title})
                    listbox.addItem(item)
        except Exception as e:
            print(f"Could not get windows: {e}")
        layout.addWidget(listbox, 1)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Share")
        ok_btn.setObjectName("GreenButton")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch(1)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_item = listbox.currentItem()
            if not selected_item:
                return
            self.share_target = selected_item.data(Qt.ItemDataRole.UserRole)
            self.screen_sharing_active.set()
            self.send_tcp_message({'type': 'screen_start'})
            self.is_presenting = True
            self.screen_presenter_name = f"{self.username} is presenting"
            self.update_grid_layout()
            threading.Thread(target=self.screen_share_loop, daemon=True, name="Screen-Send").start()
            self.add_chat_message(f"--- Started sharing: {selected_item.text()} ---", "system")
            self.share_btn.clicked.disconnect()
            self.share_btn.clicked.connect(self.stop_screen_share)
            self._slot_set_button_state(self.share_btn, {"text": "Stop", "objectName": "ControlButtonRed", "toolTip": "Stop Sharing"})

    def stop_screen_share(self):
        """
    [Qt Slot]
    Stops an active screen-sharing session.
    
    It clears the 'screen_sharing_active' event (which stops the
    'screen_share_loop' thread), sends a 'screen_stop' message to
    the server, and resets the 'Share' button.
    """
        if self.screen_sharing_active.is_set():
            self.screen_sharing_active.clear()
            self.send_tcp_message({'type': 'screen_stop'})
            self.add_chat_message("--- Stopped screen sharing. ---", "system")
            self.share_btn.clicked.disconnect()
            self.share_btn.clicked.connect(self.start_screen_share)
            self._slot_set_button_state(self.share_btn, {"text": "Share", "objectName": "ControlButton", "toolTip": "Share Screen or Window"})
            self.signals.signal_show_black_screen.emit(False)
        else: self.add_chat_message("--- You are not sharing. ---", "system")

    # --- File Handlers ---
    def select_file_to_send(self):
        """
    [Qt Slot]
    Opens the 'Open File' dialog for the user to select a file to upload.
    
    After a file is selected, it starts a background thread
    ('_hash_and_send_file_offer') to hash the file and send the
    initial 'file_init_request' to the server.
    """
        if not self.is_connected.is_set(): return
        filepath, _ = QFileDialog.getOpenFileName(self, "Select file to send")
        if not filepath: return
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        self.add_chat_message(f"--- Calculating hash for {filename}... ---", "system")
        threading.Thread(target=self._hash_and_send_file_offer, 
                         args=(filepath, filename, filesize),
                         daemon=True).start()
    
    def _hash_and_send_file_offer(self, filepath, filename, filesize):
        """
    [Thread Target]
    Hashes a large file in chunks and then sends the file offer.
    
    Hashing is done in a thread to avoid freezing the GUI.
    Once the MD5 hash is calculated, it sends the 'file_init_request'
    over TCP.
    """
        # --- *** Use chunked hashing *** ---
        file_hash = self.hash_file_md5(filepath)
        if file_hash is None:
            return # Error was already signaled by the helper
        # ---
        
        self.signals.signal_add_chat.emit(f"--- Hash: {file_hash[:10]}... ---", "system")

        self._temp_filepath_store[filename] = filepath 
        init_msg = {
            'type': 'file_init_request', 
            'filename': filename, 
            'size': filesize,
            'file_hash': file_hash
        }
        self.send_tcp_message(init_msg)
        self.signals.signal_add_chat.emit(f"--- Offering file: {filename} to all users. Waiting for server... ---", "system")

    def handle_file_upload_start(self, msg):
        """
    [TCP Handler]
    Handles the 'file_start_upload' message from the server.
    
    This is the server's "OK" to begin uploading. This function
    retrieves the file's local path and starts the
    'client_upload_file' thread to begin streaming data.
    """
        transfer_id = msg['transfer_id']
        filename = msg['filename']
        port = msg['port']
        filepath = self._temp_filepath_store.get(filename)
        if not filepath:
            self.add_chat_message(f"[ERROR] Could not find filepath for {filename}", "system")
            return
        if filename in self._temp_filepath_store:
            del self._temp_filepath_store[filename]
        self.add_chat_message(f"--- Uploading {filename} to server... ---", "system")
        threading.Thread(target=self.client_upload_file, 
                         args=(filepath, transfer_id, port), 
                         daemon=True,
                         name="File-Upload").start()
    def handle_file_download_ready(self, msg):
        """
    [TCP Handler]
    Handles the logic to begin a file download.
    
    This is called when the user clicks 'Download'. It retrieves the
    'save_path' and starts the 'client_download_file' thread
    to begin receiving data.
    """
        transfer_id = msg['transfer_id']
        filename = msg['filename']
        port = FILE_TCP_PORT
        filesize = msg['filesize']
        file_hash = msg.get('file_hash')
        save_path_data = self._temp_filepath_store.get(transfer_id)
        if not save_path_data:
            self.add_chat_message(f"[ERROR] No save path for {filename}", "system")
            self.update_file_log_status(transfer_id, "failed")
            return
        save_path = save_path_data['path']
        self.add_chat_message(f"--- File {filename} is ready. Downloading... ---", "system")
        self.update_file_log_status(transfer_id, "downloading")
        threading.Thread(target=self.client_download_file, 
                         args=(save_path, filename, transfer_id, port, filesize, file_hash),
                         daemon=True,
                         name="File-Download").start()
            
    def on_closing(self, force=False):
        """
    The master shutdown function.
    
    It asks the user for confirmation (unless 'force' is True),
    then clears all threading events, and gracefully closes
    all sockets and media streams (PyAudio, OpenCV) to
    release all system resources.
    
    Returns True if the app should close, False if it should not.
    """
        if not force and self.is_connected.is_set():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Quit")
            msg_box.setText("Are you sure you want to quit?")
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            msg_box.setStyleSheet(STYLESHEET)
            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.No:
                return False
        self.is_connected.clear()
        self.screen_sharing_active.clear()
        self.stop_camera()
        if self.audio_stream_in: 
            try: self.audio_stream_in.stop_stream()
            except Exception: pass
            try: self.audio_stream_in.close()
            except Exception: pass
            self.audio_stream_in = None
        if self.audio_stream_out: 
            try: self.audio_stream_out.stop_stream()
            except Exception: pass
            try: self.audio_stream_out.close()
            except Exception: pass
            self.audio_stream_out = None
        if self.p_audio:
            try: self.p_audio.terminate()
            except Exception: pass
            self.p_audio = None
        if self.tcp_socket:
            try: self.tcp_socket.shutdown(socket.SHUT_RDWR)
            except Exception: pass
            try: self.tcp_socket.close()
            except Exception: pass
            self.tcp_socket = None
        if self.udp_socket: 
            try: self.udp_socket.close()
            except Exception: pass
            self.udp_socket = None
        self._temp_filepath_store.clear()
        return True

    def closeEvent(self, event):
        """
    [Qt Event]
    Overrides the window's 'X' button.
    
    This function intercepts the close event and calls
    'self.on_closing()'. If 'on_closing' returns True,
    it accepts the event; otherwise, it ignores it.
    """
        if self.on_closing(force=False):
            event.accept()
        else:
            event.ignore()
            
    def resizeEvent(self, event):
        """
    [Qt Event]
    Called whenever the main window is resized.
    
    It uses a QTimer (debouncing) to call 'update_grid_layout'
    100ms *after* the resize has finished, preventing the
    layout from being recalculated 1000s of times during a
    single drag.
    """
        super().resizeEvent(event)
        if not hasattr(self, '_resize_timer'):
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self.signals.signal_update_grid.emit()
            self._resize_timer.timeout.connect(self.signals.signal_update_grid)
        self._resize_timer.start(100)

    def on_download_file_click(self):
        """
    [Qt Slot]
    Handles the 'Download Selected File' button click.
    
    It gets the selected file from the list, asks the user
    where to save it (via QFileDialog), and then calls
    'handle_file_download_ready' to start the process.
    """
        selected_item = self.available_files_list.currentItem()
        if not selected_item:
            self.add_chat_message("--- Please select a file to download first. ---", "system")
            return
        file_data = selected_item.data(Qt.ItemDataRole.UserRole)
        is_cancelled = False
        for i in range(self.available_files_list.count()):
            if self.available_files_list.item(i) == selected_item:
                is_cancelled = False
                break
        else:
            is_cancelled = True
        if is_cancelled:
            self.add_chat_message(f"--- File '{file_data['filename']}' is no longer available. ---", "system")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, f"Save {file_data['filename']}", file_data['filename'])
        if not save_path:
            self.add_chat_message("--- Download cancelled. ---", "system")
            return
        self.file_download_btn.setEnabled(False)
        self.file_download_btn.setText("Downloading...")
        self._temp_filepath_store[file_data['transfer_id']] = {'path': save_path}
        self.handle_file_download_ready(file_data)
        
    def on_cancel_file_transfer(self):
        """
    [Qt Slot]
    Handles the 'X' button click on the file progress bar.
    
    It sends a 'file_cancel' message to the server, closes the
    local file transfer socket (which kills the thread), and
    hides the progress bar.
    """
        if not self.current_file_transfer_id:
            return
        tid = self.current_file_transfer_id
        self.hide_file_progress()
        self.send_tcp_message({'type': 'file_cancel', 'transfer_id': tid})
        transfer_data = self._temp_filepath_store.pop(tid, None)
        if transfer_data and 'socket' in transfer_data:
            try:
                transfer_data['socket'].close()
            except Exception as e:
                print(f"Error closing socket on cancel: {e}")

    @pyqtSlot()
    def scroll_sidebar_up(self):
        """
    [Qt Slot]
    Scrolls the "presentation mode" participant sidebar up.
    """
        scrollbar = self.right_video_sidebar_scroll_area.verticalScrollBar()
        scroll_step = 150
        scrollbar.setValue(scrollbar.value() - scroll_step)

    @pyqtSlot()
    def scroll_sidebar_down(self):
        """
    [Qt Slot]
    Scrolls the "presentation mode" participant sidebar down.
    """
        scrollbar = self.right_video_sidebar_scroll_area.verticalScrollBar()
        scroll_step = 150
        scrollbar.setValue(scrollbar.value() + scroll_step)
    
    def handle_screen_packet(self, msg):
        """
        NEW: Decodes an H.264 packet from the TCP screen share.
        """
        if not self.is_presenting or not self.screen_decoder: return
        try:
            packet = av.Packet(msg['data'])
            frames = self.screen_decoder.decode(packet)
            for frame in frames:
                q_pixmap = self.av_frame_to_qpixmap(frame, self.screen_share_label)
                self.signals.signal_update_screen_share.emit(q_pixmap)
        # --- *** Catch generic av.AVError *** ---
        except av.error.AVError as e:
            print(f"Screen decode error: {e}, re-initializing decoder.")
            try:
                self.screen_decoder = av.CodecContext.create("h264", "r")
            except Exception as e_init:
                print(f"Failed to re-initialize screen decoder: {e_init}")
                self.screen_decoder = None
        except Exception as e:
            print(f"Unhandled screen packet error: {e}")

    def av_frame_to_qpixmap(self, frame, label_widget):
        """
        Converts an av.VideoFrame to a QPixmap,
        resized to fit the target label.
        """
        try:
            frame_rgb = frame.to_ndarray(format="rgb24")
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            q_pixmap = QPixmap.fromImage(q_img)
            
            label_w = label_widget.width()
            label_h = label_widget.height()
            
            if label_w < 10 or label_h < 10:
                target_size = (120, 90) if self.is_presenting else (240, 180)
            else:
                aspect = w / h if h > 0 else 1.0
                if label_w / aspect <= label_h: target_size = (label_w, int(label_w / aspect)) if aspect > 0 else (label_w, label_h)
                else: target_size = (int(label_h * aspect), label_h) if aspect > 0 else (label_w, label_h)
            
            target_w = max(1, target_size[0])
            target_h = max(1, target_size[1])
            
            if q_pixmap.size().width() != target_w or q_pixmap.size().height() != target_h:
                 q_pixmap = q_pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            return q_pixmap
        except Exception as e:
            print(f"Error in av_frame_to_qpixmap: {e}")
            return QPixmap() # Return empty pixmap on error

    def hash_file_md5(self, filepath):
        """
        Robustly hashes a file in chunks.
        """
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.signals.signal_add_chat.emit(f"--- [ERROR] Could not hash file: {e} ---", "system")
            return None
        
# --- Main execution ---
if __name__ == "__main__":
    # --- Setup Logging ---
    setup_logging(log_file=config.LOG_FILE, log_level=config.LOG_LEVEL)
    
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    dialog = LoginDialog()
    dialog.setStyleSheet(STYLESHEET) 
    dialog.exec()
    username, code = dialog.getValues()
    
    if username and code:
        client_gui = ClientGUI(username, code)
        client_gui.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit(0)
