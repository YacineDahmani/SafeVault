"""
SafeVault Frontend - PySide6 GUI
"""

import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QStackedWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QFormLayout, QDialog, QScrollArea, QTextEdit, QSizePolicy,
    QFileDialog, QProgressBar, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt, QSize, QTimer, QRegularExpression
from PySide6.QtGui import QIcon, QFont, QColor, QRegularExpressionValidator

import pyperclip
from backend import Backend


# ─── Unicode icon constants ──────────────────────────────────────────
ICO_COPY   = "\U0001F4CB"   # clipboard
ICO_VIEW   = "\U0001F441"   # eye
ICO_DEL    = "\U0001F5D1"   # wastebasket
ICO_HIDE   = "\U0001F512"   # lock (hidden)
ICO_SHOW   = "\U0001F513"   # open lock (visible)
ICO_READ   = "\U0001F4D6"   # open book
ICO_ADD    = "\u2795"        # heavy plus
ICO_REFRESH = "\U0001F504"  # arrows cycle


class ModernStyle:
    STYLE = """
    * {
        font-family: "Segoe UI", "San Francisco", "Helvetica Neue", Arial, sans-serif;
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
        font-size: 18px;
        padding: 4px 8px;
        min-width: 30px;
        max-width: 36px;
        color: #cccccc;
    }
    QPushButton#iconBtn:hover {
        background-color: #2b2b2b;
        border-radius: 4px;
    }
    QPushButton#dangerIconBtn {
        background: transparent;
        border: none;
        font-size: 18px;
        padding: 4px 8px;
        min-width: 30px;
        max-width: 36px;
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

        title = QLabel("\U0001F510 Welcome Back")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Enter your master password to unlock vault")
        sub.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Master Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setMinimumWidth(320)
        self.pwd.setMinimumHeight(45)
        self.pwd.returnPressed.connect(self._login)

        btn = QPushButton("Unlock Vault")
        btn.setMinimumHeight(45)
        btn.clicked.connect(self._login)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #ff5555; font-size: 13px;")
        self.err.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (title, sub):
            vb.addWidget(w)
        vb.addSpacing(10)
        for w in (self.pwd, btn, self.err):
            vb.addWidget(w)
        layout.addWidget(box)

    def _login(self):
        p = self.pwd.text()
        if not p:
            self.err.setText("Password cannot be empty")
            return
        if self.backend.verify_master_password(p):
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

        title = QLabel("\U0001F680 First Time Setup")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        warn = QLabel("Create a strong master password.\nIf you lose it, your data cannot be recovered!")
        warn.setStyleSheet("color: #ffaa00; font-size: 14px; font-weight: bold;")
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Create Master Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setMinimumWidth(320)
        self.pwd.setMinimumHeight(45)

        self.conf = QLineEdit()
        self.conf.setPlaceholderText("Confirm Master Password")
        self.conf.setEchoMode(QLineEdit.EchoMode.Password)
        self.conf.setMinimumHeight(45)

        btn = QPushButton("Create Vault")
        btn.setMinimumHeight(45)
        btn.clicked.connect(self._setup)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #ff5555; font-size: 13px;")
        self.err.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (title, warn):
            vb.addWidget(w)
        vb.addSpacing(10)
        for w in (self.pwd, self.conf, btn, self.err):
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
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            entries = (self.backend.search_vault(q)['passwords'] if q
                       else self.backend.get_all_passwords())
            self.table.setRowCount(len(entries))
            for i, p in enumerate(entries):
                self.table.setItem(i, 0, QTableWidgetItem(p['app_name']))
                self.table.setItem(i, 1, QTableWidgetItem(p['username']))
                self.table.setItem(i, 3, QTableWidgetItem(str(p['id'])))

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)

                b_copy = QPushButton(ICO_COPY)
                b_copy.setObjectName("iconBtn")
                b_copy.setToolTip("Copy password")
                b_copy.setCursor(Qt.CursorShape.PointingHandCursor)
                b_copy.clicked.connect(lambda _, pid=p['id']: self._copy(pid))

                b_show = QPushButton(ICO_VIEW)
                b_show.setObjectName("iconBtn")
                b_show.setToolTip("Show / hide password")
                b_show.setCursor(Qt.CursorShape.PointingHandCursor)
                b_show.clicked.connect(lambda _, pid=p['id'], btn=b_show, row=i: self._toggle_show(pid, btn, row))

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, pid=p['id']: self._delete(pid))

                hl.addWidget(b_copy)
                hl.addWidget(b_show)
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
        d.setMinimumWidth(420)
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

        gen = QPushButton("\U0001F3B2")
        gen.setObjectName("secondaryBtn")
        gen.setToolTip("Generate random password")
        gen.clicked.connect(lambda: pwd_in.setText(self.backend.generate_password(16)))

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
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            cards = (self.backend.search_vault(q)['cards'] if q
                     else self.backend.get_all_cards())
            self.table.setRowCount(len(cards))
            for i, c in enumerate(cards):
                self.table.setItem(i, 0, QTableWidgetItem(c['label']))
                self.table.setItem(i, 1, QTableWidgetItem(c['holder_name']))

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)

                b_view = QPushButton(ICO_VIEW)
                b_view.setObjectName("iconBtn")
                b_view.setToolTip("View card details")
                b_view.setCursor(Qt.CursorShape.PointingHandCursor)
                b_view.clicked.connect(lambda _, cid=c['id']: self._view_card(cid))

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, cid=c['id']: self._del(cid))

                hl.addWidget(b_view)
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
        d.setMinimumWidth(440)
        lay = QVBoxLayout(d)
        lay.setSpacing(12)

        header = QLabel(f"\U0001F4B3  {c['label']}")
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
        d.setMinimumWidth(420)
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
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        lay.addLayout(tb)
        lay.addWidget(self.table)

    def load_data(self, q=None):
        self.table.setRowCount(0)
        try:
            notes = (self.backend.search_vault(q)['notes'] if q
                     else self.backend.get_all_notes())
            self.table.setRowCount(len(notes))
            for i, n in enumerate(notes):
                self.table.setItem(i, 0, QTableWidgetItem(n['title']))

                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(4, 2, 4, 2)
                hl.setSpacing(4)

                b_read = QPushButton(ICO_READ)
                b_read.setObjectName("iconBtn")
                b_read.setToolTip("Read note")
                b_read.setCursor(Qt.CursorShape.PointingHandCursor)
                b_read.clicked.connect(lambda _, nid=n['id']: self._view(nid))

                b_del = QPushButton(ICO_DEL)
                b_del.setObjectName("dangerIconBtn")
                b_del.setToolTip("Delete")
                b_del.setCursor(Qt.CursorShape.PointingHandCursor)
                b_del.clicked.connect(lambda _, nid=n['id']: self._del(nid))

                hl.addWidget(b_read)
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

        title = QLabel("\u2699\uFE0F  Settings & Tools")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        lay.addWidget(title)

        # ── Password Health ──
        health_grp = QGroupBox("Password Health Check")
        hlay = QVBoxLayout(health_grp)

        scan_btn = QPushButton("\U0001F50D  Run Security Scan")
        scan_btn.setMinimumHeight(40)
        scan_btn.clicked.connect(self._run_scan)
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
        backup_btn = QPushButton("\U0001F4BE  Backup Vault")
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self._backup)

        restore_btn = QPushButton("\U0001F504  Restore Vault")
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
        export_btn = QPushButton("\U0001F4E4  Export as JSON")
        export_btn.setMinimumHeight(40)
        export_btn.clicked.connect(self._export_json)

        export_enc_btn = QPushButton("\U0001F510  Export Encrypted Report")
        export_enc_btn.setObjectName("secondaryBtn")
        export_enc_btn.setMinimumHeight(40)
        export_enc_btn.clicked.connect(self._export_encrypted)

        ierow.addWidget(export_btn)
        ierow.addWidget(export_enc_btn)
        ielay.addLayout(ierow)
        lay.addWidget(ie_grp)

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

        lay.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _run_scan(self):
        # Clear old results
        while self.scan_result_lay.count():
            child = self.scan_result_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        try:
            report = self.backend.run_security_scan()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Scan failed: {e}")
            return

        total = report['total_passwords']
        score = report['overall_score']

        # Overall score bar
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(score))
        if score >= 80:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #27ae60; border-radius: 5px; }")
        elif score >= 60:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; border-radius: 5px; }")
        else:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; border-radius: 5px; }")
        bar.setFormat(f"Overall Score: {score}/100")
        self.scan_result_lay.addWidget(bar)

        info = QLabel(
            f"Total passwords: {total}  \u2022  "
            f"Strong: {report['strength_distribution']['strong']}  \u2022  "
            f"Good: {report['strength_distribution']['good']}  \u2022  "
            f"Fair: {report['strength_distribution']['fair']}  \u2022  "
            f"Weak: {report['strength_distribution']['weak']}"
        )
        info.setStyleSheet("color: #cccccc; font-size: 13px; padding: 4px;")
        info.setWordWrap(True)
        self.scan_result_lay.addWidget(info)

        if report['weak_passwords']:
            weak_lbl = QLabel(f"\u26A0  {len(report['weak_passwords'])} weak or fair password(s) found")
            weak_lbl.setStyleSheet("color: #ff5555; font-weight: bold; padding: 4px;")
            self.scan_result_lay.addWidget(weak_lbl)

            for wp in report['weak_passwords'][:10]:
                issues = ", ".join(wp['issues']) if wp['issues'] else "No specifics"
                wl = QLabel(f"  \u2022 {wp['app_name']} \u2014 {wp['rating']} ({wp['score']}/100): {issues}")
                wl.setStyleSheet("color: #ffaa00; font-size: 12px; padding-left: 12px;")
                wl.setWordWrap(True)
                self.scan_result_lay.addWidget(wl)

        if report['duplicate_groups']:
            dup_lbl = QLabel(f"\u26A0  {len(report['duplicate_groups'])} group(s) of reused passwords")
            dup_lbl.setStyleSheet("color: #ff5555; font-weight: bold; padding: 4px;")
            self.scan_result_lay.addWidget(dup_lbl)

        if report['common_passwords']:
            com_lbl = QLabel(f"\u26A0  {len(report['common_passwords'])} commonly breached password(s)")
            com_lbl.setStyleSheet("color: #ff5555; font-weight: bold; padding: 4px;")
            self.scan_result_lay.addWidget(com_lbl)

        if not report['weak_passwords'] and not report['duplicate_groups'] and not report['common_passwords']:
            ok = QLabel("\u2705  All passwords look healthy!")
            ok.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 14px; padding: 4px;")
            self.scan_result_lay.addWidget(ok)

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


# ─── Main Window ──────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("\U0001F510 SafeVault")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(ModernStyle.STYLE)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._setup_screens()

    def _setup_screens(self):
        self.login_w = LoginWidget(self.backend, self._on_login)
        self.setup_w = SetupWidget(self.backend, self._on_login)
        self.vault_w = QWidget()
        self._init_vault()

        self.stack.addWidget(self.login_w)
        self.stack.addWidget(self.setup_w)
        self.stack.addWidget(self.vault_w)

        if self.backend.is_first_run():
            self.stack.setCurrentWidget(self.setup_w)
        else:
            self.stack.setCurrentWidget(self.login_w)

    def _init_vault(self):
        lay = QVBoxLayout(self.vault_w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        hdr = QHBoxLayout()
        logo = QLabel("\U0001F510 SafeVault")
        logo.setStyleSheet("font-size: 28px; font-weight: bold; color: #0078D4;")

        self.search = QLineEdit()
        self.search.setPlaceholderText("\U0001F50D Search vault...")
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
        self.nt_tab = NotesTab(self.backend)
        self.st_tab = SettingsTab(self.backend, self)

        self.tabs.addTab(self.pw_tab, "\U0001F511 Passwords")
        self.tabs.addTab(self.cd_tab, "\U0001F4B3 Cards")
        self.tabs.addTab(self.nt_tab, "\U0001F4DD Notes")
        self.tabs.addTab(self.st_tab, "\u2699\uFE0F Settings")

        lay.addLayout(hdr)
        lay.addWidget(self.tabs)

    def _on_login(self):
        self.stack.setCurrentWidget(self.vault_w)
        self._refresh_all()

    def lock_vault(self):
        self.backend._encryption_key = None
        self.stack.setCurrentWidget(self.login_w)

    def _on_search(self, text):
        q = text.strip() if text.strip() else None
        self.pw_tab.load_data(q)
        self.cd_tab.load_data(q)
        self.nt_tab.load_data(q)

    def _refresh_all(self):
        self.pw_tab.load_data()
        self.cd_tab.load_data()
        self.nt_tab.load_data()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    backend = Backend()
    window = MainWindow(backend)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
