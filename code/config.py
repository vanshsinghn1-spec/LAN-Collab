"""
LAN Collab Configuration
Centralized configuration for both client and server.
"""

# ==========================================
# NETWORK CONFIGURATION
# ==========================================

# Port Configuration
TCP_PORT = 9090          # Main control/chat over SSL
UDP_PORT = 9091          # Audio/video streaming
FILE_TCP_PORT = 9100     # File transfer
DISCOVERY_PORT = 9092    # Service discovery

# Server Configuration
HOST = '0.0.0.0'         # Server listens on all interfaces
FILE_TEMP_DIR = "server_uploads"

# ==========================================
# AUDIO CONFIGURATION
# ==========================================

# Audio Settings
AUDIO_CHUNK_SIZE = 1024
AUDIO_FORMAT = 16        # pyaudio.paInt16
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_RATE = 16000

# Mu-law constant for audio compression
MU_LAW_CONSTANT = 255.0

# Audio mixing settings (server-side)
MIX_INTERVAL = AUDIO_CHUNK_SIZE / AUDIO_SAMPLE_RATE
TARGET_RMS = 2500

# ==========================================
# VIDEO CONFIGURATION
# ==========================================

# Video Settings
VIDEO_CAPTURE_FPS = 24
VIDEO_RENDER_FPS = 26
VIDEO_BUFFER_TIMEOUT_SEC = 2
VIDEO_WIDTH = 854
VIDEO_HEIGHT = 480

# H.264 quality/latency tuning
VIDEO_CRF = 23
VIDEO_KEYFRAME_INTERVAL = 10
VIDEO_MAX_BITRATE_KBPS = 4000
VIDEO_BUFFER_KBPS = 8000
VIDEO_ENCODER_PRESET = "ultrafast"

# Video fragmentation for UDP safety (base64 in JSON expands payload size)
VIDEO_FRAGMENT_CHUNK_BYTES = 60000

# UDP buffering (lower queueing delay while keeping moderate burst tolerance)
VIDEO_UDP_RCVBUF_BYTES = 2097152
VIDEO_UDP_SNDBUF_BYTES = 2097152

# Server media queue tuning (prevents multi-second delay from queue buildup)
UDP_MEDIA_QUEUE_MAXSIZE = 600
UDP_PROCESS_WORKERS = 4

# ==========================================
# UI THEME CONFIGURATION
# ==========================================

# Color Palette (Modern Dark Theme)
BG_COLOR = "#202124"
FRAME_BG = "#1A1A1E"
CHAT_BG = "#2E2E33"
LIST_BG = "#2E2E33"
FG_COLOR = "#E8EAED"
FG_DARKER = "#BDC1C6"
FG_MUTED = "#9A9A9A"

# Accent Colors
ACCENT_COLOR = "#8AB4F8"
ACCENT_DARK = "#5E8CDA"

# Button Colors
BTN_SUCCESS = "#34A853"
BTN_DANGER = "#EA4335"
BTN_DANGER_ACTIVE = "#F28B82"
BTN_BG = "#3C4043"
BTN_BG_ACTIVE = "#4A4E51"

# Avatar Colors (for user display)
AVATAR_COLORS = [
    "#F28B82", "#FCCB71", "#A8DAB5", "#8AB4F8", 
    "#C58AFB", "#FDCFE8", "#E6C9A8", "#A142F4"
]

# Server-specific colors
SERVER_BG_COLOR = "#1E1E1E"
SERVER_FRAME_BG = "#2D2D2D"
SERVER_LIST_BG = "#252525"
SERVER_LOG_BG = "#252525"
SERVER_FG_COLOR = "#F1F1F1"
SERVER_ACCENT_COLOR = "#0E63F4"
SERVER_ACCENT_DARK = "#0A4ABF"

# ==========================================
# SERIALIZATION CONFIGURATION
# ==========================================

# Binary data keys for safe JSON serialization
BINARY_KEYS = ['data', 'chunk', 'frame']

# ==========================================
# WINDOW FILTERING (Screen Share)
# ==========================================

# Windows to exclude from screen share list
JUNK_WINDOW_TITLES = {
    'Program Manager',
    'Default IME',
    'MSCTFIME UI',
    'Calculator',
    'Settings',
    '',  # Empty titles
}

# ==========================================
# LOGGING CONFIGURATION
# ==========================================

# Log file settings
LOG_FILE = "lan_collab.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
