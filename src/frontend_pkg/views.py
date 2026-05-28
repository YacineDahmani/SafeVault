"""
SafeVault Frontend - PySide6 GUI
"""

import json
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QStackedWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QFormLayout, QDialog, QScrollArea, QTextEdit, QSizePolicy,
    QFileDialog, QProgressBar, QGridLayout, QGroupBox,
    QSlider, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QSize, QTimer, QRegularExpression, QUrl
from PySide6.QtGui import QIcon, QFont, QColor, QRegularExpressionValidator, QDesktopServices

import pyperclip


ICO_COPY   = "\uE16F"   # copy
ICO_VIEW   = "\uE890"   # view/eye
ICO_DEL    = "\uE711"   # cancel/close ×
ICO_HIDE   = "\uE72E"   # lock
ICO_SHOW   = "\uE785"   # unlock
ICO_READ   = "\uE736"   # dictionary/book
ICO_ADD    = "\uE710"   # add/+
ICO_REFRESH = "\uE72C"  # refresh
ICO_CARD   = "\uE8C7"   # credit card
ICO_ENV    = "\uE943"   # file code
ICO_ROCKET = "\uEB4F"   # rocket
ICO_DICE   = "\uE14B"   # shuffle/generator
ICO_KEY    = "\uE8D7"   # key
ICO_NOTES  = "\uE70B"   # edit/notes
ICO_SETTINGS = "\uE713" # settings
ICO_SEARCH = "\uE71E"   # search
ICO_SAVE   = "\uE74E"   # save
ICO_UPLOAD = "\uE78C"   # upload
ICO_WARN   = "\uE7BA"   # warning
ICO_CHECK  = "\uE73E"   # checkmark


def get_app_icon_path():
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[2]
    return base_path / "assets" / "SafeVault.ico"


class ModernStyle:
    STYLE = """
    * {
        font-family: "Segoe UI", "Segoe Fluent Icons", "Segoe MDL2 Assets", "San Francisco", "Helvetica Neue", Arial, sans-serif;
    }
    QMainWindow, QWidget {
        background-color: #121212;
        color: #e0e0e0;
    }
    QLabel {
        background: transparent;
        selection-background-color: transparent;
        selection-color: #e0e0e0;
    }
    QLineEdit, QTextEdit {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 8px;
        color: #ffffff;
        font-size: 14px;
        selection-background-color: #0078D4;
        selection-color: white;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #0078D4;
    }
    QPushButton {
        background-color: #0078D4;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #106EBE;
    }
    QPushButton:pressed {
        background-color: #005A9E;
    }
    QPushButton#secondaryBtn {
        background-color: #2b2b2b;
        border: 1px solid #3d3d3d;
        color: #cccccc;
    }
    QPushButton#secondaryBtn:hover {
        background-color: #363636;
    }
    QPushButton#dangerBtn {
        background-color: #c9302c;
        color: white;
    }
    QPushButton#dangerBtn:hover {
        background-color: #ac2925;
    }
    QPushButton#iconBtn {
        background: transparent;
        border: none;
        font-size: 16px;
        padding: 0px;
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
        color: #cccccc;
    }
    QPushButton#iconBtn:hover {
        background-color: #2b2b2b;
        border-radius: 4px;
    }
    QPushButton#dangerIconBtn {
        background: transparent;
        border: none;
        font-size: 16px;
        padding: 0px;
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
        color: #ff5555;
    }
    QPushButton#dangerIconBtn:hover {
        background-color: rgba(201, 48, 44, 0.2);
        border-radius: 4px;
    }
    QTabWidget::pane {
        border: none;
        background: #121212;
    }
    QTabBar::tab {
        background: #1e1e1e;
        color: #a0a0a0;
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-size: 14px;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background: #2b2b2b;
        color: #ffffff;
        border-bottom: 2px solid #0078D4;
    }
    QTableWidget {
        background-color: #1e1e1e;
        alternate-background-color: #181818;
        border: 1px solid #333333;
        border-radius: 8px;
        color: #ffffff;
        gridline-color: #2a2a2a;
        font-size: 14px;
    }
    QHeaderView::section {
        background-color: #252525;
        color: #a0a0a0;
        padding: 8px;
        border: none;
        border-right: 1px solid #333;
        border-bottom: 1px solid #333;
        font-weight: bold;
        font-size: 12px;
    }
    QTableWidget::item {
        padding: 4px;
        border-bottom: 1px solid #2a2a2a;
    }
    QTableWidget::item:selected {
        background-color: rgba(0, 120, 212, 0.2);
        color: white;
    }
    QScrollBar:vertical {
        background: #121212;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #333333;
        min-height: 20px;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: #444444;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QDialog {
        background-color: #1e1e1e;
        border-radius: 8px;
    }
    QGroupBox {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 20px;
        font-weight: bold;
        color: #a0a0a0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 15px;
        padding: 0 5px;
    }
    QProgressBar {
        background-color: #252525;
        border: 1px solid #333;
        border-radius: 5px;
        text-align: center;
        color: white;
        font-weight: bold;
        height: 22px;
    }
    QProgressBar::chunk {
        border-radius: 5px;
    }
    """


# ─── Shared toast helper ─────────────────────────────────────────────
def show_toast(parent, message, duration=2000):
    toast = QDialog(parent)
    toast.setWindowFlags(
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.Tool |
        Qt.WindowType.WindowStaysOnTopHint
    )
    toast.setStyleSheet("background-color: #0078D4; border-radius: 6px;")
    layout = QVBoxLayout(toast)
    lbl = QLabel(message)
    lbl.setStyleSheet("color: white; font-weight: bold; padding: 10px;")
    layout.addWidget(lbl)

    win = parent.window()
    geom = win.geometry()
    toast.adjustSize()
    toast.move(geom.x() + geom.width() - toast.width() - 20,
               geom.y() + geom.height() - 80)
    toast.show()
    QTimer.singleShot(duration, toast.accept)


# ─── Two-Factor Dialogs ───────────────────────────────────────────────
class TwoFactorVerifyDialog(QDialog):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self._build()

    def _build(self):
        self.setWindowTitle("Two-Factor Authentication")
        self.setMinimumSize(360, 200)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        title = QLabel(f"{ICO_HIDE}  Enter 2FA Code")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.code_in = QLineEdit()
        self.code_in.setPlaceholderText("6-digit code")
        self.code_in.setMaxLength(8)
        self.code_in.setMinimumHeight(36)
        self.code_in.returnPressed.connect(self._verify)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #ff5555; font-size: 12px;")

        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        verify = QPushButton("Verify")
        verify.clicked.connect(self._verify)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(verify)

        lay.addWidget(title)
        lay.addWidget(self.code_in)
        lay.addWidget(self.err)
        lay.addLayout(btns)

    def _verify(self):
        code = self.code_in.text().strip()
        if not code:
            self.err.setText("Code is required")
            return
        if self.backend.verify_2fa_code(code):
            self.accept()
        else:
            self.err.setText("Invalid or expired code")
            self.code_in.selectAll()


