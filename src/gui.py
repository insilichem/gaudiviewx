import operator
import os
import re
import sys
import yaml
import webbrowser
import copy
from PyQt5.QtCore import (
    QAbstractTableModel,
    QVariant,
    Qt,
    QSize,
    pyqtSignal,
    QTimer,
    QModelIndex,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QTableView,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QGridLayout,
    QHeaderView,
    QToolBar,
    QAction,
    QFileDialog,
    QPushButton,
    QDialog,
    QGroupBox,
    QAbstractButton,
    QLabel,
)
from PyQt5.QtGui import QIcon, QPixmap, QMouseEvent
from PyQt5 import QtGui
import chimerax.core.io
import chimerax.core.session
from chimerax.ui import MainToolWindow
from . import gaudireader
from chimerax.core.commands import run, concise_model_spec


class MainWindow(QTableView):
    def __init__(self, datain, session, parent=None):
        super(MainWindow, self).__init__(parent)

        self.path = os.path.dirname(datain)
        self.session = session

        # create the view

        # set the table model
        self.tm = MyTableModel(datain, self)
        self.setModel(self.tm)
        # set the minimum size
        self.setMinimumSize(400, 300)

        # hide grid
        self.setShowGrid(True)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selection = self.selectionModel()
        self.selection.selectionChanged.connect(self.handleSelectionChanged)

        # set the font

        # hide vertical header
        vh = self.verticalHeader()
        vh.setVisible(False)

        # set horizontal header properties
        self.hh = self.horizontalHeader()
        self.hh.setHighlightSections(False)
        # hh.setStretchLastSection(True)
        # self.hh.setSectionResizeMode(QHeaderView.Stretch)

        # set column width to fit contents
        self.resizeColumnsToContents()

        # set row height
        # nrows = len(self.tabledata)
        # for row in range(nrows):
        #     self.setRowHeight(row, 30)

        # enable sorting
        self.setSortingEnabled(True)

        self.models = self.tm.models

    def handleSelectionChanged(self, selected, deselected):

        selection = retrieve_models(selected, self.hh, self.models)
        deselection = retrieve_models(deselected, self.hh, self.models)

        if deselection:
            for model in deselection:
                hide(self.session, model)

        for model in selection:
            if not all(
                i in [actmodel._name for actmodel in self.session.models.list()]
                for i in [m._name for m in model]
            ):
                self.session.models.add(model)
            else:
                show(self.session, model)


def retrieve_models(selected, header, models):

    names = [
        selected.indexes()[i]
        for i in range(0, len(selected.indexes()) - (len(header) - 1), len(header))
    ]
    selection = [models[index.data()] for index in names]

    return selection


def show(session, models):
    run(session, "show %s target m" % concise_model_spec(session, models))


def hide(session, models):
    run(session, "hide %s target m" % concise_model_spec(session, models))


class MyTableModel(QAbstractTableModel):
    def __init__(self, data, parent=None, *args):
        with open(data, "r") as f:
            datain = yaml.load(f)
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = [[k] + v for k, v in datain["GAUDI.results"].items()]
        self.backdoor = copy.copy(self.arraydata)
        headerdata = ["Filename"] + datain["GAUDI.objectives"]
        self.headerdata = list(map(lambda text: text.replace(" (", "\n("), headerdata))

        self.gaudimodel = gaudireader.GaudiModel(data, parent.session)
        self.models = self.gaudimodel.save_models()

    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        return len(self.headerdata)

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(list(self.arraydata)[index.row()][index.column()])

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headerdata[col])
        return QVariant()

    def sort(self, Ncol, order):
        """Sort table by given column number.
        """
        self.layoutAboutToBeChanged.emit()
        self.arraydata = sorted(self.arraydata, key=operator.itemgetter(Ncol))
        if order == Qt.DescendingOrder:
            self.arraydata.reverse()
        self.layoutChanged.emit()

    def removeRows(self, row, rows=1, index=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), row, row + rows - 1)
        self.arraydata = self.arraydata[:row] + self.arraydata[row + rows :]
        self.endRemoveRows()

        return True

    def insertRows(self, position, rows=1, parent=QModelIndex()):

        self.beginInsertRows(QModelIndex(), position, position + rows - 1)
        self.arraydata = self.arraydata[:]
        self.endInsertRows()

        return True


class MyToolBar(QToolBar):
    def __init__(self, table, session, parent=None, *args):
        QToolBar.__init__(self, parent, *args)

        self.table = table
        self.session = session
        self.addAction(QAction(QIcon("icon_folder"), "Open New File", self))
        self.addAction(QAction(QIcon("icon_save"), "Save File", self))

        self.actionTriggered[QAction].connect(self.toolbtnpressed)

    def toolbtnpressed(self, a):
        if a.text() == "Open New File":
            self.nameFile = BrowserFile().path
            if self.nameFile:
                self.table.tm.layoutAboutToBeChanged.emit()
                self.table.tm.removeRows(0, len(self.table.tm.arraydata))
                self.table.tm = MyTableModel(self.nameFile, self)
                with open(self.nameFile, "r") as f:
                    data = yaml.load(f)
                datarray = [[k] + v for k, v in data["GAUDI.results"].items()]
                header = ["Filename"] + list(
                    map(lambda text: text.replace(" (", "\n("), data["GAUDI.results"])
                )
                self.table.tm.arraydata = datarray
                self.table.tm.headerdata = header
                self.table.tm.layoutChanged.emit()
                run(self.session, "close")
        elif a.text() == "Save File":
            print("File saved")


class BrowserFile(QWidget):
    def __init__(self):
        super().__init__()
        self.path = None
        self.title = "Browser File"
        self.left = 10
        self.top = 10
        self.width = 800
        self.height = 600
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.openFileNameDialog()

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Browser File",
            "",
            "Gaudi-Output Files (*.gaudi-output);;All Files (*)",
            options=options,
        )
        if fileName.endswith("gaudi-output"):
            self.path = fileName


class LogoCopyright(QHBoxLayout):
    def __init__(self, parent=None, *args):
        QHBoxLayout.__init__(self, parent, *args)
        self.addStretch(1)
        self.addWidget(self.set_logo())
        self.addLayout(self.set_label())
        self.addStretch(1)

    def set_logo(self):
        logo = QLabelClickable()
        logo.setToolTip("Insilichem logo")
        logo.setCursor(Qt.PointingHandCursor)
        logo.setPixmap(
            QtGui.QPixmap(
                "/home/andres/practicas/chimerax/tut_tool_qt/src/insilichem.png"
            ).scaled(112, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        logo.setAlignment(Qt.AlignCenter)

        return logo

    def set_label(self):
        layout = QVBoxLayout()

        label0 = QLabel("Insilichem")
        label0.setFont(QtGui.QFont("Helvetica", 20))
        label0.setStyleSheet("color:rgb(18,121,90)")
        layout.addWidget(label0)

        label1 = QLabel(
            'Developed by <a href="https://github.com/andresginera/">@andresginera</a>'
        )
        label1.setOpenExternalLinks(True)
        label1.setFont(QtGui.QFont("Helvetica", 12))
        layout.addWidget(label1)

        label2 = QLabel("at Maréchal Group, UAB, Spain")
        label2.setFont(QtGui.QFont("Helvetica", 12))
        layout.addWidget(label2)

        return layout


class QLabelClickable(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(QLabelClickable, self).__init__(parent)

    def mouseReleaseEvent(self, event):
        webbrowser.open("https://www.insilichem.com/")
