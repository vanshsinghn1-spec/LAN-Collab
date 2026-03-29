"""
LAN Collab Shared Utilities
Common functions used by both client and server.
"""

import numpy as np
import json
import base64
import logging
from typing import Dict, Any

from config import MU_LAW_CONSTANT, BINARY_KEYS

# ==========================================
# MU-LAW AUDIO COMPRESSION
# ==========================================

def lin2ulaw_numpy(audio_data: np.ndarray) -> bytes:
    """
    Converts linear PCM (16-bit) numpy array to mu-law encoded bytes.
    
    Args:
        audio_data: Input audio as int16 numpy array
        
    Returns:
        Mu-law compressed audio as bytes
    """
    # Ensure data is float and scale to [-1.0, 1.0]
    pcm_float = audio_data.astype(np.float32) / 32768.0
    
    # Apply mu-law compression formula
    compressed = np.sign(pcm_float) * (
        np.log(1.0 + MU_LAW_CONSTANT * np.abs(pcm_float)) / 
        np.log(1.0 + MU_LAW_CONSTANT)
    )
    
    # Scale to 8-bit unsigned range [0, 255] and quantize
    ulaw_encoded = ((compressed + 1.0) * 127.5).astype(np.uint8)
    
    return ulaw_encoded.tobytes()


def ulaw2lin_numpy(ulaw_data: bytes) -> bytes:
    """
    Converts mu-law encoded bytes to linear PCM (16-bit) numpy array.
    
    Args:
        ulaw_data: Mu-law compressed audio as bytes
        
    Returns:
        Linear PCM audio as bytes
    """
    # Convert bytes to numpy array [0, 255]
    ulaw_array = np.frombuffer(ulaw_data, dtype=np.uint8)
    
    # Scale to [-1.0, 1.0] range
    expanded = (ulaw_array.astype(np.float32) / 127.5) - 1.0
    
    # Apply mu-law expansion formula
    pcm_float = np.sign(expanded) * (1.0 / MU_LAW_CONSTANT) * (
        (1.0 + MU_LAW_CONSTANT)**np.abs(expanded) - 1.0
    )
    
    # Scale back to 16-bit integer range and convert type
    pcm_int16 = (pcm_float * 32768.0).astype(np.int16)
    
    return pcm_int16.tobytes()


# ==========================================
# SAFE JSON SERIALIZATION
# ==========================================

def safe_serialize(payload: Dict[str, Any]) -> bytes:
    """
    Safely serializes a payload to JSON, encoding binary fields as base64.
    
    Args:
        payload: Dictionary containing message data
        
    Returns:
        JSON-encoded bytes
    """
    try:
        # Create a copy to avoid modifying the original dict in-place
        payload_copy = payload.copy()
        
        # Encode binary fields to base64 strings
        for key in BINARY_KEYS:
            if key in payload_copy and isinstance(payload_copy[key], bytes):
                payload_copy[key] = base64.b64encode(payload_copy[key]).decode('utf-8')
        
        return json.dumps(payload_copy).encode('utf-8')
        
    except Exception as e:
        logging.error(f"Safe-serialize error: {e}. Payload type: {payload.get('type', 'N/A')}")
        return b"{}"  # Return empty JSON object on failure


def safe_deserialize(data: bytes) -> Dict[str, Any]:
    """
    Safely deserializes JSON data, decoding base64 binary fields.
    
    Args:
        data: JSON-encoded bytes
        
    Returns:
        Dictionary containing message data
    """
    try:
        # Decode bytes to string, then parse JSON
        payload = json.loads(data.decode('utf-8'))
        
        # Decode base64 strings back to bytes
        for key in BINARY_KEYS:
            if key in payload and isinstance(payload[key], str):
                try:
                    payload[key] = base64.b64decode(payload[key])
                except (base64.binascii.Error, TypeError) as e:
                    # Silently handle invalid base64 for non-critical fields
                    if "Invalid base64-encoded string" not in str(e):
                        logging.warning(f"Could not decode base64 for key '{key}': {e}")
        
        return payload
        
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.error(f"Safe-deserialize error: {e}. Data preview: {data[:50]}...")
        return {}  # Return empty dict on failure


# ==========================================
# LOGGING SETUP
# ==========================================

def setup_logging(log_file: str = None, log_level: str = "INFO") -> None:
    """
    Configures the logging system for the application.
    
    Args:
        log_file: Optional log file path
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    from config import LOG_FORMAT
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure handlers
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    # Setup logging
    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        handlers=handlers
    )
    
    logging.info(f"Logging initialized at {log_level} level")
