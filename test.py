from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
import sys

class CustomWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Fenêtre avec sous-entête")
        self.setMinimumSize(500, 400)  # Taille minimale

        ### === Sous-entête (juste sous la barre de titre native) === ###
        self.sub_header = QWidget(self)
        self.sub_header.setStyleSheet("background-color: #ddd; padding: 5px;")
        self.sub_header.setFixedHeight(40)

        # Bouton d'action dans la sous-entête
        self.action_button1 = QPushButton("Action 1", self.sub_header)
        self.action_button1.setStyleSheet("background-color: #bbb; border-radius: 5px;")

        self.action_button2 = QPushButton("Action 2", self.sub_header)
        self.action_button2.setStyleSheet("background-color: #bbb; border-radius: 5px;")

        # Layout de la sous-entête
        sub_header_layout = QHBoxLayout()
        sub_header_layout.addWidget(QLabel("Sous-entête :"))
        sub_header_layout.addWidget(self.action_button1)
        sub_header_layout.addWidget(self.action_button2)
        sub_header_layout.addStretch(1)
        self.sub_header.setLayout(sub_header_layout)

        ### === Contenu principal === ###
        self.main_widget = QWidget(self)
        self.main_widget.setStyleSheet("background-color: white;")

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.sub_header)  # Ajoute la sous-entête
        main_layout.addWidget(self.main_widget)  # Ajoute le contenu principal
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()
    sys.exit(app.exec())
