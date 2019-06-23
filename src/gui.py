#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Imports
# Python
import operator
import yaml
import webbrowser
import copy

# PyQt5
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSignal, QModelIndex
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QTableView,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)

# Relative
from . import gaudireader


class TableSkeleton(QTableView):
    def __init__(self, window, parent=None):
        super(TableSkeleton, self).__init__(parent)
        self.window = window
        self.session = window.session
        self.setFont(QFont("Helvetica", 12))

        # Set the table model
        self.tm = TableModel(window.path, self)
        self.setModel(self.tm)

        # Set the minimum size
        self.setMinimumSize(400, 300)

        # Hide grid
        self.setShowGrid(True)

        # Hide vertical header
        vh = self.verticalHeader()
        vh.setVisible(False)

        # Set horizontal header properties
        self.hh = self.horizontalHeader()
        self.hh.setHighlightSections(False)
        self.hh.setStretchLastSection(True)
        self.hh.setSectionsMovable(True)

        # Set column width to fit contents
        self.resizeColumnsToContents()

        # Set row height
        nrows = len(self.tm.arraydata)
        for row in range(nrows):
            self.setRowHeight(row, 25)

        # Enable sorting
        self.setSortingEnabled(True)

        # Set selection
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selection = self.selectionModel()
        self.selection.selectionChanged.connect(self.handle_selection)
        self.deselection = None

    def handle_selection(self):

        if self.deselection:
            for model in self.deselection:
                self.tm.gaudimain.not_display(model)

        selection = [index.data() for index in self.selection.selectedRows()]

        self.deselection = selection

        for model in selection:
            self.tm.gaudimain.display(model)
        self.window.return_pressed()


class TableModel(QAbstractTableModel):
    def __init__(self, data, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.gaudimain = gaudireader.GaudiController(parent.session)
        self.gaudimain.add_gaudimodel(data)
        self.arraydata = self.gaudimain.gaudimodel[0].data
        self.headerdata = self.gaudimain.gaudimodel[0].headers

        self.backdoor = copy.deepcopy([self.arraydata, self.headerdata])

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
        self.order = order
        self.ncol = Ncol
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

    def write_output(self, path):
        out_data = {}
        out_data["GAUDI.objectives"] = self.gaudimain.gaudimodel[0].raw_data[
            "GAUDI.objectives"
        ]
        if "Cluster" in self.headerdata:
            out_data["GAUDI.results"] = {row[0]: row[1:-1] for row in self.arraydata}
        else:
            out_data["GAUDI.results"] = {row[0]: row[1:] for row in self.arraydata}
        with open(path, "w") as out:
            out.write(self.gaudimain.gaudimodel[0].first_line + "\n")
            out.write(yaml.safe_dump(out_data, default_flow_style=False))


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
            QPixmap(
                ":/icons/insilichem.png"
            ).scaled(100, 87.5, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        return logo

    def set_label(self):
        layout = QVBoxLayout()

        label0 = QLabel("Insilichem")
        label0.setFont(QFont("Helvetica", 20))
        label0.setStyleSheet("color:rgb(18,121,90)")
        layout.addWidget(label0)

        label1 = QLabel(
            'Developed by <a href="https://github.com/andresginera/">@andresginera</a>'
        )
        label1.setOpenExternalLinks(True)
        label1.setFont(QFont("Helvetica", 12))
        layout.addWidget(label1)

        label2 = QLabel("at Maréchal Group, UAB, Spain")
        label2.setFont(QFont("Helvetica", 12))
        layout.addWidget(label2)

        return layout


class QLabelClickable(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(QLabelClickable, self).__init__(parent)

    def mouseReleaseEvent(self, event):
        webbrowser.open("https://www.insilichem.com/")

