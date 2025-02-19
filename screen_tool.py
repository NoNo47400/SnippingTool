import sys
import os
import time
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QTimer, QRect
import subprocess
import os

os.environ["DISPLAY"] = ":0.0" # Ensure we use the correct display (X11)

class ScreenRecorderApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Screen Tool")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        # Screenshot
        self.capture_button = QPushButton("Capture Area")
        self.capture_button.clicked.connect(self.capture_screen)
        layout.addWidget(self.capture_button)

        self.image_label = QLabel("No capture taken")
        layout.addWidget(self.image_label)

        # Video recording
        self.record_button = QPushButton("Select Area and Record")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)

        self.timer_label = QLabel("")
        layout.addWidget(self.timer_label)

        self.setLayout(layout)

        self.recording = False
        self.record_process = None
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        self.capture_rect = None  # Selected area

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
                self.image_label.setText(f"Capture saved: {save_path}")
                self.image_label.setPixmap(QPixmap(save_path).scaled(200, 200))

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
            self.record_button.setText("Select Area and Record")
            self.timer.stop()
            self.timer_label.setText("Recording finished")

    def update_timer(self):
        """Displays the elapsed time during recording."""
        elapsed = int(time.time() - self.start_time)
        self.timer_label.setText(f"Recording time: {elapsed}s")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScreenRecorderApp()
    window.show()
    sys.exit(app.exec())