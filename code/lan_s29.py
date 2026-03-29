import os
import platform
# --- Set High DPI Scaling ---
if platform.system() == "Windows":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

"""
LAN Collab Server (PyQt6 Version)
"""

import socket
import threading
import sys
import signal
import pickle
import struct
import logging
import uuid
import queue
import numpy as np
import time
import hashlib
import json      # For safe data serialization
import base64    # To encode/decode binary data for json
import ssl

# LAN Collab imports
from auth_utils import generate_deterministic_numeric_code, get_lan_ip
from shared_utils import lin2ulaw_numpy, ulaw2lin_numpy, safe_serialize, safe_deserialize, setup_logging
import config

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QListWidget, QListWidgetItem, QFrame,
    QLineEdit, QPushButton
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QGuiApplication

# --- Configuration (imported from config module) ---
HOST = config.HOST
TCP_PORT = config.TCP_PORT
UDP_PORT = config.UDP_PORT
FILE_TCP_PORT = config.FILE_TCP_PORT
FILE_TEMP_DIR = config.FILE_TEMP_DIR
DISCOVERY_PORT = config.DISCOVERY_PORT
AUDIO_CHUNK_SIZE = config.AUDIO_CHUNK_SIZE
AUDIO_SAMPLE_RATE = config.AUDIO_SAMPLE_RATE
MIX_INTERVAL = config.MIX_INTERVAL
TARGET_RMS = config.TARGET_RMS
VIDEO_BUFFER_TIMEOUT_SEC = config.VIDEO_BUFFER_TIMEOUT_SEC
# --------------------------------

# --- Style Configuration (imported from config module) ---
BG_COLOR = config.SERVER_BG_COLOR
FRAME_BG = config.SERVER_FRAME_BG
LIST_BG = config.SERVER_LIST_BG
LOG_BG = config.SERVER_LOG_BG
FG_COLOR = config.SERVER_FG_COLOR
ACCENT_COLOR = config.SERVER_ACCENT_COLOR
ACCENT_DARK = config.SERVER_ACCENT_DARK
BTN_SUCCESS = config.BTN_SUCCESS
FG_MUTED = config.FG_MUTED
# ------------------------------------------------------

# --- Global Stylesheet (QSS) for Server ---
STYLESHEET = f"""
    QWidget {{
        background-color: {BG_COLOR};
        color: {FG_COLOR};
        font-family: "Segoe UI", Arial, sans-serif; /* Modern font */
        font-size: 10pt;
    }}
    
    QFrame#MainFrame {{
        background-color: {BG_COLOR};
    }}

    QFrame#ClientFrame {{
        background-color: {FRAME_BG}; /* Give client panel a distinct bg */
        border: none;
    }}

    QLabel {{
        background-color: transparent;
        color: {FG_COLOR};
        font-size: 10pt;
        padding: 2px; /* Add slight padding */
    }}

    QLabel#Header {{
        font-size: 13pt;
        font-weight: 600; /* Use numerical weight */
        color: {FG_COLOR}; /* Header is white, not accent */
        padding-bottom: 8px;
        padding-top: 4px;
    }}
    
    QLabel#StatusLabel {{
        font-weight: bold;
        color: {BTN_SUCCESS};
        font-size: 11pt; /* Make status stand out */
        padding-bottom: 5px;
    }}
    
    QLabel#InfoLabel {{
        color: {FG_MUTED}; /* Muted color for info */
        font-size: 9pt;
    }}

    /* Log Area */
    QTextEdit {{
        background-color: {LOG_BG};
        color: {FG_COLOR};
        font-family: "Consolas", "Courier New", monospace;
        border: none;
        border-radius: 6px;
        padding: 8px;
    }}

    /* Client List */
    QListWidget {{
        background-color: {LIST_BG};
        color: {FG_COLOR};
        border: none;
        border-radius: 6px;
    }}
    QListWidget::item {{
        padding: 8px; /* More spacing */
        border-radius: 4px; /* Rounded items */
    }}
    QListWidget::item:alternate {{
        background-color: transparent; /* Disable default striping */
    }}
    QListWidget::item:hover {{
        background-color: {BG_COLOR}; /* Darker hover */
    }}
    QListWidget::item:selected {{
        background-color: {ACCENT_COLOR};
        color: white;
    }}

    /* Meet Code Entry */
    QLineEdit {{
        background-color: {LOG_BG};
        color: {FG_COLOR};
        border: 1px solid {FRAME_BG};
        border-radius: 6px;
        padding: 6px 8px;
        font-size: 9pt;
    }}
    QLineEdit:read-only {{
        border: 1px solid {FRAME_BG};
    }}

    /* Main "Copy Code" Button */
    QPushButton#AccentButton {{
        background-color: {ACCENT_COLOR};
        color: white;
        font-weight: bold;
        border: none;
        padding: 8px 12px;
        border-radius: 6px;
    }}
    QPushButton#AccentButton:hover {{
        background-color: {ACCENT_DARK};
    }}
    QPushButton#AccentButton:pressed {{
        background-color: {ACCENT_COLOR};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background-color: {BG_COLOR}; /* Match main bg */
        width: 10px;
        margin: 0;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {ACCENT_DARK};
        min-height: 20px;
        border-radius: 5px;
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
"""

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(threadName)s] %(message)s')


class ServerGUISignals(QObject):
    """
    Holds all signals for thread-safe UI updates.
    This is the PyQt replacement for `root.after()`.
    """
    signal_log_message = pyqtSignal(str)
    signal_update_clients = pyqtSignal(list)


