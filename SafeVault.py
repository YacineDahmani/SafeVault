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
        cursor.execute("SELECT id, label, holder_name, created_at FROM cards ORDER BY label")
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
        
        # Handle PIN (might be null for old records, though we migrate schema, data is separate)
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
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        if self.backend.is_first_run():
            self.show_setup_screen()
        else:
            self.show_login_screen()
    
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
        self.setup_password = ctk.CTkEntry(frame, placeholder_text="Enter a strong password", show="•", height=45)
        self.setup_password.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(frame, text="Confirm Password:", anchor="w").grid(row=4, column=0, sticky="w", pady=(0, 5))
        self.setup_confirm = ctk.CTkEntry(frame, placeholder_text="Confirm your password", show="•", height=45)
        self.setup_confirm.grid(row=5, column=0, sticky="ew", pady=(0, 30))
        
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
        
        self.login_password = ctk.CTkEntry(frame, placeholder_text="Master Password", show="•", width=350, height=50)
        self.login_password.grid(row=2, column=0, pady=(0, 20))
        self.login_password.bind("<Return>", lambda e: self.handle_login())
        
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
        
        ctk.CTkButton(
            header, text="🔒 Lock", command=self.show_login_screen,
            width=100, fg_color="#666666", hover_color="#555555"
        ).grid(row=0, column=2, padx=20, pady=15)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.tab_passwords = self.tabview.add("🔑 Passwords")
        self.tab_cards = self.tabview.add("💳 Cards")
        self.tab_notes = self.tabview.add("📝 Notes")
        
        for tab in [self.tab_passwords, self.tab_cards, self.tab_notes]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(1, weight=1)
        
        self.build_passwords_tab()
        self.build_cards_tab()
        self.build_notes_tab()
    

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
        
        self.pw_pass = ctk.CTkEntry(pw_frame, placeholder_text="Password", height=40, show="•")
        self.pw_pass.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ctk.CTkButton(pw_frame, text="🎲", command=self.generate_password_field, width=40, height=40,
                      fg_color="#7C3AED", hover_color="#6D28D9").grid(row=0, column=1)
        
        ctk.CTkButton(form, text="Add", command=self.add_password_entry, width=80, height=40,
                      fg_color="#10B981", hover_color="#059669").grid(row=1, column=3, padx=(5, 15), pady=(0, 15))
        
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
    
    def refresh_passwords(self):
        """Refresh the passwords list."""
        for widget in self.pw_scroll.winfo_children():
            widget.destroy()
        
        entries = self.backend.get_all_passwords()
        
        if not entries:
            ctk.CTkLabel(self.pw_scroll, text="No passwords saved yet.", text_color="gray").grid(row=0, column=0, pady=30)
            return
        
        for idx, entry in enumerate(entries):
            row = ctk.CTkFrame(self.pw_scroll)
            row.grid(row=idx, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(row, text=entry['app_name'], font=ctk.CTkFont(weight="bold"), anchor="w").grid(
                row=0, column=0, padx=15, pady=10, sticky="w")
            ctk.CTkLabel(row, text=entry['username'], text_color="gray", anchor="w").grid(
                row=0, column=1, padx=10, pady=10, sticky="ew")
            
            ctk.CTkButton(row, text="📋", command=lambda eid=entry['id']: self.copy_password(eid),
                          width=40, height=32, fg_color="#3B82F6").grid(row=0, column=2, padx=5, pady=10)
            ctk.CTkButton(row, text="🗑️", command=lambda eid=entry['id']: self.delete_password(eid),
                          width=40, height=32, fg_color="#EF4444").grid(row=0, column=3, padx=(5, 15), pady=10)
    
    def add_password_entry(self):
        """Add a new password."""
        app = self.pw_app.get().strip()
        user = self.pw_user.get().strip()
        pw = self.pw_pass.get()
        
        if not all([app, user, pw]):
            self.show_toast("Please fill all fields", error=True)
            return
        
        self.backend.add_password(app, user, pw)
        self.pw_app.delete(0, 'end')
        self.pw_user.delete(0, 'end')
        self.pw_pass.delete(0, 'end')
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
        
        digits_only = new_value.replace("/", "")
        
        if not digits_only.isdigit():
            return False
        
        if len(new_value) > 5:
            return False
        
        if len(digits_only) >= 2:
            if len(new_value) == 2:
                self.card_expiry.delete(0, 'end')
                self.card_expiry.insert(0, new_value + "/")
                return False  
            return new_value[2:3] == "/" if len(new_value) > 2 else True
        
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
        self.card_number = ctk.CTkEntry(form, placeholder_text="Num (16 digits)", height=40,
                                        validate="key", validatecommand=(card_num_validate, '%P'))
        self.card_number.grid(row=1, column=2, padx=5, pady=(0, 15), sticky="ew")
        
        expiry_validate = self.register(self.validate_expiry)
        self.card_expiry = ctk.CTkEntry(form, placeholder_text="MM/YY", height=40, width=80,
                                        validate="key", validatecommand=(expiry_validate, '%P'))
        self.card_expiry.grid(row=1, column=3, padx=5, pady=(0, 15), sticky="ew")
        
        cvv_validate = self.register(self.validate_cvv)
        self.card_cvv = ctk.CTkEntry(form, placeholder_text="CVV (4 digits)", height=40, width=60, show="•",
                                     validate="key", validatecommand=(cvv_validate, '%P'))
        self.card_cvv.grid(row=1, column=4, padx=5, pady=(0, 15), sticky="ew")
        
        pin_validate = self.register(self.validate_pin)
        self.card_pin = ctk.CTkEntry(form, placeholder_text="PIN (4 digits)", height=40, width=60, show="•",
                                     validate="key", validatecommand=(pin_validate, '%P'))
        self.card_pin.grid(row=1, column=5, padx=5, pady=(0, 15), sticky="ew")
        
        ctk.CTkButton(form, text="Add", command=self.add_card_entry, width=80, height=40,
                      fg_color="#10B981", hover_color="#059669").grid(row=1, column=6, padx=(5, 15), pady=(0, 15))
        
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
    
    def refresh_cards(self):
        """Refresh the cards list."""
        for widget in self.card_scroll.winfo_children():
            widget.destroy()
        
        cards = self.backend.get_all_cards()
        
        if not cards:
            ctk.CTkLabel(self.card_scroll, text="No cards saved yet.", text_color="gray").grid(row=0, column=0, pady=30)
            return
        
        for idx, card in enumerate(cards):
            row = ctk.CTkFrame(self.card_scroll)
            row.grid(row=idx, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(row, text=f"💳 {card['label']}", font=ctk.CTkFont(weight="bold"), anchor="w").grid(
                row=0, column=0, padx=15, pady=10, sticky="w")
            ctk.CTkLabel(row, text=card['holder_name'], text_color="gray", anchor="w").grid(
                row=0, column=1, padx=10, pady=10, sticky="ew")
            
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
            self.backend.add_card(label, holder, number, expiry, cvv, pin)
            for entry in [self.card_label, self.card_holder, self.card_number, self.card_expiry, self.card_cvv, self.card_pin]:
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
        popup.geometry("400x300")
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
            ("Number", details['card_number']),
            ("Expiry", details['expiry']),
            ("CVV", details['cvv']),
            ("PIN", details['pin'])
        ]
        
        for i, (label, value) in enumerate(info):
            ctk.CTkLabel(frame, text=f"{label}:", anchor="w", font=ctk.CTkFont(weight="bold")).grid(
                row=i, column=0, sticky="w", padx=10, pady=8)
            
            val_frame = ctk.CTkFrame(frame, fg_color="transparent")
            val_frame.grid(row=i, column=1, sticky="ew", padx=10, pady=8)
            val_frame.grid_columnconfigure(0, weight=1)
            
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
        
        ctk.CTkButton(form, text="Add", command=self.add_note_entry, width=80, height=40,
                      fg_color="#10B981", hover_color="#059669").grid(row=1, column=2, padx=(5, 15), pady=(0, 15))
        
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
    
    def refresh_notes(self):
        """Refresh the notes list."""
        for widget in self.note_scroll.winfo_children():
            widget.destroy()
        
        notes = self.backend.get_all_notes()
        
        if not notes:
            ctk.CTkLabel(self.note_scroll, text="No notes saved yet.", text_color="gray").grid(row=0, column=0, pady=30)
            return
        
        for idx, note in enumerate(notes):
            row = ctk.CTkFrame(self.note_scroll)
            row.grid(row=idx, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(0, weight=1)
            
            ctk.CTkLabel(row, text=f"📝 {note['title']}", font=ctk.CTkFont(weight="bold"), anchor="w").grid(
                row=0, column=0, padx=15, pady=10, sticky="ew")
            
            ctk.CTkButton(row, text="👁️ View", command=lambda nid=note['id']: self.view_note(nid),
                          width=70, height=32, fg_color="#3B82F6").grid(row=0, column=1, padx=5, pady=10)
            ctk.CTkButton(row, text="🗑️", command=lambda nid=note['id']: self.delete_note(nid),
                          width=40, height=32, fg_color="#EF4444").grid(row=0, column=2, padx=(5, 15), pady=10)
    
    def add_note_entry(self):
        """Add a new note."""
        title = self.note_title.get().strip()
        content = self.note_content.get().strip()
        
        if not all([title, content]):
            self.show_toast("Please fill all fields", error=True)
            return
        
        self.backend.add_note(title, content)
        self.note_title.delete(0, 'end')
        self.note_content.delete(0, 'end')
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
    
    def delete_note(self, note_id: int):
        """Delete a note."""
        self.backend.delete_note(note_id)
        self.refresh_notes()
        self.show_toast("Note deleted")
    
    
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
