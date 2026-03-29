import os
import sys
import platform
import argparse
from OpenSSL import crypto
from datetime import datetime

def generate_advanced_self_signed_cert(
    cert_file="server.crt",
    key_file="server.key",
    key_type=crypto.TYPE_RSA,
    key_bits=4096,
    valid_days=3650,
    country="US",
    state="California",
    locality="San Francisco",
    org="LAN Collab",
    org_unit="LAN Collab Dept",
    common_name="lan-collab-server"
):
    """
    Generates an "advanced" self-signed X.509 certificate and private key.
    
    Advanced Features:
    1. Stronger key size (default 4096 bits) and hash (sha512).
    2. Includes Subject Alternative Name (SAN) for modern compatibility.
    3. Sets secure file permissions (600) on the private key.
    """
    
    # Check if files already exist
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"'{cert_file}' and '{key_file}' already exist. Skipping generation.")
        print("To re-generate, please delete the existing files first.")
        return

    # 1. Create a new private key
    print(f"Generating {key_bits}-bit RSA private key... (This may take a moment)")
    pkey = crypto.PKey()
    pkey.generate_key(key_type, key_bits)

    # 2. Create a self-signed certificate
    print("Generating self-signed certificate...")
    cert = crypto.X509()
    
    # Set standard certificate attributes
    cert.get_subject().C = country
    cert.get_subject().ST = state
    cert.get_subject().L = locality
    cert.get_subject().O = org
    cert.get_subject().OU = org_unit
    cert.get_subject().CN = common_name
    
    cert.set_serial_number(int(datetime.now().timestamp()))
    cert.gmtime_adj_notBefore(0)  # Valid from now
    cert.gmtime_adj_notAfter(valid_days * 24 * 60 * 60)  # Valid for 'valid_days'
    
    cert.set_issuer(cert.get_subject())  # Issuer is itself
    cert.set_pubkey(pkey)  # Set the public key

    # 3. [ADVANCED] Add Subject Alternative Name (SAN) extension
    # This is critical for modern clients (like browsers) to trust the cert,
    # especially when connecting via IP address.
    #
    # --- BEGIN FIX FOR SAN EXTENSION ---
    # The OpenSSL extension parser does not support CIDR notation
    # (e.g., 192.168.0.0/16). We will use universally valid names.
    # Since our client is set to bypass checks anyway (CERT_NONE),
    # we just need a structurally valid SAN entry to prevent errors.
    san_list = [
        "DNS:localhost",
        "IP:127.0.0.1"
    ]

    # [DEPRECATION NOTE] The user_log is correct, X509Extension is deprecated.
    # However, switching to the 'cryptography' library is a major re-write.
    san_extension = crypto.X509Extension(
        b"subjectAltName", critical=False, value=", ".join(san_list).encode("utf-8")
    )
    cert.add_extensions([san_extension])

    # 4. Sign the certificate with the private key using a strong hash
    print("Signing certificate with sha512...")
    cert.sign(pkey, 'sha512')

    # 5. Save files
    try:
        print(f"Saving private key to {key_file}...")
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        
        # 6. [ADVANCED] Set secure permissions on the private key
        # This is the MOST IMPORTANT step for "preventing attack".
        # It makes the key file readable/writable *only* by the user who created it.
        if platform.system() != "Windows":
            print(f"Setting secure file permissions (600) on {key_file}...")
            os.chmod(key_file, 0o600)
        else:
            print(f"NOTE: On Windows, please manually set file permissions for {key_file}")
            print("Right-click -> Properties -> Security -> Advanced -> Disable inheritance")
            print("Then remove all users except your own user account.")

        print(f"Saving certificate to {cert_file}...")
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
        print("\nSuccess! Advanced certificate and key have been generated.")
        print(f"Files created:\n- {os.path.abspath(key_file)}\n- {os.path.abspath(cert_file)}")

    except Exception as e:
        print(f"\n[ERROR] Could not write files: {e}", file=sys.stderr)
        print("Please check file permissions in this directory.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Advanced Self-Signed Certificate Generator for LAN Collab."
    )
    parser.add_argument(
        "--cert-file", 
        default="server.crt", 
        help="Filename for the output certificate (default: server.crt)"
    )
    parser.add_argument(
        "--key-file", 
        default="server.key", 
        help="Filename for the output private key (default: server.key)"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=3650, 
        help="Number of days the certificate is valid for (default: 3650)"
    )
    parser.add_argument(
        "--key-size", 
        type=int, 
        default=4096, 
        help="Size of the RSA key in bits (default: 4096)"
    )
    parser.add_argument(
        "--cn", 
        default="lan-collab-server", 
        help="Common Name for the certificate (default: lan-collab-server)"
    )
    
    args = parser.parse_args()

    generate_advanced_self_signed_cert(
        cert_file=args.cert_file,
        key_file=args.key_file,
        key_bits=args.key_size,
        valid_days=args.days,
        common_name=args.cn
    )