class TwoFactorSetupDialog(QDialog):
    def __init__(self, backend, secret, otpauth_uri, parent=None, confirm_required=True):
        super().__init__(parent)
        self.backend = backend
        self.secret = secret
        self.otpauth_uri = otpauth_uri
        self.confirm_required = confirm_required
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self._build()

    def _build(self):
        self.setWindowTitle("Enable Two-Factor Authentication")
        self.setMinimumSize(460, 520)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        title = QLabel(f"{ICO_KEY}  Set Up 2FA")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        desc = QLabel("Add a new TOTP entry in your authenticator app using the setup key below.")
        desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        desc.setWordWrap(True)

        key_lbl = QLabel("Setup key:")
        key_lbl.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        self.key_box = QLineEdit(self.secret)
        self.key_box.setReadOnly(True)

        copy_key = QPushButton("Copy Setup Key")
        copy_key.setObjectName("secondaryBtn")
        copy_key.clicked.connect(lambda: (pyperclip.copy(self.secret), show_toast(self, "Setup key copied!")))

        uri_lbl = QLabel("otpauth URI (optional):")
        uri_lbl.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        self.uri_box = QLineEdit(self.otpauth_uri)
        self.uri_box.setReadOnly(True)

        copy_uri = QPushButton("Copy otpauth URI")
        copy_uri.setObjectName("secondaryBtn")
        copy_uri.clicked.connect(lambda: (pyperclip.copy(self.otpauth_uri), show_toast(self, "URI copied!")))

        code_lbl = QLabel("Enter a 6-digit code to confirm:")
        code_lbl.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        self.code_in = QLineEdit()
        self.code_in.setPlaceholderText("6-digit code")
        self.code_in.setMaxLength(8)
        self.code_in.setMinimumHeight(36)
        self.code_in.returnPressed.connect(self._confirm)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #ff5555; font-size: 12px;")

        btns = QHBoxLayout()
        close = QPushButton("Cancel")
        close.setObjectName("secondaryBtn")
        close.clicked.connect(self.reject)
        enable = QPushButton("Enable 2FA")
        enable.clicked.connect(self._confirm)
        btns.addStretch()
        btns.addWidget(close)
        btns.addWidget(enable)
        if not self.confirm_required:
            enable.setVisible(False)
            close.setText("Close")

        lay.addWidget(title)
        lay.addWidget(desc)
        lay.addWidget(key_lbl)
        lay.addWidget(self.key_box)
        lay.addWidget(copy_key)
        lay.addWidget(uri_lbl)
        lay.addWidget(self.uri_box)
        lay.addWidget(copy_uri)
        if self.confirm_required:
            lay.addWidget(code_lbl)
            lay.addWidget(self.code_in)
            lay.addWidget(self.err)
        else:
            info = QLabel("This is your existing setup key. Keep it private.")
            info.setStyleSheet("color: #a0a0a0; font-size: 12px;")
            info.setWordWrap(True)
            lay.addWidget(info)
        lay.addLayout(btns)

    def _confirm(self):
        if not self.confirm_required:
            self.accept()
            return
        code = self.code_in.text().strip()
        if not code:
            self.err.setText("Code is required")
            return
        if self.backend.verify_2fa_code_for_secret(self.secret, code):
            self.accept()
        else:
            self.err.setText("Invalid or expired code")
            self.code_in.selectAll()


# ─── Login Screen ─────────────────────────────────────────────────────
class LoginWidget(QWidget):
    def __init__(self, backend, on_success):
        super().__init__()
        self.backend = backend
        self.on_success = on_success
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("authBox")
        box.setStyleSheet(
            "#authBox { background-color: #1e1e1e; border-radius: 12px; border: 1px solid #333; }"
        )
        vb = QVBoxLayout(box)
        vb.setContentsMargins(40, 40, 40, 40)
        vb.setSpacing(20)

        title = QLabel(f"{ICO_HIDE} Welcome Back")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Enter your master password to unlock vault")
        sub.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Master Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setMinimumHeight(45)
        self.pwd.returnPressed.connect(self._login)
        
        self.vis = QPushButton(ICO_VIEW)
        self.vis.setObjectName("iconBtn")
        self.vis.setToolTip("Show password")
        self.vis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vis.clicked.connect(lambda: (
            self.pwd.setEchoMode(QLineEdit.EchoMode.Normal if self.pwd.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password),
            self.vis.setText(ICO_HIDE if self.pwd.echoMode() == QLineEdit.EchoMode.Normal else ICO_VIEW)
        ))
        
        pw_lay = QHBoxLayout()
        pw_lay.setContentsMargins(0, 0, 0, 0)
        pw_lay.addWidget(self.pwd)
        pw_lay.addWidget(self.vis)

        btn = QPushButton(f"{ICO_SHOW}  Unlock Vault")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._login)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #ff5555; font-size: 13px;")
        self.err.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (title, sub):
            vb.addWidget(w)
        vb.addSpacing(10)
        vb.addLayout(pw_lay)
        for w in (btn, self.err):
            vb.addWidget(w)
        layout.addWidget(box)

    def _login(self):
        p = self.pwd.text()
        if not p:
            self.err.setText("Password cannot be empty")
            return
        if self.backend.verify_master_password(p):
            if self.backend.is_2fa_enabled():
                d = TwoFactorVerifyDialog(self.backend, self)
                if d.exec() != QDialog.DialogCode.Accepted:
                    self.err.setText("2FA verification canceled")
                    return
            self.err.setText("")
            self.pwd.clear()
            self.on_success()
        else:
            self.err.setText("Invalid master password")
            self.pwd.selectAll()


# ─── Setup Screen ─────────────────────────────────────────────────────
class SetupWidget(QWidget):
    def __init__(self, backend, on_success):
        super().__init__()
        self.backend = backend
        self.on_success = on_success
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("authBox")
        box.setStyleSheet(
            "#authBox { background-color: #1e1e1e; border-radius: 12px; border: 1px solid #333; }"
        )
        vb = QVBoxLayout(box)
        vb.setContentsMargins(40, 40, 40, 40)
        vb.setSpacing(15)

        title = QLabel(f"{ICO_ROCKET} First Time Setup")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        warn = QLabel("Create a strong master password.\nIf you lose it, your data cannot be recovered!")
        warn.setStyleSheet("color: #ffaa00; font-size: 14px; font-weight: bold;")
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Create Master Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setMinimumHeight(45)

        self.conf = QLineEdit()
        self.conf.setPlaceholderText("Confirm Master Password")
        self.conf.setEchoMode(QLineEdit.EchoMode.Password)
        self.conf.setMinimumHeight(45)
        
        self.vis = QPushButton(ICO_VIEW)
        self.vis.setObjectName("iconBtn")
        self.vis.setToolTip("Show password")
        self.vis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vis.clicked.connect(lambda: (
            self.pwd.setEchoMode(QLineEdit.EchoMode.Normal if self.pwd.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password),
            self.conf.setEchoMode(QLineEdit.EchoMode.Normal if self.conf.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password),
            self.vis.setText(ICO_HIDE if self.pwd.echoMode() == QLineEdit.EchoMode.Normal else ICO_VIEW)
        ))
        
        pw_lay = QHBoxLayout()
        pw_lay.setContentsMargins(0, 0, 0, 0)
        pw_lay.addWidget(self.pwd)
        pw_lay.addWidget(self.vis)

        btn = QPushButton("Create Vault")
        btn.setMinimumHeight(45)
        btn.clicked.connect(self._setup)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #ff5555; font-size: 13px;")
        self.err.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (title, warn):
            vb.addWidget(w)
        vb.addSpacing(10)
        vb.addLayout(pw_lay)
        for w in (self.conf, btn, self.err):
            vb.addWidget(w)
        layout.addWidget(box)

    def _setup(self):
        p, c = self.pwd.text(), self.conf.text()
        if len(p) < 8:
            self.err.setText("Password must be at least 8 characters")
            return
        if p != c:
            self.err.setText("Passwords do not match")
            return
        if self.backend.create_master_password(p):
            self.pwd.clear()
            self.conf.clear()
            self.err.setText("")
            self.on_success()
        else:
            self.err.setText("Setup failed. Database error.")


