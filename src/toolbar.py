import operator
import copy
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QToolBar,
    QAction,
    QFileDialog,
    QPushButton,
    QDialog,
    QGroupBox,
    QLabel,
    QComboBox,
    QRadioButton,
    QDoubleSpinBox,
    QButtonGroup,
    QProgressDialog,
    QScrollArea,
    QFrame,
)
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIcon, QPixmap, QRegion
from chimerax.core.geometry import align_points
from chimerax.core.commands import run
from . import gaudireader, gui


class MyToolBar(QToolBar):
    def __init__(self, window, parent=None, *args):
        QToolBar.__init__(self, parent, *args)

        self.window = window
        self.table = window.table
        self.session = window.session
        self.addAction(QAction(QIcon("icon_folder"), "Open", self))
        self.addAction(QAction(QIcon("icon_save"), "Save", self))
        self.addSeparator()
        self.addAction(
            QAction(
                QIcon(
                    "/home/andres/practicas/chimerax/gaudiviewx/src/icons/filter.png"
                ),
                "Filter",
                self,
            )
        )
        self.addAction(
            QAction(
                QIcon(
                    "/home/andres/practicas/chimerax/gaudiviewx/src/icons/clustering.png"
                ),
                "Clustering",
                self,
            )
        )

        self.addSeparator()
        self.addAction(
            QAction(
                QIcon("/home/andres/practicas/chimerax/gaudiviewx/src/icons/help.png"),
                "Help",
                self,
            )
        )
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.actionTriggered[QAction].connect(self.toolbtnpressed)

    def toolbtnpressed(self, action):
        if action.text() == "Open":
            self.add_file()
        elif action.text() == "Save":
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            filename, _ = QFileDialog.getSaveFileName(
                QWidget(),
                "Save File",
                "",
                "Gaudi-Output Files (*.gaudi-output);;All Files (*)",
                options=options,
            )
            if not filename.endswith(".gaudi-output"):
                filename += ".gaudi-output"
            if filename:
                self.table.tm.write_output(filename)
        elif action.text() == "Filter":
            FilterBox(self)
        elif action.text() == "Clustering":
            ClusteringBox(self)
        elif action.text() == "Help":
            self.window.display_help()

    def add_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        name_file, _ = QFileDialog.getOpenFileName(
            self,
            "Browser File",
            "",
            "Gaudi-Output Files (*.gaudi-output);;All Files (*)",
            options=options,
        )

        if name_file:
            self.window.update_saves()
            self.table.tm.layoutAboutToBeChanged.emit()
            self.table.tm.removeRows(0, len(self.table.tm.arraydata))
            self.gaudimain = gaudireader.GaudiController(self.session)
            self.gaudimain.add_gaudimodel(name_file)
            self.table.tm.arraydata = self.gaudimain.gaudimodel[0].data
            self.table.tm.headerdata = self.gaudimain.gaudimodel[0].headers
            self.window.delete_butn.setEnabled(False)
            self.table.tm.layoutChanged.emit()
            nrows = len(self.table.tm.arraydata)
            for row in range(nrows):
                self.table.setRowHeight(row, 25)
            run(self.session, "close")

            self.backdoor = copy.deepcopy(
                [self.table.tm.arraydata, self.table.tm.headerdata]
            )


