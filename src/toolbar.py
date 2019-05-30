import operator
from PyQt5.QtCore import Qt, pyqtSignal
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
)
from PyQt5.QtGui import QIcon, QPixmap
from chimerax.core.geometry import align_points
from chimerax.core.commands import run
from . import gaudireader

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
                QIcon("/home/andres/practicas/chimerax/gaudiviewx/src/checklist.png"),
                "Filter",
                self,
            )
        )
        self.addAction(
            QAction(
                QIcon(
                    "/home/andres/practicas/chimerax/gaudiviewx/src/cluster-icon.png"
                ),
                "Clustering",
                self,
            )
        )

        self.addSeparator()
        self.addAction(
            QAction(
                QIcon(
                    "/home/andres/practicas/chimerax/gaudiviewx/src/Info_Simple.svg.png"
                ),
                "Help",
                self,
            )
        )
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.actionTriggered[QAction].connect(self.toolbtnpressed)

    def toolbtnpressed(self, action):
        if action.text() == "Open":
            self.window.update_saves()
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
            self.window.update_saves()
            FilterBox(self)
        elif action.text() == "Clustering":
            self.window.update_saves()
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
            self.table.tm.layoutAboutToBeChanged.emit()
            self.table.tm.removeRows(0, len(self.table.tm.arraydata))
            new_gaudimodel = gaudireader.GaudiModel(name_file, self.table.session)
            self.table.tm.arraydata = new_gaudimodel.data
            self.table.tm.backdoor = self.table.tm.arraydata
            self.table.tm.headerdata = new_gaudimodel.headers
            self.table.models = new_gaudimodel.save_models()
            self.window.delete_butn.setEnabled(False)
            self.table.tm.layoutChanged.emit()
            nrows = len(self.table.tm.arraydata)
            for row in range(nrows):
                self.table.setRowHeight(row, 25)
            run(self.session, "close")

    def save_file(self):
        self.table.tm.gaudimodel.path


class FilterBox(QDialog):
    def __init__(self, toolbar, parent=None, *args):
        QDialog.__init__(self, parent, *args)
        self.setWindowTitle("Filtering")
        self.setWindowIcon(
            QIcon("/home/andres/practicas/chimerax/gaudiviewx/src/checklist.png")
        )
        self.toolbar = toolbar
        self.setLayout(self.init_ui())
        self.setFixedSize(self.minimumSize())
        self.exec()

    def init_ui(self):

        self.vbox = QVBoxLayout()
        gbox = QGroupBox()
        gbox.setTitle("Remain the solutions with...")
        self.bbox = QButtonGroup()
        vbox_radio = QVBoxLayout()

        for objective in self.toolbar.table.tm.headerdata[1:]:
            if objective != "Cluster":
                rb = QRadioButton(objective)
                self.bbox.addButton(rb)
                vbox_radio.addWidget(rb)
        self.bbox.buttons()[0].setChecked(True)
        gbox.setLayout(vbox_radio)
        self.vbox.addWidget(gbox)

        hbox1 = QHBoxLayout()
        hbox1.addStretch(1)
        self.logicbox = QComboBox()
        self.logicbox.addItems([">", "<", "=", "≥", "≤", "≠"])
        hbox1.addWidget(self.logicbox)
        self.number_box = QDoubleSpinBox()
        self.number_box.setSingleStep(0.05)
        self.number_box.setMaximum(9999.99)
        self.number_box.setMinimum(-9999.99)

        hbox1.addWidget(self.number_box)
        hbox1.addStretch(1)
        self.vbox.addLayout(hbox1)

        self.run_butn = QPushButton("Filter!")
        self.run_butn.clicked.connect(self.run_filter)
        self.run_butn.setFixedSize(100, 30)
        last_layout = QHBoxLayout()
        last_layout.addStretch(1)
        last_layout.addWidget(self.run_butn)
        last_layout.addStretch(1)

        self.vbox.addLayout(last_layout)

        return self.vbox

    def run_filter(self):
        self.objective = self.bbox.checkedButton().text()
        logic = self.logicbox.currentText()
        self.filter_number = float(self.number_box.value())
        self.hide()
        self.index_column = self.toolbar.table.tm.headerdata.index(self.objective)
        self.toolbar.table.tm.layoutAboutToBeChanged.emit()
        if logic == ">":
            self.greater()
        elif logic == "<":
            self.lesser()
        elif logic == "=":
            self.equal()
        elif logic == "≥":
            self.greater_equal()
        elif logic == "≤":
            self.lesser_equal()
        elif logic == "≠":
            self.not_equal()
        self.toolbar.table.tm.layoutChanged.emit()

    def greater(self):
        new_array = []
        for row in self.toolbar.table.tm.arraydata:
            if float(row[self.index_column]) > self.filter_number:
                new_array.append(row)
        self.toolbar.table.tm.arraydata = new_array

    def greater_equal(self):
        new_array = []
        for row in self.toolbar.table.tm.arraydata:
            if not float(row[self.index_column]) < self.filter_number:
                new_array.append(row)
        self.toolbar.table.tm.arraydata = new_array

    def equal(self):
        new_array = []
        for row in self.toolbar.table.tm.arraydata:
            if float(row[self.index_column]) == self.filter_number:
                new_array.append(row)
        self.toolbar.table.tm.arraydata = new_array

    def not_equal(self):
        new_array = []
        for row in self.toolbar.table.tm.arraydata:
            if float(row[self.index_column]) != self.filter_number:
                new_array.append(row)
        self.toolbar.table.tm.arraydata = new_array

    def lesser(self):
        new_array = []
        for row in self.toolbar.table.tm.arraydata:
            if float(row[self.index_column]) < self.filter_number:
                new_array.append(row)
        self.toolbar.table.tm.arraydata = new_array

    def lesser_equal(self):
        new_array = []
        for row in self.toolbar.table.tm.arraydata:
            if not float(row[self.index_column]) > self.filter_number:
                new_array.append(row)
        self.toolbar.table.tm.arraydata = new_array


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
        for row in self.toolbar.table.tm.arraydata:
            solutions.append((row[0], self.toolbar.table.models[row[0]]))
        clusters = [[]]

        self.toolbar.table.tm.layoutAboutToBeChanged.emit()

        if not "Cluster" in self.toolbar.table.tm.headerdata:
            self.toolbar.table.tm.headerdata.append("Cluster")
        index_cluster = self.toolbar.table.tm.headerdata.index("Cluster")

        clusters[0].append(solutions.pop(0))

        while solutions:
            next_sol = solutions.pop(0)
            for cluster in clusters:
                rmsd = calculate_rmsd(cluster[0][1], next_sol[1], rmsd_value)
                if rmsd < rmsd_value:
                    cluster.append(next_sol)
                    break
            else:
                clusters.append([next_sol])

        for index, cluster in enumerate(clusters):
            for key, models in cluster:
                for row in self.toolbar.table.tm.arraydata:
                    if row[0] == key:
                        row.insert(index_cluster, index + 1)

        self.toolbar.table.tm.layoutChanged.emit()

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