import sys
from contextlib import nullcontext

from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QImageReader, QWheelEvent, QColor

img_path = None
main_window = None

class SelectImagePage(QWidget):
    def __init__(self):
        super().__init__()
        self.choose_file_btn = QPushButton("Select Image")
        self.choose_file_btn.clicked.connect(self.open_file_explorer)

        self.choose_file_lbl = QLabel("Please Select an Image Below:")

        layout = QVBoxLayout()

        layout.addStretch()
        layout.addWidget(self.choose_file_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.choose_file_btn)
        layout.addStretch()

        self.setLayout(layout)
        self.show()

    def open_file_explorer(self):
        global img_path, main_window
        file_dialog = QFileDialog()
        img_path, _ = file_dialog.getOpenFileName(self, "Select an Image", "",
                                                   "Images (*.png *.jpg *.jpeg)")
        self.close()
        main_window = MainWindow()

class ImageEditor(QGraphicsView):
    def __init__(self, scn):
        super().__init__(scn)
        #vars for transform tool
        self.p1 = None
        self.temp_line = None
        self.lines = []

        #vars for image panning
        self.last_pos = None
        self.last_cursor = None

        #layout init
        self.scn: QGraphicsScene = scn
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.show()

    def wheelEvent(self, event: QWheelEvent) -> None:
        zoom_factor = 1.2
        if event.angleDelta().y() < 0:
            zoom_factor = 1/zoom_factor
        self.scale(zoom_factor, zoom_factor)

    def onTransformSelect(self):
        print("onTransformSelect")
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()
        print(self.cursor())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.p1 is None:
                self.p1 = self.mapToScene(event.pos())
            else:
                #remove old line
                self.scn.removeItem(self.temp_line)
                self.temp_line = None

        if event.button() == Qt.MouseButton.MiddleButton:
            self.last_cursor = self.cursor()
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.last_pos = event.pos()

        if event.button() == Qt.MouseButton.RightButton:
            if self.temp_line is not None:
                self.lines.append(self.temp_line)
                self.lines[-1].setPen(QColor("green"))

                self.p1 = None
                self.temp_line = None

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.p1 is not None:
                if self.temp_line is not None:
                    self.scn.removeItem(self.temp_line)
                    self.temp_line = None

                p2 = self.mapToScene(event.pos())
                self.temp_line = QGraphicsLineItem(self.p1.x(), self.p1.y(), p2.x(), p2.y())
                self.scn.addItem(self.temp_line)


        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            delta = event.pos() - self.last_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            #deactivate panning
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(self.last_cursor)


class SidePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        btn_layout = QGridLayout()

        # transform, auto char select, remove lines, recognize chars, change color
        tools = ["TRS", "ACS", "RML", "OCR", "CLR"]
        events = [img_editor.onTransformSelect] * 5
        self.button_group = QButtonGroup()
        rows, cols = 4, 3

        for i, tool in enumerate(tools):
            btn = QPushButton(tool)
            btn.setFixedSize(100, 50)
            btn.setCheckable(True)
            row, clm = divmod(i, cols)
            self.button_group.addButton(btn)
            btn_layout.addWidget(btn, row, clm)
            btn.clicked.connect(lambda: events[row]())

        self.setLayout(layout)
        layout.addLayout(btn_layout)
        layout.addStretch()

        self.show()


class MainWindow(QWidget):
    def __init__(self):
        global img_editor
        super().__init__()
        layout = QHBoxLayout()

        scene = QGraphicsScene()
        pixmap = QPixmap(img_path)
        scene.addPixmap(pixmap)
        img_editor = ImageEditor(scene)
        self.side = SidePanel()
        layout.addWidget(self.side)

        layout.addWidget(img_editor)
        self.setLayout(layout)
        layout.addStretch()
        self.show()

img_editor: ImageEditor = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    p = SelectImagePage()

    app.exec()