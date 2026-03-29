import random
import string
import socket
import uuid

def generate_deterministic_numeric_code():
    """
    Generates a 9-digit code (e.g., 123-456-789) based on the machine's
    unique, permanent MAC address.
    
    This is deterministic (same machine = same code) and 
    collision-resistant (different machine = different code).
    """
    try:
        # 1. Get the MAC address as a stable, unique number.
        # This is the "secret" unique ID for the server.
        mac_num = uuid.getnode()
        
        # 2. Use a LOCAL random instance (avoid reseeding the global module).
        rng = random.Random(mac_num)
        
        # 3. Generate a 9-digit number.
        code_num = rng.randint(100_000_000, 999_999_999)
        
        # 4. Format it for readability (e.g., "123-456-789")
        part1 = code_num // 1_000_000
        part2 = (code_num % 1_000_000) // 1_000
        part3 = code_num % 1_000
        
        # zfill(3) ensures we get "001" instead of "1"
        return f"{str(part1).zfill(3)}-{str(part2).zfill(3)}-{str(part3).zfill(3)}"
        
    except Exception as e:
        print(f"[ERROR] Could not generate deterministic code: {e}")
        # Fallback to a simple random code if uuid fails
        return f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"

def get_lan_ip():
    """
    Finds the server's local LAN IP address.
    Works offline by falling back to hostname.
    """
    # print("Attempting to determine LAN IP...")
    try:
        # We connect to a public DNS to find our *outbound* IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 80)) # Connect to Google DNS
        ip = s.getsockname()[0]
        s.close()
        # print(f"Determined LAN IP: {ip}")
        return ip
    except Exception as e:
        # print(f"[WARN] Could not auto-detect IP via Google: {e}")
        # Fallback for offline environments
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                print("Warning: IP is loopback. Clients on other machines cannot connect.")
            # print(f"Determined Hostname IP: {ip}")
            return ip
        except Exception as e_host:
            print(f"[ERROR] Hostname IP lookup failed: {e_host}")
            return None # Return None on failure

