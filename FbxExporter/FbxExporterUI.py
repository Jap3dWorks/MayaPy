"""
TODO: FbxExporterUI
    We need:
        A widget with exportable objects:
            Here we can change exp attr or path attr. preferable with right click.
        Export button.
        AddObj button.

"""
from FbxExporter import FbxExporter

from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter UI:')
logger.setLevel(logging.INFO)

# global var with fbxExporter obj
fbxExporter = FbxExporter.instance()

class FbxExporterUIWidget(QtWidgets.QWidget):
    """
    need: name of object. on click select, able or enable exp attr
    Class of Widgets for element
    BuildUI: construct of the UI
    Refresh info, with callbacks. if True, exportable path.
    """
    def __init__(self, item):
        super(FbxExporterUIWidget, self).__init__()

        self.item = item

        if not isinstance(self.item, pm.nodetypes.Transform):
            self.item = pm.PyNode(self.item)

        # TODO: background color variations
        self.BGcolor = None

        self.buildUI()

    def buildUI(self):
        global fbxExporter

        layout = QtWidgets.QGridLayout(self)
        layout.setAlignment(QtCore.Qt.AlignJustify)

        # leftLayout, label / chbox / pathButtons
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QGridLayout(left_widget)
        layout.addWidget(left_widget, 0, 0)

        # name_button
        name_button = QtWidgets.QPushButton(str(self.item))
        left_layout.addWidget(name_button, 0, 0)
        name_button.clicked.connect(lambda: pm.select(self.item))

        # chBox
        chBox = QtWidgets.QCheckBox(fbxExporter.attrBoolName)
        left_layout.addWidget(chBox, 0, 1)
        chBox.setChecked(self.item.attr(fbxExporter.attrBoolName).get())
        chBox.toggled.connect(lambda val: self.item.attr(fbxExporter.attrBoolName).set(val))

        # todo: multiple paths
        # pathButton
        self.pathButton = QtWidgets.QPushButton('Path')
        self.pathButton.setToolTip(self.item.attr(fbxExporter.attrPathName).get())
        left_layout.addWidget(self.pathButton, 0, 2)
        self.pathButton.clicked.connect(self.getPath)

        # Right layout
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QGridLayout(right_widget)
        layout.addWidget(right_widget, 0, 1)
        # delButton
        delButton = QtWidgets.QPushButton('Delete')
        right_layout.addWidget(delButton, 0, 0)
        delButton.clicked.connect(self.delete)
        delButton.setToolTip('Delete from Fbx Exporter, not from scene')

    def delete(self):
        # delete widget
        global fbxExporter
        self.setVisible(False)
        self.deleteLater()

        # remove item attr
        fbxExporter.removeAttr(self.item)

    def getPath(self):
        global fbxExporter
        self.item.attr(fbxExporter.attrPathName).set(getPathFunc(self.item.attr(fbxExporter.attrPathName)))

        # update Tooltip
        self.pathButton.setToolTip(self.item.attr(fbxExporter.attrPathName).get())