# ─── Passwords Tab ────────────────────────────────────────────────────
class PasswordsTab(QWidget):
    def __init__(self, backend, show_passwords_default=False):
        super().__init__()
        self.backend = backend
        self.passwords_visible = show_passwords_default
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(15)

        tb = QHBoxLayout()
        title = QLabel("Saved Passwords")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")

        add = QPushButton(f"{ICO_ADD}  Add Password")
        add.clicked.connect(self._add_dialog)

        ref = QPushButton(f"{ICO_REFRESH}")
        ref.setObjectName("secondaryBtn")
        ref.setToolTip("Refresh")
        ref.clicked.connect(lambda: self.load_data())

        tb.addWidget(title)
        tb.addStretch()
        tb.addWidget(ref)
        tb.addWidget(add)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["App / Website", "Username", "Actions", ""])
        self.table.setColumnHidden(3, True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 170)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            entries = (self.backend.search_vault(q)['passwords'] if q
                       else self.backend.get_all_passwords())
            self.table.setRowCount(len(entries))
            for i, p in enumerate(entries):
                item0 = QTableWidgetItem(p['app_name'])
                item0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 0, item0)
                item1 = QTableWidgetItem(p['username'])
                item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 1, item1)
                self.table.setItem(i, 3, QTableWidgetItem(str(p['id'])))

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)
                hl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                b_copy = QPushButton(ICO_COPY)
                b_copy.setObjectName("iconBtn")
                b_copy.setToolTip("Copy password")
                b_copy.setCursor(Qt.CursorShape.PointingHandCursor)
                b_copy.clicked.connect(lambda _, pid=p['id']: self._copy(pid))
                b_copy.setFixedSize(32, 32)

                b_show = QPushButton(ICO_VIEW)
                b_show.setObjectName("iconBtn")
                b_show.setToolTip("Show / hide password")
                b_show.setCursor(Qt.CursorShape.PointingHandCursor)
                b_show.clicked.connect(lambda _, pid=p['id'], btn=b_show, row=i: self._toggle_show(pid, btn, row))
                b_show.setFixedSize(32, 32)

                b_edit = QPushButton(ICO_NOTES)
                b_edit.setObjectName("iconBtn")
                b_edit.setToolTip("Edit entry")
                b_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                b_edit.clicked.connect(lambda _, pid=p['id']: self._edit_dialog(pid))
                b_edit.setFixedSize(32, 32)

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, pid=p['id']: self._delete(pid))
                b_del.setFixedSize(32, 32)

                hl.addWidget(b_copy)
                hl.addWidget(b_show)
                hl.addWidget(b_edit)
                hl.addWidget(b_del)
                self.table.setCellWidget(i, 2, w)
            self.table.resizeRowsToContents()
        except Exception as e:
            print("Password load error:", e)

    def _copy(self, pid):
        try:
            pyperclip.copy(self.backend.get_password(pid))
            show_toast(self, "Password copied!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _toggle_show(self, pid, btn, row):
        col_user = self.table.item(row, 1)
        if col_user is None:
            return
        current_tooltip = btn.toolTip()
        if "Show" in current_tooltip:
            try:
                pwd_text = self.backend.get_password(pid)
                # Show password by temporarily placing it in a tooltip-like way
                # in the username column suffix
                original_user = col_user.text()
                if " \u2502 " not in original_user:
                    col_user.setText(f"{original_user} \u2502 {pwd_text}")
                btn.setText(ICO_HIDE)
                btn.setToolTip("Hide password")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        else:
            txt = col_user.text()
            if " \u2502 " in txt:
                col_user.setText(txt.split(" \u2502 ")[0])
            btn.setText(ICO_VIEW)
            btn.setToolTip("Show / hide password")

    def _delete(self, pid):
        if QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this password?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.backend.delete_password(pid)
            self.load_data()

    def _add_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add Password")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(420, 260)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)
        QLabel("New Password Entry").setParent(d)
        t = QLabel("New Password Entry")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        form = QFormLayout()
        app_in = QLineEdit()
        usr_in = QLineEdit()
        pwd_in = QLineEdit()
        pwd_in.setEchoMode(QLineEdit.EchoMode.Password)

        gen = QPushButton(ICO_DICE)
        gen.setObjectName("secondaryBtn")
        gen.setToolTip("Generate random password")
        gen.clicked.connect(lambda: pwd_in.setText(self.backend.generate_password()))

        vis = QPushButton(ICO_VIEW)
        vis.setObjectName("iconBtn")
        vis.setToolTip("Show password")
        vis.clicked.connect(lambda: (
            pwd_in.setEchoMode(QLineEdit.EchoMode.Normal if pwd_in.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password),
            vis.setText(ICO_HIDE if pwd_in.echoMode() == QLineEdit.EchoMode.Normal else ICO_VIEW)
        ))

        pw = QHBoxLayout()
        pw.addWidget(pwd_in)
        pw.addWidget(vis)
        pw.addWidget(gen)

        form.addRow("App / Website:", app_in)
        form.addRow("Username:", usr_in)
        form.addRow("Password:", pw)

        btns = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addLayout(form)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            a, u, p = app_in.text().strip(), usr_in.text().strip(), pwd_in.text()
            if a and u and p:
                self.backend.add_password(a, u, p)
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", "All fields are required!")

    def _edit_dialog(self, pid):
        try:
            entry = self.backend.get_password_entry(pid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        d = QDialog(self)
        d.setWindowTitle("Edit Password")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(420, 260)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("Edit Password Entry")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        form = QFormLayout()
        app_in = QLineEdit(entry['app_name'])
        usr_in = QLineEdit(entry['username'])
        pwd_in = QLineEdit(entry['password'])
        pwd_in.setEchoMode(QLineEdit.EchoMode.Password)

        gen = QPushButton(ICO_DICE)
        gen.setObjectName("secondaryBtn")
        gen.setToolTip("Generate random password")
        gen.clicked.connect(lambda: pwd_in.setText(self.backend.generate_password()))

        vis = QPushButton(ICO_VIEW)
        vis.setObjectName("iconBtn")
        vis.setToolTip("Show password")
        vis.clicked.connect(lambda: (
            pwd_in.setEchoMode(QLineEdit.EchoMode.Normal if pwd_in.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password),
            vis.setText(ICO_HIDE if pwd_in.echoMode() == QLineEdit.EchoMode.Normal else ICO_VIEW)
        ))
        vis.setFixedSize(32, 32)

        pw = QHBoxLayout()
        pw.addWidget(pwd_in)
        pw.addWidget(vis)
        pw.addWidget(gen)

        form.addRow("App / Website:", app_in)
        form.addRow("Username:", usr_in)
        form.addRow("Password:", pw)

        btns = QHBoxLayout()
        save = QPushButton("Save Changes")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addLayout(form)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            a, u, p = app_in.text().strip(), usr_in.text().strip(), pwd_in.text()
            if a and u and p:
                self.backend.update_password(pid, a, u, p)
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", "All fields are required!")


# ─── Cards Tab ────────────────────────────────────────────────────────
class CardsTab(QWidget):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(15)

        tb = QHBoxLayout()
        title = QLabel("Credit Cards")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")

        add = QPushButton(f"{ICO_ADD}  Add Card")
        add.clicked.connect(self._add_dialog)

        ref = QPushButton(f"{ICO_REFRESH}")
        ref.setObjectName("secondaryBtn")
        ref.setToolTip("Refresh")
        ref.clicked.connect(lambda: self.load_data())

        tb.addWidget(title)
        tb.addStretch()
        tb.addWidget(ref)
        tb.addWidget(add)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Label / Bank", "Cardholder", "Actions"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            cards = (self.backend.search_vault(q)['cards'] if q
                     else self.backend.get_all_cards())
            self.table.setRowCount(len(cards))
            for i, c in enumerate(cards):
                item0 = QTableWidgetItem(c['label'])
                item0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 0, item0)
                item1 = QTableWidgetItem(c['holder_name'])
                item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 1, item1)

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)
                hl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                b_view = QPushButton(ICO_VIEW)
                b_view.setObjectName("iconBtn")
                b_view.setToolTip("View card details")
                b_view.setCursor(Qt.CursorShape.PointingHandCursor)
                b_view.clicked.connect(lambda _, cid=c['id']: self._view_card(cid))
                b_view.setFixedSize(32, 32)

                b_edit = QPushButton(ICO_NOTES)
                b_edit.setObjectName("iconBtn")
                b_edit.setToolTip("Edit card")
                b_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                b_edit.clicked.connect(lambda _, cid=c['id']: self._edit_dialog(cid))
                b_edit.setFixedSize(32, 32)

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, cid=c['id']: self._del(cid))
                b_del.setFixedSize(32, 32)

                hl.addWidget(b_view)
                hl.addWidget(b_edit)
                hl.addWidget(b_del)
                self.table.setCellWidget(i, 2, w)
            self.table.resizeRowsToContents()
        except Exception as e:
            print("Card load error:", e)

    def _view_card(self, cid):
        """Open a detailed card dialog with individual copy buttons per field."""
        try:
            c = self.backend.get_card_details(cid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        d = QDialog(self)
        d.setWindowTitle(f"Card: {c['label']}")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(440, 320)
        lay = QVBoxLayout(d)
        lay.setSpacing(12)

        header = QLabel(f"{ICO_CARD}  {c['label']}")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #0078D4;")
        lay.addWidget(header)

        fields = [
            ("Cardholder", c['holder_name']),
            ("Card Number", c['card_number']),
            ("Expiry", c['expiry']),
            ("CVV", c['cvv']),
        ]
        if c.get('pin'):
            fields.append(("PIN", c['pin']))

        for label, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("color: #a0a0a0; font-size: 13px; min-width: 100px;")
            val = QLineEdit(value)
            val.setReadOnly(True)
            val.setStyleSheet("background-color: #252525; border: 1px solid #333; border-radius: 4px; padding: 6px; color: white;")

            cp = QPushButton(ICO_COPY)
            cp.setObjectName("iconBtn")
            cp.setToolTip(f"Copy {label}")
            cp.setCursor(Qt.CursorShape.PointingHandCursor)
            cp.clicked.connect(lambda _, v=value, l=label: (
                pyperclip.copy(v),
                show_toast(self, f"{l} copied!")
            ))
            cp.setFixedSize(32, 32)

            row.addWidget(lbl)
            row.addWidget(val, 1)
            row.addWidget(cp)
            lay.addLayout(row)

        close = QPushButton("Close")
        close.setObjectName("secondaryBtn")
        close.clicked.connect(d.accept)
        lay.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        d.exec()

    def _del(self, cid):
        if QMessageBox.question(
            self, "Confirm Delete", "Delete this credit card?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.backend.delete_card(cid)
            self.load_data()

    def _add_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add Credit Card")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(420, 360)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("New Credit Card")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        form = QFormLayout()
        label_in = QLineEdit()
        holder_in = QLineEdit()
        num_in = QLineEdit()
        num_in.setPlaceholderText("16 digits")
        num_in.setMaxLength(16)
        num_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,16}$")))
        
        exp_in = QLineEdit()
        exp_in.setPlaceholderText("MM/YY")
        exp_in.setMaxLength(5)
        # Allows entering MM followed by / and YY
        exp_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^(0[1-9]|1[0-2])/?([0-9]{0,2})$")))
        
        cvv_in = QLineEdit()
        cvv_in.setEchoMode(QLineEdit.EchoMode.Password)
        cvv_in.setPlaceholderText("3 or 4 digits")
        cvv_in.setMaxLength(4)
        cvv_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$")))
        
        pin_in = QLineEdit()
        pin_in.setEchoMode(QLineEdit.EchoMode.Password)
        pin_in.setPlaceholderText("4 digits (Optional)")
        pin_in.setMaxLength(4)
        pin_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$")))

        form.addRow("Label:", label_in)
        form.addRow("Cardholder:", holder_in)
        form.addRow("Card Number:", num_in)
        form.addRow("Expiry:", exp_in)
        form.addRow("CVV:", cvv_in)
        form.addRow("PIN:", pin_in)

        btns = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addLayout(form)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            num = num_in.text()
            cvv = cvv_in.text()
            pin = pin_in.text()
            if not label_in.text() or not num:
                QMessageBox.warning(self, "Error", "Label and Card Number are required!")
                return
            if len(num) < 13:
                QMessageBox.warning(self, "Error", "Card Number must be at least 13 digits!")
                return
            if cvv and len(cvv) < 3:
                QMessageBox.warning(self, "Error", "CVV must be 3 or 4 digits!")
                return
            if pin and len(pin) < 4:
                QMessageBox.warning(self, "Error", "PIN must be 4 digits!")
                return
                
            self.backend.add_card(
                label_in.text(), holder_in.text(), num,
                exp_in.text(), cvv, pin
            )
            self.load_data()

    def _edit_dialog(self, cid):
        try:
            c = self.backend.get_card_details(cid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        d = QDialog(self)
        d.setWindowTitle("Edit Card")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(440, 380)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("Edit Card Entry")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        form = QFormLayout()
        label_in = QLineEdit(c['label'])
        holder_in = QLineEdit(c['holder_name'])

        num_in = QLineEdit(c['card_number'])
        num_in.setMaxLength(16)
        num_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,16}$")))

        exp_in = QLineEdit(c['expiry'])
        exp_in.setPlaceholderText("MM/YY")
        exp_in.setMaxLength(5)
        exp_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^(0[1-9]|1[0-2])/?([0-9]{0,2})$")))

        cvv_in = QLineEdit(c['cvv'])
        cvv_in.setEchoMode(QLineEdit.EchoMode.Password)
        cvv_in.setPlaceholderText("3 or 4 digits")
        cvv_in.setMaxLength(4)
        cvv_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$")))

        pin_in = QLineEdit(c.get('pin', ''))
        pin_in.setEchoMode(QLineEdit.EchoMode.Password)
        pin_in.setPlaceholderText("4 digits (Optional)")
        pin_in.setMaxLength(4)
        pin_in.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$")))

        form.addRow("Label:", label_in)
        form.addRow("Cardholder:", holder_in)
        form.addRow("Card Number:", num_in)
        form.addRow("Expiry:", exp_in)
        form.addRow("CVV:", cvv_in)
        form.addRow("PIN:", pin_in)

        btns = QHBoxLayout()
        save = QPushButton("Save Changes")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addLayout(form)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            num = num_in.text()
            cvv = cvv_in.text()
            pin = pin_in.text()
            if not label_in.text() or not num:
                QMessageBox.warning(self, "Error", "Label and Card Number are required!")
                return
            if len(num) < 13:
                QMessageBox.warning(self, "Error", "Card Number must be at least 13 digits!")
                return
            if cvv and len(cvv) < 3:
                QMessageBox.warning(self, "Error", "CVV must be 3 or 4 digits!")
                return
            if pin and len(pin) < 4:
                QMessageBox.warning(self, "Error", "PIN must be 4 digits!")
                return

            self.backend.update_card(
                cid,
                label_in.text(), holder_in.text(), num,
                exp_in.text(), cvv, pin
            )
            self.load_data()


# ─── .env Files Tab ──────────────────────────────────────────────────
class EnvFilesTab(QWidget):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(15)

        tb = QHBoxLayout()
        title = QLabel(".env Files")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")

        add = QPushButton(f"{ICO_ADD}  Add .env")
        add.clicked.connect(self._add_dialog)

        ref = QPushButton(f"{ICO_REFRESH}")
        ref.setObjectName("secondaryBtn")
        ref.setToolTip("Refresh")
        ref.clicked.connect(lambda: self.load_data())

        tb.addWidget(title)
        tb.addStretch()
        tb.addWidget(ref)
        tb.addWidget(add)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["File Label", "Actions"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 140)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            entries = (self.backend.search_vault(q)['env_files'] if q
                       else self.backend.get_all_env_files())
            self.table.setRowCount(len(entries))
            for i, e in enumerate(entries):
                item0 = QTableWidgetItem(e['label'])
                item0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 0, item0)

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)
                hl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                b_view = QPushButton(ICO_VIEW)
                b_view.setObjectName("iconBtn")
                b_view.setToolTip("View .env content")
                b_view.setCursor(Qt.CursorShape.PointingHandCursor)
                b_view.clicked.connect(lambda _, eid=e['id']: self._view(eid))
                b_view.setFixedSize(32, 32)

                b_edit = QPushButton(ICO_NOTES)
                b_edit.setObjectName("iconBtn")
                b_edit.setToolTip("Edit .env file")
                b_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                b_edit.clicked.connect(lambda _, eid=e['id']: self._edit_dialog(eid))
                b_edit.setFixedSize(32, 32)

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, eid=e['id']: self._del(eid))
                b_del.setFixedSize(32, 32)

                hl.addWidget(b_view)
                hl.addWidget(b_edit)
                hl.addWidget(b_del)
                self.table.setCellWidget(i, 1, w)
            self.table.resizeRowsToContents()
        except Exception as e:
            print(".env load error:", e)

    def _view(self, env_id):
        try:
            env_entry = self.backend.get_env_file_content(env_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        d = QDialog(self)
        d.setWindowTitle(f".env: {env_entry['label']}")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(620, 450)
        lay = QVBoxLayout(d)
        lay.setSpacing(12)

        t = QLabel(f"{ICO_ENV}  {env_entry['label']}")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D4;")
        lay.addWidget(t)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setPlainText(env_entry['content'])
        lay.addWidget(content)

        btns = QHBoxLayout()
        copy_btn = QPushButton(f"{ICO_COPY}  Copy All")
        copy_btn.setObjectName("secondaryBtn")
        copy_btn.clicked.connect(lambda: (pyperclip.copy(env_entry['content']), show_toast(self, ".env content copied!")))

        close = QPushButton("Close")
        close.clicked.connect(d.accept)

        btns.addWidget(copy_btn)
        btns.addStretch()
        btns.addWidget(close)
        lay.addLayout(btns)

        d.exec()

    def _del(self, env_id):
        if QMessageBox.question(
            self, "Confirm Delete", "Delete this .env entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.backend.delete_env_file(env_id)
            self.load_data()

    def _load_env_file(self, editor_widget: QTextEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Select .env File", "", "Env Files (*.env);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                editor_widget.setPlainText(f.read())
            show_toast(self, "Loaded .env file")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _add_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add .env File")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(620, 450)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("New .env File")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        form = QFormLayout()
        label_in = QLineEdit()
        label_in.setPlaceholderText("e.g. Production API")
        content_in = QTextEdit()
        content_in.setPlaceholderText("API_KEY=...\nDATABASE_URL=...\nDEBUG=false")

        form.addRow("Label:", label_in)
        form.addRow("Content:", content_in)

        btns = QHBoxLayout()
        load_btn = QPushButton(f"{ICO_UPLOAD}  Load .env File")
        load_btn.setObjectName("secondaryBtn")
        load_btn.clicked.connect(lambda: self._load_env_file(content_in))

        save = QPushButton("Save")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)

        btns.addWidget(load_btn)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addLayout(form)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            label = label_in.text().strip()
            content = content_in.toPlainText()
            if not label:
                QMessageBox.warning(self, "Error", "Label is required!")
                return
            if not content.strip():
                QMessageBox.warning(self, "Error", ".env content cannot be empty!")
                return
            self.backend.add_env_file(label, content)
            self.load_data()

    def _edit_dialog(self, env_id):
        try:
            env_entry = self.backend.get_env_file_content(env_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        d = QDialog(self)
        d.setWindowTitle("Edit .env File")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(620, 450)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("Edit .env File")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        form = QFormLayout()
        label_in = QLineEdit(env_entry['label'])
        content_in = QTextEdit()
        content_in.setPlainText(env_entry['content'])

        form.addRow("Label:", label_in)
        form.addRow("Content:", content_in)

        btns = QHBoxLayout()
        load_btn = QPushButton(f"{ICO_UPLOAD}  Load .env File")
        load_btn.setObjectName("secondaryBtn")
        load_btn.clicked.connect(lambda: self._load_env_file(content_in))

        save = QPushButton("Save Changes")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)

        btns.addWidget(load_btn)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addLayout(form)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            label = label_in.text().strip()
            content = content_in.toPlainText()
            if not label:
                QMessageBox.warning(self, "Error", "Label is required!")
                return
            if not content.strip():
                QMessageBox.warning(self, "Error", ".env content cannot be empty!")
                return
            self.backend.update_env_file(env_id, label, content)
            self.load_data()


# ─── Notes Tab ────────────────────────────────────────────────────────
class NotesTab(QWidget):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(15)

        tb = QHBoxLayout()
        title = QLabel("Secret Notes")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")

        add = QPushButton(f"{ICO_ADD}  Add Note")
        add.clicked.connect(self._add_dialog)

        ref = QPushButton(f"{ICO_REFRESH}")
        ref.setObjectName("secondaryBtn")
        ref.setToolTip("Refresh")
        ref.clicked.connect(lambda: self.load_data())

        tb.addWidget(title)
        tb.addStretch()
        tb.addWidget(ref)
        tb.addWidget(add)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Title", "Actions"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 140)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            notes = (self.backend.search_vault(q)['notes'] if q
                     else self.backend.get_all_notes())
            self.table.setRowCount(len(notes))
            for i, n in enumerate(notes):
                item0 = QTableWidgetItem(n['title'])
                item0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 0, item0)

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)
                hl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                b_read = QPushButton(ICO_READ)
                b_read.setObjectName("iconBtn")
                b_read.setToolTip("Read note")
                b_read.setCursor(Qt.CursorShape.PointingHandCursor)
                b_read.clicked.connect(lambda _, nid=n['id']: self._view(nid))
                b_read.setFixedSize(32, 32)

                b_edit = QPushButton(ICO_NOTES)
                b_edit.setObjectName("iconBtn")
                b_edit.setToolTip("Edit note")
                b_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                b_edit.clicked.connect(lambda _, nid=n['id']: self._edit_dialog(nid))
                b_edit.setFixedSize(32, 32)

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, nid=n['id']: self._del(nid))
                b_del.setFixedSize(32, 32)

                hl.addWidget(b_read)
                hl.addWidget(b_edit)
                hl.addWidget(b_del)
                self.table.setCellWidget(i, 1, w)
            self.table.resizeRowsToContents()
        except Exception as e:
            print("Note load error:", e)

    def _view(self, nid):
        try:
            n = self.backend.get_note_content(nid)
            d = QDialog(self)
            d.setWindowTitle(f"Note: {n['title']}")
            d.setWindowFlags(
                d.windowFlags() |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowMaximizeButtonHint
            )
            d.setMinimumSize(500, 400)
            lay = QVBoxLayout(d)
            t = QLabel(n['title'])
            t.setStyleSheet("font-size: 20px; font-weight: bold;")
            cv = QTextEdit()
            cv.setReadOnly(True)
            cv.setPlainText(n['content'])
            close = QPushButton("Close")
            close.clicked.connect(d.accept)
            lay.addWidget(t)
            lay.addWidget(cv)
            lay.addWidget(close)
            d.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _del(self, nid):
        if QMessageBox.question(
            self, "Confirm Delete", "Delete this note?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.backend.delete_note(nid)
            self.load_data()

    def _add_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add Secret Note")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(500, 400)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("New Secret Note")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        title_in = QLineEdit()
        title_in.setPlaceholderText("Title")
        content_in = QTextEdit()
        content_in.setPlaceholderText("Write your secret notes here. Everything is encrypted...")

        btns = QHBoxLayout()
        save = QPushButton("Save Note")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addWidget(title_in)
        lay.addWidget(content_in)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            if not title_in.text():
                QMessageBox.warning(self, "Error", "Title cannot be empty!")
                return
            self.backend.add_note(title_in.text(), content_in.toPlainText())
            self.load_data()

    def _edit_dialog(self, nid):
        try:
            n = self.backend.get_note_content(nid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        d = QDialog(self)
        d.setWindowTitle("Edit Secret Note")
        d.setWindowFlags(
            d.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        d.setMinimumSize(500, 400)
        lay = QVBoxLayout(d)
        lay.setSpacing(15)

        t = QLabel("Edit Secret Note")
        t.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(t)

        title_in = QLineEdit(n['title'])
        content_in = QTextEdit()
        content_in.setPlainText(n['content'])

        btns = QHBoxLayout()
        save = QPushButton("Save Changes")
        save.clicked.connect(d.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(d.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)

        lay.addWidget(title_in)
        lay.addWidget(content_in)
        lay.addLayout(btns)

        if d.exec() == QDialog.DialogCode.Accepted:
            if not title_in.text():
                QMessageBox.warning(self, "Error", "Title cannot be empty!")
                return
            self.backend.update_note(nid, title_in.text(), content_in.toPlainText())
            self.load_data()


# ─── Settings Tab ─────────────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self, backend, main_window):
        super().__init__()
        self.backend = backend
        self.main_window = main_window
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(20)

        title = QLabel(f"{ICO_SETTINGS}  Settings & Tools")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        lay.addWidget(title)

        # ── Manual Password Analyzer ──
        analyzer_grp = QGroupBox("Password Analyzer")
        alay = QVBoxLayout(analyzer_grp)

        analyzer_hint = QLabel("Check a password before saving it. The password stays local and is never exported.")
        analyzer_hint.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        analyzer_hint.setWordWrap(True)

        analyzer_row = QHBoxLayout()
        self.analyzer_input = QLineEdit()
        self.analyzer_input.setPlaceholderText("Type a password to analyze")
        self.analyzer_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.analyzer_input.setMinimumHeight(36)

        self.analyzer_toggle = QPushButton(ICO_VIEW)
        self.analyzer_toggle.setObjectName("iconBtn")
        self.analyzer_toggle.setToolTip("Show password")
        self.analyzer_toggle.clicked.connect(self._toggle_analyzer_visibility)

        analyze_btn = QPushButton(f"{ICO_SEARCH}  Analyze")
        analyze_btn.setMinimumHeight(36)
        analyze_btn.clicked.connect(self._analyze_custom_password)

        analyzer_row.addWidget(self.analyzer_input, 1)
        analyzer_row.addWidget(self.analyzer_toggle)
        analyzer_row.addWidget(analyze_btn)

        self.analyzer_score = QLabel("No analysis yet.")
        self.analyzer_score.setStyleSheet("font-size: 13px; color: #a0a0a0;")
        self.analyzer_feedback = QLabel("")
        self.analyzer_feedback.setStyleSheet("font-size: 12px; color: #d0d0d0;")
        self.analyzer_feedback.setWordWrap(True)

        alay.addWidget(analyzer_hint)
        alay.addLayout(analyzer_row)
        alay.addWidget(self.analyzer_score)
        alay.addWidget(self.analyzer_feedback)
        lay.addWidget(analyzer_grp)

        # ── Password Health ──
        health_grp = QGroupBox("Password Health Check")
        hlay = QVBoxLayout(health_grp)

        health_hint = QLabel("Runs a full scan for weak, reused, and commonly breached passwords.")
        health_hint.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        health_hint.setWordWrap(True)

        scan_btn = QPushButton(f"{ICO_SEARCH}  Run Security Scan")
        scan_btn.setMinimumHeight(40)
        scan_btn.clicked.connect(self._run_scan)
        hlay.addWidget(health_hint)
        hlay.addWidget(scan_btn)

        self.scan_result = QWidget()
        self.scan_result_lay = QVBoxLayout(self.scan_result)
        self.scan_result_lay.setContentsMargins(0, 0, 0, 0)
        hlay.addWidget(self.scan_result)
        lay.addWidget(health_grp)

        # ── Backup & Restore ──
        backup_grp = QGroupBox("Backup & Restore")
        blay = QVBoxLayout(backup_grp)

        brow = QHBoxLayout()
        backup_btn = QPushButton(f"{ICO_SAVE}  Backup Vault")
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self._backup)

        restore_btn = QPushButton(f"{ICO_REFRESH}  Restore Vault")
        restore_btn.setObjectName("secondaryBtn")
        restore_btn.setMinimumHeight(40)
        restore_btn.clicked.connect(self._restore)

        brow.addWidget(backup_btn)
        brow.addWidget(restore_btn)
        blay.addLayout(brow)
        lay.addWidget(backup_grp)

        # ── Import / Export ──
        ie_grp = QGroupBox("Import / Export")
        ielay = QVBoxLayout(ie_grp)

        ierow = QHBoxLayout()
        export_btn = QPushButton(f"{ICO_UPLOAD}  Export as JSON")
        export_btn.setMinimumHeight(40)
        export_btn.clicked.connect(self._export_json)

        export_enc_btn = QPushButton(f"{ICO_HIDE}  Export Encrypted Report")
        export_enc_btn.setObjectName("secondaryBtn")
        export_enc_btn.setMinimumHeight(40)
        export_enc_btn.clicked.connect(self._export_encrypted)

        ierow.addWidget(export_btn)
        ierow.addWidget(export_enc_btn)
        ielay.addLayout(ierow)
        lay.addWidget(ie_grp)

        # ── Two-Factor Authentication ──
        twofa_grp = QGroupBox("Two-Factor Authentication (2FA)")
        tlay = QVBoxLayout(twofa_grp)

        self.twofa_status = QLabel("")
        self.twofa_status.setStyleSheet("color: #a0a0a0; font-size: 12px;")

        self.twofa_enable_btn = QPushButton("")
        self.twofa_enable_btn.setMinimumHeight(40)
        self.twofa_enable_btn.clicked.connect(self._toggle_2fa)

        self.twofa_show_btn = QPushButton("Show Setup Key")
        self.twofa_show_btn.setObjectName("secondaryBtn")
        self.twofa_show_btn.setMinimumHeight(36)
        self.twofa_show_btn.clicked.connect(self._show_2fa_info)

        tlay.addWidget(self.twofa_status)
        tlay.addWidget(self.twofa_enable_btn)
        tlay.addWidget(self.twofa_show_btn)
        # ── Password Generator ──
        gen_grp = QGroupBox("Password Generator Preferences")
        gen_lay = QVBoxLayout(gen_grp)
        gen_lay.setSpacing(12)

        gen_hint = QLabel("Customize the default options for generating cryptographically secure passwords.")
        gen_hint.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        gen_hint.setWordWrap(True)
        gen_lay.addWidget(gen_hint)

        len_row = QHBoxLayout()
        len_lbl = QLabel("Password Length:")
        len_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: white;")
        
        self.len_slider = QSlider(Qt.Orientation.Horizontal)
        self.len_slider.setRange(6, 64)
        self.len_slider.setSingleStep(1)
        self.len_slider.setPageStep(4)
        
        self.len_spin = QSpinBox()
        self.len_spin.setRange(6, 64)
        self.len_spin.setSingleStep(1)
        self.len_spin.setMinimumHeight(30)
        self.len_spin.setStyleSheet("QSpinBox { background-color: #1a1a2e; color: white; border: 1px solid #333; border-radius: 4px; padding: 2px 4px; }")

        self.len_slider.valueChanged.connect(self.len_spin.setValue)
        self.len_spin.valueChanged.connect(self.len_slider.setValue)

        len_row.addWidget(len_lbl)
        len_row.addWidget(self.len_slider, 1)
        len_row.addWidget(self.len_spin)
        gen_lay.addLayout(len_row)

        chk_grid = QGridLayout()
        chk_grid.setSpacing(10)

        self.chk_upper = QCheckBox("Include Uppercase Letters (A-Z)")
        self.chk_lower = QCheckBox("Include Lowercase Letters (a-z)")
        self.chk_digits = QCheckBox("Include Numbers (0-9)")
        self.chk_symbols = QCheckBox("Include Symbols (!@#$...?)")

        chk_grid.addWidget(self.chk_upper, 0, 0)
        chk_grid.addWidget(self.chk_lower, 0, 1)
        chk_grid.addWidget(self.chk_digits, 1, 0)
        chk_grid.addWidget(self.chk_symbols, 1, 1)
        gen_lay.addLayout(chk_grid)

        preview_title = QLabel("Live Preview:")
        preview_title.setStyleSheet("font-size: 12px; color: #a0a0a0; margin-top: 4px;")
        gen_lay.addWidget(preview_title)

        preview_row = QHBoxLayout()
        self.preview_in = QLineEdit()
        self.preview_in.setReadOnly(True)
        self.preview_in.setMinimumHeight(36)
        self.preview_in.setStyleSheet("""
            QLineEdit {
                background-color: #111122;
                color: #27ae60;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #27ae6040;
                border-radius: 6px;
                padding-left: 8px;
            }
        """)

        preview_copy = QPushButton(ICO_COPY)
        preview_copy.setObjectName("secondaryBtn")
        preview_copy.setToolTip("Copy preview password")
        preview_copy.setFixedSize(36, 36)
        preview_copy.setStyleSheet("""
            QPushButton {
                font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets";
                font-size: 16px;
            }
        """)
        preview_copy.clicked.connect(self._copy_preview)

        preview_refresh = QPushButton(ICO_REFRESH)
        preview_refresh.setObjectName("secondaryBtn")
        preview_refresh.setToolTip("Regenerate preview")
        preview_refresh.setFixedSize(36, 36)
        preview_refresh.setStyleSheet("""
            QPushButton {
                font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets";
                font-size: 16px;
            }
        """)
        preview_refresh.clicked.connect(self._update_preview)

        preview_row.addWidget(self.preview_in, 1)
        preview_row.addWidget(preview_refresh)
        preview_row.addWidget(preview_copy)
        gen_lay.addLayout(preview_row)

        lay.addWidget(gen_grp)

        # Load initial settings from backend
        try:
            length_val = int(self.backend.get_setting('pwd_gen_length', '16'))
        except ValueError:
            length_val = 16
        upper_val = self.backend.get_setting('pwd_gen_include_uppercase', '1') == '1'
        lower_val = self.backend.get_setting('pwd_gen_include_lowercase', '1') == '1'
        digits_val = self.backend.get_setting('pwd_gen_include_digits', '1') == '1'
        symbols_val = self.backend.get_setting('pwd_gen_include_symbols', '1') == '1'

        self.len_slider.setValue(length_val)
        self.chk_upper.setChecked(upper_val)
        self.chk_lower.setChecked(lower_val)
        self.chk_digits.setChecked(digits_val)
        self.chk_symbols.setChecked(symbols_val)

        # Connect signals
        self.len_slider.valueChanged.connect(self._save_generator_settings)
        self.chk_upper.stateChanged.connect(self._save_generator_settings)
        self.chk_lower.stateChanged.connect(self._save_generator_settings)
        self.chk_digits.stateChanged.connect(self._save_generator_settings)
        self.chk_symbols.stateChanged.connect(self._save_generator_settings)

        self._update_preview()

        # ── Display Preferences ──
        disp_grp = QGroupBox("Display")
        dlay = QVBoxLayout(disp_grp)

        self.vis_btn = QPushButton(f"{ICO_VIEW}  Show Passwords in List")
        self.vis_btn.setObjectName("secondaryBtn")
        self.vis_btn.setMinimumHeight(40)
        self.vis_btn.setCheckable(True)
        self.vis_btn.clicked.connect(self._toggle_visibility)
        dlay.addWidget(self.vis_btn)
        lay.addWidget(disp_grp)

        credit = QLabel('Built by YacineDahmani • <a href="https://github.com/YacineDahmani">github.com/YacineDahmani</a>')
        credit.setStyleSheet("font-size: 11px; color: #8f8f8f; padding-top: 8px;")
        credit.setOpenExternalLinks(False)
        credit.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        lay.addWidget(credit, alignment=Qt.AlignmentFlag.AlignRight)

        lay.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._refresh_2fa_ui()

    def _toggle_analyzer_visibility(self):
        if self.analyzer_input.echoMode() == QLineEdit.EchoMode.Password:
            self.analyzer_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.analyzer_toggle.setText(ICO_HIDE)
            self.analyzer_toggle.setToolTip("Hide password")
        else:
            self.analyzer_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.analyzer_toggle.setText(ICO_VIEW)
            self.analyzer_toggle.setToolTip("Show password")

    def _analyze_custom_password(self):
        pwd = self.analyzer_input.text()
        if not pwd:
            self.analyzer_score.setText("Enter a password to analyze.")
            self.analyzer_score.setStyleSheet("font-size: 13px; color: #ff8c8c;")
            self.analyzer_feedback.setText("")
            return

        result = self.backend.calculate_password_strength(pwd)
        score = result['score']
        rating = result['rating']
        issues = result.get('issues', [])
        recommendations = result.get('recommendations', [])

        if score >= 85:
            color = "#27ae60"
        elif score >= 65:
            color = "#f39c12"
        else:
            color = "#e74c3c"

        self.analyzer_score.setText(f"Score: {score}/100 • {rating}")
        self.analyzer_score.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")

        lines = []
        if issues:
            lines.append("Issues: " + "; ".join(issues[:4]))
        if recommendations:
            lines.append("Tips: " + " ".join(recommendations[:3]))
        if not lines:
            lines.append("Looks strong. Keep using unique passwords per account.")
        self.analyzer_feedback.setText("\n".join(lines))

    def _make_stat_card(self, value, label, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a2e;
                border: 1px solid {color}40;
                border-radius: 10px;
                padding: 8px;
            }}
        """)
        vb = QVBoxLayout(card)
        vb.setContentsMargins(12, 10, 12, 10)
        vb.setSpacing(2)
        val = QLabel(str(value))
        val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color}; background: transparent;")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(val)
        vb.addWidget(lbl)
        return card

    def _make_issue_card(self, icon, title, subtitle, accent_color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a2e;
                border-left: 3px solid {accent_color};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        hl = QHBoxLayout(card)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)
        ico = QLabel(icon)
        ico.setStyleSheet(f"font-size: 18px; color: {accent_color}; background: transparent;")
        ico.setFixedWidth(24)
        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {accent_color}; background: transparent;")
        s = QLabel(subtitle)
        s.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
        s.setWordWrap(True)
        text_lay.addWidget(t)
        text_lay.addWidget(s)
        hl.addWidget(ico)
        hl.addLayout(text_lay, 1)
        return card

    def _run_scan(self):
        while self.scan_result_lay.count():
            child = self.scan_result_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        try:
            report = self.backend.run_security_scan()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Scan failed: {e}")
            return

        total = report['total_passwords']
        score = report['overall_score']
        dist = report['strength_distribution']

        # ── Score header with circular-style display ──
        if score >= 80:
            score_color = "#27ae60"
            score_label = "Excellent"
        elif score >= 60:
            score_color = "#f39c12"
            score_label = "Fair"
        else:
            score_color = "#e74c3c"
            score_label = "Needs Work"

        score_frame = QFrame()
        score_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 1px solid {score_color}30;
                border-radius: 12px;
            }}
        """)
        sf_lay = QHBoxLayout(score_frame)
        sf_lay.setContentsMargins(20, 16, 20, 16)
        sf_lay.setSpacing(16)

        score_num = QLabel(f"{int(score)}")
        score_num.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {score_color}; background: transparent;")
        score_num.setFixedWidth(80)
        score_num.setAlignment(Qt.AlignmentFlag.AlignCenter)

        score_details = QVBoxLayout()
        score_details.setSpacing(4)
        score_title = QLabel(f"Security Score  \u2022  {score_label}")
        score_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {score_color}; background: transparent;")
        score_sub = QLabel(f"{total} password{'s' if total != 1 else ''} analyzed")
        score_sub.setStyleSheet("font-size: 12px; color: #888; background: transparent;")

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(score))
        bar.setFixedHeight(8)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #252530; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {score_color}; border-radius: 4px; }}
        """)

        score_details.addWidget(score_title)
        score_details.addWidget(bar)
        score_details.addWidget(score_sub)
        sf_lay.addWidget(score_num)
        sf_lay.addLayout(score_details, 1)
        self.scan_result_lay.addWidget(score_frame)

        # ── Strength distribution stat cards ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        stats_row.addWidget(self._make_stat_card(dist.get('strong', 0), "Strong", "#27ae60"))
        stats_row.addWidget(self._make_stat_card(dist.get('good', 0), "Good", "#2ecc71"))
        stats_row.addWidget(self._make_stat_card(dist.get('fair', 0), "Fair", "#f39c12"))
        stats_row.addWidget(self._make_stat_card(dist.get('weak', 0), "Weak", "#e74c3c"))
        self.scan_result_lay.addLayout(stats_row)

        # ── Issues section ──
        has_issues = report['weak_passwords'] or report['duplicate_groups'] or report['common_passwords']

        if has_issues:
            issues_title = QLabel(f"{ICO_WARN}  Issues Found")
            issues_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ff8855; padding-top: 8px;")
            self.scan_result_lay.addWidget(issues_title)

        if report['weak_passwords']:
            count = len(report['weak_passwords'])
            self.scan_result_lay.addWidget(self._make_issue_card(
                ICO_WARN, f"{count} Weak Password{'s' if count > 1 else ''}",
                "These passwords may be easy to guess or crack.", "#e74c3c"
            ))
            for wp in report['weak_passwords'][:8]:
                issues = ", ".join(wp['issues']) if wp['issues'] else "Low complexity"
                self.scan_result_lay.addWidget(self._make_issue_card(
                    "\u2022", f"{wp['app_name']}  \u2014  {wp['rating']} ({wp['score']}/100)",
                    issues, "#ff8855"
                ))

        if report['duplicate_groups']:
            count = len(report['duplicate_groups'])
            self.scan_result_lay.addWidget(self._make_issue_card(
                ICO_WARN, f"{count} Reused Password Group{'s' if count > 1 else ''}",
                "Using the same password across accounts is risky.", "#f39c12"
            ))
            for group in report['duplicate_groups'][:5]:
                apps = ", ".join(item['app_name'] for item in group[:4])
                extra = "" if len(group) <= 4 else f" +{len(group) - 4} more"
                self.scan_result_lay.addWidget(self._make_issue_card(
                    "\u2022", "Password reused across:", f"{apps}{extra}", "#f39c12"
                ))

        if report['common_passwords']:
            count = len(report['common_passwords'])
            self.scan_result_lay.addWidget(self._make_issue_card(
                ICO_WARN, f"{count} Commonly Breached Password{'s' if count > 1 else ''}",
                "These passwords appear in known breach databases.", "#e74c3c"
            ))
            for cp in report['common_passwords'][:8]:
                self.scan_result_lay.addWidget(self._make_issue_card(
                    "\u2022", cp['app_name'], "Uses a common or easily guessed password.", "#e74c3c"
                ))

        if report['weak_passwords']:
            unique_reco = []
            for item in report['weak_passwords']:
                for reco in item.get('recommendations', []):
                    if reco not in unique_reco:
                        unique_reco.append(reco)
            if unique_reco:
                self.scan_result_lay.addWidget(self._make_issue_card(
                    ICO_CHECK,
                    "Recommended Fixes",
                    " ".join(unique_reco[:4]),
                    "#4da3ff"
                ))

        if not has_issues:
            ok_frame = QFrame()
            ok_frame.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1a2e1a, stop:1 #1a1a2e);
                    border: 1px solid #27ae6040;
                    border-radius: 10px;
                    padding: 16px;
                }
            """)
            ok_lay = QHBoxLayout(ok_frame)
            ok_lay.setContentsMargins(16, 12, 16, 12)
            ok_ico = QLabel(ICO_CHECK)
            ok_ico.setStyleSheet("font-size: 24px; color: #27ae60; background: transparent;")
            ok_ico.setFixedWidth(32)
            ok_txt = QVBoxLayout()
            ok_t = QLabel("All Clear!")
            ok_t.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60; background: transparent;")
            ok_s = QLabel("All your passwords meet security standards.")
            ok_s.setStyleSheet("font-size: 12px; color: #6fcf97; background: transparent;")
            ok_txt.addWidget(ok_t)
            ok_txt.addWidget(ok_s)
            ok_lay.addWidget(ok_ico)
            ok_lay.addLayout(ok_txt, 1)
            self.scan_result_lay.addWidget(ok_frame)

    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Backup Vault", "vault_backup.db", "Database (*.db)")
        if path:
            try:
                self.backend.export_vault(path)
                show_toast(self, f"Vault backed up!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _restore(self):
        ret = QMessageBox.warning(
            self, "Restore Vault",
            "This will REPLACE your current vault with the backup.\nYou will need to log in again.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select Backup", "", "Database (*.db)")
        if path:
            try:
                self.backend.import_vault(path)
                show_toast(self, "Vault restored! Please log in again.")
                self.main_window.lock_vault()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_json(self):
        ret = QMessageBox.warning(
            self, "Export Warning",
            f"{ICO_WARN}  Exporting as JSON will save all your passwords, cards, "
            "notes, and .env files in plain text (unencrypted).\n\n"
            "Anyone with access to this file can read your data.\n"
            "Only use this for migration purposes and delete the file after.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Vault", "vault_export.json", "JSON (*.json)")
        if path:
            try:
                data = self.backend.get_full_export_data()
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2)
                show_toast(self, "Vault exported as JSON!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_encrypted(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Encrypted Report", "security_report.enc", "Encrypted (*.enc)")
        if path:
            try:
                report = self.backend.run_security_scan()
                self.backend.export_encrypted_report(report, path)
                show_toast(self, "Encrypted report saved!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _toggle_visibility(self):
        checked = self.vis_btn.isChecked()
        if checked:
            self.vis_btn.setText(f"{ICO_HIDE}  Hide Passwords in List")
        else:
            self.vis_btn.setText(f"{ICO_VIEW}  Show Passwords in List")

    def _refresh_2fa_ui(self):
        enabled = self.backend.is_2fa_enabled()
        if enabled:
            self.twofa_status.setText("2FA is enabled for this vault.")
            self.twofa_enable_btn.setText(f"{ICO_DEL}  Disable 2FA")
            self.twofa_enable_btn.setObjectName("dangerBtn")
            self.twofa_show_btn.setVisible(True)
        else:
            self.twofa_status.setText("Add a second step when unlocking your vault.")
            self.twofa_enable_btn.setText(f"{ICO_KEY}  Enable 2FA")
            self.twofa_enable_btn.setObjectName("")
            self.twofa_show_btn.setVisible(False)
        self.twofa_enable_btn.style().unpolish(self.twofa_enable_btn)
        self.twofa_enable_btn.style().polish(self.twofa_enable_btn)

    def _toggle_2fa(self):
        if self.backend.is_2fa_enabled():
            self._disable_2fa()
        else:
            self._enable_2fa()

    def _enable_2fa(self):
        try:
            secret = self.backend.generate_2fa_secret()
            uri = self.backend.build_2fa_otpauth_uri(secret, "LocalVault")
            d = TwoFactorSetupDialog(self.backend, secret, uri, self)
            if d.exec() == QDialog.DialogCode.Accepted:
                self.backend.enable_2fa(secret)
                show_toast(self, "2FA enabled!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self._refresh_2fa_ui()

    def _disable_2fa(self):
        ret = QMessageBox.warning(
            self, "Disable 2FA",
            "This will remove two-factor protection from your vault.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        try:
            self.backend.disable_2fa()
            show_toast(self, "2FA disabled.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self._refresh_2fa_ui()

    def _show_2fa_info(self):
        try:
            secret = self.backend.get_2fa_secret()
            uri = self.backend.build_2fa_otpauth_uri(secret, "LocalVault")
            d = TwoFactorSetupDialog(self.backend, secret, uri, self, confirm_required=False)
            d.setWindowTitle("2FA Setup Key")
            d.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _save_generator_settings(self):
        # Prevent disabling all checkboxes (ensure at least one character type is enabled)
        if not (self.chk_upper.isChecked() or self.chk_lower.isChecked() or 
                self.chk_digits.isChecked() or self.chk_symbols.isChecked()):
            # Block signals temporarily to prevent infinite recursion
            self.chk_lower.blockSignals(True)
            self.chk_lower.setChecked(True)
            self.chk_lower.blockSignals(False)

        length = self.len_slider.value()
        try:
            self.backend.set_setting('pwd_gen_length', str(length))
            self.backend.set_setting('pwd_gen_include_uppercase', '1' if self.chk_upper.isChecked() else '0')
            self.backend.set_setting('pwd_gen_include_lowercase', '1' if self.chk_lower.isChecked() else '0')
            self.backend.set_setting('pwd_gen_include_digits', '1' if self.chk_digits.isChecked() else '0')
            self.backend.set_setting('pwd_gen_include_symbols', '1' if self.chk_symbols.isChecked() else '0')
        except Exception as e:
            print("Failed to save generator settings:", e)
        
        self._update_preview()

    def _update_preview(self):
        try:
            pwd = self.backend.generate_password()
            self.preview_in.setText(pwd)
        except Exception as e:
            print("Preview generation error:", e)

    def _copy_preview(self):
        pwd = self.preview_in.text()
        if pwd:
            pyperclip.copy(pwd)
            show_toast(self, "Preview password copied!")


# ─── Main Window ──────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.setWindowIcon(QIcon(str(get_app_icon_path())))
        self.setWindowTitle(f"SafeVault v{self.backend.VERSION}")
        self.setMinimumSize(750, 500)
        self.setStyleSheet(ModernStyle.STYLE)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._setup_screens()

    def _setup_screens(self):
        self.login_w = LoginWidget(self.backend, self._on_login)
        self.setup_w = SetupWidget(self.backend, self._on_login)
        self.vault_w = None  # Defer construction until successful login

        self.stack.addWidget(self.login_w)
        self.stack.addWidget(self.setup_w)

        if self.backend.is_first_run():
            self.stack.setCurrentWidget(self.setup_w)
        else:
            self.stack.setCurrentWidget(self.login_w)

    def _init_vault(self):
        lay = QVBoxLayout(self.vault_w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        hdr = QHBoxLayout()
        logo = QLabel(f"{ICO_HIDE} SafeVault")
        logo.setStyleSheet("font-size: 28px; font-weight: bold; color: #0078D4;")

        self.search = QLineEdit()
        self.search.setPlaceholderText(f"{ICO_SEARCH} Search vault...")
        self.search.setMinimumWidth(300)
        self.search.setMinimumHeight(35)
        self.search.textChanged.connect(self._on_search)

        lock = QPushButton(f"{ICO_HIDE}  Lock")
        lock.setObjectName("secondaryBtn")
        lock.setMinimumHeight(35)
        lock.clicked.connect(self.lock_vault)

        hdr.addWidget(logo)
        hdr.addStretch()
        hdr.addWidget(self.search)
        hdr.addSpacing(10)
        hdr.addWidget(lock)

        self.tabs = QTabWidget()
        self.pw_tab = PasswordsTab(self.backend)
        self.cd_tab = CardsTab(self.backend)
        self.env_tab = EnvFilesTab(self.backend)
        self.nt_tab = NotesTab(self.backend)
        self.st_tab = SettingsTab(self.backend, self)

        self.tabs.addTab(self.pw_tab, f"{ICO_KEY} Passwords")
        self.tabs.addTab(self.cd_tab, f"{ICO_CARD} Cards")
        self.tabs.addTab(self.env_tab, f"{ICO_ENV} .env Files")
        self.tabs.addTab(self.nt_tab, f"{ICO_NOTES} Notes")
        self.tabs.addTab(self.st_tab, f"{ICO_SETTINGS} Settings")

        self._loaded_tabs = set()
        self.tabs.currentChanged.connect(self._on_tab_changed)

        lay.addLayout(hdr)
        lay.addWidget(self.tabs)

    def _on_login(self):
        if self.vault_w is None:
            self.vault_w = QWidget()
            self._init_vault()
            self.stack.addWidget(self.vault_w)
        
        self.stack.setCurrentWidget(self.vault_w)
        self._refresh_all()

    def lock_vault(self):
        self.backend._encryption_key = None
        if self.vault_w is not None:
            self.stack.removeWidget(self.vault_w)
            self.vault_w.deleteLater()
            self.vault_w = None
        self.stack.setCurrentWidget(self.login_w)

    def _on_tab_changed(self, index):
        active_tab = self.tabs.widget(index)
        if active_tab in (self.pw_tab, self.cd_tab, self.env_tab, self.nt_tab):
            if active_tab not in self._loaded_tabs:
                q = self.search.text().strip() if self.search.text().strip() else None
                active_tab.load_data(q)
                self._loaded_tabs.add(active_tab)

    def _on_search(self, text):
        q = text.strip() if text.strip() else None
        self._loaded_tabs.clear()
        active_tab = self.tabs.currentWidget()
        if active_tab in (self.pw_tab, self.cd_tab, self.env_tab, self.nt_tab):
            active_tab.load_data(q)
            self._loaded_tabs.add(active_tab)

    def _refresh_all(self):
        self._loaded_tabs.clear()
        active_tab = self.tabs.currentWidget()
        if active_tab in (self.pw_tab, self.cd_tab, self.env_tab, self.nt_tab):
            q = self.search.text().strip() if self.search.text().strip() else None
            active_tab.load_data(q)
            self._loaded_tabs.add(active_tab)


