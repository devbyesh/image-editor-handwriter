import sys

from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QImageReader, QWheelEvent

img_path = "img.png"

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
        global img_path
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select an Image", "",
                                                   "Images (*.png *.jpg *.jpeg)")
        self.choose_file_btn.setDisabled(True)

        self.choose_file_lbl.setText("Loading Image...")

class ImageEditor(QGraphicsView):
    def __init__(self, scn):
        super().__init__(scn)
        rect_item = QGraphicsRectItem(QRectF(0, 0, 100, 100))
        scn.addItem(rect_item)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.show()

    def wheelEvent(self, event: QWheelEvent) -> None:
        pass



if __name__ == '__main__':
    app = QApplication(sys.argv)
    scene = QGraphicsScene()
    pixmap = QPixmap.fromImageReader(QImageReader("img.png"))
    if pixmap.isNull():
        print("Failed to load pixmap")
    else:
        scene.addPixmap(pixmap)

    dialog = ImageEditor(scene)
    app.exec()