class FilterBox(QDialog):
    def __init__(self, toolbar, parent=None, *args):
        QDialog.__init__(self, parent, *args)
        self.setWindowTitle("Filtering")
        self.setWindowIcon(
            QIcon("/home/andres/practicas/chimerax/gaudiviewx/src/icons/filter.png")
        )

        self.setFixedSize(self.minimumSize())
        self.toolbar = toolbar
        box = QVBoxLayout()
        self.setLayout(box)
        self.scroll = QScrollArea(self)
        box.addWidget(QLabel("Keep solutions with..."))
        box.addWidget(self.scroll)
        self.scroll.setWidgetResizable(True)
        scroll_content = QWidget(self.scroll)
        self.scroll_layout = QVBoxLayout(scroll_content)
        scroll_content.setLayout(self.scroll_layout)

        first = FilterCondition(self.toolbar, widgets=None, first=True)
        self.scroll_layout.addWidget(first)
        self.widgets = [first]

        # self.scroll_layout.addStretch(1)
        self.scroll.setFixedHeight(200)
        self.scroll.setFixedWidth(400)

        self.run_butn = QPushButton("Filter!")
        self.run_butn.clicked.connect(self.run_filter)
        self.run_butn.setFixedSize(100, 30)
        last_layout = QHBoxLayout()

        self.add_button = QPushButton()
        self.add_button.setIcon(
            QIcon("/home/andres/practicas/chimerax/gaudiviewx/src/icons/add.png")
        )
        self.add_button.setFixedHeight(30)
        self.add_button.clicked.connect(self.add_one)

        last_layout.addWidget(self.add_button)
        last_layout.addStretch(1)
        last_layout.addWidget(self.run_butn)
        last_layout.addStretch(1)
        last_layout.addSpacing(20)

        box.addLayout(last_layout)

        self.scroll.setWidget(scroll_content)

        self.exec()

    def add_one(self):
        new = FilterCondition(self.toolbar, widgets=self.widgets)
        self.scroll_layout.addWidget(new)
        self.widgets.append(new)
        # self.scroll_layout.addStretch(2)

    def run_filter(self):
        self.toolbar.window.update_saves()
        filter_conditions = [[]]
        index = 0
        w = self.widgets.pop(0)
        filter_conditions[index].append(
            [
                w.objective_combo.currentText(),
                w.logicbox.currentText(),
                w.number_box.value(),
            ]
        )

        for w in self.widgets:
            if w.add_or.text() == " AND":
                filter_conditions[index].append(
                    [
                        w.objective_combo.currentText(),
                        w.logicbox.currentText(),
                        w.number_box.value(),
                    ]
                )
            else:
                index += 1
                filter_conditions.append(
                    [
                        [
                            w.objective_combo.currentText(),
                            w.logicbox.currentText(),
                            w.number_box.value(),
                        ]
                    ]
                )

        filtered_array = []
        for condition in filter_conditions:
            conditional_array = copy.deepcopy(self.toolbar.table.tm.arraydata)
            for w in condition:
                index = self.toolbar.table.tm.headerdata.index(w[0])
                if w[1] == ">":
                    a = greater(index, conditional_array, w[2])
                elif w[1] == "<":
                    a = lesser(index, conditional_array, w[2])
                elif w[1] == "=":
                    a = equal(index, conditional_array, w[2])
                elif w[1] == "≥":
                    a = greater_equal(index, conditional_array, w[2])
                elif w[1] == "≤":
                    a = lesser_equal(index, conditional_array, w[2])
                elif w[1] == "≠":
                    a = not_equal(index, conditional_array, w[2])
                conditional_array = a
            filtered_array.extend(conditional_array)

        unique_fa = []
        for row in filtered_array:
            if not row in unique_fa:
                unique_fa.append(row)

        self.toolbar.table.tm.arraydata = unique_fa
        self.toolbar.table.tm.layoutChanged.emit()
        self.hide()


def greater(index, array, threshold):
    new_array = []
    for row in array:
        if float(row[index]) > threshold:
            new_array.append(row)
    array = new_array

    return array


def greater_equal(index, array, threshold):
    new_array = []
    for row in array:
        if not float(row[index]) < threshold:
            new_array.append(row)
    array = new_array

    return array


def equal(index, array, threshold):
    new_array = []
    for row in array:
        if float(row[index]) == threshold:
            new_array.append(row)
    array = new_array

    return array


def not_equal(index, array, threshold):
    new_array = []
    for row in array:
        if float(row[index]) != threshold:
            new_array.append(row)
    array = new_array

    return array


