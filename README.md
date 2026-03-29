# LAN Collaboration Project (LAN Collab)

A secure, offline-capable video conferencing and collaboration tool designed for Local Area Networks (LAN). Built with Python and PyQt6.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## 📌 Overview
LAN Collab is a standalone application that allows users on the same network to connect, chat, video call, and share files **without an internet connection**. It uses a custom client-server architecture with:
*   **TCP (SSL/TLS)** for secure control messages and chat.
*   **UDP** for low-latency real-time audio and video streaming.
*   **Service Discovery** for automatic server detection.

## ✨ Features
*   **Encrypted Chat**: Secure messaging using SSL sockets.
*   **Video Conferencing**: Real-time H.264 video streaming with dynamic grid layout.
*   **Crystal Clear Audio**: Mu-law compressed audio with active speaker detection.
*   **Screen Sharing**: Low-latency desktop mirroring (using `mss` and `av`).
*   **File Transfer**: Drag-and-drop file sharing with MD5 integrity checks.
*   **Modern UI**: Dark mode interface built with Qt6.

## 🚀 Getting Started

Choose one of the two options below:

### Option A: Run From Source (for developers)

### Prerequisites
*   Python 3.9+
*   A microphone and webcam (optional but recommended)

### Installation
1.  Fork/clone the repository or download the source ZIP.
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the System
**Step 1: Start the Server**
The server acts as the central hub. Run it on one machine:
```bash
python code/lan_s29.py
```
*Note: The first time you run this, you must run `python code/generate_certs.py` to create the SSL certificates.*

**Step 2: Start Clients**
Run the client on the same machine or other machines on the network:
```bash
python code/lan_c29.py
```
*   Enter your **Name** and the **Meet Code** displayed on the Server's screen.
*   If the server isn't found automatically, enter the Server's IP address (shown on the Server dashboard).

### Option B: Run Prebuilt Executables (for non-developers)
If you just want to run the app without installing Python, use the files in `executables_win11/`:

1.  Start server: `executables_win11/lan_server.exe`
2.  Start client: `executables_win11/lan_client.exe`
3.  Keep these files in the same folder as the executables:
    * `server.crt`
    * `server.key`

Tip: For GitHub distribution, it's best to upload executables as a Release asset ZIP.

## 🛠 Project Structure
*   `code/lan_s29.py`: **Server**. Handles connection logic, audio mixing, and broadcasting.
*   `code/lan_c29.py`: **Client**. The main GUI application for users.
*   `code/auth_utils.py`: Utilities for IP detection and secure code generation.
*   `code/config.py`: Central settings (ports, video quality, latency tuning, UI constants).
*   `code/shared_utils.py`: Shared helper functions used by both client and server.
*   `code/generate_certs.py`: Helper script to generate self-signed SSL certificates.

## ⚠️ Security Note
This project uses **Self-Signed Certificates** for SSL encryption.
*   **Pros**: No need for a domain name or internet access. Zero configuration.
*   **Cons**: The client is configured to bypass certificate verification (`CERT_NONE`) to allow these self-signed certs.
*   **Implication**: The connection is encrypted against passive eavesdropping, but is theoretically vulnerable to active Man-in-the-Middle attacks on the LAN. This is a design choice for usability in a trusted home/office environment.

### What `server.crt` and `server.key` actually do
*   `server.crt` is the public certificate. It helps clients start an encrypted TLS session.
*   `server.key` is the private key. It proves the server identity and must stay secret.

### Why you should not publish private keys in a public repo
If someone gets your `server.key`, they can impersonate your server and intercept traffic in some scenarios.
Even in LAN projects, private keys should be treated as secrets.

### Recommended GitHub practice
*   Do **not** commit `server.key`.
*   Prefer generating certificates locally with `python code/generate_certs.py`.
*   If distributing executables, include cert/key in a downloadable ZIP or generate on first run.

## 📦 Building Executables
To compile this project into `.exe` files for easier distribution, you can use `pyinstaller`:
```bash
pyinstaller --noconsole --onefile code/lan_c29.py
pyinstaller --noconsole --onefile code/lan_s29.py
```
