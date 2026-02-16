# SafeVault 🔐

**SafeVault** is a secure, local, and user-friendly password manager built with Python. It features a modern tabbed interface to manage your passwords, credit cards, and secret notes securely.

[![Download](https://img.shields.io/github/v/release/YacineDahmani/SafeVault?label=Download&style=for-the-badge&logo=github)](https://github.com/YacineDahmani/SafeVault/releases/latest)


## 🌟 Features

*   **Strong Encryption:** Uses **Fernet (AES-128)** symmetric encryption for all sensitive data.
*   **Secure Storage:** Your data is stored locally in an encrypted SQLite database (`vault.db`).
*   **Zero-Knowledge Architecture:** The master password is never stored. A salted hash is used for verification, and the encryption key is derived at runtime using **PBKDF2-HMAC-SHA256**.
*   **Modern UI:** Clean, dark-themed interface built with `customtkinter`.
*   **Password Generator:** Built-in cryptographic random password generator.
*   **Clipboard Integration:** One-click copy for passwords and card details.
*   **Organized:** Separate tabs for Passwords, Credit Cards, and Notes.

## 🛠️ Tech Stack

*   **Python 3.10+**
*   **GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
*   **Security:** [Cryptography](https://cryptography.io/en/latest/) (Fernet, PBKDF2)
*   **Database:** SQLite3
*   **Clipboard:** Pyperclip

## 🚀 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YacineDahmani/SafeVault.git
    cd SafeVault
    ```

2.  **Create and activate a virtual environment (Recommended):**
    *   **Windows:**
        ```bash
        python -m venv .venv
        .venv\Scripts\activate
        ```
    *   **macOS / Linux:**
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 💻 Usage

1.  **Run the application:**
    ```bash
    python SafeVault.py
    ```

2.  **First Run:**
    *   You will be prompted to create a **Master Password**.
    *   **⚠️ IMPORTANT:** Remember this password! It cannot be recovered. If you lose it, you lose access to your encrypted data.

3.  **Dashboard:**
    *   **Passwords:** Add app/website credentials. Use the dice 🎲 icon to generate strong passwords.
    *   **Cards:** Store credit/debit card details securely.
    *   **Notes:** Keep secure text notes.

## 🔒 Security Details

*   **Master Password:** Hashed using PBKDF2-HMAC-SHA256 with a unique 16-byte salt and 100,000 iterations.
*   **Data Encryption:** Each entry (password, card number, note content) is encrypted individually using a unique salt and a derived key from your master password.
*   **Local Only:** No data is ever sent to the cloud. You are in full control of your `vault.db` file.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
