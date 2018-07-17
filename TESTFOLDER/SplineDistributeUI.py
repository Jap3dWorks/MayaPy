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
        # general grid, i will try to create trhee grids and put them un a general grid
        layoutGeneral = QtWidgets.QGridLayout(self)
        layoutGeneral.setAlignment(QtCore.Qt.AlignHCenter)

        # create grid A <- ^
        layoutAWidget = QtWidgets.QWidget()
        layoutAWidget.setMaximumWidth(200)
        layoutA = QtWidgets.QGridLayout(layoutAWidget)
        layoutA.setAlignment(QtCore.Qt.AlignTop)
        layoutGeneral.addWidget(layoutAWidget, 0, 0)
        # elements Grid A
        incrementLabel = QtWidgets.QLabel('Increment:')
        layoutA.addWidget(incrementLabel, 0, 0)
        BboxCBx = QtWidgets.QCheckBox('BBox')
        layoutA.addWidget(BboxCBx,0,1)
        increment = QtWidgets.QLineEdit('00')
        # increment.setMaxLength(5)-->max digits
        layoutA.addWidget(increment, 1, 0,1,2)


        # create grid RandomTrn -> random Tranlate
        # qwidget that containt the grid
        layoutBWidget = QtWidgets.QWidget()
        layoutBWidget.setMaximumHeight(100)
        layoutBWidget.setMaximumWidth(300)
        layoutB = QtWidgets.QGridLayout(layoutBWidget)
        layoutB.setAlignment(QtCore.Qt.AlignHCenter)
        layoutGeneral.addWidget(layoutBWidget, 0, 1)
        # label trnsRandom
        randomTrnLabel = QtWidgets.QLabel('Translate Random:')
        layoutB.addWidget(randomTrnLabel, 0, 0,1,2)
        # X random
        XrndTLbl = QtWidgets.QLabel('X:')
        layoutB.addWidget(XrndTLbl, 1, 0)
        XTrnRnd = QtWidgets.QLineEdit('00')
        layoutB.addWidget(XTrnRnd, 2, 0)
        # Y random
        YrndTLbl = QtWidgets.QLabel('Y:')
        layoutB.addWidget(YrndTLbl, 1,1)
        YTrnRnd = QtWidgets.QLineEdit('00')
        layoutB.addWidget(YTrnRnd, 2, 1)
        # Z random
        ZrndTLbl = QtWidgets.QLabel('Z:')
        layoutB.addWidget(ZrndTLbl, 1, 2)
        ZTrnRnd = QtWidgets.QLineEdit('00')
        layoutB.addWidget(ZTrnRnd, 2, 2)

        # create grid RandomRo -> random Rotation
        # qwidget that containt the grid
        layRRoWid = QtWidgets.QWidget()
        layRRoWid.setMaximumHeight(100)
        layRRoWid.setMaximumWidth(300)
        layRRo = QtWidgets.QGridLayout(layRRoWid)
        layRRo.setAlignment(QtCore.Qt.AlignHCenter)
        layoutGeneral.addWidget(layRRoWid, 1, 1)
        # label trnsRandom
        labRRo = QtWidgets.QLabel('Rotate Random:')
        layRRo.addWidget(labRRo, 0, 0,1,2)
        # X random
        XrndRLbl = QtWidgets.QLabel('X:')
        layRRo.addWidget(XrndRLbl, 1, 0)
        XRoRnd = QtWidgets.QLineEdit('00')
        layRRo.addWidget(XRoRnd, 2, 0)
        # Y random
        YrndRLbl = QtWidgets.QLabel('Y:')
        layRRo.addWidget(YrndRLbl, 1,1)
        YRoRnd = QtWidgets.QLineEdit('00')
        layRRo.addWidget(YRoRnd, 2, 1)
        # Z random
        ZrndRLbl = QtWidgets.QLabel('Z:')
        layRRo.addWidget(ZrndRLbl, 1, 2)
        ZRoRnd = QtWidgets.QLineEdit('00')
        layRRo.addWidget(ZRoRnd, 2, 2)

        # create grid RandomSc -> Scale Rotation
        # qwidget that containt the grid
        layRScWid = QtWidgets.QWidget()
        layRScWid.setMaximumHeight(100)
        layRScWid.setMaximumWidth(300)
        layRSc = QtWidgets.QGridLayout(layRScWid)
        layRSc.setAlignment(QtCore.Qt.AlignHCenter)
        layoutGeneral.addWidget(layRScWid, 2, 1)
        # label
        lblWidget = QtWidgets.QWidget()
        lblWidLay = QtWidgets.QGridLayout(lblWidget)
        layRScLab = QtWidgets.QLabel('Scale Random:')
        lblWidLay.addWidget(layRScLab, 0, 0)
        checkBxScXZ = QtWidgets.QCheckBox('XZ lock')
        lblWidLay.addWidget(checkBxScXZ,0,1)
        layRSc.addWidget(lblWidget, 0, 0, 1, 3)
        # X random
        XrndScLbl = QtWidgets.QLabel('X:')
        layRSc.addWidget(XrndScLbl, 1, 0)
        XScRnd = QtWidgets.QLineEdit('00')
        layRSc.addWidget(XScRnd, 2, 0)
        # Y random
        YrndScLbl = QtWidgets.QLabel('Y:')
        layRSc.addWidget(YrndScLbl, 1, 1)
        YScRnd = QtWidgets.QLineEdit('00')
        layRSc.addWidget(YScRnd, 2, 1)
        # Z random
        ZrndScLbl = QtWidgets.QLabel('Z:')
        layRSc.addWidget(ZrndScLbl, 1, 2)
        ZScRnd = QtWidgets.QLineEdit('00')
        layRSc.addWidget(ZScRnd, 2, 2)

        # create grid Buttons _
        layoutCWidget = QtWidgets.QWidget()
        layoutC = QtWidgets.QGridLayout(layoutCWidget)
        layoutGeneral.addWidget(layoutCWidget, 3, 0, 1, 2)

        generate = QtWidgets.QPushButton('Generate')
        layoutC.addWidget(generate,0 ,0)

        refresh = QtWidgets.QPushButton('Refresh')
        layoutC.addWidget(refresh, 0, 1)

        bake = QtWidgets.QPushButton('Bake')
        layoutC.addWidget(bake,0,2)




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