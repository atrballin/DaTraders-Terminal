"""
Cryptographic utilities for DaTraders Security System.
Provides encryption/decryption for sensitive data storage.
"""
import os
import json
import hashlib
from cryptography.fernet import Fernet
import uuid
import platform

# SECURITY SEED (Used for cross-machine license verification)
# Do not change this or previously issued keys will become invalid.
_S1 = b'DaTraders'
_S2 = b'Secure'
_S3 = b'Algo'
_S4 = b'2026'

def get_static_license_key():
    """Derive the static license key from internal seeds."""
    combined = hashlib.sha256(_S1 + _S2 + _S3 + _S4).digest()
    import base64
    return base64.urlsafe_b64encode(combined)

LICENSE_KEY = get_static_license_key()

def get_machine_id():
    """
    Generate a machine-specific identifier.
    Uses MAC address + hostname for uniqueness.
    """
    mac = uuid.getnode()
    hostname = platform.node()
    combined = f"{mac}-{hostname}".encode()
    return hashlib.sha256(combined).hexdigest()

def derive_key():
    """
    Derive encryption key from machine ID.
    This makes encrypted files machine-specific.
    """
    machine_id = get_machine_id()
    # Use machine ID as base, add salt
    salt = b"DaTraders_Algo_Security_2026"
    key_material = machine_id.encode() + salt
    key_hash = hashlib.sha256(key_material).digest()
    # Fernet requires base64-encoded 32-byte key
    import base64
    return base64.urlsafe_b64encode(key_hash)

def get_cipher():
    """Get Fernet cipher instance."""
    key = derive_key()
    return Fernet(key)

def encrypt_data(data):
    """
    Encrypt Python object (dict/list) to encrypted string.
    Returns base64-encoded encrypted JSON.
    """
    cipher = get_cipher()
    json_str = json.dumps(data)
    encrypted = cipher.encrypt(json_str.encode())
    return encrypted.decode()

def decrypt_data(encrypted_str):
    """
    Decrypt encrypted string back to Python object.
    """
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_str.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

def encrypt_file(filepath, data):
    """
    Encrypt and write data to file.
    """
    encrypted = encrypt_data(data)
    with open(filepath, 'w') as f:
        f.write(encrypted)

def decrypt_file(filepath):
    """
    Read and decrypt data from file.
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        encrypted = f.read()
    
    return decrypt_data(encrypted)

def hash_password(password):
    """
    Hash password using SHA256.
    (For master password verification)
    """
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    """
    Verify password against hash.
    """
    import bcrypt
    return bcrypt.checkpw(password.encode(), hashed.encode())

def encrypt_license(data):
    """
    Encrypt data using the static LICENSE_KEY for distribution.
    """
    cipher = Fernet(LICENSE_KEY)
    json_str = json.dumps(data)
    return cipher.encrypt(json_str.encode()).decode()

def decrypt_license(encrypted_str):
    """
    Decrypt data using the static LICENSE_KEY.
    """
    try:
        cipher = Fernet(LICENSE_KEY)
        decrypted = cipher.decrypt(encrypted_str.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        raise ValueError(f"License decryption failed: {e}")

def load_key_pool(pool_path, key_size=16):
    """
    Loads keys from the binary pool, decrypts them, and stores in a set.
    """
    if not os.path.exists(pool_path):
        return set()
    
    with open(pool_path, 'rb') as f:
        encrypted_data = f.read()
    
    from cryptography.fernet import Fernet
    cipher = Fernet(LICENSE_KEY)
    try:
        data = cipher.decrypt(encrypted_data)
    except:
        return set()
    
    keys = set()
    for i in range(0, len(data), key_size):
        keys.add(data[i:i+key_size])
    return keys

def get_random_pool_key(pool_path, key_size=16):
    """
    Decrypts the pool and picks a random key.
    """
    if not os.path.exists(pool_path):
        return None
    
    with open(pool_path, 'rb') as f:
        encrypted_data = f.read()
    
    from cryptography.fernet import Fernet
    cipher = Fernet(LICENSE_KEY)
    try:
        data = cipher.decrypt(encrypted_data)
    except:
        return None
    
    num_keys = len(data) // key_size
    import secrets
    idx = secrets.randbelow(num_keys)
    
    start = idx * key_size
    return data[start:start+key_size]

def calculate_file_hash(filepath):
    """
    Calculates the SHA256 hash of a file by reading it in chunks.
    Useful for verifying application integrity without loading the whole file into memory.
    """
    if not os.path.exists(filepath):
        return None
    
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            # Read in 64KB chunks
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculating hash for {filepath}: {e}")
        return None
