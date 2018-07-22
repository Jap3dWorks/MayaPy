from PySide2 import QtWidgets, QtCore, QtGui
import PySide2
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import pymel.core as pm
from TESTFOLDER import splineDistribute

import logging
logging.basicConfig()
logger = logging.getLogger('Spline Distribute UI')
logger.setLevel(logging.DEBUG)

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
        self.distributeObj = None

    def buildUI(self):
        def QDoubleSpinDef():
            qDoubleSpin = QtWidgets.QDoubleSpinBox()
            qDoubleSpin.setRange(0, 500)
            qDoubleSpin.setSingleStep(.1)
            return qDoubleSpin

        # general grid, i will try to create three grids and put them un a general grid
        layoutGeneral = QtWidgets.QGridLayout(self)
        layoutGeneral.setAlignment(QtCore.Qt.AlignHCenter)
        # validator = QtGui.QDoubleValidator()
        # validator.setDecimals(2)
        # validator.setBottom(0)
        # validator.setTop(500)


        # create grid A <- ^
        layoutAWidget = QtWidgets.QWidget()
        layoutAWidget.setMaximumWidth(200)
        layoutA = QtWidgets.QGridLayout(layoutAWidget)
        # layoutA.setAlignment(QtCore.Qt.AlignTop)
        layoutGeneral.addWidget(layoutAWidget, 0, 0)
        # elements Grid A
        incrementLabel = QtWidgets.QLabel('Increment:')
        layoutA.addWidget(incrementLabel, 0, 0)
        self.BboxCBx = QtWidgets.QCheckBox('BBox')
        layoutA.addWidget(self.BboxCBx, 0, 1)
        self.increment = QtWidgets.QDoubleSpinBox()
        self.increment.setRange(-500, 500)
        self.increment.setSingleStep(.1)
        # self.increment.setMaxLength(5)-->max digits
        layoutA.addWidget(self.increment, 1, 0, 1, 2)

        # Container Widget
        scrollWidget = QtWidgets.QWidget()
        scrollWidget.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum) #adaptable
        self.scrollLayout = QtWidgets.QVBoxLayout(scrollWidget)
        # now set that our widget have an scroll, this is a scroll area
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        # aply to scrollWidget
        scrollArea.setWidget(scrollWidget)
        layoutGeneral.addWidget(scrollArea, 1, 0, 2, 1)


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
        self.XTrnRnd = QDoubleSpinDef()
        layoutB.addWidget(self.XTrnRnd, 2, 0)
        # Y random
        YrndTLbl = QtWidgets.QLabel('Y:')
        layoutB.addWidget(YrndTLbl, 1,1)
        self.YTrnRnd = QDoubleSpinDef()
        layoutB.addWidget(self.YTrnRnd, 2, 1)
        # Z random
        ZrndTLbl = QtWidgets.QLabel('Z:')
        layoutB.addWidget(ZrndTLbl, 1, 2)
        self.ZTrnRnd = QDoubleSpinDef()
        layoutB.addWidget(self.ZTrnRnd, 2, 2)

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
        self.XRoRnd = QDoubleSpinDef()
        layRRo.addWidget(self.XRoRnd, 2, 0)
        # Y random
        YrndRLbl = QtWidgets.QLabel('Y:')
        layRRo.addWidget(YrndRLbl, 1,1)
        self.YRoRnd = QDoubleSpinDef()
        layRRo.addWidget(self.YRoRnd, 2, 1)
        # Z random
        ZrndRLbl = QtWidgets.QLabel('Z:')
        layRRo.addWidget(ZrndRLbl, 1, 2)
        self.ZRoRnd = QDoubleSpinDef()
        layRRo.addWidget(self.ZRoRnd, 2, 2)

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
        # checkBox xz Same Scale random
        self.checkBxScXZ = QtWidgets.QCheckBox('XZ lock')
        self.checkBxScXZ.stateChanged.connect(lambda x: self.ZScRnd.setEnabled(not(bool(x))))
        lblWidLay.addWidget(self.checkBxScXZ,0,1)
        layRSc.addWidget(lblWidget, 0, 0, 1, 3)
        # X random
        XrndScLbl = QtWidgets.QLabel('X:')
        layRSc.addWidget(XrndScLbl, 1, 0)
        self.XScRnd = QDoubleSpinDef()
        layRSc.addWidget(self.XScRnd, 2, 0)
        # Y random
        YrndScLbl = QtWidgets.QLabel('Y:')
        layRSc.addWidget(YrndScLbl, 1, 1)
        self.YScRnd = QDoubleSpinDef()
        layRSc.addWidget(self.YScRnd, 2, 1)
        # Z random
        ZrndScLbl = QtWidgets.QLabel('Z:')
        layRSc.addWidget(ZrndScLbl, 1, 2)
        self.ZScRnd = QDoubleSpinDef()
        layRSc.addWidget(self.ZScRnd, 2, 2)

        # create grid Buttons _
        layoutCWidget = QtWidgets.QWidget()
        layoutC = QtWidgets.QGridLayout(layoutCWidget)
        layoutGeneral.addWidget(layoutCWidget, 3, 0, 1, 2)

        generate = QtWidgets.QPushButton('Generate')
        generate.clicked.connect(self.generate)
        layoutC.addWidget(generate,0 ,0)

        refresh = QtWidgets.QPushButton('Refresh')
        layoutC.addWidget(refresh, 0, 1)

        bake = QtWidgets.QPushButton('Bake')
        layoutC.addWidget(bake,0,2)

    def generate(self):
        # if another instance of the class is in scene, bake the old objects
        try:
            if isinstance(self.distributeObj, splineDistribute.splineDistribute):
                logger.info('Previus distributed objects find')
                self.distributeObj.bakePositions()
        except:
            logger.debug('No previus distributen find')
        # create new isntance os the class
        logger.info('Distributing objects')
        self.distributeObj = splineDistribute.splineDistribute()
        self.distributeObj.saveObjects()
        self.distributeObj.distribute(float(self.increment.value()), bool(self.BboxCBx.checkState()),
                                 float(self.XTrnRnd.value()), float(self.YTrnRnd.value()), float(self.ZTrnRnd.value()),
                                 float(self.XRoRnd.value()), float(self.YRoRnd.value()), float(self.ZRoRnd.value()),
                                 float(self.XScRnd.value()), float(self.YScRnd.value()), float(self.ZScRnd.value()), bool(self.checkBxScXZ.checkState()))


# can't be a static method class
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