from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication

from services.file_utils import initialize_app
from ui.main_window import MainWindow


if __name__ == "__main__":
    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    paths = initialize_app(root)
    application = QApplication(sys.argv)
    application.setApplicationName("Quotation Generator")
    window = MainWindow(paths)
    window.show()
    sys.exit(application.exec())
