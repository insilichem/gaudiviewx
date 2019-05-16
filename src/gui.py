import operator
import os
import re
import sys
import yaml
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, QSize, pyqtSignal, QTimer
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
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5 import QtGui
import chimerax.core.io
import chimerax.core.session
from chimerax.ui import MainToolWindow
import weakref
from . import gaudireader
from chimerax.core.commands import run, concise_model_spec


def show(models, session):
    run(session, "show %s target m" % concise_model_spec(session, models))


class MainWindow(QTableView):
    def __init__(self, datain, session, parent=None):
        super(MainWindow, self).__init__(parent)

        self.path = os.path.dirname(datain)
        self.session = session
        self.models_active = []

        # create the view

        # set the table model
        tm = MyTableModel(datain, self)
        self.setModel(tm)
        # set the minimum size
        self.setMinimumSize(400, 400)

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
        self.hh.setSectionResizeMode(QHeaderView.Stretch)

        # set column width to fit contents
        self.resizeColumnsToContents()

        # set row height
        # nrows = len(self.tabledata)
        # for row in range(nrows):
        #     self.setRowHeight(row, 30)

        # enable sorting
        self.setSortingEnabled(True)

        self.models = tm.models

    def handleSelectionChanged(self, selected, deselected):

        from chimerax.core.commands import run, concise_model_spec

        name_selected = [
            selected.indexes()[i]
            for i in range(
                0, len(selected.indexes()) - (len(self.hh) - 1), len(self.hh)
            )
        ]
        selection = [self.models[index.data()] for index in name_selected]

        name_deselected = [
            deselected.indexes()[i]
            for i in range(
                0, len(deselected.indexes()) - (len(self.hh) - 1), len(self.hh)
            )
        ]
        deselection = [self.models[index.data()] for index in name_deselected]

        if deselection:
            for model in deselection:
                run(
                    self.session,
                    "hide %s target m" % concise_model_spec(self.session, model),
                )

        for model in selection:
            if not all(
                i in [actmodel._name for actmodel in self.session.models.list()]
                for i in [m._name for m in model]
            ):
                self.session.models.add(model)
            else:
                run(
                    self.session,
                    "show %s target m" % concise_model_spec(self.session, model),
                )


class MyTableModel(QAbstractTableModel):
    def __init__(self, data, parent=None, *args):
        """ datain: a list of lists
            headerdata: a list of strings
        """
        with open(data, "r") as f:
            datain = yaml.load(f)
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = [[k] + v for k, v in datain["GAUDI.results"].items()]
        headerdata = ["Filename"] + datain["GAUDI.objectives"]
        self.headerdata = list(map(lambda text: text.replace(" (", "\n("), headerdata))

        gaudim = gaudireader.GaudiModel(data, parent.session)
        self.models = gaudim.save_models()

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


class QLabelClickable(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QLabelClickable, self).__init__(parent)

    def mousePressEvent(self, event):
        self.ultimo = "Clic"

    def mouseReleaseEvent(self, event):
        if self.ultimo == "Clic":
            QTimer.singleShot(
                MainToolWindow.instance().doubleClickInterval(),
                self.performSingleClickAction,
            )
        else:
            # Realizar acción de doble clic.
            self.clicked.emit(self.ultimo)

    def mouseDoubleClickEvent(self, event):
        self.ultimo = "Doble Clic"

    def performSingleClickAction(self):
        if self.ultimo == "Clic":
            self.clicked.emit(self.ultimo)


class MyToolBar(QToolBar):
    def __init__(self, parent=None, *args):
        QToolBar.__init__(self, parent, *args)

        self.addAction(QAction(QIcon("icon_folder"), "Open New File", self))
        print(os.path.abspath("."))

        self.addAction(QAction(QIcon("icon_save"), "Save File", self))

        self.actionTriggered[QAction].connect(self.toolbtnpressed)

    def toolbtnpressed(self, a):
        if a.text() == "Open New File":
            self.nameFile = BrowserFile()
        elif a.text() == "Save File":
            print("File saved")


class BrowserFile(QWidget):
    def __init__(self):
        super().__init__()
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

