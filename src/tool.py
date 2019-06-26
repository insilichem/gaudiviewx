#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############
#   GaudiViewX: UCSF ChimeraX extension to
#   explore and analyze GaudiMM solutions

#   https://github.com/insilichem/gaudiviewx

#   Copyright 2019 Andrés Giner Antón, Jaime Rodriguez-Guerra
#   and Jean-Didier Marechal

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
##############

# Imports
# Python
import yaml
import copy
import os

# ChimeraX
from chimerax.core.tools import ToolInstance
from chimerax.ui import MainToolWindow
from chimerax.core.commands import run

# PyQt5
from PyQt5.QtCore import QResource
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QWidget,
    QMessageBox,
    QLabel,
)

# Relative
from . import gui, toolbar

# Resource
QResource.registerResource(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources.rrc")
)


class GaudiViewXTool(ToolInstance):

    SESSION_ENDURING = True  # Does this instance persist when session closes
    SESSION_SAVE = True  # We do save/restore in sessions
    help = "help:user/tools/guide.html"

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        self.display_name = "GaudiViewX"

        self.tool_window = MainToolWindow(self)
        self._build_ui()

    def _build_ui(self):

        main_layout = QVBoxLayout()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        self.path, _ = QFileDialog.getOpenFileName(
            QWidget(),
            "Browser File",
            "",
            "Gaudi-Output Files (*.gaudi-output);;All Files (*)",
            options=options,
        )

        if self.path:

            self.table = gui.TableSkeleton(self)
            main_layout.addWidget(toolbar.MyToolBar(self))
            hbox = QHBoxLayout()

            hbox.addWidget(self.table)

            # Undo
            self.data_save0, self.data_save1, self.data_save2, self.data_save3, self.data_save4 = [
                copy.deepcopy([self.table.tm.arraydata, self.table.tm.headerdata])
                for i in range(5)
            ]

            # Box bottons
            box_layout = QVBoxLayout()
            box_layout.addStretch(1)

            add_butn = QPushButton("Add...")
            add_butn.clicked.connect(self.add_new_data)
            add_butn.setFont(QFont("Helvetica", 12))
            box_layout.addWidget(add_butn)

            self.delete_butn = QPushButton("Delete")
            self.delete_butn.setEnabled(False)
            self.delete_butn.setFont(QFont("Helvetica", 12))
            self.delete_butn.clicked.connect(self.remove_selected_rows)

            self.selection = self.table.selectionModel()
            self.selection.selectionChanged.connect(self.activate_delete_button)

            box_layout.addWidget(self.delete_butn)

            undo_butn = QPushButton("Undo")
            undo_butn.clicked.connect(self.undo)
            undo_butn.setFont(QFont("Helvetica", 12))
            box_layout.addWidget(undo_butn)

            box_layout.addSpacing(25)

            reset_butn = QPushButton("RESET")
            reset_butn.setFont(QFont("Helvetica", 12))
            reset_butn.setStyleSheet("color: rgb(206, 22,22);")
            reset_butn.clicked.connect(self.reset_changes)
            box_layout.addWidget(reset_butn)

            box_layout.addStretch(1)

            hbox.addLayout(box_layout)
            main_layout.addLayout(hbox)

            self.command_layout = QHBoxLayout()

            self.label = QLabel("Command:")
            self.command_layout.addWidget(self.label)
            self.line_edit = QLineEdit()
            self.line_edit.setPlaceholderText("It will be applied to all solutions")
            self.line_edit.returnPressed.connect(self.return_pressed)
            self.command_layout.addWidget(self.line_edit)

            main_layout.addSpacing(10)
            main_layout.addLayout(self.command_layout)
            main_layout.addSpacing(10)

            main_layout.addLayout(gui.LogoCopyright())

            #######################

            self.tool_window.ui_area.setLayout(main_layout)
            self.tool_window.manage("side")

        else:

            self.tool_window.destroy()

    def add_new_data(self):

        self.update_saves()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        name_file, _ = QFileDialog.getOpenFileName(
            QWidget(),
            "Browser File",
            "",
            "Gaudi-Output Files (*.gaudi-output);;All Files (*)",
            options=options,
        )
        if name_file:
            if equal_objectives(name_file) == self.table.tm.headerdata:
                self.table.tm.gaudimain.add_gaudimodel(name_file)
                self.table.tm.layoutAboutToBeChanged.emit()
                self.table.tm.arraydata = (
                    self.table.tm.arraydata
                    + self.table.tm.gaudimain.gaudimodel[-1].data
                )
                self.table.tm.layoutChanged.emit()
                nrows = len(self.table.tm.arraydata)
                for row in range(nrows):
                    self.table.setRowHeight(row, 25)
            else:
                mesbox = QMessageBox()
                mesbox.setIcon(QMessageBox.Warning)
                mesbox.setText(
                    "The objectives of the new file are not the same as the original output file."
                )
                mesbox.setStandardButtons(QMessageBox.Ok)
                mesbox.exec()

    def reset_changes(self):

        self.update_saves()
        self.table.tm.layoutAboutToBeChanged.emit()
        self.table.tm.arraydata, self.table.tm.headerdata = self.table.tm.backdoor
        self.table.tm.layoutChanged.emit()
        nrows = len(self.table.tm.arraydata)
        for row in range(nrows):
            self.table.setRowHeight(row, 25)

    def activate_delete_button(self, selected):
        if self.delete_butn.isEnabled() == False:
            self.delete_butn.setEnabled(True)

    def remove_selected_rows(self):

        self.update_saves()
        indexes = self.table.selectionModel().selectedRows()
        self.table.tm.removeRows(indexes[0].row(), len(indexes))
        self.delete_butn.setEnabled(False)

    def undo(self):

        self.table.tm.layoutAboutToBeChanged.emit()

        if [self.table.tm.arraydata, self.table.tm.headerdata] == self.data_save4:
            return
        elif [self.table.tm.arraydata, self.table.tm.headerdata] == self.data_save3:
            self.table.tm.arraydata, self.table.tm.headerdata = self.data_save4
        elif [self.table.tm.arraydata, self.table.tm.headerdata] == self.data_save2:
            self.table.tm.arraydata, self.table.tm.headerdata = self.data_save3
        elif [self.table.tm.arraydata, self.table.tm.headerdata] == self.data_save1:
            self.table.tm.arraydata, self.table.tm.headerdata = self.data_save2
        elif [self.table.tm.arraydata, self.table.tm.headerdata] == self.data_save0:
            self.table.tm.arraydata, self.table.tm.headerdata = self.data_save1
        else:
            self.table.tm.arraydata, self.table.tm.headerdata = self.data_save0
        self.table.tm.layoutChanged.emit()

        nrows = len(self.table.tm.arraydata)
        for row in range(nrows):
            self.table.setRowHeight(row, 25)

    def update_saves(self):

        self.data_save4 = copy.deepcopy(self.data_save3)
        self.data_save3 = copy.deepcopy(self.data_save2)
        self.data_save2 = copy.deepcopy(self.data_save1)
        self.data_save1 = copy.deepcopy(self.data_save0)
        self.data_save0 = copy.deepcopy(
            [self.table.tm.arraydata, self.table.tm.headerdata]
        )

    def return_pressed(self):
        run(self.session, "%s" % self.line_edit.text())


def equal_objectives(path):
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    header = ["Filename"] + list(
        map(lambda text: text.split()[0], data["GAUDI.objectives"])
    )
    return header
