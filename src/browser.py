import sys
from PyQt5.QtWidgets import (
    QApplication,
    QPushButton,
    QMainWindow,
    QLabel,
    QFileDialog,
    QDialog,
    QVBoxLayout,
)
from PyQt5 import QtGui
from PyQt5.QtCore import QRect


class Window(QDialog):
    def __init__(self):
        super().__init__()

        self.title = "GaudiCreate"
        self.top = 200
        self.left = 500
        self.width = 300
        self.height = 250
        self.iconName = "./logo.png"

        self.InitIU()

    def InitIU(self):
        self.setWindowIcon(QtGui.QIcon(self.iconName))
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        vbox = QVBoxLayout()
        self.btn = QPushButton("Browse File")
        self.btn.clicked.connect(self.BrowseFile)
        vbox.addWidget(self.btn)

        self.label = QLabel("Hello")
        vbox.addWidget(self.label)

        self.setLayout(vbox)

        self.show()

    def BrowseFile(self):
        fname = QFileDialog.getOpenFileName(
            self, "Open File", "/home", "Gaudi-Output File (*.gaudi-output)"
        )

        filepath = fname[0]
        print(filepath)
        self.label.setText(filepath)


if __name__ == "__main__":
    App = QApplication(sys.argv)
    window = Window()
    sys.exit(App.exec())
