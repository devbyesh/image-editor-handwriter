import sys

import cv2
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QWheelEvent, QColor, QImage

import numpy as np

main_window = None


class SelectImagePage(QWidget):
    def __init__(self):
        super().__init__()
        self.img_path = None
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
        global main_window
        file_dialog = QFileDialog()
        img_path, _ = file_dialog.getOpenFileName(self, "Select an Image", "",
                                                  "Images (*.png *.jpg *.jpeg)")
        self.close()
        main_window = MainWindow(img_path)


class ImageEditor(QGraphicsView):
    def __init__(self, scn):
        super().__init__(scn)
        self.tooltips = [TransformTooltip()]
        self.transformTooltip = self.tooltips[0]

        # vars for image panning
        self.last_pos = None
        self.last_cursor = None
        self.img = None

        # layout init
        self.scn: QGraphicsScene = scn
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.show()

    def addImg(self, pixmap):
        self.scn.clear()
        self.scn.addPixmap(pixmap)
        self.img = pixmap

    def wheelEvent(self, event: QWheelEvent) -> None:
        zoom_factor = 1.2
        if event.angleDelta().y() < 0:
            zoom_factor = 1 / zoom_factor
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.last_cursor = self.cursor()
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.last_pos = event.pos()

        for tooltip in self.tooltips:
            tooltip.handle_event("mouse_press", event, self)

    def mouseMoveEvent(self, event):
        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            delta = event.pos() - self.last_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_pos = event.pos()

        for tooltip in self.tooltips:
            tooltip.handle_event("mouse_move", event, self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            # deactivate panning
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(self.last_cursor)

    def keyPressEvent(self, event):
        for tooltip in self.tooltips:
            tooltip.handle_event("key_press", event, self)

    def onTransformActivate(self):
        self.transformTooltip.activate()


class Tooltip:
    def __init__(self):
        self.isActivated = False

    def activate(self):
        self.isActivated = True

    def deactivate(self):
        if not self.isActivated:
            raise Exception("Invalid state detected")
        self.isActivated = False

    def handle_event(self, event_type, event, caller):
        if not self.isActivated:
            return

        # find on_{event_type} method and call it
        method = getattr(self, f"on_{event_type}", None)
        if method:
            method(event, caller)


class TransformTooltip(Tooltip):
    def __init__(self):
        super().__init__()
        self.p1 = None
        self.temp_line = None
        self.lines = []

    def on_key_press(self, event, context):
        if event.key() == Qt.Key.Key_Escape:
            self.deactivate()
            context.setDragMode(QGraphicsView.DragMode.NoDrag)
            context.setCursor(Qt.CursorShape.ArrowCursor)
            context.update()
        if event.key() == Qt.Key.Key_Return:
            self.deactivate()
            t_lines = []
            lines = []
            for line in self.lines:
                t_lines.append((line.line().x1(), line.line().y1()))
                t_lines.append((context.scn.sceneRect().width(), line.line().y1()))
                lines.append((line.line().x1(), line.line().y1()))
                lines.append((line.line().x2(), line.line().y2()))

            t_lines = np.array(t_lines)
            lines = np.array(lines)

            H, status = cv2.findHomography(lines, t_lines)
            img = pixmap_to_cv2_image(context.img)
            img = cv2.warpPerspective(img, H,
                                      (int(context.scn.sceneRect().width()), int(context.scn.sceneRect().height())))
            cv2.imwrite("output.png", img)
            context.scn.clear()
            pixmap = QPixmap("output.png")
            context.addImg(pixmap)
            self.lines = []

    def on_mouse_move(self, event, context):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.p1 is not None:
                if self.temp_line is not None:
                    context.scn.removeItem(self.temp_line)
                    self.temp_line = None

                p2 = context.mapToScene(event.pos())
                self.temp_line = QGraphicsLineItem(self.p1.x(), self.p1.y(), p2.x(), p2.y())
                context.scn.addItem(self.temp_line)

    def on_mouse_press(self, event, context):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.p1 is None:
                self.p1 = context.mapToScene(event.pos())
            else:
                # remove old line
                context.scn.removeItem(self.temp_line)
                self.temp_line = None

        if event.button() == Qt.MouseButton.RightButton:
            if self.temp_line is not None:
                # remove old line
                context.scn.removeItem(self.temp_line)

                # extend line to either end of page
                m = (self.temp_line.line().y2() - self.temp_line.line().y1()) / (
                        self.temp_line.line().x2() - self.temp_line.line().x1())
                b = self.temp_line.line().y1() - m * self.temp_line.line().x1()

                x2 = context.scn.sceneRect().width()
                y2 = m * x2 + b

                self.lines.append(QGraphicsLineItem(0, b, x2, y2))
                self.lines[-1].setPen(QColor("green"))
                context.scn.addItem(self.lines[-1])

                self.p1 = None
                self.temp_line = None


class SidePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        btn_layout = QGridLayout()

        # transform, auto char select, remove lines, recognize chars, change color
        tools = ["TRS", "ACS", "RML", "OCR", "CLR"]
        events = [img_editor.onTransformActivate] * 5
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
    def __init__(self, img_path):
        global img_editor
        super().__init__()
        layout = QHBoxLayout()

        scene = QGraphicsScene()
        pixmap = QPixmap(img_path)
        img_editor = ImageEditor(scene)
        img_editor.addImg(pixmap)
        self.side = SidePanel()
        layout.addWidget(self.side)

        layout.addWidget(img_editor)
        self.setLayout(layout)
        layout.addStretch()
        self.show()


def pixmap_to_cv2_image(pixmap):
    q_image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)  # QImage.Format_RGB32 (value = 4)
    width, height = q_image.width(), q_image.height()

    # Convert QImage to NumPy array
    img = np.array(q_image.bits().asarray(width * height * 4)).reshape((height, width, 4))

    # Convert RGBA to BGR for OpenCV
    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return img


img_editor: ImageEditor = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    p = SelectImagePage()

    app.exec()
