import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from backend import Backend
from .views import MainWindow, get_app_icon_path


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(get_app_icon_path())))
    backend = Backend()
    window = MainWindow(backend)
    window.setWindowIcon(QIcon(str(get_app_icon_path())))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
