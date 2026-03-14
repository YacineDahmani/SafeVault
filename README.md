# SafeVault 🔐

**SafeVault** is a secure, local, and user-friendly password manager built with Python and PySide6. It features a modern, premium tabbed interface to manage your passwords, credit cards, and secret notes securely. 

[![Download](https://img.shields.io/github/v/release/YacineDahmani/SafeVault?label=Download&style=for-the-badge&logo=github)](https://github.com/YacineDahmani/SafeVault/releases/latest)

## 🌟 Features

- **Strong Encryption:** Uses **Fernet (AES-128)** symmetric encryption for all sensitive data.
- **Secure Storage:** Your data is stored locally in an encrypted SQLite database (`vault.db`).
- **Zero-Knowledge Architecture:** The master password is never stored. A salted hash is used for verification, and the encryption key is derived at runtime using **PBKDF2-HMAC-SHA256**.
- **Modern PySide6 UI:** Premium dark-themed interface with smooth transitions and icon-based controls.
- **Security Scan:** Built-in password health check to identify weak, reused, or common passwords.
- **Backup & Restore:** Easily backup your vault to a separate file and restore it when needed.
- **Import/Export:** Export your data as JSON or generate an encrypted security report.
- **Improved Card View:** Detailed individual view for credit cards with per-field copy buttons and strict input validation.
- **Password Generator:** Built-in cryptographic random password generator.

## 📁 Project Structure

```text
SafeVault/
├── assets/             # Icons and media
├── src/                # Source code
│   ├── backend.py      # Core logic and encryption
│   └── frontend.py     # PySide6 GUI implementation
├── main.py             # Application entry point
├── requirements.txt    # Dependencies
└── SafeVault.spec      # PyInstaller build specification
```

## 🛠️ Tech Stack

- **Python 3.10+**
- **GUI:** [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python)
- **Security:** [Cryptography](https://cryptography.io/en/latest/) (Fernet, PBKDF2)
- **Database:** SQLite3
- **Clipboard:** Pyperclip

## 🚀 Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/YacineDahmani/SafeVault.git
    cd SafeVault
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    .venv\Scripts\activate  # Windows
    # source .venv/bin/activate  # macOS / Linux
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 💻 Usage

1.  **Run the application:**

    ```bash
    python main.py
    ```

2.  **First Run:**
    - You will be prompted to create a **Master Password**.
    - **⚠️ IMPORTANT:** Remember this password! It cannot be recovered. If you lose it, you lose access to your encrypted data.

3.  **Dashboard:**
    - **Passwords:** Manage your credentials. Use the Roll 🎲 icon to generate strong passwords.
    - **Cards:** Store credit/debit card details with individual field copying.
    - **Notes:** Keep secure text notes.
    - **Settings:** Access health scans, backup, and export tools.

## 🔒 Security Details

- **Master Password:** Hashed using PBKDF2-HMAC-SHA256 with a unique 16-byte salt and 100,000 iterations.
- **Data Encryption:** Each entry (password, card number, note content) is encrypted individually using a unique salt and a derived key from your master password.
- **Local Only:** No data is ever sent to the cloud. You are in full control of your `vault.db` file.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full list of changes and version history.