def lesser(index, array, threshold):
    new_array = []
    for row in array:
        if float(row[index]) < threshold:
            new_array.append(row)
    array = new_array

    return array


def lesser_equal(index, array, threshold):
    new_array = []
    for row in array:
        if not float(row[index]) > threshold:
            new_array.append(row)
    array = new_array

    return array


class FilterCondition(QFrame):
    def __init__(self, toolbar, widgets, first=False, parent=None, *args):
        self.toolbar = toolbar
        self.widgets = widgets
        QFrame.__init__(self, parent, *args)

        self.vbox = QHBoxLayout()

        self.add_or = None
        if first == False:
            self.add_or = ToogleAndOr()
            self.vbox.addWidget(self.add_or)

        self.objective_combo = QComboBox()
        for objective in self.toolbar.table.tm.headerdata[1:]:
            if objective != "Cluster":
                self.objective_combo.addItem(objective)
        self.vbox.addWidget(self.objective_combo)

        self.logicbox = QComboBox()
        self.logicbox.setFixedWidth(40)
        self.logicbox.addItems([">", "<", "=", "≥", "≤", "≠"])
        self.vbox.addWidget(self.logicbox)

        self.number_box = QDoubleSpinBox()
        self.number_box.setSingleStep(0.05)
        self.number_box.setMaximum(9999.99)
        self.number_box.setMinimum(-9999.99)
        self.number_box.setFixedWidth(85)
        self.vbox.addWidget(self.number_box)

        self.remove_button = None
        if first == False:
            self.remove_button = QCancelBotton(self)
            self.remove_button.setToolTip("Remove conditional")
            icono = QPixmap(
                "/home/andres/practicas/chimerax/gaudiviewx/src/icons/cross.png"
            ).scaled(15, 15, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.remove_button.setPixmap(icono)

            self.remove_button.setCursor(Qt.PointingHandCursor)
            self.remove_button.setAlignment(Qt.AlignCenter)

            self.remove_button.setStyleSheet(
                "border: 1px solid #8f8f91; border-radius: 10px;\
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, top:\
            0 #f6f7fa, stop: 1 #dadbde0)"
            )

            self.vbox.addWidget(self.remove_button)
            self.remove_button.setFixedWidth(25)
            self.remove_button.setFixedHeight(25)
        else:
            self.vbox.addSpacing(30)

        self.setLayout(self.vbox)
        self.setFrameShape(self.Shape())

    def remove(self):
        self.close()
        self.widgets.remove(self)


class ToogleAndOr(QPushButton):
    def __init__(self, parent=None):
        super(ToogleAndOr, self).__init__(parent)

        self.setText(" AND")
        self.setStyleSheet("color: blue")
        self.clicked.connect(self.change)
        self.setIcon(
            QIcon("/home/andres/practicas/chimerax/gaudiviewx/src/icons/reload.png")
        )
        self.setFixedWidth(70)

    def change(self):
        if self.text() == " AND":
            self.setText(" OR")
            self.setStyleSheet("color: green")
        else:
            self.setText(" AND")
            self.setStyleSheet("color: blue")


class QCancelBotton(QLabel):
    clicked = pyqtSignal()

    def __init__(self, widget, parent=None):
        super(QCancelBotton, self).__init__(parent)
        self.widget = widget

    def mouseReleaseEvent(self, event):
        self.widget.close()
        self.widget.widgets.remove(self.widget)
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 10px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:\
        0 #dadbde, stop: 1 #f6f7fa)"
        )

    def mousePressEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 10px;\
        background-color:qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:\
        0 #dadbde, stop: 1 #dedee0)"
        )

    def enterEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 10px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:\
        0 #dadbde, stop: 1 #f6f7fa)"
        )

    def leaveEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 10px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, top:\
        0 #f6f7fa, stop: 1 #dadbde0)"
        )


