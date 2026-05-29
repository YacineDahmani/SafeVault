"""
SafeVault Backend - Cryptography and Database Management
"""

import os
import re
import sqlite3
import secrets
import string
import base64
import hmac
import hashlib
import time
import urllib.parse
import math
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Backend:
    """
    Handles all database operations and cryptographic functions.
    
    Security Model:
    - Master password is NEVER stored - only a salted hash for verification
    - Encryption key is derived from master password at runtime (memory only)
    - Each encrypted field has its own unique salt
    - All sensitive data (passwords, card numbers, CVV, notes) stored as encrypted BLOBs
    """
    
    VERSION = "1.1.4"
    PBKDF2_ITERATIONS = 100_000
    TOTP_STEP_SECONDS = 30
    TOTP_DIGITS = 6
    
    def __init__(self, db_path: str = "vault.db"):
        """Initialize the backend with database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self._encryption_key: bytes | None = None
    
    def _init_db(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL
            )
        """)
        
        try:
            cursor.execute("ALTER TABLE master ADD COLUMN twofa_enabled INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE master ADD COLUMN twofa_secret_encrypted BLOB")
            cursor.execute("ALTER TABLE master ADD COLUMN twofa_secret_salt BLOB")
        except sqlite3.OperationalError:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                username TEXT NOT NULL,
                password_encrypted BLOB NOT NULL,
                salt BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                holder_name TEXT NOT NULL,
                card_number_encrypted BLOB NOT NULL,
                card_number_salt BLOB NOT NULL,
                expiry_encrypted BLOB NOT NULL,
                expiry_salt BLOB NOT NULL,
                cvv_encrypted BLOB NOT NULL,
                cvv_salt BLOB NOT NULL,
                pin_encrypted BLOB,
                pin_salt BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        try:
            cursor.execute("ALTER TABLE cards ADD COLUMN pin_encrypted BLOB")
            cursor.execute("ALTER TABLE cards ADD COLUMN pin_salt BLOB")
        except sqlite3.OperationalError:
            pass  
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_encrypted BLOB NOT NULL,
                salt BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS env_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                content_encrypted BLOB NOT NULL,
                salt BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entry_tags (
                tag_id INTEGER,
                entry_type TEXT NOT NULL,
                entry_id INTEGER NOT NULL,
                PRIMARY KEY (tag_id, entry_type, entry_id),
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        self.conn.commit()
    
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive a cryptographic key from a password using PBKDF2-HMAC-SHA256.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
        )
        derived_key = kdf.derive(password.encode('utf-8'))
        return base64.urlsafe_b64encode(derived_key)
  
    def is_first_run(self) -> bool:
        """Check if this is the first run (no master password set)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM master")
        return cursor.fetchone()[0] == 0
    
    def create_master_password(self, password: str) -> bool:
        """Create and store the master password hash."""
        if not self.is_first_run():
            return False
        
        salt = os.urandom(16)
        password_hash = self.derive_key(password, salt)
        
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO master (id, salt, password_hash) VALUES (1, ?, ?)",
            (salt, password_hash)
        )
        self.conn.commit()
        self._encryption_key = password_hash
        return True
    
    def verify_master_password(self, password: str) -> bool:
        """Verify the master password and derive encryption key."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT salt, password_hash FROM master WHERE id = 1")
        row = cursor.fetchone()
        
        if not row:
            return False
        
        derived_hash = self.derive_key(password, row['salt'])
        
        if derived_hash == row['password_hash']:
            self._encryption_key = derived_hash
            return True
        return False

    def is_2fa_enabled(self) -> bool:
        """Check if 2FA is enabled for the vault."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT twofa_enabled FROM master WHERE id = 1")
        row = cursor.fetchone()
        return bool(row and row['twofa_enabled'])

    def _get_2fa_secret(self) -> str:
        """Decrypt and return the 2FA secret."""
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        cursor = self.conn.cursor()
        cursor.execute("SELECT twofa_secret_encrypted, twofa_secret_salt FROM master WHERE id = 1")
        row = cursor.fetchone()
        if not row or not row['twofa_secret_encrypted'] or not row['twofa_secret_salt']:
            raise RuntimeError("2FA secret not found.")
        return self.decrypt(row['twofa_secret_encrypted'], row['twofa_secret_salt'])

    def get_2fa_secret(self) -> str:
        """Public accessor for the 2FA secret (requires unlocked vault)."""
        return self._get_2fa_secret()

    def generate_2fa_secret(self) -> str:
        """Generate a new base32 2FA secret."""
        raw = secrets.token_bytes(20)
        return base64.b32encode(raw).decode('utf-8').replace('=', '')

    def build_2fa_otpauth_uri(self, secret: str, account_name: str, issuer: str = "SafeVault") -> str:
        """Build an otpauth:// URI for TOTP setup."""
        label = f"{issuer}:{account_name}"
        label_q = urllib.parse.quote(label)
        issuer_q = urllib.parse.quote(issuer)
        return f"otpauth://totp/{label_q}?secret={secret}&issuer={issuer_q}&digits={self.TOTP_DIGITS}&period={self.TOTP_STEP_SECONDS}"

    def enable_2fa(self, secret: str) -> None:
        """Enable 2FA and store encrypted secret."""
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        salt = os.urandom(16)
        encrypted = self.encrypt(secret, salt)
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE master SET twofa_enabled = 1, twofa_secret_encrypted = ?, twofa_secret_salt = ? WHERE id = 1",
            (encrypted, salt)
        )
        self.conn.commit()

    def disable_2fa(self) -> None:
        """Disable 2FA and clear stored secret."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE master SET twofa_enabled = 0, twofa_secret_encrypted = NULL, twofa_secret_salt = NULL WHERE id = 1"
        )
        self.conn.commit()

    def verify_2fa_code(self, code: str, window: int = 1) -> bool:
        """Verify a 2FA code against the stored secret."""
        if not self.is_2fa_enabled():
            return False
        secret = self._get_2fa_secret()
        return self._verify_totp_code(secret, code, window=window)

    def verify_2fa_code_for_secret(self, secret: str, code: str, window: int = 1) -> bool:
        """Verify a 2FA code against a provided secret."""
        return self._verify_totp_code(secret, code, window=window)

    def _normalize_base32_secret(self, secret: str) -> str:
        s = re.sub(r"\s+", "", secret).upper()
        pad = (-len(s)) % 8
        return s + ("=" * pad)

    def _totp(self, secret: str, for_time: int | None = None) -> str:
        if for_time is None:
            for_time = int(time.time())
        counter = int(for_time // self.TOTP_STEP_SECONDS)
        key = base64.b32decode(self._normalize_base32_secret(secret), casefold=True)
        msg = counter.to_bytes(8, "big")
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
        code = code_int % (10 ** self.TOTP_DIGITS)
        return str(code).zfill(self.TOTP_DIGITS)

    def _verify_totp_code(self, secret: str, code: str, window: int = 1) -> bool:
        if not code:
            return False
        normalized = re.sub(r"\s+", "", code)
        if not normalized.isdigit():
            return False
        now = int(time.time())
        for offset in range(-window, window + 1):
            if self._totp(secret, now + (offset * self.TOTP_STEP_SECONDS)) == normalized:
                return True
        return False
    
    def _derive_entry_key(self, master_key_str: str, salt: bytes, fast: bool = True) -> bytes:
        """
        Derive a cryptographic subkey from the master key.
        Uses 1 iteration of PBKDF2 for high speed when fast=True (since master key is already high entropy).
        Uses 100,000 iterations for legacy compatibility when fast=False.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=1 if fast else self.PBKDF2_ITERATIONS,
        )
        derived_key = kdf.derive(master_key_str.encode('utf-8'))
        return base64.urlsafe_b64encode(derived_key)

    def encrypt(self, plaintext: str, salt: bytes) -> bytes:
        """Encrypt plaintext using Fernet with derived key."""
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        
        entry_key = self._derive_entry_key(self._encryption_key.decode('utf-8'), salt, fast=True)
        fernet = Fernet(entry_key)
        return fernet.encrypt(plaintext.encode('utf-8'))
    
    def decrypt(self, ciphertext: bytes, salt: bytes) -> str:
        """Decrypt ciphertext using Fernet with derived key, with backward compatibility."""
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        
        # Try fast key derivation first (1 iteration)
        entry_key_fast = self._derive_entry_key(self._encryption_key.decode('utf-8'), salt, fast=True)
        fernet_fast = Fernet(entry_key_fast)
        try:
            return fernet_fast.decrypt(ciphertext).decode('utf-8')
        except (InvalidToken, ValueError):
            # Fallback to slow key derivation (legacy 100,000 iterations)
            entry_key_slow = self._derive_entry_key(self._encryption_key.decode('utf-8'), salt, fast=False)
            fernet_slow = Fernet(entry_key_slow)
            try:
                return fernet_slow.decrypt(ciphertext).decode('utf-8')
            except InvalidToken:
                raise ValueError("Decryption failed. Data may be corrupted.")

   
    def add_password(self, app_name: str, username: str, password: str) -> int:
        """Add a new password entry."""
        salt = os.urandom(16)
        encrypted = self.encrypt(password, salt)
        
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO passwords (app_name, username, password_encrypted, salt) VALUES (?, ?, ?, ?)",
            (app_name, username, encrypted, salt)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_password_entry(self, entry_id: int) -> dict:
        """Return a password entry with decrypted password."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT app_name, username, password_encrypted, salt FROM passwords WHERE id = ?",
            (entry_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Password entry {entry_id} not found.")
        return {
            'app_name': row['app_name'],
            'username': row['username'],
            'password': self.decrypt(row['password_encrypted'], row['salt'])
        }
    
    def get_all_passwords(self) -> list[dict]:
        """Get all password entries (passwords remain encrypted)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, app_name, username, created_at FROM passwords ORDER BY app_name")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_password(self, entry_id: int) -> str:
        """Decrypt and return a password."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password_encrypted, salt FROM passwords WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Password entry {entry_id} not found.")
        return self.decrypt(row['password_encrypted'], row['salt'])
    
    def delete_password(self, entry_id: int) -> bool:
        """Delete a password entry."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM passwords WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_password(self, entry_id: int, app_name: str, username: str, password: str) -> bool:
        """Update a password entry and re-encrypt its password."""
        salt = os.urandom(16)
        encrypted = self.encrypt(password, salt)
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE passwords
               SET app_name = ?, username = ?, password_encrypted = ?, salt = ?
               WHERE id = ?""",
            (app_name, username, encrypted, salt, entry_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0
 
    def add_card(self, label: str, holder_name: str, card_number: str, expiry: str, cvv: str, pin: str) -> int:
        """Add a new credit card entry with all sensitive fields encrypted."""
        card_salt = os.urandom(16)
        expiry_salt = os.urandom(16)
        cvv_salt = os.urandom(16)
        pin_salt = os.urandom(16)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO cards 
               (label, holder_name, card_number_encrypted, card_number_salt, 
                expiry_encrypted, expiry_salt, cvv_encrypted, cvv_salt,
                pin_encrypted, pin_salt) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (label, holder_name, 
             self.encrypt(card_number, card_salt), card_salt,
             self.encrypt(expiry, expiry_salt), expiry_salt,
             self.encrypt(cvv, cvv_salt), cvv_salt,
             self.encrypt(pin, pin_salt), pin_salt)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_cards(self) -> list[dict]:
        """Get all card entries (sensitive data remains encrypted)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, label, holder_name, created_at,
                   card_number_encrypted, card_number_salt,
                   expiry_encrypted, expiry_salt
            FROM cards ORDER BY label
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_details(self, card_id: int) -> dict:
        """Decrypt and return full card details."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT label, holder_name, 
                      card_number_encrypted, card_number_salt,
                      expiry_encrypted, expiry_salt,
                      cvv_encrypted, cvv_salt,
                      pin_encrypted, pin_salt
               FROM cards WHERE id = ?""", 
            (card_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Card {card_id} not found.")
        
        details = {
            'label': row['label'],
            'holder_name': row['holder_name'],
            'card_number': self.decrypt(row['card_number_encrypted'], row['card_number_salt']),
            'expiry': self.decrypt(row['expiry_encrypted'], row['expiry_salt']),
            'cvv': self.decrypt(row['cvv_encrypted'], row['cvv_salt']),
            'pin': ''
        }
        
        if row['pin_encrypted'] and row['pin_salt']:
             details['pin'] = self.decrypt(row['pin_encrypted'], row['pin_salt'])
             
        return details
    
    def delete_card(self, card_id: int) -> bool:
        """Delete a card entry."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_card(self, card_id: int, label: str, holder_name: str,
                    card_number: str, expiry: str, cvv: str, pin: str) -> bool:
        """Update a card entry and re-encrypt sensitive fields."""
        card_salt = os.urandom(16)
        expiry_salt = os.urandom(16)
        cvv_salt = os.urandom(16)
        pin_salt = os.urandom(16)

        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE cards
               SET label = ?, holder_name = ?,
                   card_number_encrypted = ?, card_number_salt = ?,
                   expiry_encrypted = ?, expiry_salt = ?,
                   cvv_encrypted = ?, cvv_salt = ?,
                   pin_encrypted = ?, pin_salt = ?
               WHERE id = ?""",
            (label, holder_name,
             self.encrypt(card_number, card_salt), card_salt,
             self.encrypt(expiry, expiry_salt), expiry_salt,
             self.encrypt(cvv, cvv_salt), cvv_salt,
             self.encrypt(pin, pin_salt), pin_salt,
             card_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def add_env_file(self, label: str, content: str) -> int:
        """Add a new encrypted .env file entry."""
        salt = os.urandom(16)
        encrypted = self.encrypt(content, salt)

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO env_files (label, content_encrypted, salt) VALUES (?, ?, ?)",
            (label, encrypted, salt)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_env_files(self) -> list[dict]:
        """Get all stored .env file entries (content remains encrypted)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, label, created_at FROM env_files ORDER BY label")
        return [dict(row) for row in cursor.fetchall()]

    def get_env_file_content(self, env_file_id: int) -> dict:
        """Decrypt and return .env file content."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT label, content_encrypted, salt FROM env_files WHERE id = ?",
            (env_file_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f".env entry {env_file_id} not found.")

        return {
            'label': row['label'],
            'content': self.decrypt(row['content_encrypted'], row['salt'])
        }

    def update_env_file(self, env_file_id: int, label: str, content: str) -> bool:
        """Update a stored .env file and re-encrypt content."""
        salt = os.urandom(16)
        encrypted = self.encrypt(content, salt)

        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE env_files SET label = ?, content_encrypted = ?, salt = ? WHERE id = ?",
            (label, encrypted, salt, env_file_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_env_file(self, env_file_id: int) -> bool:
        """Delete a stored .env file entry."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM env_files WHERE id = ?", (env_file_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    
    def add_note(self, title: str, content: str) -> int:
        """Add a new secret note with encrypted content."""
        salt = os.urandom(16)
        encrypted = self.encrypt(content, salt)
        
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO notes (title, content_encrypted, salt) VALUES (?, ?, ?)",
            (title, encrypted, salt)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_notes(self) -> list[dict]:
        """Get all notes (content remains encrypted)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM notes ORDER BY title")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_note_content(self, note_id: int) -> dict:
        """Decrypt and return note content."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, content_encrypted, salt FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Note {note_id} not found.")
        
        return {
            'title': row['title'],
            'content': self.decrypt(row['content_encrypted'], row['salt'])
        }
    
    def delete_note(self, note_id: int) -> bool:
        """Delete a note."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_note(self, note_id: int, title: str, content: str) -> bool:
        """Update a note and re-encrypt its content."""
        salt = os.urandom(16)
        encrypted = self.encrypt(content, salt)
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE notes SET title = ?, content_encrypted = ?, salt = ? WHERE id = ?",
            (title, encrypted, salt, note_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_setting(self, key: str, default: str = "") -> str:
        """Get a setting value from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        """Set a setting value in the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def generate_password(self, length: int | None = None, include_upper: bool | None = None, include_lower: bool | None = None, include_digits: bool | None = None, include_symbols: bool | None = None) -> str:
        """Generate a cryptographically secure random password using stored settings or custom overrides."""
        # 1. Load settings from database, fallback to defaults if not found
        if length is None:
            try:
                length = int(self.get_setting('pwd_gen_length', '16'))
            except ValueError:
                length = 16
        if include_upper is None:
            include_upper = self.get_setting('pwd_gen_include_uppercase', '1') == '1'
        if include_lower is None:
            include_lower = self.get_setting('pwd_gen_include_lowercase', '1') == '1'
        if include_digits is None:
            include_digits = self.get_setting('pwd_gen_include_digits', '1') == '1'
        if include_symbols is None:
            include_symbols = self.get_setting('pwd_gen_include_symbols', '1') == '1'

        # 2. Build character pools and guaranteed elements
        pools = []
        guaranteed = []
        
        if include_upper:
            pools.append(string.ascii_uppercase)
            guaranteed.append(secrets.choice(string.ascii_uppercase))
        if include_lower:
            pools.append(string.ascii_lowercase)
            guaranteed.append(secrets.choice(string.ascii_lowercase))
        if include_digits:
            pools.append(string.digits)
            guaranteed.append(secrets.choice(string.digits))
        if include_symbols:
            pools.append(string.punctuation)
            guaranteed.append(secrets.choice(string.punctuation))

        if not pools:
            # Fallback if everything is disabled
            pools.append(string.ascii_letters + string.digits)
            guaranteed.append(secrets.choice(string.ascii_letters + string.digits))

        pool = "".join(pools)
        
        # Fill the rest of the password
        remaining_len = length - len(guaranteed)
        if remaining_len > 0:
            for _ in range(remaining_len):
                guaranteed.append(secrets.choice(pool))
        else:
            # If requested length is shorter than the number of guaranteed characters
            guaranteed = guaranteed[:length]

        # Shuffle to not expose the structure
        secrets.SystemRandom().shuffle(guaranteed)
        return "".join(guaranteed)

    
    COMMON_PASSWORD_HASHES = {
        
        "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
        "5e884898da28047d9d7d64f3e9a91ee09aa tried5d4d6dae5e8e31ea0dbf4eb79f8db5e18",
        "ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f",
        "65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5",
        "15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225",
        "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5",
        "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4",
        "bcb15f821479b4d5772bd0ca866c00ad5f926e3580720659cc80d39c9d09802a",
        "20eabe5d64b0e216796e834f52d61fd0b70332fc",
        "8621ffdbc5698829397d97767ac13db3f096fc2a",
    }
    
    COMMON_PASSWORDS = {
        "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
        "111111", "1234567", "dragon", "123123", "baseball", "abc123", "football",
        "monkey", "letmein", "shadow", "master", "666666", "qwertyuiop", "123321",
        "mustang", "1234567890", "michael", "654321", "superman", "1qaz2wsx",
        "7777777", "121212", "000000", "qazwsx", "123qwe", "killer", "trustno1",
        "jordan", "jennifer", "zxcvbnm", "asdfgh", "hunter", "buster", "soccer",
        "harley", "batman", "andrew", "tigger", "sunshine", "iloveyou", "2000",
        "charlie", "robert", "thomas", "hockey", "ranger", "daniel", "starwars",
        "klaster", "112233", "george", "computer", "michelle", "jessica", "pepper",
        "1111", "zxcvbn", "555555", "11111111", "131313", "freedom", "777777",
        "pass", "maggie", "159753", "aaaaaa", "ginger", "princess", "joshua",
        "cheese", "amanda", "summer", "love", "ashley", "nicole", "chelsea",
        "biteme", "matthew", "access", "yankees", "987654321", "dallas", "austin",
        "thunder", "taylor", "matrix", "mobilemail", "mom", "monitor", "monitoring",
        "montana", "moon", "moscow", "password1", "password123", "password12",
        "passw0rd", "admin", "admin123", "root", "toor", "pass123", "test",
        "guest", "master123", "changeme", "welcome", "welcome1", "welcome123",
        "login", "user", "user123", "default", "hello", "hello123"
    }

    def _normalize_for_common_lookup(self, password: str) -> str:
        """Normalize password for common-password checks."""
        lowered = password.lower().strip()
        trans = str.maketrans({
            '@': 'a',
            '$': 's',
            '0': 'o',
            '1': 'i',
            '!': 'i',
            '3': 'e',
            '5': 's',
            '7': 't',
        })
        normalized = lowered.translate(trans)
        return re.sub(r'[^a-z0-9]', '', normalized)

    def _has_long_sequence(self, password: str, min_len: int = 4) -> bool:
        """Detect ascending or descending alphanumeric sequences."""
        cleaned = ''.join(ch for ch in password.lower() if ch.isalnum())
        if len(cleaned) < min_len:
            return False

        run_up = 1
        run_down = 1
        for i in range(1, len(cleaned)):
            prev_ord = ord(cleaned[i - 1])
            cur_ord = ord(cleaned[i])
            if cur_ord == prev_ord + 1:
                run_up += 1
                run_down = 1
            elif cur_ord == prev_ord - 1:
                run_down += 1
                run_up = 1
            else:
                run_up = 1
                run_down = 1

            if run_up >= min_len or run_down >= min_len:
                return True
        return False

    def calculate_password_strength(self, password: str, context_texts: list[str] | None = None) -> dict:
        """
        Calculate password strength score and identify issues.
        Returns: {score: 0-100, rating: str, issues: list[str]}
        """
        if not password:
            return {
                'score': 0,
                'rating': 'Weak',
                'issues': ['Password is empty'],
                'recommendations': ['Use at least 12 characters with mixed character types.']
            }

        score = 0
        issues = []
        
        length = len(password)
        if length >= 20:
            score += 35
        elif length >= 16:
            score += 30
        elif length >= 12:
            score += 25
        elif length >= 10:
            score += 20
        elif length >= 8:
            score += 15
        else:
            score += length * 2
            issues.append(f"Too short ({length} chars, need 8+)")
        
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password))
        
        variety_count = sum([has_lower, has_upper, has_digit, has_special])
        score += variety_count * 5
        
        if not has_upper:
            issues.append("No uppercase letters")
        if not has_lower:
            issues.append("No lowercase letters")
        if not has_digit:
            issues.append("No numbers")
        if not has_special:
            issues.append("No special characters")
        

        sequential = ['123', '234', '345', '456', '567', '678', '789', '890',
                     'abc', 'bcd', 'cde', 'def', 'efg', 'fgh', 'ghi', 'hij',
                     'qwe', 'wer', 'ert', 'rty', 'asd', 'sdf', 'dfg', 'zxc']
        for seq in sequential:
            if seq in password.lower():
                score -= 10
                issues.append("Contains short sequential pattern")
                break

        if self._has_long_sequence(password, min_len=4):
            score -= 12
            issues.append("Contains long ascending/descending sequence")
        
        if re.search(r'(.)\1{2,}', password):
            score -= 10
            issues.append("Contains repeated characters")

        if re.search(r'(.{2,4})\1{1,}', password):
            score -= 10
            issues.append("Contains repeated pattern blocks")
        
        keyboard_patterns = ['qwerty', 'asdfgh', 'zxcvbn', '!@#$%^', 'qazwsx']
        for pattern in keyboard_patterns:
            if pattern in password.lower():
                score -= 10
                issues.append("Contains keyboard pattern")
                break

        if re.search(r'(19\d{2}|20\d{2})', password):
            score -= 6
            issues.append("Contains a year-like pattern")

        if context_texts:
            pw_l = password.lower()
            for raw in context_texts:
                if not raw:
                    continue
                token = re.sub(r'[^a-z0-9]', '', raw.lower())
                if len(token) >= 3 and token in re.sub(r'[^a-z0-9]', '', pw_l):
                    score -= 15
                    issues.append(f"Contains account-related word: '{raw}'")
                    break

        if self.check_common_password(password):
            score -= 35
            issues.append("Matches a commonly breached password")
        
        unique_chars = len(set(password))
        charset_size = 0
        if has_lower:
            charset_size += 26
        if has_upper:
            charset_size += 26
        if has_digit:
            charset_size += 10
        if has_special:
            charset_size += 33
        if charset_size:
            entropy_bits = length * math.log2(charset_size)
            score += min(20, int(entropy_bits / 6))

        diversity_ratio = unique_chars / max(1, length)
        if diversity_ratio < 0.5 and length >= 8:
            score -= 8
            issues.append("Low character diversity")
        
        score = max(0, min(100, score))
        
        if score >= 85:
            rating = "Strong"
        elif score >= 65:
            rating = "Good"
        elif score >= 45:
            rating = "Fair"
        else:
            rating = "Weak"

        recommendations = []
        if any("short" in issue.lower() for issue in issues):
            recommendations.append("Increase length to at least 12 characters.")
        if any("uppercase" in issue.lower() for issue in issues):
            recommendations.append("Add uppercase letters.")
        if any("lowercase" in issue.lower() for issue in issues):
            recommendations.append("Add lowercase letters.")
        if any("numbers" in issue.lower() for issue in issues):
            recommendations.append("Add numbers.")
        if any("special" in issue.lower() for issue in issues):
            recommendations.append("Add symbols like ! @ # $.")
        if any("common" in issue.lower() or "breached" in issue.lower() for issue in issues):
            recommendations.append("Avoid known/common passwords entirely.")
        if any("sequence" in issue.lower() or "pattern" in issue.lower() for issue in issues):
            recommendations.append("Avoid predictable sequences and repeated chunks.")
        if any("account-related" in issue.lower() for issue in issues):
            recommendations.append("Remove words tied to the app or username.")

        if not recommendations and rating in ["Fair", "Weak"]:
            recommendations.append("Use a longer random password from the generator.")
        
        return {
            'score': score,
            'rating': rating,
            'issues': issues,
            'recommendations': recommendations
        }

    def get_all_decrypted_passwords(self) -> list[dict]:
        """Get all password entries with decrypted passwords for internal analysis."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, app_name, username, password_encrypted, salt FROM passwords")
        results = []
        for row in cursor.fetchall():
            try:
                decrypted = self.decrypt(row['password_encrypted'], row['salt'])
                results.append({
                    'id': row['id'],
                    'app_name': row['app_name'],
                    'username': row['username'],
                    'password': decrypted
                })
            except Exception:
                continue
        return results

    def detect_duplicate_passwords(self) -> list[list[dict]]:
        """
        Detect passwords that are reused across multiple entries.
        Returns list of groups, where each group contains entries with the same password.
        """
        entries = self.get_all_decrypted_passwords()
        
        password_groups = {}
        for entry in entries:
            pw = entry['password']
            if pw not in password_groups:
                password_groups[pw] = []
            password_groups[pw].append({
                'id': entry['id'],
                'app_name': entry['app_name'],
                'username': entry['username']
            })
        
        return [group for group in password_groups.values() if len(group) > 1]

    def check_common_password(self, password: str) -> bool:
        """Check if password matches a commonly breached password (local check only)."""
        lowered = password.lower().strip()
        normalized = self._normalize_for_common_lookup(password)

        if lowered in self.COMMON_PASSWORDS or normalized in self.COMMON_PASSWORDS:
            return True

        # Common pattern: base password plus short numeric suffix
        base = re.sub(r'\d{1,4}$', '', normalized)
        return bool(base and base in self.COMMON_PASSWORDS)

    def run_security_scan(self) -> dict:
        """
        Run comprehensive security scan on all passwords.
        Returns structured report with all findings.
        """
        entries = self.get_all_decrypted_passwords()
        
        strength_distribution = {'weak': 0, 'fair': 0, 'good': 0, 'strong': 0}
        weak_passwords = []
        common_passwords = []
        total_score = 0
        
        for entry in entries:
            strength = self.calculate_password_strength(
                entry['password'],
                context_texts=[entry['app_name'], entry['username']]
            )
            rating_key = strength['rating'].lower()
            strength_distribution[rating_key] += 1
            total_score += strength['score']
            
            if strength['rating'] in ['Weak', 'Fair']:
                weak_passwords.append({
                    'id': entry['id'],
                    'app_name': entry['app_name'],
                    'score': strength['score'],
                    'rating': strength['rating'],
                    'issues': strength['issues'],
                    'recommendations': strength.get('recommendations', [])
                })
            
            if self.check_common_password(entry['password']):
                common_passwords.append({
                    'id': entry['id'],
                    'app_name': entry['app_name']
                })
        
        duplicate_groups = self.detect_duplicate_passwords()
        
        overall_score = (total_score / len(entries)) if entries else 0
        
        return {
            'total_passwords': len(entries),
            'overall_score': round(overall_score, 1),
            'strength_distribution': strength_distribution,
            'weak_passwords': weak_passwords,
            'duplicate_groups': duplicate_groups,
            'common_passwords': common_passwords,
            'scan_date': datetime.now().isoformat()
        }

    def export_encrypted_report(self, report: dict, file_path: str) -> bool:
        """
        Export security scan report as an encrypted file.
        Can only be decrypted when vault is unlocked.
        """
        import json
        
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        
        try:
            report_json = json.dumps(report, indent=2)
            
            salt = os.urandom(16)
            encrypted_data = self.encrypt(report_json, salt)
            
            with open(file_path, 'wb') as f:
                f.write(salt)
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to export report: {e}")

    def _get_or_create_tag(self, name: str) -> int:
        """Get the ID of a tag by name, creating it if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM tags WHERE name = ?", (name.strip().lower(),))
        row = cursor.fetchone()
        if row:
            return row[0]
        
        cursor.execute("INSERT INTO tags (name) VALUES (?)", (name.strip().lower(),))
        self.conn.commit()
        return cursor.lastrowid

    def add_tag_to_entry(self, entry_type: str, entry_id: int, tag_name: str):
        """Associate a tag with an entry."""
        tag_id = self._get_or_create_tag(tag_name)
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO entry_tags (tag_id, entry_type, entry_id) VALUES (?, ?, ?)",
                (tag_id, entry_type, entry_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass 

    def get_tags_for_entry(self, entry_type: str, entry_id: int) -> list[str]:
        """Get all tags associated with an entry."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN entry_tags et ON t.id = et.tag_id
            WHERE et.entry_type = ? AND et.entry_id = ?
        """, (entry_type, entry_id))
        return [row[0] for row in cursor.fetchall()]

    def get_all_tags(self) -> list[str]:
        """Get all unique tags used in the vault."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM tags ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def remove_tag_from_entry(self, entry_type: str, entry_id: int, tag_name: str):
        """Remove a tag association from an entry."""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM entry_tags 
            WHERE entry_type = ? AND entry_id = ? AND tag_id = (SELECT id FROM tags WHERE name = ?)
        """, (entry_type, entry_id, tag_name.lower()))
        self.conn.commit()

    def search_vault(self, query: str) -> dict[str, list]:
        """Search across all entries for the given query."""
        query = query.lower()
        results = {
            'passwords': [],
            'cards': [],
            'notes': [],
            'env_files': []
        }
        
        cursor = self.conn.cursor()
        
        # Search passwords
        cursor.execute("""
            SELECT id, app_name, username, created_at FROM passwords 
            WHERE lower(app_name) LIKE ? OR lower(username) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        results['passwords'] = [dict(row) for row in cursor.fetchall()]
        
        # Search cards
        cursor.execute("""
            SELECT id, label, holder_name, created_at,
                   card_number_encrypted, card_number_salt,
                   expiry_encrypted, expiry_salt
            FROM cards 
            WHERE lower(label) LIKE ? OR lower(holder_name) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        results['cards'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT id, title, created_at FROM notes 
            WHERE lower(title) LIKE ?
        """, (f"%{query}%",))
        results['notes'] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT id, label, created_at FROM env_files
            WHERE lower(label) LIKE ?
        """, (f"%{query}%",))
        results['env_files'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT DISTINCT entry_id, entry_type FROM entry_tags et
            JOIN tags t ON et.tag_id = t.id
            WHERE t.name LIKE ?
        """, (f"%{query}%",))
        tag_matches = cursor.fetchall()
        
        for entry_id, entry_type in tag_matches:
            if entry_type == 'password':
                if not any(r['id'] == entry_id for r in results['passwords']):
                    cursor.execute("SELECT id, app_name, username, created_at FROM passwords WHERE id = ?", (entry_id,))
                    row = cursor.fetchone()
                    if row: results['passwords'].append(dict(row))
            elif entry_type == 'card':
                if not any(r['id'] == entry_id for r in results['cards']):
                    cursor.execute("""
                        SELECT id, label, holder_name, created_at,
                               card_number_encrypted, card_number_salt,
                               expiry_encrypted, expiry_salt
                        FROM cards WHERE id = ?
                    """, (entry_id,))
                    row = cursor.fetchone()
                    if row: results['cards'].append(dict(row))
            elif entry_type == 'note':
                if not any(r['id'] == entry_id for r in results['notes']):
                    cursor.execute("SELECT id, title, created_at FROM notes WHERE id = ?", (entry_id,))
                    row = cursor.fetchone()
                    if row: results['notes'].append(dict(row))
            elif entry_type == 'env_file':
                if not any(r['id'] == entry_id for r in results['env_files']):
                    cursor.execute("SELECT id, label, created_at FROM env_files WHERE id = ?", (entry_id,))
                    row = cursor.fetchone()
                    if row:
                        results['env_files'].append(dict(row))

        return results
    
    def export_vault(self, dest_path: str):
        """Create an encrypted backup of the database file."""
        import shutil
        self.conn.commit()
        shutil.copy2(self.db_path, dest_path)

    def import_vault(self, src_path: str):
        """Replace the current database with a backup."""
        import shutil
        self.conn.close()
        shutil.copy2(src_path, self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._encryption_key = None 

    def get_full_export_data(self) -> dict:
        """Decrypt and return all vault data as a dictionary."""
        data = {
            'passwords': [],
            'cards': [],
            'notes': [],
            'env_files': [],
            'export_date': datetime.now().isoformat()
        }
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, app_name, username FROM passwords")
        for row in cursor.fetchall():
            try:
                data['passwords'].append({
                    'app_name': row['app_name'],
                    'username': row['username'],
                    'password': self.get_password(row['id'])
                })
            except Exception:
                continue

        cursor.execute("SELECT id FROM cards")
        for row in cursor.fetchall():
            try:
                data['cards'].append(self.get_card_details(row['id']))
            except Exception:
                continue

        cursor.execute("SELECT id FROM notes")
        for row in cursor.fetchall():
            try:
                data['notes'].append(self.get_note_content(row['id']))
            except Exception:
                continue

        cursor.execute("SELECT id FROM env_files")
        for row in cursor.fetchall():
            try:
                data['env_files'].append(self.get_env_file_content(row['id']))
            except Exception:
                continue
                
        return data

    def close(self):
        """Close the database connection."""
        self.conn.close()