class ServerGUI(QWidget):
    def __init__(self):
        """
        Initializes the main server GUI and all backend components.
        This constructor sets up all state variables, locks, and queues needed
        for a multi-threaded, multi-client environment. It also initializes
        the SSL context and kicks off the four main server threads.
        """
        super().__init__()
        
        # --- State Variables ---
        self.tcp_clients = {}
        self.username_to_socket = {}
        self.known_udp_addrs = set()
        self.active_file_transfers = {}
        self.client_lock = threading.Lock()
        self.tcp_send_lock = threading.Lock()
        
        self.udp_packet_queue = queue.Queue(maxsize=config.UDP_MEDIA_QUEUE_MAXSIZE)
        self._dropped_udp_packets = 0
        self._last_drop_log = 0.0
        self.audio_buffers = {} 
        self.audio_buffer_lock = threading.Lock()
        
        self.video_reassembly_buffers = {}
        self.video_buffer_lock = threading.Lock()
        
        self.running = threading.Event()
        self.running.set()
        self.server_lan_ip = get_lan_ip() 
        if not self.server_lan_ip:
            self.server_lan_ip = "Error: Not Found"
        # Generate the 9-digit code from the MAC address
        self.meet_code = generate_deterministic_numeric_code() 
        
        # --- Active Speaker State ---
        self.current_active_speaker_addr = None
        self.last_broadcast_speaker_addr = None
        self.speaker_lock = threading.Lock()
        
        # --- PyQt Specific ---
        self.signals = ServerGUISignals()
        # ---
        
        self.setup_gui()
        self.connect_signals()
        
        self.log_message("Server starting...")
        os.makedirs(FILE_TEMP_DIR, exist_ok=True)
        # self.log_message(f"File transfer directory: {FILE_TEMP_DIR}")
        self.log_message(f"Generated deterministic code: {self.meet_code}")

        self.log_message("Creating SSL context...")
        try:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(certfile="server.crt", keyfile="server.key")
            self.log_message("SSL context loaded successfully (server.crt, server.key).")
        except FileNotFoundError:
            self.log_message("[FATAL ERROR] SSL certificate/key not found.")
            self.log_message("Please run 'generate_certs.py' first and restart the server.")
            return # Stop initialization
        except Exception as e:
            self.log_message(f"[FATAL ERROR] Could not load SSL context: {e}")
            return # Stop initialization

        # Start all network threads
        self.start_tcp_server()
        self.start_udp_server()
        self.start_file_server()
        self.start_discovery_service()
        
        # --- Start Active Speaker Broadcaster ---
        self.start_speaker_broadcast_thread()
        # ---

    def setup_gui(self):
        """Creates the PyQt6 user interface."""
        self.setWindowTitle("LAN Collab Server (Control Panel)")
        self.setGeometry(200, 200, 700, 500)
        self.setMinimumSize(500, 400)

        # Main horizontal layout
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Left Side (Log) ---
        log_frame = QFrame(self)
        log_frame.setObjectName("MainFrame")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        log_header = QLabel("Server Activity Log")
        log_header.setObjectName("Header")
        log_layout.addWidget(log_header)

        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area, 1) # 1 = stretch

        # --- Right Side (Clients & Info) ---
        client_frame = QFrame(self)
        client_frame.setObjectName("ClientFrame")
        client_frame.setFixedWidth(250)
        client_layout = QVBoxLayout(client_frame)
        client_layout.setContentsMargins(10, 10, 10, 10)

        client_header = QLabel("Connected Clients")
        client_header.setObjectName("Header")
        client_layout.addWidget(client_header)
        
        self.client_listbox = QListWidget(self)
        self.client_listbox.setAlternatingRowColors(True) # We'll control colors via QSS
        client_layout.addWidget(self.client_listbox, 1) # 1 = stretch

        # Info Frame
        info_frame = QFrame(self)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(0, 10, 0, 0)
        info_layout.setSpacing(2)

        status_label = QLabel("Server Status: Online")
        status_label.setObjectName("StatusLabel")
        info_layout.addWidget(status_label)
        
        info_layout.addWidget(QLabel(f"TCP: {HOST}:{TCP_PORT}", objectName="InfoLabel"))
        info_layout.addWidget(QLabel(f"UDP: {HOST}:{UDP_PORT}", objectName="InfoLabel"))
        info_layout.addWidget(QLabel(f"FILES: {HOST}:{FILE_TCP_PORT}", objectName="InfoLabel"))
        info_layout.addStretch(1)
        # --- Meet Code Display ---
        info_layout.addSpacing(10)
        
        info_layout.addWidget(QLabel("SERVER IP (Share this):"))
        self.ip_entry = QLineEdit(self)
        self.ip_entry.setText(self.server_lan_ip)
        self.ip_entry.setReadOnly(True)
        info_layout.addWidget(self.ip_entry)

        info_layout.addWidget(QLabel("MEET CODE (Share this):"))
        self.meet_code_entry = QLineEdit(self)
        self.meet_code_entry.setText(self.meet_code)
        self.meet_code_entry.setReadOnly(True)
        info_layout.addWidget(self.meet_code_entry)

        self.copy_btn = QPushButton("Copy Code")
        self.copy_btn.setObjectName("AccentButton") # Set object name for QSS
        self.copy_btn.clicked.connect(self.copy_meet_code_to_clipboard)
        info_layout.addWidget(self.copy_btn)

        info_layout.addStretch(1)
        # --- End Meet Code Display ---
        client_layout.addWidget(info_frame)

        # Add panes to root layout
        root_layout.addWidget(log_frame, 3) # 3 = stretch factor
        root_layout.addWidget(client_frame, 1) # 1 = stretch factor

    def connect_signals(self):
        """Connect all signals to their slots."""
        self.signals.signal_log_message.connect(self._slot_log_message)
        self.signals.signal_update_clients.connect(self._slot_update_clients)
  
    def copy_meet_code_to_clipboard(self):
        """
        Copies the invite token to the system clipboard.
        """
        try:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self.meet_code)
            self.log_message("Invite Token copied to clipboard.")
            self.copy_btn.setText("Copied!")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy Code"))
        except Exception as e:
            self.log_message(f"[ERROR] Could not copy to clipboard: {e}")

    # --- PyQt Slots (Thread-safe UI updates) ---

    @pyqtSlot(str)
    def _slot_log_message(self, message):
        """Appends a message to the log area."""
        self.log_area.append(message)
        # Ensure it scrolls to the bottom
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    @pyqtSlot(list)
    def _slot_update_clients(self, clients_info):
        """Updates the QListWidget with current clients."""
        self.client_listbox.clear()
        for i, (username, tcp_ip) in enumerate(clients_info):
            item_text = f" {username} @ {tcp_ip}"
            item = QListWidgetItem(item_text)
            self.client_listbox.addItem(item)

    # --- Core Logic (Re-implemented to use signals) ---

    def log_message(self, message):
        """
        Logs a message to the console and emits a signal to update the GUI.
        """
        logging.info(message)
        if hasattr(self, 'signals'):
            self.signals.signal_log_message.emit(message)

    def update_client_listbox(self):
        """
        Gathers client info and emits a signal to update the GUI.
        """
        with self.client_lock:
            clients_info = [(data['username'], data['tcp_ip']) for data in self.tcp_clients.values()]
        if hasattr(self, 'signals'):
            self.signals.signal_update_clients.emit(clients_info)
    
    def start_tcp_server(self):
        """
        Creates and binds the main, secure TCP control socket.
        
        This socket (on port 9090) is wrapped with SSL/TLS and is responsible for
        all reliable communication: authentication, chat, user lists, and commands.
        It spawns the main 'accept_connections' thread.
        """
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((HOST, TCP_PORT))
            self.tcp_socket.listen(5)
            self.tcp_socket = self.ssl_context.wrap_socket(self.tcp_socket, server_side=True) # added for SSL certifications
            self.log_message(f"Main TCP Server listening on {HOST}:{TCP_PORT}")
            self.accept_thread = threading.Thread(target=self.accept_connections, name="TCP-Accept", daemon=True)
            self.accept_thread.start()
        except Exception as e:
            self.log_message(f"[FATAL ERROR] Main TCP Server: {e}")

    def accept_connections(self):
        """
        [Thread Target: TCP-Accept]
        Blocks and listens for new client connections on the main TCP port.
        
        When a new connection is received, it spawns a dedicated
        'handle_tcp_client' thread to manage that client's session,
        ensuring the accept loop can immediately listen for the next client.
        """
        client_count = 1
        while self.running.is_set():
            try:
                client_socket, (client_ip, client_tcp_port) = self.tcp_socket.accept()
                if not self.running.is_set(): break
                self.log_message(f"New TCP connection from {client_ip}:{client_tcp_port}")
                
                # --- Store client socket temporarily for file transfers ---
                client_data = {'socket': client_socket, 'ip': client_ip}
                
                client_thread = threading.Thread(target=self.handle_tcp_client, 
                                                 args=(client_data,), 
                                                 name=f"Client-{client_count}",
                                                 daemon=True)
                client_thread.start()
                client_count += 1
            except OSError:
                if self.running.is_set():
                    self.log_message("Main TCP Server shutting down.")
                break
            except Exception as e:
                if self.running.is_set():
                    self.log_message(f"[ERROR] Accepting connection: {e}")

    def start_udp_server(self):
        """
        Creates and binds the main UDP media socket.
        
        This socket (on port 9091) handles all high-volume, low-latency
        media streams (audio and video). It spawns the threads responsible
        for receiving, processing, and mixing this media.
        """
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, config.VIDEO_UDP_RCVBUF_BYTES)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, config.VIDEO_UDP_SNDBUF_BYTES)
            self.udp_socket.bind((HOST, UDP_PORT))
            self.log_message(f"UDP Server listening on {HOST}:{UDP_PORT}")
            
            self.udp_recv_thread = threading.Thread(target=self.handle_udp_packets, name="UDP-Recv", daemon=True)
            self.udp_process_threads = [
                threading.Thread(target=self.process_udp_queue, name=f"UDP-Process-{i+1}", daemon=True)
                for i in range(max(1, int(config.UDP_PROCESS_WORKERS)))
            ]
            self.audio_mixer_thread = threading.Thread(target=self.mix_and_send_audio, name="Audio-Mixer", daemon=True)
            self.video_buffer_cleanup_thread = threading.Thread(target=self.cleanup_video_buffers, name="UDP-Cleanup", daemon=True)
            
            self.udp_recv_thread.start()
            for t in self.udp_process_threads:
                t.start()
            self.audio_mixer_thread.start()
            self.video_buffer_cleanup_thread.start()
            
        except Exception as e:
            self.log_message(f"[FATAL ERROR] UDP Server: {e}")

    def start_file_server(self):
        """
        Creates and binds the dedicated, secure TCP file transfer socket.
        
        This socket (on port 9100) is wrapped with SSL/TLS and handles
        all bulk file data. Using a separate port prevents large file
        transfers from blocking or "clogging" the main control socket.
        """
        try:
            self.file_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.file_tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.file_tcp_socket.bind((HOST, FILE_TCP_PORT))
            self.file_tcp_socket.listen(5)
            self.file_tcp_socket = self.ssl_context.wrap_socket(self.file_tcp_socket, server_side=True) # for SSL Certification
            self.log_message(f"File Server listening on {HOST}:{FILE_TCP_PORT}")
            self.file_accept_thread = threading.Thread(target=self.accept_file_connections, name="File-Accept", daemon=True)
            self.file_accept_thread.start()
        except Exception as e:
            self.log_message(f"[FATAL ERROR] File Server: {e}")

    def start_discovery_service(self):
        """
        Starts a UDP listener to respond to client discovery broadcasts.
        """
        try:
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_socket.bind((HOST, DISCOVERY_PORT))
            self.log_message(f"Discovery Service listening on UDP {HOST}:{DISCOVERY_PORT}")

            self.discovery_thread = threading.Thread(target=self.handle_discovery_requests, daemon=True, name="Discovery")
            self.discovery_thread.start()
        except Exception as e:
            self.log_message(f"[FATAL ERROR] Discovery Service: {e}")
            
    # --- NEW: Active Speaker Broadcaster ---
    def start_speaker_broadcast_thread(self):
        """Starts a thread to broadcast the active speaker."""
        self.speaker_broadcast_thread = threading.Thread(target=self.broadcast_active_speaker, name="Speaker-Broadcast", daemon=True)
        self.speaker_broadcast_thread.start()
        
    def broadcast_active_speaker(self):
        """Periodically checks for a change in active speaker and broadcasts it."""
        while self.running.is_set():
            time.sleep(0.5) # Broadcast update interval
            
            with self.speaker_lock:
                current_addr = self.current_active_speaker_addr
                last_addr = self.last_broadcast_speaker_addr
                
                if current_addr != last_addr:
                    self.last_broadcast_speaker_addr = current_addr
                    speaker_username = None
                    
                    if current_addr is not None:
                        # Find username from UDP address
                        with self.client_lock:
                            for client_data in self.tcp_clients.values():
                                if client_data['udp_addr'] == current_addr:
                                    speaker_username = client_data['username']
                                    break
                    
                    if speaker_username:
                        # self.log_message(f"Active speaker changed: {speaker_username}")
                        self.broadcast_message({
                            'type': 'active_speaker',
                            'username': speaker_username
                        }, None, "System")
                    else:
                        # No one is speaking
                        self.broadcast_message({
                            'type': 'active_speaker',
                            'username': None
                        }, None, "System")

    def handle_discovery_requests(self):
        """
        Listens for broadcast messages and replies if the meet code matches.
        """
        while self.running.is_set():
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = safe_deserialize(data)

                if message.get('type') == 'discover' and message.get('code') == self.meet_code:
                    self.log_message(f"Discovery request from {addr} with correct code. Replying.")

                    # Get the server's *current* LAN IP to send back
                    server_lan_ip = get_lan_ip() 

                    if not server_lan_ip:
                        self.log_message("[WARN] Could not determine reply IP for discovery.")
                        continue

                    reply = safe_serialize({'type': 'discover_reply', 'ip': server_lan_ip, 'port': TCP_PORT})
                    self.discovery_socket.sendto(reply, addr)

            except OSError:
                if self.running.is_set():
                    self.log_message("Discovery Service shutting down.")
                break
            except Exception as e:
                if self.running.is_set():
                    self.log_message(f"[ERROR] Discovery: {e}")

    def accept_file_connections(self):
        """
        [Thread Target: File-Accept]
        Blocks and listens for new client connections on the file TCP port.
        
        When a client connects (for an upload or download), this spawns a
        dedicated 'handle_file_transfer' thread to manage the data stream.
        """
        while self.running.is_set():
            try:
                conn, addr = self.file_tcp_socket.accept()
                if not self.running.is_set(): break
                self.log_message(f"New FILE connection from {addr}")
                
                # --- Pass connection to handler ---
                file_thread = threading.Thread(target=self.handle_file_transfer, 
                                                 args=(conn,), 
                                                 name=f"File-Transfer-{addr[1]}",
                                                 daemon=True)
                file_thread.start()
            except OSError:
                if self.running.is_set():
                    self.log_message("File Server shutting down.")
                break
            except Exception as e:
                if self.running.is_set():
                    self.log_message(f"[ERROR] Accepting file connection: {e}")

    # ---
    # ---
    def handle_file_transfer(self, conn):
        """
        [Thread Target: File-Transfer]
        Handles a single file upload or download session.
        
        This function performs the handshake ('UPLOAD' or 'DOWNLOAD'),
        finds the transfer details from 'active_file_transfers', and then
        either reads data from the socket (saving a file) or reads data
        from a file (sending to the socket).
        """
        transfer_id = None
        action_type = None
        upload_success = False
        try:
            buffer = b""
            handshake_data = ""
            file_data_started = b""
            while b'\n' not in buffer:
                chunk = conn.recv(128) 
                if not chunk:
                    raise ConnectionError("Client disconnected before handshake")
                buffer += chunk
            handshake_part, file_data_started = buffer.split(b'\n', 1)
            handshake_data = handshake_part.decode('utf-8').strip()
            if not handshake_data or ':' not in handshake_data:
                raise ValueError("Invalid file handshake")
                
            action, transfer_id = handshake_data.split(':', 1)
            action_type = action
            
            with self.client_lock:
                if transfer_id not in self.active_file_transfers:
                    raise ValueError(f"Unknown transfer_id: {transfer_id}")
                transfer_data = self.active_file_transfers[transfer_id]
                
                # --- Store the connection object for cancellation ---
                transfer_data['connection'] = conn
                # ---

            if action == "UPLOAD":
                self.log_message(f"Receiving file for {transfer_id} from {transfer_data['sender']}...")
                safe_filename = os.path.basename(transfer_data['filename'])
                local_filepath = os.path.join(FILE_TEMP_DIR, f"{transfer_id}_{safe_filename}")
                with open(local_filepath, 'wb') as f:
                    f.write(file_data_started)
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk: break
                        f.write(chunk)
                
                # If we reached here, transfer was successful (not cancelled)
                self.log_message(f"File {transfer_id} received. Stored at {local_filepath}")
                
                with self.client_lock:
                    transfer_data['local_filepath'] = local_filepath
                    transfer_data['status'] = 'uploaded'
                
                # Broadcast the file's availability to EVERYONE
                broadcast_payload = {
                    'type': 'file_available', # New message type
                    'transfer_id': transfer_id,
                    'filename': transfer_data['filename'],
                    'filesize': transfer_data['filesize'],
                    'from_user': transfer_data['sender'],
                    'file_hash': transfer_data.get('file_hash')
                }
                self.broadcast_message(broadcast_payload, None, "System")
                upload_success = True
                
            elif action == "DOWNLOAD":
                downloader_username = "Unknown"
                try:
                    downloader_ip = conn.getpeername()[0]
                    with self.client_lock:
                        for data in self.tcp_clients.values():
                            # Find username by IP.
                            if data['ip'] == downloader_ip:
                                downloader_username = data['username']
                                break
                    transfer_data['receiver'] = downloader_username # Update the dict
                except Exception:
                    pass
                self.log_message(f"Sending file for {transfer_id} to {transfer_data['receiver']}...")
                local_filepath = transfer_data.get('local_filepath')
                if not local_filepath or not os.path.exists(local_filepath):
                    raise FileNotFoundError(f"File not found on server for {transfer_id}")
                with open(local_filepath, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk: break
                        conn.sendall(chunk)
                self.log_message(f"File {transfer_id} sent to {transfer_data['receiver']}.")

            else:
                raise ValueError(f"Invalid file action: {action}")
                
        except (UnicodeDecodeError, ValueError) as e_handshake:
            self.log_message(f"[CRITICAL_ERROR] Handshake failed for {transfer_id or 'unknown'}: {e_handshake}")
        except (OSError, ConnectionError) as e_conn:
            # This is now the expected path for a cancellation
            if transfer_id:
                with self.client_lock:
                    if transfer_id in self.active_file_transfers:
                        if self.active_file_transfers[transfer_id].get('status') == 'cancelled':
                            self.log_message(f"File transfer {transfer_id} cancelled by user.")
                        else:
                            self.log_message(f"[ERROR] File transfer {transfer_id} failed: {e_conn}")
            else:
                self.log_message(f"[ERROR] File transfer failed: {e_conn}")
        except Exception as e:
            self.log_message(f"[ERROR] File transfer failed for {transfer_id or 'unknown'}: {e}")
        
        finally:
            if action_type == "UPLOAD" and not upload_success:
                # Upload FAILED, remove the record
                self.log_message(f"Upload {transfer_id} failed. Cleaning up.")
                if transfer_id:
                    self.remove_file_transfer(transfer_id, conn_closed=True)
            elif action_type == "DOWNLOAD":
                # Download is finished, just log it. DO NOT remove.
                self.log_message(f"Download {transfer_id} socket closing.")
            elif action_type == "UPLOAD" and upload_success:
                    # Upload is finished, just log it. DO NOT remove.
                self.log_message(f"Upload {transfer_id} socket closing.")
            # --- !!! END OF FIX !!! ---
                
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def remove_file_transfer(self, transfer_id, conn_closed=False):
        """Safely removes a file transfer and cleans up resources."""
        data = None
        with self.client_lock:
            if transfer_id in self.active_file_transfers:
                data = self.active_file_transfers.pop(transfer_id)
                self.log_message(f"Cleaning up file transfer: {transfer_id}")
                
            # --- Check if we actually popped anything ---
            if data:
                # (All the rest of cleanup logic goes inside this "if" block)
                if not conn_closed and 'connection' in data:
                    try:
                        data['connection'].shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass
                    try:
                        data['connection'].close()
                    except Exception:
                        pass

                if data.get('local_filepath') and os.path.exists(data['local_filepath']):
                    try:
                        os.remove(data['local_filepath'])
                        self.log_message(f"Cleaned up temp file: {data['local_filepath']}")
                    except Exception as e_clean:
                        self.log_message(f"[WARN] Failed to clean up file: {e_clean}")

    def handle_udp_packets(self):
        """
        [Thread Target: UDP-Recv]
        Dedicated thread to receive all incoming UDP packets.
        
        This function's only job is to read from the UDP socket as fast as
        possible and put the raw (data, address) tuple into the 'udp_packet_queue'.
        
        It first validates that the sender's address is in 'known_udp_addrs'
        (populated after TCP auth) to filter unauthorized packets. This
        separation of I/O from processing prevents buffer overflows.
        """
        while self.running.is_set():
            try:
                data, sender_addr = self.udp_socket.recvfrom(65536)
                with self.client_lock:
                    if sender_addr not in self.known_udp_addrs:
                        continue 
                try:
                    self.udp_packet_queue.put_nowait((data, sender_addr))
                except queue.Full:
                    # Drop newest packet when overloaded to keep latency low.
                    self._dropped_udp_packets += 1
                    now = time.time()
                    if now - self._last_drop_log > 2.0:
                        self.log_message(f"[WARN] UDP queue full, dropped {self._dropped_udp_packets} packets")
                        self._last_drop_log = now
            except OSError as e:
                if self.running.is_set():
                    # self.log_message("UDP Server shutting down.")
                    self.log_message(f"[WARN] UDP socket error (likely client disconnect): {e}")
                pass
            except Exception as e:
                if self.running.is_set():
                    self.log_message(f"[ERROR] UDP Recv: {e}. Packet dropped.")

    def process_udp_queue(self):
        """
        [Thread Target: UDP-Process]
        Dedicated thread to process packets from the 'udp_packet_queue'.
        
        This "worker" thread dequeues packets, de-serializes them, and routes
        the data.
        - 'audio' packets are placed in the sender's audio buffer for the mixer.
        - 'video_packet' packets are immediately relayed to all other clients.
        """        
        while self.running.is_set():
            try:
                (data, sender_addr) = self.udp_packet_queue.get(timeout=0.1) 
                
                payload = safe_deserialize(data)
                msg_type = payload.get("type")

                if msg_type == "audio":
                    with self.audio_buffer_lock:
                        if sender_addr not in self.audio_buffers:
                            self.audio_buffers[sender_addr] = queue.Queue(maxsize=5)
                    try:
                        self.audio_buffers[sender_addr].put_nowait(payload['data'])
                    except queue.Full:
                        pass 

                elif msg_type == "video_packet" or msg_type == "video_frag":
                    with self.client_lock:
                        targets = [
                            data['udp_addr'] for data in self.tcp_clients.values() 
                            if data['udp_addr'] is not None and data['udp_addr'] != sender_addr
                        ]
                    for target_addr in targets:
                        try:
                            self.udp_socket.sendto(data, target_addr)
                        except Exception: pass
            
            except queue.Empty:
                continue
            except (pickle.UnpicklingError, KeyError):
                pass
            except Exception as e:
                if self.running.is_set():
                    self.log_message(f"[ERROR] UDP-Process: {e}")

    def cleanup_video_buffers(self):
        """
        [Thread Target: UDP-Cleanup]
        Periodically cleans up incomplete video frame buffers.
        
        This is a garbage collector. If a video packet is lost, its
        corresponding frame buffer might never be completed. This thread
        runs on a timer and deletes any frame buffers that are older
        than VIDEO_BUFFER_TIMEOUT_SEC to prevent memory leaks.
        """
        while self.running.is_set():
            time.sleep(VIDEO_BUFFER_TIMEOUT_SEC)
            with self.video_buffer_lock:
                now = time.time()
                for sender_addr in list(self.video_reassembly_buffers.keys()):
                    for pkt_id in list(self.video_reassembly_buffers[sender_addr].keys()):
                        if now - self.video_reassembly_buffers[sender_addr][pkt_id]['timestamp'] > VIDEO_BUFFER_TIMEOUT_SEC:
                            del self.video_reassembly_buffers[sender_addr][pkt_id]
                    if not self.video_reassembly_buffers[sender_addr]:
                        del self.video_reassembly_buffers[sender_addr]

    def mix_and_send_audio(self):
        """
        This is the hybrid model:
        1. Uses high-precision timer to prevent drops.
        2. Decompresses Mu-law audio from clients.
        3. Noise-gates, mixes, and normalizes the audio.
        4. Compresses the final mix back to Mu-law for low bandwidth.
        5. Also tracks the loudest speaker.
        """
        
        perf_counter = time.perf_counter
        interval = float(AUDIO_CHUNK_SIZE) / AUDIO_SAMPLE_RATE
        next_wake_time = perf_counter()

        while self.running.is_set():
            try:
                with self.client_lock:
                    clients = list(self.tcp_clients.values())
                
                if len(clients) < 1: 
                    time.sleep(0.1) 
                    next_wake_time = perf_counter()
                    continue
                
                sleep_duration = next_wake_time - perf_counter()
                
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                else:
                    if self.running.is_set():
                        pass
                        # self.log_message("[WARN] Audio-Mixer: CPU lag detected. Audio may stutter.")
                
                next_wake_time += interval
                
                all_chunks = {}
                with self.audio_buffer_lock:
                    for addr in list(self.audio_buffers.keys()):
                        try:
                            # --- Get compressed bytes and decompress ---
                            compressed_bytes = self.audio_buffers[addr].get_nowait()
                            pcm_bytes = ulaw2lin_numpy(compressed_bytes)
                            all_chunks[addr] = np.frombuffer(pcm_bytes, dtype=np.int16)
                        except queue.Empty:
                            all_chunks[addr] = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int16)
                        except (AttributeError, ValueError, KeyError):
                            all_chunks[addr] = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int16)

                # --- Active Speaker Detection ---
                loudest_addr = None
                max_rms = 0
                NOISE_THRESHOLD = 120
                # ---
                
                for client_data in clients:
                    target_addr = client_data['udp_addr']
                    if not target_addr: continue

                    mix_buffer = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int32)
                    
                    for sender_addr, chunk_array in all_chunks.items():
                        if sender_addr == target_addr: 
                            continue 
                        if len(chunk_array) != AUDIO_CHUNK_SIZE: 
                            continue

                        float_chunk = chunk_array.astype(np.float32)
                        rms = np.sqrt(np.mean(float_chunk**2))

                        if rms > NOISE_THRESHOLD:
                            mix_buffer += chunk_array.astype(np.int32)
                            
                            # --- Check if this is the loudest speaker ---
                            if rms > max_rms:
                                max_rms = rms
                                loudest_addr = sender_addr
                            # ---
                        else:
                            pass 
                    
                    mix_buffer_float = mix_buffer.astype(np.float32)
                    mix_rms = np.sqrt(np.mean(mix_buffer_float**2))
                    
                    MAX_GAIN = 4.0
                    TARGET_RMS_MIX = 3000
                    final_mix_int16 = mix_buffer.astype(np.int16) 
                    
                    if mix_rms > NOISE_THRESHOLD:
                        gain = TARGET_RMS_MIX / mix_rms
                        gain = min(gain, MAX_GAIN)
                        mix_buffer_float *= gain
                        final_mix_int16 = np.clip(mix_buffer_float, -32768, 32767).astype(np.int16)
                    else:
                        final_mix_int16 = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int16)

                    # --- Compress the final mix back to Mu-law ---
                    compressed_mix = lin2ulaw_numpy(final_mix_int16)
                    payload = safe_serialize({"type": "audio", "from": "ServerMix", "data": compressed_mix})
                    
                    self.udp_socket.sendto(payload, target_addr)
                
                # --- Update global active speaker ---
                with self.speaker_lock:
                    self.current_active_speaker_addr = loudest_addr
                # ---
                        
            except Exception as e:
                if self.running.is_set():
                    self.log_message(f"[ERROR] Audio-Mixer: {e}")

    def handle_tcp_client(self, client_data):
        client_socket = client_data['socket']
        client_ip = client_data['ip']
        username = None
        udp_addr = None
        
        try:
            # --- Authentication Flow ---
            metadata = client_socket.recv(1024).decode('utf-8')
            parts = metadata.split(':')

            # Expecting: JOIN:Username:UDPPort:MeetCode
            if not (parts[0] == 'JOIN' and len(parts) == 4):
                raise ValueError(f"Invalid JOIN format from {client_ip}")

            username = parts[1]
            client_udp_port = int(parts[2])
            client_meet_code = parts[3]

            # --- THE AUTHENTICATION CHECK ---
            if client_meet_code != self.meet_code:
                self.log_message(f"[AUTH_FAIL] Client {client_ip} used invalid code: {client_meet_code}")
                rejection_msg = {'type': 'auth_fail', 'content': 'Invalid meet code.'}
                try:
                    self.pack_and_send(client_socket, rejection_msg, acquire_lock=False)
                except Exception: pass
                client_socket.close()
                return # Stop handling this client

            self.log_message(f"[AUTH_SUCCESS] Client {client_ip} authenticated successfully.")
            # --- End Authentication Flow ---
            
            with self.client_lock:
                if username in self.username_to_socket:
                    self.log_message(f"Username '{username}' already taken. Disconnecting {client_ip}.")
                    rejection_msg = {'type': 'system', 'content': 'Username already taken.'}
                    try:
                        self.pack_and_send(client_socket, rejection_msg, acquire_lock=False)
                    except Exception: pass
                    client_socket.close()
                    return
            
            udp_addr = (client_ip, client_udp_port)
            
            with self.client_lock:
                # --- Store the main client socket ---
                client_data['username'] = username
                client_data['udp_addr'] = udp_addr
                client_data['tcp_ip'] = client_ip
                client_data['video_on'] = False
                self.tcp_clients[client_socket] = client_data
                # ---
                
                self.username_to_socket[username] = client_socket
                self.known_udp_addrs.add(udp_addr) 
            with self.audio_buffer_lock:
                if udp_addr not in self.audio_buffers:
                    self.audio_buffers[udp_addr] = queue.Queue(maxsize=5)
            self.log_message(f"Client '{username}' joined from {client_ip}:{client_udp_port}")
            self.broadcast_user_list()
            self.update_client_listbox() # <-- Will emit signal

            while True:
                prefix_data = client_socket.recv(8)
                if not prefix_data: break
                payload_size = struct.unpack("Q", prefix_data)[0]
                payload_data = b""
                while len(payload_data) < payload_size:
                    chunk_size = min(4096, payload_size - len(payload_data))
                    chunk = client_socket.recv(chunk_size)
                    if not chunk: raise ConnectionError("Client disconnected mid-payload")
                    payload_data += chunk
                
                if not self.running.is_set(): break
                message = safe_deserialize(payload_data)
                msg_type = message.get('type')
                
                if msg_type == 'file_init_request':
                    transfer_id = f"{username}_{message.get('filename').replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
                    with self.client_lock:
                        self.active_file_transfers[transfer_id] = {
                            'sender': username,
                            'receiver': None, # This is now a broadcast, no specific receiver
                            'filename': message.get('filename'),
                            'filesize': message.get('size'),
                            'local_filepath': None,
                            'status': 'waiting_for_upload', # New status
                            'file_hash': message.get('file_hash'),
                            'connection': None # Will be set by file_transfer thread
                        }
                    self.pack_and_send(client_socket, {
                        'type': 'file_start_upload',
                        'transfer_id': transfer_id,
                        'filename': message.get('filename'),
                        'port': FILE_TCP_PORT
                    })
                
                # --- Handle File Cancel ---
                elif msg_type == 'file_cancel':
                    transfer_id = message.get('transfer_id')
                    self.log_message(f"Received cancel request for {transfer_id} from {username}")
                    with self.client_lock:
                        if transfer_id in self.active_file_transfers:
                            self.active_file_transfers[transfer_id]['status'] = 'cancelled'
                    
                    # This will close the socket, kill the thread, and trigger cleanup
                    self.remove_file_transfer(transfer_id) 
                    
                    # Notify all clients
                    self.broadcast_message({
                        'type': 'file_transfer_cancelled',
                        'transfer_id': transfer_id
                    }, None, "System")
                # ---
                
                elif msg_type == 'file_accept':
                    pass
                elif msg_type == 'file_reject':
                    pass
                
                elif msg_type == 'video_toggle':
                    with self.client_lock:
                        if client_socket in self.tcp_clients:
                            self.tcp_clients[client_socket]['video_on'] = message['status']
                    self.broadcast_message(message, client_socket, username)
                
                elif msg_type == 'chat':
                     self.log_message(f"Chat from {username}: {message['content'][:50]}...")
                     self.broadcast_message(message, client_socket, username)

                else:
                    self.broadcast_message(message, client_socket, username)
                
        except (ConnectionResetError, ConnectionError, EOFError, struct.error, ValueError, OSError) as e:
            if self.running.is_set():
                self.log_message(f"Client {username or client_ip} disconnected: {e}")
        except Exception as e:
            if self.running.is_set():
                self.log_message(f"[ERROR] Client {username or client_ip}: {e}")
        
        finally:
            self.remove_client(client_socket)

    def remove_client(self, client_socket):
        """
        Safely removes a client and cleans up all associated resources.
        
        This is the primary cleanup function called when a client
        disconnects. It acquires all necessary locks to thread-safely
        remove the client from stateful dictionaries (tcp_clients,
        username_to_socket, known_udp_addrs) and media buffers
        (audio_buffers, video_reassembly_buffers).
        
        It also cleans up any file transfers associated with the user
        and broadcasts the new user list to all remaining clients.
        """
        username = None
        user_list_changed = False
        udp_addr_to_remove = None
        with self.client_lock:
            if client_socket in self.tcp_clients:
                client_data = self.tcp_clients.pop(client_socket)
                username = client_data['username']
                udp_addr = client_data['udp_addr']
                udp_addr_to_remove = udp_addr
                user_list_changed = True
                if udp_addr and udp_addr in self.known_udp_addrs:
                    self.known_udp_addrs.remove(udp_addr)
                if username and username in self.username_to_socket:
                    if self.username_to_socket[username] == client_socket:
                        del self.username_to_socket[username]
        
        if udp_addr_to_remove:
            with self.audio_buffer_lock:
                if udp_addr_to_remove in self.audio_buffers:
                    del self.audio_buffers[udp_addr_to_remove]
                    self.log_message(f"Removed audio buffer for {username or udp_addr_to_remove}")
            with self.video_buffer_lock:
                if udp_addr_to_remove in self.video_reassembly_buffers:
                    del self.video_reassembly_buffers[udp_addr_to_remove]
                    self.log_message(f"Removed video buffer for {username or udp_addr_to_remove}")
            with self.speaker_lock:
                if self.current_active_speaker_addr == udp_addr_to_remove:
                    self.current_active_speaker_addr = None

        try: client_socket.shutdown(socket.SHUT_RDWR)
        except Exception: pass
        try: client_socket.close()
        except Exception: pass

        if user_list_changed and username:
            self.log_message(f"'{username}' has left. Cleaning up resources.")
            transfers_to_clean = []
            with self.client_lock:
                for tid, data in self.active_file_transfers.items():
                    if (data['sender'] == username or data['receiver'] == username):
                        transfers_to_clean.append(tid)
            
            # Call the locking function *outside* the lock.
            # Now, remove_file_transfer can acquire the lock freely.
            for tid in transfers_to_clean:
                self.remove_file_transfer(tid)
            # Saves you from deadly deadlock 
            # Only update GUI if the server is still running
            if self.running.is_set():
                self.broadcast_message({'type': 'screen_stop', 'from': username}, None, "System")
                self.broadcast_user_list()
                self.update_client_listbox()

        elif user_list_changed:
            self.log_message("Unknown client disconnected. Cleaned up socket.")
            if self.running.is_set():
                self.update_client_listbox()
            
    def broadcast_user_list(self):
        """
        Gathers the current list of all connected users and broadcasts it.
        
        This function is called whenever a user joins or leaves. It
        constructs a list of user data (username, video_on status)
        and sends it as a 'user_list' message to all clients, allowing
        them to update their UIs.
        """
        with self.client_lock:
            user_list = []
            for client_data in self.tcp_clients.values():
                user_list.append({
                    'username': client_data['username'],
                    'video_on': client_data['video_on']
                })
        self.log_message(f"Updating user list: {user_list}")
        self.broadcast_message({'type': 'user_list', 'users': user_list}, None, "System")

    def pack_and_send(self, target_socket, message_dict, acquire_lock=True):
        """
        Serializes, packs, and sends a message to a single TCP socket.
        
        This helper function:
        1. Serializes the 'message_dict' to JSON bytes using 'safe_serialize'.
        2. Packs the length of the JSON data into an 8-byte (unsigned long long 'Q')
        binary prefix.
        3. Sends the prefix, immediately followed by the JSON data.
        
        This (Length-Prefix) + (Data) structure solves the TCP "stream" problem
        by allowing the receiver to know exactly how many bytes to read
        for one complete message.
        """
        if not self.running.is_set(): return
        try:
            data = safe_serialize(message_dict)
            prefix = struct.pack("Q", len(data))
            if acquire_lock:
                with self.tcp_send_lock:
                    target_socket.sendall(prefix + data)
            else:
                target_socket.sendall(prefix + data)
        except Exception as e:
            if self.running.is_set():
                self.log_message(f"[WARN] Failed to send: {e}. Removing client.")
                # We are in a backend thread, so we can call remove_client directly
                # (it will emit signals to update the UI)
                self.remove_client(target_socket)

    def relay_message(self, message_dict, target_username, log_info=""):
        """
        Finds a user by username and sends them a direct message.
        
        Used for features like file transfer handshakes where only one
        client (the receiver) should get the message.
        """
        if not target_username:
            self.log_message("[WARN] Tried to relay message to 'None' user.")
            return
        with self.client_lock:
            target_socket = self.username_to_socket.get(target_username)
        if target_socket:
            self.log_message(f"Relaying {message_dict['type']} {log_info}")
            self.pack_and_send(target_socket, message_dict)
        else:
            self.log_message(f"[WARN] Could not relay message to unknown user {target_username}")

    def broadcast_message(self, message_dict, sender_socket, sender_username):
        """
        Sends a TCP message to all connected clients *except* the sender.
        
        This is the primary relay mechanism for chat, screen sharing,
        and video status toggles.
        """
        if 'from' not in message_dict:
             message_dict['from'] = sender_username or "Unknown"
        with self.client_lock:
            clients_snapshot = list(self.tcp_clients.keys())
        for client in clients_snapshot:
            if client != sender_socket:
                self.pack_and_send(client, message_dict)

    # --- Shutdown Logic ---
    
    def on_closing(self):
        """
        This is the core shutdown logic, called by closeEvent.
        It now starts a non-blocking worker thread.
        """
        # --- Prevent double-shutdown ---
        if not self.running.is_set():
            return # Already shutting down

        self.log_message("Server is shutting down...")
        self.running.clear() 
        
        # Start a daemon thread to handle all blocking I/O
        shutdown_thread = threading.Thread(target=self._shutdown_worker, daemon=True, name="ShutdownWorker")
        shutdown_thread.start()
        
        self.log_message("GUI closing immediately.")
        # The main thread returns, allowing the window to close.

    def _shutdown_worker(self):
        """
        This function runs on a background thread to
        handle all blocking shutdown tasks.
        """
        # Close sockets to interrupt blocking calls in threads
        self.log_message("Closing server sockets...")
        if hasattr(self, 'tcp_socket'): 
            try: self.tcp_socket.close()
            except Exception: pass
        if hasattr(self, 'udp_socket'): 
            try: self.udp_socket.close()
            except Exception: pass
        if hasattr(self, 'file_tcp_socket'): 
            try: self.file_tcp_socket.close()
            except Exception: pass
        if hasattr(self, 'discovery_socket'): 
            try: self.discovery_socket.close()
            except Exception: pass
        
        with self.client_lock:
            clients_snapshot = list(self.tcp_clients.keys())
            
        self.log_message(f"Closing {len(clients_snapshot)} client connections in background...")
        for client in clients_snapshot:
            # This is now running on the worker thread,
            # so remove_client's blocking calls are safe.
            self.remove_client(client) 
            
        self.log_message("Cleaning up temp file directory...")
        try:
            if os.path.exists(FILE_TEMP_DIR):
                for f in os.listdir(FILE_TEMP_DIR):
                    try:
                        os.remove(os.path.join(FILE_TEMP_DIR, f))
                    except Exception as e_file:
                        self.log_message(f"[WARN] Could not remove file: {e_file}")
                os.rmdir(FILE_TEMP_DIR)
                self.log_message("Temp directory cleaned.")
        except Exception as e:
            self.log_message(f"[WARN] Could not clean up temp dir: {e}")
            
        self.log_message("Background cleanup complete. Process will exit.")

    def closeEvent(self, event):
        """
        PyQt's equivalent of `root.protocol("WM_DELETE_WINDOW")`.
        This event is triggered when the user clicks the 'X' button.
        """
        self.on_closing()
        event.accept()


if __name__ == "__main__":
    
    # --- Setup Logging ---
    setup_logging(log_file=config.LOG_FILE, log_level=config.LOG_LEVEL)
    
    # --- PyQt Application Setup ---
    # (DPI scaling is handled by the env var at the top of the file)
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    main_window = ServerGUI()
    main_window.show()

    # --- START: Graceful Ctrl+C Shutdown Fix ---

    # This function will run when Ctrl+C is pressed
    def sigint_handler(*args):
        """Handler for the SIGINT (Ctrl+C) signal."""
        print("\nCtrl+C detected. Shutting down server gracefully...")
        # Manually trigger the same cleanup as clicking 'X'
        main_window.on_closing()
        # Tell the Qt application to quit its event loop
        QApplication.quit()

    # Register the sigint_handler to run on SIGINT
    signal.signal(signal.SIGINT, sigint_handler)

    # This timer is a Qt-specific quirk. It forces the Python
    # interpreter to wake up every 500ms to check for signals
    # like Ctrl+C. Without this, the signal may not be caught
    # until you interact with the GUI.
    timer = QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None)  # Just wakes up Python
    
    # --- END: Graceful Ctrl+C Shutdown Fix ---
    
    # Run the application
    sys.exit(app.exec())