class ClusteringBox(QDialog):
    def __init__(self, toolbar, parent=None, *args):
        QDialog.__init__(self, parent, *args)
        self.setWindowTitle("Clustering")
        self.toolbar = toolbar
        self.obj_sel = self.toolbar.table.tm.headerdata[self.toolbar.table.tm.ncol]
        self.order = self.toolbar.table.tm.order
        self.setLayout(self.init_ui())
        self.setFixedSize(self.minimumSize())
        self.exec()

    def init_ui(self):
        self.vbox = QVBoxLayout()
        gbox = QGroupBox()
        gbox.setTitle("Cluster by...")
        self.bbox = QButtonGroup()
        vbox_radio = QVBoxLayout()

        # Toogle Bottons
        if self.obj_sel != "Filename" and self.obj_sel != "Cluster":
            self.toogle_bar = ToogleBar(activated=self.order)
        else:
            self.toogle_bar = ToogleBar()
        vbox_radio.addLayout(self.toogle_bar)

        # Radio Buttons
        for objective in self.toolbar.table.tm.headerdata[1:]:
            if objective != "Cluster":
                rb = QRadioButton(objective)
                self.bbox.addButton(rb)
                vbox_radio.addWidget(rb)

        if self.obj_sel != "Filename" and self.obj_sel != "Cluster":
            self.bbox.buttons()[self.toolbar.table.tm.ncol - 1].setChecked(True)
        else:
            self.bbox.buttons()[0].setChecked(True)
        gbox.setLayout(vbox_radio)
        self.vbox.addWidget(gbox)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("With a RMSD cutoff of"))
        self.rmsd_box = QDoubleSpinBox()
        self.rmsd_box.setSingleStep(0.5)
        self.rmsd_box.setValue(0.5)
        hbox.addWidget(self.rmsd_box)
        self.vbox.addLayout(hbox)

        self.run_butn = QPushButton("Cluster!")
        self.run_butn.clicked.connect(self.run_clustering)
        self.run_butn.setFixedSize(100, 30)
        self.last_layout = QHBoxLayout()
        self.last_layout.addStretch(1)
        self.last_layout.addWidget(self.run_butn)
        self.last_layout.addStretch(1)
        self.vbox.addLayout(self.last_layout)

        return self.vbox

    def run_clustering(self):

        self.toolbar.window.update_saves()
        save = copy.deepcopy(
            [self.toolbar.table.tm.arraydata, self.toolbar.table.tm.headerdata]
        )
        order = self.toogle_bar.activated
        objective = self.bbox.checkedButton().text()
        sorted(
            self.toolbar.table.tm.arraydata,
            key=operator.itemgetter(self.toolbar.table.tm.headerdata.index(objective)),
        )
        if order == "max":
            self.toolbar.table.tm.arraydata.reverse()

        rmsd_value = self.rmsd_box.value()
        solutions = []

        count = 0
        progress = QProgressDialog(
            "Loading the solutions...",
            "Cancel",
            count,
            len(self.toolbar.table.tm.arraydata) * 2,
        )
        progress.setFixedWidth(300)
        progress.setWindowTitle("Clustering Progress")
        progress.setWindowModality(Qt.WindowModal)

        progress.forceShow()

        for row in self.toolbar.table.tm.arraydata:
            if progress.isVisible() == False:
                break
            count += 1
            progress.setValue(count)
            if not row[0] in self.toolbar.table.tm.gaudimain.models:
                for gm in self.toolbar.table.tm.gaudimain.gaudimodel:
                    if row[0] in gm.keys:
                        gm.parse_zip(row[0])
            solutions.append((row[0], self.toolbar.table.tm.gaudimain.models[row[0]]))
        clusters = [[]]

        self.toolbar.table.tm.layoutAboutToBeChanged.emit()

        if not "Cluster" in self.toolbar.table.tm.headerdata:
            self.toolbar.table.tm.headerdata.append("Cluster")
        index_cluster = self.toolbar.table.tm.headerdata.index("Cluster")

        clusters[0].append(solutions.pop(0))

        progress.setLabelText("Calculating RMSD...")
        while solutions:
            if progress.isVisible() == False:
                self.toolbar.table.tm.arraydata, self.toolbar.table.tm.headerdata = save
                break
            next_sol = solutions.pop(0)
            count += 1
            progress.setValue(count)
            for cluster in clusters:
                rmsd = calculate_rmsd(cluster[0][1], next_sol[1], rmsd_value)
                if rmsd < rmsd_value:
                    cluster.append(next_sol)
                    break
            else:
                clusters.append([next_sol])

        progress.setLabelText("DONE")

        for index, cluster in enumerate(clusters):
            for key, models in cluster:
                for row in self.toolbar.table.tm.arraydata:
                    if row[0] == key:
                        row.insert(index_cluster, index + 1)

        self.toolbar.table.tm.layoutChanged.emit()
        if self.toolbar.table.selectionModel().hasSelection():
            for index in self.toolbar.table.selectionModel().selection().indexes():
                if index.data() in self.toolbar.table.tm.gaudimain.models:
                    model = self.toolbar.table.tm.gaudimain.models[index.data()]
                    gaudireader.hide(self.toolbar.session, model)

        progress.close()
        self.hide()


