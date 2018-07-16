from PySide2 import QtWidgets, QtCore, QtGui
import PySide2
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import pymel.core as pm

import logging
logging.basicConfig()
lHandler = logging.Handler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
lHandler.setFormatter(formatter)
logger = logging.getLogger('Spline Distribute UI')
logger.setLevel(logging.DEBUG)
logger.addHandler(lHandler)

class splineDistributeUI(QtWidgets.QWidget):
    def __init__(self, dock = True):
        if dock:
            parent = getDock()
        else:
            deleteDock()
            try:
                pm.deleteUI('splineDistributeUI')
            except:
                logger.debug('no previus ui detected')

            # top level window
            parent = QtWidgets.QDialog(parent=getMayaWindow())
            parent.setObjectName('splineDistributeUI')
            parent.setWindowTitle('Spline Distribute')

            # add a layout
            dlgLayout = QtWidgets.QBoxLayout(parent)

        super(splineDistributeUI, self).__init__(parent=parent)

        self.buildUI()
        self.parent().layout().addWidget(self)

    def buildUI(self):
        # create grid
        layout = QtWidgets.QGridLayout(self)
        increment = QtWidgets.QLineEdit('Increment')
        # increment.setMaxLength(5) max digits
        layout.addWidget(increment, 0, 0, 0, 1)

        generate = QtWidgets.QPushButton('Generate')
        layout.addWidget(generate,2 ,0)

        refresh = QtWidgets.QPushButton('Refresh')
        layout.addWidget(refresh, 2, 1)

        bake = QtWidgets.QPushButton('Bake')
        layout.addWidget(bake,2,2)



# don't know why, this cant be a @staticmethod inside the class
def getDock(name = 'splineDistributeUIDock'):
    deleteDock(name)

    # Creates and manages the widget used to host windows in a layout
    # which enables docking and stacking windows together
    ctrl = pm.workspaceControl(name, dockToMainWindow=('right', 1), label='Spline Distribute')
    #we need the QT version, MQtUtil_findControl return the qt widget of the named maya control
    qtCtrl = omui.MQtUtil_findControl(ctrl)
    # translate to something python undertand
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)
    return ptr

def deleteDock(name = 'splineDistributeUIDock'):
    if pm.workspaceControl(name, query=True, exists=True):
        pm.deleteUI(name)

def getMayaWindow():
    #get maya main window
    win = omui.MQtUtil_mainWindow()
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)
    return ptr