class FbxExporterUI(QtWidgets.QWidget):
    """
    need: widget to fill, export button, add and remove buttons.
    addButton: ask for the path. enable multi object
    Class of general ui for FbxExporter
    BuildUI: construct of the UI
    Refresh info on deleting obj, or deleting attr

    We fill the UI of FbxExpUIWidgets objects.
    """
    def __init__(self, dock=True):
        if dock:
            parent = getDock()
        else:
            deleteDock()
            try:
                pm.deleteUI('FbxExporterUI')
            except:
                logger.debug('no previous ui detected')

            # top level window
            parent = QtWidgets.QDialog(parent=getMayaWindow())
            parent.setObjectName('FbxExporterUI')
            parent.setWindowTitle('Fbx Exporter')

            # add a layout
            dlgLayout = QtWidgets.QVBoxLayout(parent)

        super(FbxExporterUI, self).__init__(parent=parent)

        self.buildUI()
        self._refresh()
        self.parent().layout().addWidget(self)  # add widget finding preiously the parent
        self.distributeObj = None

    def buildUI(self):
        global fbxExporter

        # general layout
        general_layout = QtWidgets.QGridLayout(self)
        general_layout.setAlignment(QtCore.Qt.AlignHCenter)

        # create upper grid, widgets // visible checkbox
        upper_Widget = QtWidgets.QWidget()
        upper_layout = QtWidgets.QGridLayout(upper_Widget)
        general_layout.addWidget(upper_Widget, 0, 0)

        # fill upper Grid

        # check box visibility
        # TODO: alignment to right and color background
        checkVi_widget = QtWidgets.QWidget()
        checkVi_Layout = QtWidgets.QGridLayout(checkVi_widget)
        upper_layout.addWidget(checkVi_widget, 0, 0)
        upper_layout.setAlignment(QtCore.Qt.AlignRight)
        # checkBox
        cvCheckBox = QtWidgets.QCheckBox('Export visible only')
        cvCheckBox.setChecked(True)
        checkVi_Layout.addWidget(cvCheckBox)

        # container
        container_widget = QtWidgets.QWidget()
        container_widget.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)  # adaptable
        self.container_layout = QtWidgets.QVBoxLayout(container_widget)
        self.container_layout.setAlignment(QtCore.Qt.AlignJustify)
        # now set that our widget have an scroll, this is a scroll area
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setAlignment(QtCore.Qt.AlignJustify)
        # Apply to scrollWidget
        scrollArea.setWidget(container_widget)
        upper_layout.addWidget(scrollArea, 1, 0)

        # Bottom grid, Add // Export buttons
        botom_Widget = QtWidgets.QWidget()
        botom_layout = QtWidgets.QGridLayout(botom_Widget)
        botom_layout.setAlignment(QtCore.Qt.AlignTop)
        general_layout.addWidget(botom_Widget, 1, 0)
        # elements Grid B
        # Add button
        addButton = QtWidgets.QPushButton('Add')
        botom_layout.addWidget(addButton, 0, 0)
        addButton.clicked.connect(self.add)
        # Export Button
        exportButton = QtWidgets.QPushButton('export')
        exportButton.clicked.connect(lambda : fbxExporter.export(cvCheckBox.isChecked()))
        botom_layout.addWidget(exportButton, 0, 1)
        exportButton.setToolTip('ToolTip')

    def add(self):
        """
        add attributes and refresh the container
        """
        global fbxExporter
        # add attributes // this method refresh the list
        fbxExporter.addAttributes(getPathFunc(fbxExporter.attrPathName))

        # refresh container
        self._refresh()

    def _refresh(self):
        """
        Refresh container, for add and remove options, or change attributes
        """
        global fbxExporter
        # private method for refresh list
        # clear container
        while self.container_layout.count():
            widget = self.container_layout.takeAt(0).widget()
            widget.setVisible(False)
            widget.deleteLater()

        # fill container
        for item in fbxExporter:
            widget = FbxExporterUIWidget(item)
            self.container_layout.addWidget(widget)

def getPathFunc(defaultPath):
    pathWin = QtWidgets.QFileDialog.getExistingDirectory(getMayaWindow(), "Light Browser", defaultPath)
    if not pathWin:
        return defaultPath
    return pathWin

def getDock(name='FbxExporterUIDock'):
    deleteDock(name)

    # Creates and manages the widget used to host windows in a layout
    # which enables docking and stacking windows together
    ctrl = pm.workspaceControl(name, dockToMainWindow=('right', 1), label='Fbx Exporter')
    #we need the QT version, MQtUtil_findControl return the qt widget of the named maya control
    qtCtrl = omui.MQtUtil_findControl(ctrl)
    # translate to something python undertand
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)
    return ptr

def deleteDock(name = 'FbxExporterUIDock'):
    if pm.workspaceControl(name, query=True, exists=True):
        pm.deleteUI(name)

def getMayaWindow():
    #get maya main window
    win = omui.MQtUtil_mainWindow()
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)
    return ptr
