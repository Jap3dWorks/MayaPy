"""
TODO: UI for FbxExporter
    We need:
        A widget with exportable objects:
            Here we can change exp attr or path attr. preferable with right click.
        Refresh.
        Export button.
        AddObj button.
            On clicked: PathExplorer window.
                        Add attributes.

"""
from FbxExporter import FbxExporter
# reload(FbxExporter)

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
    def __init__(self):
        super(FbxExporterUIWidget, self).__init__()

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
        self.parent().layout().addWidget(self)  # add widget finding preiously the parent
        self.distributeObj = None

    def buildUI(self):
        # general layout
        layoutGeneral = QtWidgets.QGridLayout(self)
        layoutGeneral.setAlignment(QtCore.Qt.AlignHCenter)

        # create grid A
        layoutAWidget = QtWidgets.QWidget()
        # layoutAWidget.setMaximumWidth(200)
        layoutA = QtWidgets.QGridLayout(layoutAWidget)
        layoutGeneral.addWidget(layoutAWidget, 0, 0, 2, 1)
        # elements Grid A



        # create grid b
        layoutBWidget = QtWidgets.QWidget()
        layoutB = QtWidgets.QGridLayout(layoutBWidget)
        layoutGeneral.addWidget(layoutBWidget, 1, 0)
        # elements Grid B
        # Add button
        addButton = QtWidgets.QPushButton('Add')
        layoutB.addWidget(addButton, 0, 0)
        # Export Button
        exportButton = QtWidgets.QPushButton('export')
        layoutB.addWidget(exportButton, 0, 1)



# can't be a static method class
def getDock(name = 'FbxExporterUIDock'):
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
