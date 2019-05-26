# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===

import sys
import yaml
import copy
from chimerax.core.tools import ToolInstance
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
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QFileDialog,
    QWidget,
    QMessageBox,
    QMenuBar,
    QSplitter,
    QFrame,
)
from PyQt5 import QtGui
from PyQt5.QtGui import QKeySequence
from . import gui, gaudireader


class GaudiViewXTool(ToolInstance):

    # Inheriting from ToolInstance makes us known to the ChimeraX tool mangager,
    # so we can be notified and take appropriate action when sessions are closed,
    # saved, or restored, and we will be listed among running tools and so on.
    #
    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end.

    SESSION_ENDURING = False  # Does this instance persist when session closes
    SESSION_SAVE = True  # We do save/restore in sessions
    help = "help:user/tools/guide.html"
    # Let ChimeraX know about our help page

    def __init__(self, session, tool_name):
        # 'session'   - chimerax.core.session.Session instance
        # 'tool_name' - string

        # Initialize base class.
        super().__init__(session, tool_name)

        # Set name displayed on title bar (defaults to tool_name)
        # Must be after the superclass init, which would override it.
        self.display_name = "GaudiViewX"

        # Create the main window for our tool.  The window object will have
        # a 'ui_area' where we place the widgets composing our interface.
        # The window isn't shown until we call its 'manage' method.
        #
        # Note that by default, tool windows are only hidden rather than
        # destroyed when the user clicks the window's close button.  To change
        # this behavior, specify 'close_destroys=True' in the MainToolWindow
        # constructor.
        from chimerax.ui import MainToolWindow

        self.tool_window = MainToolWindow(self)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill_context_menu method
        # self.tool_window.fill_context_menu = self.fill_context_menu

        # Our user interface is simple enough that we could probably inline
        # the code right here, but for any kind of even moderately complex
        # interface, it is probably better to put the code in a method so
        # that this __init__ method remains readable.
        self._build_ui()

    def _build_ui(self):
        # Put our widgets in the tool window

        # We will use an editable single-line text input field (QLineEdit)
        # with a descriptive text label to the left of it (QLabel).  To
        # arrange them horizontally side by side we use QHBoxLayout

        # layout = QHBoxLayout()
        # layout.addWidget(QLabel("Log this text:"))
        # self.line_edit = QLineEdit()

        # # Arrange for our 'return_pressed' method to be called when the
        # # user presses the Return key
        # self.line_edit.returnPressed.connect(self.return_pressed)
        # layout.addWidget(self.line_edit)

        # # Set the layout as the contents of our window
        # self.tool_window.ui_area.setLayout(layout)

        vbox = QVBoxLayout()
        data = gui.BrowserFile().path

        #####################################

        if data:

            self.table = gui.MainWindow(data, self.session)
            vbox.addWidget(gui.MyToolBar(self))
            line = QFrame()
            hbox = QHBoxLayout()

            hbox.addWidget(self.table)

            # Undo
            self.data_save0 = copy.copy(
                [self.table.tm.arraydata, self.table.tm.headerdata]
            )
            self.data_save1 = copy.copy(
                [self.table.tm.arraydata, self.table.tm.headerdata]
            )
            self.data_save2 = copy.copy(
                [self.table.tm.arraydata, self.table.tm.headerdata]
            )
            self.data_save3 = copy.copy(
                [self.table.tm.arraydata, self.table.tm.headerdata]
            )
            self.data_save4 = copy.copy(
                [self.table.tm.arraydata, self.table.tm.headerdata]
            )

            # Box bottons
            box_layout = QVBoxLayout()
            box_layout.addStretch(1)

            add_butn = QPushButton("Add...")
            add_butn.clicked.connect(self.add_new_data)
            add_butn.setFont(QtGui.QFont("Helvetica", 11))
            box_layout.addWidget(add_butn)

            self.delete_butn = QPushButton("Delete")
            self.delete_butn.setEnabled(False)
            self.delete_butn.setFont(QtGui.QFont("Helvetica", 11))
            self.delete_butn.clicked.connect(self.remove_selected_rows)

            self.selection = self.table.selectionModel()
            self.selection.selectionChanged.connect(self.activate_delete_button)

            box_layout.addWidget(self.delete_butn)

            undo_butn = QPushButton("Undo")
            undo_butn.clicked.connect(self.undo)
            undo_butn.setFont(QtGui.QFont("Helvetica", 11))
            undo_butn.setShortcut(QKeySequence("Ctrl+Z"))
            box_layout.addWidget(undo_butn)

            box_layout.addSpacing(25)

            reset_butn = QPushButton("Reset")
            reset_butn.setFont(QtGui.QFont("Helvetica", 11))
            reset_butn.setStyleSheet("color: rgb(206, 22,22);")
            reset_butn.clicked.connect(self.reset_changes)
            box_layout.addWidget(reset_butn)

            box_layout.addStretch(1)

            hbox.addLayout(box_layout)
            vbox.addLayout(hbox)
            vbox.addSpacing(25)

            vbox.addLayout(gui.LogoCopyright())

            #######################

            self.tool_window.ui_area.setLayout(vbox)

            # Show the window on the user-preferred side of the ChimeraX
            # main window
            self.tool_window.manage("side")

        else:

            self.tool_window.destroy()

    def add_new_data(self):

        self.update_saves()
        add_file = gui.BrowserFile().path
        if add_file:
            add_gaudimodel = gaudireader.GaudiModel(add_file, self.session)
            if add_gaudimodel.headers == self.table.tm.headerdata:
                self.table.tm.layoutAboutToBeChanged.emit()
                self.table.tm.arraydata = self.table.tm.arraydata + add_gaudimodel.data
                self.table.tm.layoutChanged.emit()
                nrows = len(self.table.tm.arraydata)
                for row in range(nrows):
                    self.table.setRowHeight(row, 25)
                self.table.models.update(add_gaudimodel.save_models())
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

    def activate_delete_button(self, selected):
        if self.delete_butn.isEnabled() == False:
            self.delete_butn.setEnabled(True)

    def remove_selected_rows(self):

        self.update_saves()
        indexes = self.table.selectionModel().selectedRows()
        self.table.tm.removeRows(indexes[0].row(), len(indexes))

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

    def update_saves(self):

        self.data_save4 = copy.copy(self.data_save3)
        self.data_save3 = copy.copy(self.data_save2)
        self.data_save2 = copy.copy(self.data_save1)
        self.data_save1 = copy.copy(self.data_save0)
        self.data_save0 = copy.copy([self.table.tm.arraydata, self.table.tm.headerdata])

    def return_pressed(self):
        # The use has pressed the Return key; log the current text as HTML
        from chimerax.core.commands import run

        # ToolInstance has a 'session' attribute...
        run(self.session, "log html %s" % self.line_edit.text())

    def fill_context_menu(self, menu, x, y):
        # Add any tool-specific items to the given context menu (a QMenu instance).
        # The menu will then be automatically filled out with generic tool-related actions
        # (e.g. Hide Tool, Help, Dockable Tool, etc.)
        #
        # The x,y args are the x() and y() values of QContextMenuEvent, in the rare case
        # where the items put in the menu depends on where in the tool interface the menu
        # was raised.
        from PyQt5.QtWidgets import QAction

        clear_action = QAction("Clear", menu)
        clear_action.triggered.connect(lambda *args: self.line_edit.clear())
        menu.addAction(clear_action)

    def take_snapshot(self, session, flags):
        return {"version": 1, "current text": self.line_edit.text()}

    @classmethod
    def restore_snapshot(class_obj, session, data):
        # Instead of using a fixed string when calling the constructor below, we could
        # have saved the tool name during take_snapshot() (from self.tool_name, inherited
        # from ToolInstance) and used that saved tool name.  There are pros and cons to
        # both approaches.
        inst = class_obj(session, "GaudiViewX")
        inst.line_edit.setText(data["current text"])
        return inst