def calculate_rmsd(ref_models, to_models, cutoff):

    if isinstance(ref_models, list) and isinstance(to_models, list):
        for ref_model, to_model in zip(ref_models, to_models):
            rmsd = align_points(
                ref_model.atoms.scene_coords, to_model.atoms.scene_coords
            )[1]
    else:
        rmsd = align_points(ref_model.atoms.scene_coords, to_model.atoms.scene_coords)[
            1
        ]
    return rmsd


class ToogleBar(QHBoxLayout):
    def __init__(self, activated=None, parent=None):
        super(ToogleBar, self).__init__(parent)

        self.max_label = QLabel("Maximazing")
        self.min_label = QLabel("Minimazing")
        self.activated = activated

        if self.activated == 0:
            self.activated = "min"
            self.max_label.setStyleSheet("color:rgb(189,189,189)")
            self.min_label.setStyleSheet("color:default")

        elif self.activated == 1 or self.activated == None:
            self.activated = "max"
            self.min_label.setStyleSheet("color:rgb(189,189,189)")
            self.max_label.setStyleSheet("color:default")

        icon = ToogleIcon(bar=self)
        icon.setCursor(Qt.PointingHandCursor)
        icon.setPixmap(
            QPixmap("arrows.png").scaled(
                20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 6px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, top:\
        0 #f6f7fa, stop: 1 #dadbde0)"
        )

        self.addWidget(self.max_label)
        self.addWidget(icon)
        self.addWidget(self.min_label)


class ToogleIcon(QLabel):
    clicked = pyqtSignal()

    def __init__(self, bar, parent=None):
        super(ToogleIcon, self).__init__(parent)
        self.bar = bar

    def mouseReleaseEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 6px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:\
        0 #dadbde, stop: 1 #f6f7fa)"
        )

        if self.bar.activated == "max":
            self.bar.activated = "min"
            self.bar.max_label.setStyleSheet("color:rgb(189,189,189)")
            self.bar.min_label.setStyleSheet("color:default")

        elif self.bar.activated == "min":
            self.bar.activated = "max"
            self.bar.min_label.setStyleSheet("color:rgb(189,189,189)")
            self.bar.max_label.setStyleSheet("color:default")

    def mousePressEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 6px;\
        background-color:qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:\
        0 #dadbde, stop: 1 #dedee0)"
        )

    def enterEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 6px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:\
        0 #dadbde, stop: 1 #f6f7fa)"
        )

    def leaveEvent(self, event):
        self.setStyleSheet(
            "border: 1px solid #8f8f91; border-radius: 6px;\
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, top:\
        0 #f6f7fa, stop: 1 #dadbde0)"
        )
