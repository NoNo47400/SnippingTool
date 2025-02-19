import sys
import os
import time
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QInputDialog, QHBoxLayout, QLineEdit, QColorDialog
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtCore import QTimer, QRect, Qt, QPoint
import subprocess
import os

os.environ["DISPLAY"] = ":0.0" # Ensure we use the correct display (X11)

class ScreenRecorderApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Screen Tool")
        self.setFixedSize(400, 100)

        layout = QVBoxLayout()
        subheader_layout = QHBoxLayout()
        
        # Screenshot
        self.capture_button = QPushButton("Screenshot")
        self.capture_button.clicked.connect(self.capture_screen)
        subheader_layout.addWidget(self.capture_button)
        
        self.record_button = QPushButton("Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)
        
        layout.addLayout(subheader_layout)

        self.info_label = QLabel("")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

        self.recording = False
        self.record_process = None
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        self.capture_rect = None  # Selected area
        self.selected_shape = None  # Selected shape

    def select_area(self):
        """Uses `slop` to select an area on the screen and returns its coordinates"""
        try:
            result = subprocess.run(["slop", "-f", "%x %y %w %h"], capture_output=True, text=True)
            x, y, w, h = map(int, result.stdout.strip().split())
            return QRect(x, y, w, h)
        except Exception as e:
            print("Error during selection:", e)
            return None

    def capture_screen(self):
        """Captures a selected area of the screen using maim"""
        self.capture_rect = self.select_area()
        if self.capture_rect:
            save_path, selected_filter = QFileDialog.getSaveFileName(self, "Save Capture", "", "PNG (*.png);;JPEG (*.jpg)")
            if save_path:
                if selected_filter == "PNG (*.png)" and not save_path.endswith(".png"):
                    save_path += ".png"
                elif selected_filter == "JPEG (*.jpg)" and not save_path.endswith(".jpg"):
                    save_path += ".jpg"
                x, y, w, h = self.capture_rect.x(), self.capture_rect.y(), self.capture_rect.width(), self.capture_rect.height()
                subprocess.run(["maim", "-g", f"{w}x{h}+{x}+{y}", save_path])
                self.info_label.setText(f"Capture saved: {save_path}")
                self.edit_image(save_path)

    def edit_image(self, image_path):
        """Opens the captured image for editing"""
        self.image_editor = ImageEditor(image_path, self)
        self.image_editor.show()

    def toggle_recording(self):
        """Starts or stops video recording of a selected area"""
        if not self.recording:
            self.capture_rect = self.select_area()
            if self.capture_rect:
                save_path, selected_filter = QFileDialog.getSaveFileName(self, "Save Video", "", "MP4 (*.mp4)")
                if save_path:
                    if selected_filter == "MP4 (*.mp4)" and not save_path.endswith(".mp4"):
                        save_path += ".mp4"
                    self.start_recording(save_path)
        else:
            self.stop_recording()

    def get_audio_source(self):
        result = subprocess.run(["pactl", "list", "short", "sources"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "monitor" in line:
                return line.split()[1]  # Returns the first audio device found
        return None  # No device found

    def start_recording(self, save_path):
        """Starts ffmpeg to record a specific area."""
        if not self.capture_rect:
            return
        audio_source = self.get_audio_source()
        if audio_source:
            print("Using audio source:", audio_source)
        else:
            print("No audio source detected")
        x, y, w, h = self.capture_rect.x(), self.capture_rect.y(), self.capture_rect.width(), self.capture_rect.height()
        self.recording = True
        self.record_button.setText("Stop Recording")
        self.start_time = time.time()

        self.record_process = subprocess.Popen([
            "ffmpeg", "-y",
            "-video_size", f"{w}x{h}",
            "-framerate", "30",
            "-f", "x11grab", "-i", f":0.0+{x},{y}",
            "-f", "pulse", "-i", "alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink.monitor",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            save_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.timer.start(1000)

    def stop_recording(self):
        """Stops ffmpeg properly."""
        if self.recording and self.record_process:
            self.record_process.terminate()
            self.record_process.wait()
            self.recording = False
            self.record_button.setText("Recording")
            self.timer.stop()
            self.info_label.setText("Recording finished")

    def update_timer(self):
        """Displays the elapsed time during recording."""
        elapsed = int(time.time() - self.start_time)
        self.info_label.setText(f"Recording time: {elapsed}s")

class ImageEditor(QWidget):
    def __init__(self, image_path, parent):
        super().__init__()
        self.setWindowTitle("Image Editor")
        self.setGeometry(100, 100, 800, 600)
        self.image_path = image_path
        self.image = QPixmap(image_path)
        self.drawing = False
        self.last_point = None
        self.shapes = []
        self.parent = parent
        self.text_edit = None
        self.color = QColor(255, 0, 0)
        self.temp_shape = None
        self.temp_tracing = None

        layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Shape selection button
        self.shape_button = QPushButton("Select Shape")
        self.shape_button.clicked.connect(self.select_shape)
        button_layout.addWidget(self.shape_button)

        # Text button
        self.text_button = QPushButton("Add Text")
        self.text_button.clicked.connect(self.add_text)
        button_layout.addWidget(self.text_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        

    def select_shape(self):
        shapes = ["Rectangle", "Circle", "Triangle", "Line"]
        shape, ok = QInputDialog.getItem(self, "Select Shape", "Shape:", shapes, 0, False)
        self.color = QColorDialog.getColor()
        if ok:
            self.parent.selected_shape = shape

    def add_text(self):
        self.color = QColorDialog.getColor()
        self.parent.selected_shape = "Text"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.image)
        pen = QPen(self.color, 3)
        painter.setPen(pen)
        for shape in self.shapes:
            if shape['type'] == 'line':
                painter.drawLine(shape['start'], shape['end'])
            elif shape['type'] == 'rect':
                painter.drawRect(QRect(shape['start'], shape['end']))
            elif shape['type'] == 'circle':
                self.temp_tracing = QRect(shape['start'], shape['end'])
                painter.drawEllipse(self.temp_tracing)
            elif shape['type'] == 'triangle':
                self.temp_tracing = [
                    shape['start'],
                    QPoint(shape['end'].x(), shape['start'].y()),
                    QPoint((shape['start'].x() + shape['end'].x()) // 2, shape['end'].y())
                ]
                painter.drawPolygon(*self.temp_tracing)
            elif shape['type'] == 'text':
                painter.drawText(shape['start'], shape['text'])
        if hasattr(self, 'temp_shape') and self.temp_shape:
            if self.temp_shape['type'] == 'rect':
                painter.drawRect(QRect(self.temp_shape['start'], self.temp_shape['end']))
            elif self.temp_shape['type'] == 'circle':
                self.temp_tracing = QRect(self.temp_shape['start'], self.temp_shape['end'])
                painter.drawEllipse(self.temp_tracing)
            elif self.temp_shape['type'] == 'triangle':
                self.temp_tracing = [
                    self.temp_shape['start'],
                    QPoint(self.temp_shape['end'].x(), self.temp_shape['start'].y()),
                    QPoint((self.temp_shape['start'].x() + self.temp_shape['end'].x()) // 2, self.temp_shape['end'].y())
                ]
                painter.drawPolygon(*self.temp_tracing)


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position().toPoint()
            self.start_point = self.last_point  # Store the start point for shapes

            if self.parent.selected_shape == "Text":
                self.text_edit = QLineEdit(self)
                self.text_edit.move(self.last_point.x() - self.text_edit.width(), self.last_point.y() - self.text_edit.height())
                self.text_edit.setFixedWidth(200)
                self.text_edit.returnPressed.connect(self.finish_text)
                self.text_edit.show()
                self.text_edit.setFocus()

    def mouseMoveEvent(self, event):
        if self.drawing:
            current_point = event.position().toPoint()
            if self.parent.selected_shape == "None":
                self.shapes.append({'type': 'line', 'start': self.last_point, 'end': current_point, 'color': self.color})
                self.last_point = current_point
            elif self.parent.selected_shape == "Rectangle":
                self.temp_shape = {'type': 'rect', 'start': self.start_point, 'end': current_point, 'color': self.color}
            elif self.parent.selected_shape == "Circle":
                self.temp_shape = {'type': 'circle', 'start': self.start_point, 'end': current_point, 'color': self.color}
            elif self.parent.selected_shape == "Triangle":
                self.temp_shape = {'type': 'triangle', 'start': self.start_point, 'end': current_point, 'color': self.color}
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            if self.temp_shape:
                if self.parent.selected_shape == "Rectangle":
                    self.shapes.append(self.temp_shape)
                elif self.parent.selected_shape == "Circle":
                    self.shapes.append(self.temp_shape)
                elif self.parent.selected_shape == "Triangle":
                    self.shapes.append(self.temp_shape)
            self.temp_shape = None
            self.update()

    def finish_text(self):
        text = self.text_edit.text()
        self.shapes.append({'type': 'text', 'start': self.last_point, 'text': text, 'color': self.color})
        self.text_edit.deleteLater()
        self.text_edit = None
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScreenRecorderApp()
    window.show()
    sys.exit(app.exec())