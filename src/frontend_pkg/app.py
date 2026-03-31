import sys

from PySide6.QtWidgets import QApplication

from backend import Backend
from .views import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    backend = Backend()
    window = MainWindow(backend)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
