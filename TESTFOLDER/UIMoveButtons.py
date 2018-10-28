from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import maya.api.OpenMaya as OpenMaya
import pymel.core as pm
from functools import partial

import logging
logging.basicConfig()
logger = logging.getLogger('UI Move Buttons:')
logger.setLevel(logging.INFO)

class UIMoveButtons(QtWidgets.QWidget):

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
            # parent.closeEvent(lambda: logger.debug('clossing'))
            # Review: do not work well if not dockable
            # add a layout
            dlgLayout = QtWidgets.QVBoxLayout(parent)
            # dlgLayout.addWidget(self)

        parent.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        super(UIMoveButtons, self).__init__(parent=parent)
        self.parent().layout().addWidget(self)  # add widget finding preiously the parent

        self.buildUI()

    def buildUI(self):
        general_layout = QtWidgets.QGridLayout(self)
        general_layout.setAlignment(QtCore.Qt.AlignHCenter)
        general_layout.setMargin(0)

        moveButton = QtWidgets.QPushButton('move')
        general_layout.addWidget(moveButton)


def getPathFunc(defaultPath):
    pathWin = QtWidgets.QFileDialog.getExistingDirectory(parent=getMayaWindow(), caption='FBX exporter browser',
                                                         dir=defaultPath)
    if not pathWin:
        return defaultPath
    return pathWin

def getDock(name='FbxExporterUIDock'):
    deleteDock(name)

    # Creates and manages the widget used to host windows in a layout
    # which enables docking and stacking windows together
    ctrl = pm.workspaceControl(name, dockToMainWindow=('right', 1), label='Fbx Exporter')
    # we need the QT version, MQtUtil_findControl return the qt widget of the named maya control
    qtCtrl = omui.MQtUtil_findControl(ctrl)
    # translate to something python understand
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)

    return ptr

def deleteDock(name='FbxExporterUIDock'):
    if pm.workspaceControl(name, query=True, exists=True):
        pm.deleteUI(name)

def getMayaWindow():
    # get maya main window
    win = omui.MQtUtil_mainWindow()
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)

    return ptr
