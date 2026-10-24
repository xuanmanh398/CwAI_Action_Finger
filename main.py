import os
import sys
import argparse

# Set High DPI environment variables before QApplication initialization
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app_gui import MainWindow
from config import AppConfig

def main():
    parser = argparse.ArgumentParser(description="Hand Gesture Computer Controller")
    parser.add_argument("--cam", type=int, default=0, help="Camera index (default: 0)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Hand Gesture Computer Controller")
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
