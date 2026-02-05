import sys
import os

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QShortcut
from PySide6.QtWidgets import QMessageBox

from PIL import Image
import fitz  # PyMuPDF
import pypdf

from common_fn import resource_path, Toast, PageItem, PagePreviewWidget, V_Line, H_Line



class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.pages: list[PageItem] = []
        self.zoom_factor = 1.0
        self.auto_fit = True

        self.setWindowTitle("PyDF")
        self.setMinimumSize(1100, 650)
        self.setWindowIcon(QtGui.QIcon(resource_path("embedded_images/PDF_app_icon.ico")))

        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QtWidgets.QHBoxLayout(self.central)

        self.build_ui()
        self.connect_signals()

        QShortcut(Qt.Key_Delete, self, activated=self.delete_selected_page)
        QShortcut(Qt.CTRL | Qt.Key_S, self, activated=self.export_pdf)

    def build_ui(self):
        self.controls = QtWidgets.QVBoxLayout()

        hline1 = H_Line()
        hline2 = H_Line()
        hline3 = H_Line()
        hline4 = H_Line()
        hline5 = H_Line()

        self.btn_add = QtWidgets.QPushButton("Add PDFs / Images")
        self.btn_rotate_left = QtWidgets.QPushButton("Rotate ⟲")
        self.btn_rotate_right = QtWidgets.QPushButton("Rotate ⟳")

        self.btn_zoom_in = QtWidgets.QPushButton("Zoom +")
        self.btn_zoom_out = QtWidgets.QPushButton("Zoom −")
        self.btn_zoom_fit = QtWidgets.QPushButton("Fit")

        self.btn_duplicate = QtWidgets.QPushButton("Duplicate page")
        self.btn_delete = QtWidgets.QPushButton("Delete page - DEL")
        self.btn_export = QtWidgets.QPushButton("Export PDF - CTRL+S")
        self.btn_clear = QtWidgets.QPushButton("Clear")

        self.controls.addWidget(hline1)
        self.controls.addWidget(self.btn_add)
        self.controls.addSpacing(10)
        self.controls.addWidget(hline2)
        self.controls.addSpacing(10)
        self.controls.addWidget(QtWidgets.QLabel("Preview scale:"))
        self.controls.addWidget(self.btn_zoom_in)
        self.controls.addWidget(self.btn_zoom_out)
        self.controls.addWidget(self.btn_zoom_fit)
        self.controls.addSpacing(10)
        self.controls.addWidget(hline3)
        self.controls.addSpacing(10)

        for w in [
            QtWidgets.QLabel("Edit selected page:"),
            self.btn_rotate_left,
            self.btn_rotate_right,
            self.btn_duplicate,
            self.btn_delete
        ]:
            self.controls.addWidget(w)

        self.controls.addStretch()
        self.controls.addWidget(hline4)
        self.controls.addWidget(self.btn_export)
        self.controls.addWidget(self.btn_clear)
        self.controls.addWidget(hline5)

        # Preview
        preview_wrapper = QtWidgets.QVBoxLayout()
        header = QtWidgets.QLabel("Export preview")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.preview_container = QtWidgets.QWidget()
        self.preview_layout = QtWidgets.QVBoxLayout(self.preview_container)
        self.preview_layout.setAlignment(Qt.AlignTop)

        self.preview_scroll = QtWidgets.QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setWidget(self.preview_container)

        preview_wrapper.addWidget(header)
        preview_wrapper.addWidget(self.preview_scroll)

        # Page list
        page_wrapper = QtWidgets.QVBoxLayout()
        page_header = QtWidgets.QLabel("Page list - Drag to reorder")
        page_header.setAlignment(Qt.AlignCenter)
        page_header.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.page_list = QtWidgets.QListWidget()
        self.page_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        page_wrapper.addWidget(page_header)
        page_wrapper.addWidget(self.page_list)

        # Loading overlay
        self.loading_overlay = QtWidgets.QLabel("Loading preview…", self.central)
        self.loading_overlay.setAlignment(Qt.AlignCenter)
        self.loading_overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 120); color: white; font-size: 18px;"
        )
        self.loading_overlay.hide()

        # Assemble
        vline1 = V_Line()
        vline2 = V_Line()
        vline3 = V_Line()
        vline4 = V_Line()
        self.main_layout.addWidget(vline1)
        self.main_layout.addLayout(self.controls, 1)
        self.main_layout.addWidget(vline2)
        self.main_layout.addLayout(preview_wrapper, 4)
        self.main_layout.addWidget(vline3)
        self.main_layout.addLayout(page_wrapper, 1)
        self.main_layout.addWidget(vline4)

    def connect_signals(self):
        self.btn_add.clicked.connect(self.add_files)
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_selected(-90))
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_selected(90))
        self.btn_zoom_in.clicked.connect(lambda: self.adjust_zoom(1.15))
        self.btn_zoom_out.clicked.connect(lambda: self.adjust_zoom(0.87))
        self.btn_zoom_fit.clicked.connect(self.fit_zoom)
        self.btn_duplicate.clicked.connect(self.duplicate_selected_page)
        self.btn_delete.clicked.connect(self.delete_selected_page)
        self.btn_export.clicked.connect(self.export_pdf)
        self.btn_clear.clicked.connect(self.clear_all)
        self.page_list.model().rowsMoved.connect(self.reorder_pages)

    def set_loading(self, loading: bool):
        self.loading_overlay.setVisible(loading)
        self.central.setEnabled(not loading)
        QtWidgets.QApplication.processEvents()

    def duplicate_selected_page(self):
        row = self.page_list.currentRow()
        if row < 0:
            return

        original = self.pages[row]

        duplicate = PageItem(
            original.source_path,
            page_index=original.page_index,
            image=original.image
        )
        duplicate.rotation = original.rotation

        self.pages.insert(row + 1, duplicate)

        label = self.page_list.item(row).text()
        self.page_list.insertItem(row + 1, label)

        self.page_list.setCurrentRow(row + 1)
        self.render_full_preview()

    ## OLD
    # def duplicate_selected_page(self):
    #     row = self.page_list.currentRow()
    #     if row < 0:
    #         return
    #
    #     original = self.pages[row]
    #     dup = PageItem(
    #         original.source_path,
    #         page_index=original.page_index,
    #         image=original.image
    #     )
    #     dup.rotation = original.rotation
    #
    #     self.pages.insert(row + 1, dup)
    #     self.page_list.insertItem(row + 1, self.page_list.item(row).text())
    #     self.page_list.setCurrentRow(row + 1)
    #     self.render_full_preview()

    def clear_all(self):
        self.pages.clear()
        self.page_list.clear()
        self.clear_preview()


    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add PDFs or Images", "", "PDF & Images (*.pdf *.png *.jpg *.jpeg)"
        )

        for path in files:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                doc = fitz.open(path)
                for i in range(doc.page_count):
                    self.pages.append(PageItem(path, page_index=i))
                    self.page_list.addItem(
                        f"{os.path.basename(path)} — page {i + 1}"
                    )
            else:
                img = Image.open(path).convert("RGB")
                self.pages.append(PageItem(path, image=img))
                self.page_list.addItem(os.path.basename(path))

        self.fit_zoom()
        self.render_full_preview()

    def delete_selected_page(self):
        row = self.page_list.currentRow()
        if row < 0:
            return
        del self.pages[row]
        self.page_list.takeItem(row)
        self.render_full_preview()

    def reorder_pages(self):
        new_pages = []
        for i in range(self.page_list.count()):
            label = self.page_list.item(i).text()
            for page in self.pages:
                expected = (
                    f"{os.path.basename(page.source_path)} — page {page.page_index + 1}"
                    if page.page_index is not None
                    else os.path.basename(page.source_path)
                )
                if label == expected:
                    new_pages.append(page)
                    break

        self.pages = new_pages
        self.render_full_preview()

    def rotate_selected(self, deg):
        row = self.page_list.currentRow()
        if row < 0:
            return
        self.pages[row].rotation = (self.pages[row].rotation + deg) % 360
        self.render_full_preview()

    def adjust_zoom(self, factor):
        self.auto_fit = False
        self.zoom_factor = max(0.2, min(self.zoom_factor * factor, 4.0))
        self.render_full_preview()

    def fit_zoom(self):
        self.auto_fit = True
        self.render_full_preview()

    def clear_preview(self):
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def render_full_preview(self):
        self.clear_preview()
        if not self.pages:
            return

        self.set_loading(True)

        preview_width = self.preview_scroll.viewport().width() - 40

        for i, page in enumerate(self.pages):
            if page.image:
                img = page.image.rotate(-page.rotation, expand=True)
                qimage = QImage(
                    img.tobytes("raw", "RGB"),
                    img.width,
                    img.height,
                    img.width * 3,
                    QImage.Format_RGB888
                )
                pixmap = QPixmap.fromImage(qimage)
            else:
                doc = fitz.open(page.source_path)
                pdf_page = doc.load_page(page.page_index)
                mat = fitz.Matrix(2, 2).prerotate(page.rotation)
                pix = pdf_page.get_pixmap(matrix=mat)
                pixmap = QPixmap.fromImage(
                    QImage(
                        pix.samples,
                        pix.width,
                        pix.height,
                        pix.stride,
                        QImage.Format_RGB888
                    )
                )

            scale = preview_width / pixmap.width() if self.auto_fit else self.zoom_factor
            pixmap = pixmap.scaled(
                pixmap.size() * scale,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.preview_layout.addWidget(
                PagePreviewWidget(pixmap, page_number=i + 1)
            )
            self.preview_layout.setAlignment(Qt.AlignCenter)
        self.set_loading(False)

    def export_pdf(self):
        if not self.pages:
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save PDF", "output.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return

        self.btn_export.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        try:
            writer = pypdf.PdfWriter()

            for page in self.pages:
                if page.image:
                    img = page.image.rotate(-page.rotation, expand=True)
                    temp = "_img.pdf"
                    img.save(temp)
                    reader = pypdf.PdfReader(temp)
                    writer.add_page(reader.pages[0])
                    os.remove(temp)
                else:
                    reader = pypdf.PdfReader(page.source_path)
                    pdf_page = reader.pages[page.page_index]
                    if page.rotation:
                        pdf_page.rotate(page.rotation)
                    writer.add_page(pdf_page)

            with open(path, "wb") as f:
                writer.write(f)

            self.btn_export.setEnabled(True)
            Toast(self, "PDF exported successfully")

        except Exception as e:
            self.btn_export.setEnabled(True)

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Export failed")
            msg.setText("Failed to export PDF.")
            msg.setInformativeText(str(e))
            msg.exec()

        finally:
            self.btn_export.setEnabled(True)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())
