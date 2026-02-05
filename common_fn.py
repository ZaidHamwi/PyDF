import os
import sys

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame


def resizeEvent(self, event):
    super().resizeEvent(event)
    self.loading_overlay.setGeometry(self.central.rect())


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class H_Line(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy()
        )

class V_Line(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy()
        )


class PagePreviewWidget(QtWidgets.QWidget):
    def __init__(self, pixmap: QPixmap, page_number: int):
        super().__init__()

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(pixmap.size())

        self.overlay = QtWidgets.QLabel(f"Page {page_number}", self)
        self.overlay.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 160);
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 11px;
            }
        """)
        self.overlay.adjustSize()

        self.setFixedSize(pixmap.size())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = 10
        self.overlay.move(
            self.width() - self.overlay.width() - margin,
            self.height() - self.overlay.height() - margin
        )


class PageItem:
    def __init__(self, source_path, page_index=None, image=None):
        self.source_path = source_path
        self.page_index = page_index
        self.image = image
        self.rotation = 0


class Toast(QtWidgets.QWidget):
    def __init__(self, parent, message, duration=2000):
        super().__init__(parent)

        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(message)

        label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(30, 30, 30, 220);
                padding: 10px 16px;
                border-radius: 8px;
                font-size: 13px;
            }
        """)

        layout.addWidget(label)

        self.adjustSize()
        self.position_to_parent()
        self.show()

        QtCore.QTimer.singleShot(duration, self.close)

    def position_to_parent(self):
        parent_rect = self.parent().rect()
        x = parent_rect.width() - self.width() - 20
        y = parent_rect.height() - self.height() - 20
        self.move(self.parent().mapToGlobal(QtCore.QPoint(x, y)))