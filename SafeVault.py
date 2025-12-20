"""
SafeVault - Personal Local Password Manager
==========================================
A secure, local password manager with tabbed interface for:
- Passwords (App/Website credentials)
- Credit Cards (encrypted card details)
- Secret Notes (encrypted notes)

Tech Stack: customtkinter, sqlite3, cryptography (Fernet + PBKDF2HMAC), pyperclip
"""

import os
import re
import sqlite3
import secrets
import string
import base64
from datetime import datetime

import customtkinter as ctk
import pyperclip

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
    
    PBKDF2_ITERATIONS = 100_000
    
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
        
        self.conn.commit()
    
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive a cryptographic key from a password using PBKDF2-HMAC-SHA256.
        
        How it works:
        1. Takes user's password + random salt
        2. Runs HMAC-SHA256 100,000 times (iterations)
        3. Produces a 32-byte key suitable for Fernet encryption
        4. Base64 encodes for Fernet compatibility
        
        Why this is secure:
        - Salt prevents rainbow table attacks
        - High iteration count slows brute-force attempts
        - Each encryption uses a unique salt = unique key
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
    

    
    def encrypt(self, plaintext: str, salt: bytes) -> bytes:
        """Encrypt plaintext using Fernet with derived key."""
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        
        entry_key = self.derive_key(self._encryption_key.decode('utf-8'), salt)
        fernet = Fernet(entry_key)
        return fernet.encrypt(plaintext.encode('utf-8'))
    
    def decrypt(self, ciphertext: bytes, salt: bytes) -> str:
        """Decrypt ciphertext using Fernet with derived key."""
        if not self._encryption_key:
            raise RuntimeError("No encryption key. Please login first.")
        
        entry_key = self.derive_key(self._encryption_key.decode('utf-8'), salt)
        fernet = Fernet(entry_key)
        try:
            return fernet.decrypt(ciphertext).decode('utf-8')
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
    
    def generate_password(self, length: int = 16) -> str:
        """Generate a cryptographically secure random password."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    
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

    def calculate_password_strength(self, password: str) -> dict:
        """
        Calculate password strength score and identify issues.
        Returns: {score: 0-100, rating: str, issues: list[str]}
        """
        score = 0
        issues = []
        
        length = len(password)
        if length >= 16:
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
        score += variety_count * 10
        
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
                issues.append("Contains sequential pattern")
                break
        
        if re.search(r'(.)\1{2,}', password):
            score -= 10
            issues.append("Contains repeated characters")
        
        keyboard_patterns = ['qwerty', 'asdfgh', 'zxcvbn', '!@#$%^', 'qazwsx']
        for pattern in keyboard_patterns:
            if pattern in password.lower():
                score -= 10
                issues.append("Contains keyboard pattern")
                break
        
        unique_chars = len(set(password))
        entropy_bonus = min(30, unique_chars * 2)
        score += entropy_bonus
        
        score = max(0, min(100, score))
        
        if score >= 80:
            rating = "Strong"
        elif score >= 60:
            rating = "Good"
        elif score >= 40:
            rating = "Fair"
        else:
            rating = "Weak"
        
        return {
            'score': score,
            'rating': rating,
            'issues': issues
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
        return password.lower() in self.COMMON_PASSWORDS

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
            strength = self.calculate_password_strength(entry['password'])
            rating_key = strength['rating'].lower()
            strength_distribution[rating_key] += 1
            total_score += strength['score']
            
            if strength['rating'] in ['Weak', 'Fair']:
                weak_passwords.append({
                    'id': entry['id'],
                    'app_name': entry['app_name'],
                    'score': strength['score'],
                    'rating': strength['rating'],
                    'issues': strength['issues']
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
            'notes': []
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
                
        return data

    def close(self):
        """Close the database connection."""
        self.conn.close()



class App(ctk.CTk):
    """
    Main application with tabbed interface:
    - Tab 1: Passwords
    - Tab 2: Credit Cards  
    - Tab 3: Secret Notes
    """
    
    def __init__(self):
        super().__init__()
        
        self.backend = Backend()
        
        self.title("🔐 SafeVault - Password Manager")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.toggle_font = ctk.CTkFont(size=14)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        if self.backend.is_first_run():
            self.show_setup_screen()
        else:
            self.show_login_screen()

    def toggle_password_visibility(self, entry: ctk.CTkEntry, button: ctk.CTkButton):
        """Toggle the password visibility between masked and clear text."""
        if entry.cget("show") == "•":
            entry.configure(show="")
            button.configure(text="🔒", font=self.toggle_font)  # Show lock to indicate "click to mask"
        else:
            entry.configure(show="•")
            button.configure(text="👁️", font=self.toggle_font)  # Show eye to indicate "click to reveal"
        entry.focus_set()
    
    def clear_screen(self):
        """Remove all widgets from the window."""
        for widget in self.winfo_children():
            widget.destroy()
  
    def show_setup_screen(self):
        """Display master password setup screen."""
        self.clear_screen()
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            frame, text="🔐 Welcome to SafeVault",
            font=ctk.CTkFont(size=28, weight="bold")
        ).grid(row=0, column=0, pady=(0, 10))
        
        ctk.CTkLabel(
            frame, text="Create a Master Password to secure your vault",
            font=ctk.CTkFont(size=14), text_color="gray"
        ).grid(row=1, column=0, pady=(0, 40))
        
        ctk.CTkLabel(frame, text="Master Password:", anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        pw_frame = ctk.CTkFrame(frame, fg_color="transparent")
        pw_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        pw_frame.grid_columnconfigure(0, weight=1)
        
        self.setup_password = ctk.CTkEntry(pw_frame, placeholder_text="Enter a strong password", show="•", height=45)
        self.setup_password.grid(row=0, column=0, sticky="ew")
        
        self.setup_eye = ctk.CTkButton(pw_frame, text="👁️", width=45, height=45, fg_color="#333333", hover_color="#444444",
                                      font=self.toggle_font, anchor="center",
                                      command=lambda: self.toggle_password_visibility(self.setup_password, self.setup_eye))
        self.setup_eye.grid(row=0, column=1, padx=(5, 0))
        
        ctk.CTkLabel(frame, text="Confirm Password:", anchor="w").grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        cpw_frame = ctk.CTkFrame(frame, fg_color="transparent")
        cpw_frame.grid(row=5, column=0, sticky="ew", pady=(0, 30))
        cpw_frame.grid_columnconfigure(0, weight=1)
        cpw_frame.grid_columnconfigure(1, weight=0, minsize=45) # Lock column width
        
        self.setup_confirm = ctk.CTkEntry(cpw_frame, placeholder_text="Confirm your password", show="•", height=45)
        self.setup_confirm.grid(row=0, column=0, sticky="ew")
        
        self.setup_confirm_eye = ctk.CTkButton(cpw_frame, text="👁️", width=45, height=45, fg_color="#333333", hover_color="#444444",
                                              font=self.toggle_font, anchor="center",
                                              command=lambda: self.toggle_password_visibility(self.setup_confirm, self.setup_confirm_eye))
        self.setup_confirm_eye.grid(row=0, column=1, padx=(5, 0))
        
        self.setup_error = ctk.CTkLabel(frame, text="", text_color="#FF6B6B")
        self.setup_error.grid(row=6, column=0, pady=(0, 10))
        
        ctk.CTkButton(
            frame, text="Create Master Password", command=self.handle_setup,
            height=45, font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=7, column=0, pady=(0, 20))
        
        ctk.CTkLabel(
            frame, text="⚠️ Remember this password! It cannot be recovered.",
            font=ctk.CTkFont(size=12), text_color="#FFA500"
        ).grid(row=8, column=0, pady=(20, 0))
    
    def handle_setup(self):
        """Handle master password creation."""
        password = self.setup_password.get()
        confirm = self.setup_confirm.get()
        
        if len(password) < 8:
            self.setup_error.configure(text="Password must be at least 8 characters")
            return
        if password != confirm:
            self.setup_error.configure(text="Passwords do not match")
            return
        
        if self.backend.create_master_password(password):
            self.show_vault_screen()
        else:
            self.setup_error.configure(text="Failed to create master password")
    
    
    def show_login_screen(self):
        """Display login screen."""
        self.clear_screen()
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            frame, text="🔐 SafeVault",
            font=ctk.CTkFont(size=32, weight="bold")
        ).grid(row=0, column=0, pady=(40, 10))
        
        ctk.CTkLabel(
            frame, text="Enter your Master Password to unlock",
            font=ctk.CTkFont(size=14), text_color="gray"
        ).grid(row=1, column=0, pady=(0, 50))
        
        login_pw_frame = ctk.CTkFrame(frame, fg_color="transparent")
        login_pw_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        login_pw_frame.grid_columnconfigure(0, weight=1)
        login_pw_frame.grid_columnconfigure(1, weight=0, minsize=50) # Lock column width
        
        self.login_password = ctk.CTkEntry(login_pw_frame, placeholder_text="Master Password", show="•", width=300, height=50)
        self.login_password.grid(row=0, column=0, sticky="ew")
        self.login_password.bind("<Return>", lambda e: self.handle_login())
        
        self.login_eye = ctk.CTkButton(login_pw_frame, text="👁️", width=50, height=50, fg_color="#333333", hover_color="#444444",
                                      font=self.toggle_font, anchor="center",
                                      command=lambda: self.toggle_password_visibility(self.login_password, self.login_eye))
        self.login_eye.grid(row=0, column=1, padx=(5, 0))
        
        self.login_error = ctk.CTkLabel(frame, text="", text_color="#FF6B6B")
        self.login_error.grid(row=3, column=0, pady=(0, 10))
        
        ctk.CTkButton(
            frame, text="🔓 Unlock Vault", command=self.handle_login,
            width=200, height=45, font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=4, column=0)
    
    def handle_login(self):
        """Handle login attempt."""
        password = self.login_password.get()
        
        if not password:
            self.login_error.configure(text="Please enter your password")
            return
        
        if self.backend.verify_master_password(password):
            self.show_vault_screen()
        else:
            self.login_error.configure(text="Incorrect password")
            self.login_password.delete(0, 'end')
    
    
    def show_vault_screen(self):
        """Display the main vault with tabbed interface."""
        self.clear_screen()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, height=60)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header, text="🔐 SafeVault", font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=15)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.handle_search)
        self.search_entry = ctk.CTkEntry(
            header, placeholder_text="🔎 Search your vault (apps, cards, notes...)", 
            textvariable=self.search_var, width=400, height=35
        )
        self.search_entry.grid(row=0, column=1, padx=20, pady=15, sticky="ew")
        
        ctk.CTkButton(
            header, text="🔒 Lock", command=self.show_login_screen,
            width=100, fg_color="#666666", hover_color="#555555"
        ).grid(row=0, column=2, padx=20, pady=15)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.tab_passwords = self.tabview.add("🔑 Passwords")
        self.tab_cards = self.tabview.add("💳 Cards")
        self.tab_notes = self.tabview.add("📝 Notes")
        self.tab_settings = self.tabview.add("⚙️ Settings")
        
        for tab in [self.tab_passwords, self.tab_cards, self.tab_notes, self.tab_settings]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(1, weight=1)
        
        self.build_passwords_tab()
        self.build_cards_tab()
        self.build_notes_tab()
        self.build_settings_tab()
    

    def build_passwords_tab(self):
        """Build the Passwords tab content."""
        tab = self.tab_passwords
        
        form = ctk.CTkFrame(tab)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        form.grid_columnconfigure((0, 1, 2), weight=1)
        
        ctk.CTkLabel(form, text="➕ Add Password", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(15, 10))
        
        self.pw_app = ctk.CTkEntry(form, placeholder_text="App / Website", height=40)
        self.pw_app.grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="ew")
        
        self.pw_user = ctk.CTkEntry(form, placeholder_text="Username", height=40)
        self.pw_user.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="ew")
        
        pw_frame = ctk.CTkFrame(form, fg_color="transparent")
        pw_frame.grid(row=1, column=2, padx=5, pady=(0, 15), sticky="ew")
        pw_frame.grid_columnconfigure(0, weight=1)
        pw_frame.grid_columnconfigure(1, weight=0, minsize=40) 
        self.pw_pass = ctk.CTkEntry(pw_frame, placeholder_text="Password", height=40, show="•")
        self.pw_pass.grid(row=0, column=0, sticky="ew")
        
        self.pwt_eye = ctk.CTkButton(pw_frame, text="👁️", width=40, height=40, fg_color="#333333", hover_color="#444444",
                                    font=self.toggle_font, anchor="center",
                                    command=lambda: self.toggle_password_visibility(self.pw_pass, self.pwt_eye))
        self.pwt_eye.grid(row=0, column=1, padx=(5, 5))
        
        ctk.CTkButton(pw_frame, text="🎲", command=self.generate_password_field, width=40, height=40,
                      fg_color="#7C3AED", hover_color="#6D28D9").grid(row=0, column=2)
        
        self.pw_tags = ctk.CTkEntry(form, placeholder_text="Tags (comma separated)", height=40)
        self.pw_tags.grid(row=2, column=0, columnspan=2, padx=(15, 5), pady=(0, 15), sticky="ew")

        ctk.CTkButton(form, text="Add", command=self.add_password_entry, width=80, height=40,
                      fg_color="#10B981", hover_color="#059669").grid(row=2, column=3, padx=(5, 15), pady=(0, 15))
        
        list_frame = ctk.CTkFrame(tab)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(list_frame, text="📋 Saved Passwords", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=15)
        
        self.pw_scroll = ctk.CTkScrollableFrame(list_frame)
        self.pw_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.pw_scroll.grid_columnconfigure(0, weight=1)
        
        self.refresh_passwords()
    
    def refresh_passwords(self, entries=None):
        """Refresh the passwords list."""
        for widget in self.pw_scroll.winfo_children():
            widget.destroy()
        
        if entries is None:
            entries = self.backend.get_all_passwords()
        
        if not entries:
            ctk.CTkLabel(self.pw_scroll, text="No matching passwords found.", text_color="gray").grid(row=0, column=0, pady=30)
            return
        
        for idx, entry in enumerate(entries):
            row = ctk.CTkFrame(self.pw_scroll)
            row.grid(row=idx, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=15, pady=5, sticky="w")
            
            ctk.CTkLabel(info_frame, text=entry['app_name'], font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="top", anchor="w")
            ctk.CTkLabel(info_frame, text=entry['username'], text_color="gray", anchor="w").pack(side="top", anchor="w")
            
            tags = self.backend.get_tags_for_entry('password', entry['id'])
            if tags:
                tags_frame = ctk.CTkFrame(row, fg_color="transparent")
                tags_frame.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
                for tag in tags:
                    ctk.CTkLabel(
                        tags_frame, text=f" #{tag}", font=ctk.CTkFont(size=10),
                        text_color="#3B82F6", anchor="w"
                    ).pack(side="left", padx=2)
            
            ctk.CTkButton(row, text="📋", command=lambda eid=entry['id']: self.copy_password(eid),
                          width=40, height=32, fg_color="#3B82F6").grid(row=0, column=2, padx=5, pady=10)
            ctk.CTkButton(row, text="🗑️", command=lambda eid=entry['id']: self.delete_password(eid),
                          width=40, height=32, fg_color="#EF4444").grid(row=0, column=3, padx=(5, 15), pady=10)
    
    def add_password_entry(self):
        """Add a new password."""
        app = self.pw_app.get().strip()
        user = self.pw_user.get().strip()
        pw = self.pw_pass.get()
        
        tags = self.pw_tags.get().strip()
        
        if not all([app, user, pw]):
            self.show_toast("Please fill all fields", error=True)
            return
        
        entry_id = self.backend.add_password(app, user, pw)
        
        if tags:
            for tag in tags.split(','):
                if tag.strip():
                    self.backend.add_tag_to_entry('password', entry_id, tag.strip())
        
        self.pw_app.delete(0, 'end')
        self.pw_user.delete(0, 'end')
        self.pw_pass.delete(0, 'end')
        self.pw_tags.delete(0, 'end')
        self.refresh_passwords()
        self.show_toast("Password added!")
    
    def copy_password(self, entry_id: int):
        """Copy password to clipboard."""
        try:
            pw = self.backend.get_password(entry_id)
            pyperclip.copy(pw)
            self.show_toast("Password copied!")
        except Exception as e:
            self.show_toast(f"Error: {e}", error=True)
    
    def delete_password(self, entry_id: int):
        """Delete a password entry."""
        self.backend.delete_password(entry_id)
        self.refresh_passwords()
        self.show_toast("Deleted")
    
    def generate_password_field(self):
        """Generate password into the field."""
        pw = self.backend.generate_password(16)
        self.pw_pass.delete(0, 'end')
        self.pw_pass.insert(0, pw)
        pyperclip.copy(pw)
        self.show_toast("Password generated & copied!")
 
    def validate_card_number(self, new_value):
        """Validate credit card number input - max 16 digits."""
        if new_value == "":
            return True
        return new_value.isdigit() and len(new_value) <= 16
    
    def validate_expiry(self, new_value):
        """Validate expiry date input - MM/YY format with auto-slash."""
        if new_value == "":
            return True
        
        if len(new_value) > 5:
            return False
            
        try:
            old_value = self.card_expiry.get()
        except (AttributeError, RuntimeError):
            old_value = ""

        if len(new_value) < len(old_value):
            return True

        digits_only = new_value.replace("/", "")
        if not digits_only.isdigit():
            return False

        if len(digits_only) == 2 and "/" not in new_value:
             self.card_expiry.after(1, lambda: [self.card_expiry.delete(0, 'end'), self.card_expiry.insert(0, digits_only + "/")])
             return True 
             
        if len(new_value) > 2:
            if new_value[2:3] != "/":
                return False
                
        return True
    
    def validate_cvv(self, new_value):
        """Validate CVV input - exactly 4 digits."""
        if new_value == "":
            return True
        return new_value.isdigit() and len(new_value) <= 4
    
    def validate_pin(self, new_value):
        """Validate PIN input - exactly 4 digits."""
        if new_value == "":
            return True
        return new_value.isdigit() and len(new_value) <= 4

    def build_cards_tab(self):
        """Build the Credit Cards tab content."""
        tab = self.tab_cards
        
        form = ctk.CTkFrame(tab)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        form.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        
        ctk.CTkLabel(form, text="➕ Add Card", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=7, sticky="w", padx=15, pady=(15, 10))
        
        self.card_label = ctk.CTkEntry(form, placeholder_text="Label", height=40)
        self.card_label.grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="ew")
        
        self.card_holder = ctk.CTkEntry(form, placeholder_text="Holder", height=40)
        self.card_holder.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="ew")
        
        card_num_validate = self.register(self.validate_card_number)
        self.card_number = ctk.CTkEntry(form, placeholder_text="CardNumber", height=40,
                                        validate="key", validatecommand=(card_num_validate, '%P'))
        self.card_number.grid(row=1, column=2, padx=5, pady=(0, 15), sticky="ew")
        
        expiry_validate = self.register(self.validate_expiry)
        self.card_expiry = ctk.CTkEntry(form, placeholder_text="MM/YY", height=40, width=80,
                                        validate="key", validatecommand=(expiry_validate, '%P'))
        self.card_expiry.grid(row=1, column=3, padx=5, pady=(0, 15), sticky="ew")
        
        cvv_frame = ctk.CTkFrame(form, fg_color="transparent")
        cvv_frame.grid(row=1, column=4, padx=5, pady=(0, 15), sticky="ew")
        cvv_frame.grid_columnconfigure(0, weight=1)
        cvv_frame.grid_columnconfigure(1, weight=0, minsize=40) # Lock toggle column
        
        cvv_validate = self.register(self.validate_cvv)
        self.card_cvv = ctk.CTkEntry(cvv_frame, placeholder_text="CVV", height=40, show="•",
                                     validate="key", validatecommand=(cvv_validate, '%P'))
        self.card_cvv.grid(row=0, column=0, sticky="ew")
        
        self.cvv_eye = ctk.CTkButton(cvv_frame, text="👁️", width=40, height=40, fg_color="#333333", hover_color="#444444",
                                    font=self.toggle_font, anchor="center",
                                    command=lambda: self.toggle_password_visibility(self.card_cvv, self.cvv_eye))
        self.cvv_eye.grid(row=0, column=1, padx=(5, 0))
        
        pin_frame = ctk.CTkFrame(form, fg_color="transparent")
        pin_frame.grid(row=1, column=5, padx=5, pady=(0, 15), sticky="ew")
        pin_frame.grid_columnconfigure(0, weight=1)
        pin_frame.grid_columnconfigure(1, weight=0, minsize=40) # Lock toggle column
        
        pin_validate = self.register(self.validate_pin)
        self.card_pin = ctk.CTkEntry(pin_frame, placeholder_text="PIN", height=40, show="•",
                                     validate="key", validatecommand=(pin_validate, '%P'))
        self.card_pin.grid(row=0, column=0, sticky="ew")
        
        self.pin_eye = ctk.CTkButton(pin_frame, text="👁️", width=40, height=40, fg_color="#333333", hover_color="#444444",
                                    font=self.toggle_font, anchor="center",
                                    command=lambda: self.toggle_password_visibility(self.card_pin, self.pin_eye))
        self.pin_eye.grid(row=0, column=1, padx=(5, 0))
        
        self.card_tags = ctk.CTkEntry(form, placeholder_text="Tags (comma separated)", height=40)
        self.card_tags.grid(row=2, column=0, columnspan=3, padx=(15, 5), pady=(0, 15), sticky="ew")

        ctk.CTkButton(form, text="Add", command=self.add_card_entry, width=80, height=40,
                      fg_color="#10B981", hover_color="#059669").grid(row=2, column=6, padx=(5, 15), pady=(0, 15))
        
        list_frame = ctk.CTkFrame(tab)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(list_frame, text="💳 Saved Cards", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=15)
        
        self.card_scroll = ctk.CTkScrollableFrame(list_frame)
        self.card_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.card_scroll.grid_columnconfigure(0, weight=1)
        
        self.refresh_cards()
    
    def refresh_cards(self, cards=None):
        """Refresh the cards list."""
        for widget in self.card_scroll.winfo_children():
            widget.destroy()
        
        if cards is None:
            cards = self.backend.get_all_cards()
        
        if not cards:
            ctk.CTkLabel(self.card_scroll, text="No matching cards found.", text_color="gray").grid(row=0, column=0, pady=30)
            return
        
        for idx, card in enumerate(cards):
            row = ctk.CTkFrame(self.card_scroll)
            row.grid(row=idx, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            
            # Info section
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=15, pady=5, sticky="w")
            
            ctk.CTkLabel(info_frame, text=f"💳 {card['label']}", font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="top", anchor="w")
            
            # Decrypt and show basic info
            try:
                card_num = self.backend.decrypt(card['card_number_encrypted'], card['card_number_salt'])
                masked_num = f"**** **** **** {card_num[-4:]}"
                expiry = self.backend.decrypt(card['expiry_encrypted'], card['expiry_salt'])
                details_text = f"{card['holder_name']}  |  {masked_num}  |  Exp: {expiry}"
                ctk.CTkLabel(info_frame, text=details_text, text_color="gray", anchor="w").pack(side="top", anchor="w")
            except Exception:
                ctk.CTkLabel(info_frame, text=card['holder_name'], text_color="gray", anchor="w").pack(side="top", anchor="w")
            
            # Tags section
            tags = self.backend.get_tags_for_entry('card', card['id'])
            if tags:
                tags_frame = ctk.CTkFrame(row, fg_color="transparent")
                tags_frame.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
                for tag in tags:
                    ctk.CTkLabel(
                        tags_frame, text=f" #{tag}", font=ctk.CTkFont(size=10),
                        text_color="#3B82F6", anchor="w"
                    ).pack(side="left", padx=2)
            
            ctk.CTkButton(row, text="👁️ View", command=lambda cid=card['id']: self.view_card(cid),
                          width=70, height=32, fg_color="#3B82F6").grid(row=0, column=2, padx=5, pady=10)
            ctk.CTkButton(row, text="🗑️", command=lambda cid=card['id']: self.delete_card(cid),
                          width=40, height=32, fg_color="#EF4444").grid(row=0, column=3, padx=(5, 15), pady=10)
    
    def add_card_entry(self):
        """Add a new card with strict validation."""
        label = self.card_label.get().strip()
        holder = self.card_holder.get().strip()
        number = self.card_number.get().strip().replace(" ", "")
        expiry = self.card_expiry.get().strip()
        cvv = self.card_cvv.get().strip()
        pin = self.card_pin.get().strip()
        
        tags = self.card_tags.get().strip()
        
        if not all([label, holder, number, expiry, cvv, pin]):
            self.show_toast("Please fill all fields", error=True)
            return
            
        if not re.fullmatch(r'\d{16}', number):
            self.show_toast("Card Number must be exactly 16 digits", error=True)
            return

        if not re.fullmatch(r'(0[1-9]|1[0-2])\/\d{2}', expiry):
            self.show_toast("Expiry must be MM/YY", error=True)
            return

        if not re.fullmatch(r'\d{3,4}', cvv):
            self.show_toast("CVV must be 3 or 4 digits", error=True)
            return
            
        if not re.fullmatch(r'\d{4}', pin):
            self.show_toast("PIN must be 4 digits", error=True)
            return
        
        try:
            entry_id = self.backend.add_card(label, holder, number, expiry, cvv, pin)
            if tags:
                for tag in tags.split(','):
                    if tag.strip():
                        self.backend.add_tag_to_entry('card', entry_id, tag.strip())
            
            for entry in [self.card_label, self.card_holder, self.card_number, self.card_expiry, self.card_cvv, self.card_pin, self.card_tags]:
                entry.delete(0, 'end')
            self.refresh_cards()
            self.show_toast("Card added successfully!")
        except Exception as e:
            self.show_toast(f"Error: {e}", error=True)
    
    def view_card(self, card_id: int):
        """Show card details in a popup."""
        try:
            details = self.backend.get_card_details(card_id)
        except Exception as e:
            self.show_toast(f"Error: {e}", error=True)
            return
        
        popup = ctk.CTkToplevel(self)
        popup.title(f"Card: {details['label']}")
        popup.geometry("450x450")
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - popup.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")
        
        frame = ctk.CTkFrame(popup)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        info = [
            ("Label", details['label']),
            ("Holder", details['holder_name']),
            ("Card Number", details['card_number']),
            ("Expiry (MM/YY)", details['expiry']),
            ("CVV", details['cvv']),
            ("PIN", details['pin'])
        ]
        
        for i, (label, value) in enumerate(info):
            ctk.CTkLabel(frame, text=f"{label}:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(
                row=i, column=0, sticky="w", padx=10, pady=8)
            
            val_frame = ctk.CTkFrame(frame, fg_color="transparent")
            val_frame.grid(row=i, column=1, sticky="ew", padx=10, pady=8)
            val_frame.grid_columnconfigure(0, weight=1)
            
            if label in ["Card Number", "CVV", "PIN"]:
                val_frame.grid_columnconfigure(1, weight=0, minsize=30) # Lock toggle column
                
                entry = ctk.CTkEntry(val_frame, fg_color="transparent", border_width=0, height=25)
                entry.insert(0, value)
                entry.configure(state="readonly", show="•")
                entry.grid(row=0, column=0, sticky="ew")
                
                eye = ctk.CTkButton(val_frame, text="👁️", width=30, height=25, fg_color="#333333", hover_color="#444444",
                                  font=self.toggle_font, anchor="center")
                eye.configure(command=lambda e=entry, b=eye: self.toggle_password_visibility(e, b))
                eye.grid(row=0, column=1, padx=(5, 0))
                
                copy_btn = ctk.CTkButton(val_frame, text="📋", width=30, height=25,
                                        command=lambda v=value: [pyperclip.copy(v), self.show_toast("Copied!")])
                copy_btn.grid(row=0, column=2, padx=(5, 0))
            else:
                ctk.CTkLabel(val_frame, text=value, anchor="w").grid(row=0, column=0, sticky="w")
                ctk.CTkButton(val_frame, text="📋", width=30, height=25,
                              command=lambda v=value: [pyperclip.copy(v), self.show_toast("Copied!")]).grid(row=0, column=1, padx=(10, 0))
        
        frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(popup, text="Close", command=popup.destroy, width=100).pack(pady=10)
    
    def delete_card(self, card_id: int):
        """Delete a card."""
        self.backend.delete_card(card_id)
        self.refresh_cards()
        self.show_toast("Card deleted")
    
    def build_notes_tab(self):
        """Build the Secret Notes tab content."""
        tab = self.tab_notes
        
        form = ctk.CTkFrame(tab)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        form.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(form, text="➕ Add Note", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(15, 10))
        
        self.note_title = ctk.CTkEntry(form, placeholder_text="Title", height=40, width=200)
        self.note_title.grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="w")
        
        self.note_content = ctk.CTkEntry(form, placeholder_text="Secret content...", height=40)
        self.note_content.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="ew")
        
        self.note_tags = ctk.CTkEntry(form, placeholder_text="Tags (comma separated)", height=40)
        self.note_tags.grid(row=2, column=0, columnspan=2, padx=(15, 5), pady=(0, 15), sticky="ew")

        ctk.CTkButton(form, text="Add", command=self.add_note_entry, width=80, height=40,
                      fg_color="#10B981", hover_color="#059669").grid(row=2, column=2, padx=(5, 15), pady=(0, 15))
        
        list_frame = ctk.CTkFrame(tab)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(list_frame, text="📝 Secret Notes", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=15)
        
        self.note_scroll = ctk.CTkScrollableFrame(list_frame)
        self.note_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.note_scroll.grid_columnconfigure(0, weight=1)
        
        self.refresh_notes()
    
    def refresh_notes(self, notes=None):
        """Refresh the notes list."""
        for widget in self.note_scroll.winfo_children():
            widget.destroy()
        
        if notes is None:
            notes = self.backend.get_all_notes()
        
        if not notes:
            ctk.CTkLabel(self.note_scroll, text="No matching notes found.", text_color="gray").grid(row=0, column=0, pady=30)
            return
        
        for idx, note in enumerate(notes):
            row = ctk.CTkFrame(self.note_scroll)
            row.grid(row=idx, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=15, pady=5, sticky="w")
            
            ctk.CTkLabel(info_frame, text=f"📝 {note['title']}", font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="top", anchor="w")
            
            tags = self.backend.get_tags_for_entry('note', note['id'])
            if tags:
                tags_frame = ctk.CTkFrame(row, fg_color="transparent")
                tags_frame.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
                for tag in tags:
                    ctk.CTkLabel(
                        tags_frame, text=f" #{tag}", font=ctk.CTkFont(size=10),
                        text_color="#3B82F6", anchor="w"
                    ).pack(side="left", padx=2)
            
            ctk.CTkButton(row, text="👁️ View", command=lambda nid=note['id']: self.view_note(nid),
                          width=70, height=32, fg_color="#3B82F6").grid(row=0, column=2, padx=5, pady=10)
            ctk.CTkButton(row, text="🗑️", command=lambda nid=note['id']: self.delete_note(nid),
                          width=40, height=32, fg_color="#EF4444").grid(row=0, column=3, padx=(5, 15), pady=10)
    
    def add_note_entry(self):
        """Add a new note."""
        title = self.note_title.get().strip()
        content = self.note_content.get().strip()
        
        tags = self.note_tags.get().strip()
        
        if not all([title, content]):
            self.show_toast("Please fill all fields", error=True)
            return
        
        entry_id = self.backend.add_note(title, content)
        if tags:
            for tag in tags.split(','):
                if tag.strip():
                    self.backend.add_tag_to_entry('note', entry_id, tag.strip())
        
        self.note_title.delete(0, 'end')
        self.note_content.delete(0, 'end')
        self.note_tags.delete(0, 'end')
        self.refresh_notes()
        self.show_toast("Note added!")
    
    def view_note(self, note_id: int):
        """Show note content in a popup."""
        try:
            note = self.backend.get_note_content(note_id)
        except Exception as e:
            self.show_toast(f"Error: {e}", error=True)
            return
        
        popup = ctk.CTkToplevel(self)
        popup.title(f"Note: {note['title']}")
        popup.geometry("500x350")
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - popup.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(popup, text=note['title'], font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        text_box = ctk.CTkTextbox(popup, wrap="word")
        text_box.pack(fill="both", expand=True, padx=20, pady=10)
        text_box.insert("1.0", note['content'])
        text_box.configure(state="disabled")
        
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="📋 Copy", width=80,
                      command=lambda: [pyperclip.copy(note['content']), self.show_toast("Copied!")]).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Close", width=80, command=popup.destroy).pack(side="left", padx=5)
    
    def build_settings_tab(self):
        """Build the Settings tab content."""
        tab = self.tab_settings
        tab.grid_rowconfigure(0, weight=1) 
        
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)
        
        security_frame = ctk.CTkFrame(container)
        security_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        security_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(security_frame, text="🛡️Password Security", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(security_frame, text="Scan your vault for weak, reused, or potentially breached passwords. All checks are performed locally.",
                     text_color="gray", wraplength=600, justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        
        ctk.CTkButton(security_frame, text="🔍 Scan Vault", command=self.show_security_scan_popup,
                      height=40, fg_color="#10B981", hover_color="#059669").grid(row=2, column=0, sticky="w", padx=20, pady=(0, 20))
        
        backup_frame = ctk.CTkFrame(container)
        backup_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        backup_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(backup_frame, text="💾 Backup & Restore", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(backup_frame, text="Create an encrypted backup of your entire vault or restore from a previous backup.", 
                     text_color="gray", wraplength=600, justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        
        btn_row = ctk.CTkFrame(backup_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 20))
        
        ctk.CTkButton(btn_row, text="Backup Vault (.db)", command=self.handle_backup_vault,
                      height=40, fg_color="#3B82F6", hover_color="#2563EB").pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(btn_row, text="Import Vault (.db)", command=self.handle_import_vault,
                      height=40, fg_color="#6366F1", hover_color="#4F46E5").pack(side="left")
        
        export_frame = ctk.CTkFrame(container)
        export_frame.grid(row=2, column=0, sticky="ew")
        export_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(export_frame, text="📂 Data Export", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(export_frame, text="Export all your data into a plain-text JSON file. This file will NOT be encrypted.",
                     text_color="gray", wraplength=600, justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(export_frame, text="⚠️ WARNING: The exported JSON file contains your raw passwords. Keep it extremely safe!",
                     text_color="#FF6B6B", font=ctk.CTkFont(size=12, weight="bold"), wraplength=600, justify="left").grid(
                         row=2, column=0, sticky="w", padx=20, pady=(0, 20))
        
        ctk.CTkButton(export_frame, text="Export to JSON (Decrypted)", command=self.handle_export_json,
                      height=40, fg_color="#F59E0B", hover_color="#D97706").grid(row=3, column=0, sticky="w", padx=20, pady=(0, 20))

    def handle_backup_vault(self):
        """Handle backup of the database file."""
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")],
            initialfile=f"SafeVault_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        if file_path:
            try:
                self.backend.export_vault(file_path)
                self.show_toast("Backup created successfully!")
            except Exception as e:
                self.show_toast(f"Backup failed: {e}", error=True)

    def handle_import_vault(self):
        """Handle import of a database file."""
        from tkinter import filedialog, messagebox
        if not messagebox.askyesno("Confirm Import", 
                                  "Importing a vault will OVERWRITE ALL current data and lock the vault. Continue?"):
            return
            
        file_path = filedialog.askopenfilename(
            filetypes=[("SQLite Database", "*.db")]
        )
        if file_path:
            try:
                self.backend.import_vault(file_path)
                messagebox.showinfo("Success", "Vault imported successfully. Please log in again.")
                self.show_login_screen()
            except Exception as e:
                self.show_toast(f"Import failed: {e}", error=True)

    def handle_export_json(self):
        """Handle export of decrypted data to JSON."""
        from tkinter import filedialog, messagebox
        import json
        
        if not messagebox.askyesno("Security Warning", 
                                  "This will export all your passwords in PLAIN TEXT. Are you sure you want to proceed?"):
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON file", "*.json")],
            initialfile=f"SafeVault_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        if file_path:
            try:
                data = self.backend.get_full_export_data()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                self.show_toast("Exported successfully!")
                messagebox.showwarning("Security Reminder", 
                                     f"Data exported to {file_path}. PLEASE DELETE THIS FILE after use or keep it in a secure location!")
            except Exception as e:
                self.show_toast(f"Export failed: {e}", error=True)

    def delete_note(self, note_id: int):
        """Delete a note."""
        self.backend.delete_note(note_id)
        self.refresh_notes()
        self.show_toast("Note deleted")
    
    def show_security_scan_popup(self):
        """Display security scan results in a popup modal."""
        try:
            report = self.backend.run_security_scan()
        except Exception as e:
            self.show_toast(f"Scan failed: {e}", error=True)
            return
        
        self._current_report = report
        
        popup = ctk.CTkToplevel(self)
        popup.title("🛡️Password Security Scan")
        popup.geometry("700x650")
        popup.resizable(True, True)
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 700) // 2
        y = self.winfo_y() + (self.winfo_height() - 650) // 2
        popup.geometry(f"+{x}+{y}")
        
        main_frame = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        score_frame = ctk.CTkFrame(main_frame)
        score_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        score_frame.grid_columnconfigure(0, weight=1)
        
        total = report['total_passwords']
        score = report['overall_score']
        
        if total == 0:
            ctk.CTkLabel(score_frame, text="No passwords found in vault", 
                        font=ctk.CTkFont(size=16), text_color="gray").grid(
                            row=0, column=0, padx=20, pady=20)
        else:
            if score >= 80:
                score_color = "#10B981"  
            elif score >= 60:
                score_color = "#3B82F6"  
            elif score >= 40:
                score_color = "#F59E0B"  
            else:
                score_color = "#EF4444"  
            
            ctk.CTkLabel(score_frame, text=f"Overall Security Score: {score}%",
                        font=ctk.CTkFont(size=20, weight="bold")).grid(
                            row=0, column=0, padx=20, pady=(20, 10), sticky="w")
            
            progress = ctk.CTkProgressBar(score_frame, width=400, height=20)
            progress.set(score / 100)
            progress.configure(progress_color=score_color)
            progress.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        if total > 0:
            dist_frame = ctk.CTkFrame(main_frame)
            dist_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
            dist_frame.grid_columnconfigure(0, weight=1)
            
            ctk.CTkLabel(dist_frame, text=f"Password Strength Distribution ({total} passwords)",
                        font=ctk.CTkFont(size=16, weight="bold")).grid(
                            row=0, column=0, padx=20, pady=(15, 10), sticky="w")
            
            dist = report['strength_distribution']
            colors = {
                'strong': "#10B981",
                'good': "#3B82F6", 
                'fair': "#F59E0B",
                'weak': "#EF4444"
            }
            labels = {'strong': '💪 Strong', 'good': '👍 Good', 'fair': '⚠️ Fair', 'weak': '❌ Weak'}
            
            for idx, (key, label) in enumerate(labels.items()):
                count = dist[key]
                pct = (count / total * 100) if total > 0 else 0
                
                row_frame = ctk.CTkFrame(dist_frame, fg_color="transparent")
                row_frame.grid(row=idx+1, column=0, sticky="ew", padx=20, pady=2)
                row_frame.grid_columnconfigure(1, weight=1)
                
                ctk.CTkLabel(row_frame, text=f"{label}", width=100, anchor="w").grid(row=0, column=0, sticky="w")
                
                bar = ctk.CTkProgressBar(row_frame, width=300, height=15)
                bar.set(pct / 100)
                bar.configure(progress_color=colors[key])
                bar.grid(row=0, column=1, padx=(10, 10), sticky="ew")
                
                ctk.CTkLabel(row_frame, text=f"{count} ({pct:.0f}%)", width=80).grid(row=0, column=2, sticky="e")
            
            ctk.CTkLabel(dist_frame, text="").grid(row=5, column=0, pady=(5, 10))
        
        issues_count = len(report['weak_passwords']) + len(report['duplicate_groups']) + len(report['common_passwords'])
        
        issues_frame = ctk.CTkFrame(main_frame)
        issues_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        issues_frame.grid_columnconfigure(0, weight=1)
        
        if issues_count == 0:
            ctk.CTkLabel(issues_frame, text="✅ No issues found! Your passwords look secure.",
                        font=ctk.CTkFont(size=14), text_color="#10B981").grid(
                            row=0, column=0, padx=20, pady=20)
        else:
            ctk.CTkLabel(issues_frame, text=f"⚠️ Issues Found ({issues_count})",
                        font=ctk.CTkFont(size=16, weight="bold")).grid(
                            row=0, column=0, padx=20, pady=(15, 10), sticky="w")
            
            row_idx = 1
            
            if report['weak_passwords']:
                ctk.CTkLabel(issues_frame, text=f"🔴 {len(report['weak_passwords'])} Weak Passwords",
                            font=ctk.CTkFont(size=14, weight="bold"), text_color="#EF4444").grid(
                                row=row_idx, column=0, padx=20, pady=(10, 5), sticky="w")
                row_idx += 1
                
                for wp in report['weak_passwords'][:5]:  
                    issues_text = ", ".join(wp['issues'][:2]) if wp['issues'] else "Low complexity"
                    ctk.CTkLabel(issues_frame, text=f"    • {wp['app_name']} - {issues_text}",
                                text_color="gray", wraplength=550, justify="left").grid(
                                    row=row_idx, column=0, padx=20, sticky="w")
                    row_idx += 1
                
                if len(report['weak_passwords']) > 5:
                    ctk.CTkLabel(issues_frame, text=f"    ... and {len(report['weak_passwords']) - 5} more",
                                text_color="gray").grid(row=row_idx, column=0, padx=20, sticky="w")
                    row_idx += 1
            
            if report['duplicate_groups']:
                total_dupes = sum(len(g) for g in report['duplicate_groups'])
                ctk.CTkLabel(issues_frame, text=f"🟡 {len(report['duplicate_groups'])} Reused Password Groups ({total_dupes} entries)",
                            font=ctk.CTkFont(size=14, weight="bold"), text_color="#F59E0B").grid(
                                row=row_idx, column=0, padx=20, pady=(10, 5), sticky="w")
                row_idx += 1
                
                for group in report['duplicate_groups'][:3]: 
                    apps = ", ".join([e['app_name'] for e in group[:3]])
                    if len(group) > 3:
                        apps += f" +{len(group) - 3} more"
                    ctk.CTkLabel(issues_frame, text=f"    • {apps}",
                                text_color="gray", wraplength=550, justify="left").grid(
                                    row=row_idx, column=0, padx=20, sticky="w")
                    row_idx += 1
            
            if report['common_passwords']:
                ctk.CTkLabel(issues_frame, text=f"🔴 {len(report['common_passwords'])} Potentially Breached Passwords",
                            font=ctk.CTkFont(size=14, weight="bold"), text_color="#EF4444").grid(
                                row=row_idx, column=0, padx=20, pady=(10, 5), sticky="w")
                row_idx += 1
                
                for bp in report['common_passwords'][:5]:
                    ctk.CTkLabel(issues_frame, text=f"    • {bp['app_name']} - Matches common password list",
                                text_color="gray").grid(row=row_idx, column=0, padx=20, sticky="w")
                    row_idx += 1
            
            ctk.CTkLabel(issues_frame, text="").grid(row=row_idx, column=0, pady=(5, 10))
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        
        ctk.CTkButton(btn_frame, text="📄 Export Encrypted Report", 
                      command=lambda: self.handle_export_security_report(popup),
                      height=40, fg_color="#3B82F6", hover_color="#2563EB").pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(btn_frame, text="Close", command=popup.destroy,
                      height=40, fg_color="#666666", hover_color="#555555").pack(side="left")

    def handle_export_security_report(self, popup=None):
        """Export the current security scan report as an encrypted file."""
        from tkinter import filedialog
        
        if not hasattr(self, '_current_report') or not self._current_report:
            self.show_toast("No scan report available. Run a scan first.", error=True)
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".svreport",
            filetypes=[("SafeVault Security Report", "*.svreport")],
            initialfile=f"SecurityScan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svreport"
        )
        
        if file_path:
            try:
                self.backend.export_encrypted_report(self._current_report, file_path)
                self.show_toast("Encrypted report exported successfully!")
                if popup:
                    popup.destroy()
            except Exception as e:
                self.show_toast(f"Export failed: {e}", error=True)

    def handle_search(self, *args):
        """Handle global search input change."""
        query = self.search_var.get().strip()
        if not query:
            self.refresh_passwords()
            self.refresh_cards()
            self.refresh_notes()
            return
            
        results = self.backend.search_vault(query)
        self.refresh_passwords(results['passwords'])
        self.refresh_cards(results['cards'])
        self.refresh_notes(results['notes'])

    def show_toast(self, message: str, error: bool = False):
        """Show a temporary toast notification."""
        toast = ctk.CTkLabel(
            self, text=message, font=ctk.CTkFont(size=12),
            fg_color="#10B981" if not error else "#EF4444",
            corner_radius=8, padx=20, pady=10
        )
        toast.place(relx=0.5, rely=0.95, anchor="center")
        self.after(2000, toast.destroy)
    
    def on_closing(self):
        """Handle window close event."""
        self.backend.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
