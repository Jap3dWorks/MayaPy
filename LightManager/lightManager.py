import json
import os

import PySide2

# I will use the following modules more often, so let me import them directly
import time
from PySide2 import QtWidgets, QtCore, QtGui

import logging

logDirectory = os.path.dirname(os.path.realpath(__file__))
logDirectory = os.path.join(logDirectory, 'LM_log.log')

logging.basicConfig()

#get directory file and format log
fh = logging.FileHandler(logDirectory, 'a')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger = logging.getLogger('LightingManager')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

from shiboken2 import wrapInstance
from PySide2.QtCore import Signal

from maya import OpenMayaUI as omui

import pymel.core as pm

from functools import partial

class LightWidget(QtWidgets.QWidget):
    """
    Now on to the good stuff
    This is our Basic controller for controlling lights
    to display it, give it the name of a light like so
    ui = LightWidget('directionalLight1')
    ui.show()
    """
    
    # signal must be here
    onSolo = Signal(bool)
    
    def __init__(self, light):
        super(LightWidget, self).__init__()

        if isinstance(light, basestring):
            logger.debug('Converting node to a PyNode')
            light = pm.PyNode(light)
            
        if isinstance(light, pm.nodetypes.Transform):
            light = light.getShape()
            
        self.light = light
        self.transform = self.light.getTransform()
        self.buildUI()

        self.prevVal = None

    def buildUI(self):
        # create grid
        layout = QtWidgets.QGridLayout(self)
        # get transform node of loght shape
        self.name = name = QtWidgets.QCheckBox(str(self.light.getTransform()))
        name.setChecked(self.transform.visibility.get())
        name.toggled.connect(lambda val: self.light.getTransform().visibility.set(val))

        # addto layout
        layout.addWidget(name, 0, 0)
        
        # solo light button
        self.solo = QtWidgets.QPushButton('Solo')
        # make button checkable
        self.solo.setCheckable(True)
        self.solo.toggled.connect(lambda val: self.onSolo.emit(val)) # emit true or false signal.
        layout.addWidget(self.solo, 0, 1)
        delete = QtWidgets.QPushButton('X')
        delete.clicked.connect(self.deleteLight)
        delete.setMaximumWidth(10)
        layout.addWidget(delete, 0, 2)
        
        # intensity slider
        intensity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        intensity.setMaximum(100)
        intensity.setMinimum(0)
        intensity.setValue(self.light.intensity.get()*10.0)
        intensity.valueChanged.connect(lambda val: self.light.intensity.set(val/10.0))
        layout.addWidget(intensity, 1, 0, 1, 2)
        
        # colorButton
        self.colorBtn = QtWidgets.QPushButton()
        self.colorBtn.setMaximumHeight(20)
        self.colorBtn.setMaximumWidth(20)
        self.setButtonColor()
        self.colorBtn.clicked.connect(self.setColor)
        layout.addWidget(self.colorBtn, 1, 2)
        
        # the widget never will be larger than the space it needs
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        
    def disableLight(self, val):
        logger.debug('light Visibility previous State %s %s' % (bool(self.name.checkState()), str(self.light.getTransform())))
        if val:
            # on press
            # save the actual visibility value of the light
            self.prevVal = bool(self.name.checkState())
            logger.debug('previus Value stored as: %s' % (self.prevVal))
            logger.debug('changing light %s' %self.light.getTransform())
            self.name.setChecked(not bool(val))
        else:
            # on release
            # if the visibility value of the light was true, then active the light
            logger.debug('previus Value stored was: %s' % (self.prevVal))
            if self.prevVal:
                self.name.setChecked(not bool(val))

    def deleteLight(self):
        # make parent of none, this will delete the widget
        self.setParent(None)
        # turn visibility off, delete isn't inmediatly
        self.setVisible(False)
        self.deleteLater()

        pm.delete(self.light.getTransform())

    def setColor(self):
        lightColor = self.light.color.get()
        # maya color editor give us rbc values
        color = pm.colorEditor(rgbValue=lightColor)

        # maya give us a string, we split the string a convert to float
        r, g, b, a = [float(c) for c in color.split()]

        color = (r, g, b)
        self.light.color.set(color)
        self.setButtonColor(color)

    def setButtonColor(self, color=None):
        # sets de color of the picker button
        if not color:
            color = self.light.color.get()

        assert len(color) == 3, "You must provide a list of 3 colors"

        # QT needs color in 255 value
        r, g, b = [c * 255 for c in color]

        # paint button
        self.colorBtn.setStyleSheet('background-color: rgba(%s, %s, %s, 1.0);' % (r, g, b))


class LightingManager(QtWidgets.QWidget):
    """
    This is the main lighting manager.
    To call it we just do
    LightingManager(dock=True) and it will display docked, otherwise dock=False will display it as a window
    """
    # dictionary of lightTypes
    lightTypes = {
        "Point Light": pm.pointLight,
        "Spot Light": pm.spotLight,
        "Area Light": partial(pm.shadingNode, 'areaLight', asLight=True),
        # partial with the func of area light with the values
        "Directional Light": pm.directionalLight,
        "Volume Light": partial(pm.shadingNode, 'volumeLight', asLight=True)
    }
    def __init__(self, dock=False):
        if dock:
            parent = getDock()

        else:
            deleteDock()

            try:
                pm.deleteUI('lightingManager')

            except:
                logger.debug('No previous UI exists')

            parent = QtWidgets.QDialog(parent=getMayaMainWindow())
            parent.setObjectName('lightingManager')
            parent.setWindowTitle('Lighting Manager')

            # layout
            dlgLayout = QtWidgets.QVBoxLayout(parent)

        super(LightingManager, self).__init__(parent=parent)

        self.buildUI()
        self.populate()
        self.parent().layout().addWidget(self)


        if not dock:
            parent.show()

    def buildUI(self):
        layout = QtWidgets.QGridLayout(self)
        self.lightTypeCB = QtWidgets.QComboBox()

        for lightType in sorted(self.lightTypes):
            self.lightTypeCB.addItem(lightType)

        layout.addWidget(self.lightTypeCB, 0, 0, 1, 2)

        # create light button
        createBtn = QtWidgets.QPushButton('Create')
        createBtn.clicked.connect(self.createLight)
        layout.addWidget(createBtn, 0, 2)

        # container widget to our light widgets
        scrollWidget = QtWidgets.QWidget()
        scrollWidget.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self.scrollLayout = QtWidgets.QVBoxLayout(scrollWidget) # here will be the light widgets, aply the layout to the widget

        # scrollArea
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(scrollWidget)
        layout.addWidget(scrollArea, 1, 0, 1, 3)

        saveBtn = QtWidgets.QPushButton('Save')
        saveBtn.clicked.connect(self.saveLights)
        layout.addWidget(saveBtn, 2, 0)

        importBtn = QtWidgets.QPushButton('Import')
        importBtn.clicked.connect(self.importLights)
        layout.addWidget(importBtn, 2, 1)

        refreshBtn = QtWidgets.QPushButton('Refresh')
        refreshBtn.clicked.connect(self.refresh)
        layout.addWidget(refreshBtn, 2, 2)

    def refresh(self):
        # count tell us how many children has
        while self.scrollLayout.count():
            # here we take the first child of the widget
            widget = self.scrollLayout.takeAt(0).widget()
            if widget:
                # delete Widget
                widget.setVisible(False)
                widget.deleteLater()
        # populate again the ui
        self.populate()

    def populate(self):
        # list all the existing lights by type
        for light in pm.ls(type=["areaLight", "spotLight", "pointLight", "directionalLight", "volumeLight"]):
            self.addLight(light)

    def saveLights(self):
        # save lights in a json
        # properties dictionary will save all the parmeters
        properties = {}

        # first get all the light widgets in our manager
        for lightWidget in self.findChildren(LightWidget):
            # lightWidget class light variable
            light = lightWidget.light
            transform = light.getTransform()

            # add to dictionary
            properties[str(transform)] = {
                'translate': list(transform.translate.get()),
                'rotation': list(transform.rotate.get()),
                'lightType': pm.objectType(light),
                'intensity': light.intensity.get(),
                'color': light.color.get()
            }
        directory = self.getDirectory()

        # %m%d will give 0701 for July 1st (month and day)
        # lightFile = os.path.join(directory, 'lightFile_%s.json' % time.strftime('%m%d'))
        # open a filebrowser qfileFialog
        lightFile = QtWidgets.QFileDialog.getSaveFileName(self, "Light Browser", directory, '*.json')
        # open file to write
        with open(lightFile[0], 'w') as f:
            # use json to write our file
            json.dump(properties, f, indent=4)

        logger.info('Saving file to %s' % lightFile)

    def getDirectory(self):
        directory = os.path.join(pm.internalVar(userAppDir=True), 'lightManager')
        if not os.path.exists(directory):
            os.mkdir(directory)
        return directory

    def importLights(self):
        # find directory
        directory = self.getDirectory()

        # open a filebrowser qfileFialog
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, "Light Browser", directory)
        with open(fileName[0], 'r') as f:
            properties = json.load(f)

        # loop trough keys and values
        for light, info in properties.items():
            lightType = info.get('lightType')

            #check if we support the light type
            for lt in self.lightTypes:
                # But the light type of a Point Light is pointLight, so we convert Point Light to pointLight and then compare
                if ('%sLight' % lt.split()[0].lower()) == lightType:
                    break
            # else of a for loop, it only runs if the loop has not been broken out
            else:
                logger.info('Cannot find a corresponding light type for %s (%s)' % (light, lightType))
                continue

            # reuse varieble from the loop
            if pm.objExists(light):
                light = pm.PyNode(light)
            else:
                light = self.createLight(lightType=lt)

            # set parameters of light
            light.intensity.set(info.get('intensity'))
            light.color.set(info.get('color'))
            transform = light.getTransform()
            transform.translate.set(info.get('translate'))
            transform.rotate.set(info.get('rotation'))

        self.refresh()


    def createLight(self, lightType=None, add=True):
        # this function create light
        if not lightType:
            lightType = self.lightTypeCB.currentText()
        # look dictionary to find function
        func = self.lightTypes[lightType]

        light = func()
        if add:
            self.addLight(light)
        logger.debug('Create light type: %s' %lightType)
        return light

    def addLight(self, light):
        # create LightWidget
        widget = LightWidget(light)
        # conect on solo signal to our isolate method
        widget.onSolo.connect(self.isolate) #connect solo signal with isolate method
        self.scrollLayout.addWidget(widget)

    def isolate(self, val):
        # find children who are Lightwidgets
        # self = class.// findChildren  = class method => QtWidgets.QWidget.findChildren()
        lightWidgets = self.findChildren(LightWidget)
        for widget in lightWidgets:
            # Every signal lets us know who sent it that we can query with sender()
            # So for every widget we check if its the sender
            if widget != self.sender():
                logger.debug('isolate val %s' % val)
                # if isn't the widget disable it
                widget.disableLight(val)
                widget.solo.setEnabled(not val)

def getMayaMainWindow():
    """
    Since Maya is Qt, we can parent our UIs to it.
    This means that we don't have to manage our UI and can leave it to Maya.
    Returns:
        QtWidgets.QMainWindow: The Maya MainWindow
    """
    # open maya to get a reference to maya's main window
    win = omui.MQtUtil_mainWindow()
    # transform to something python can understand
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)
    return ptr

def getDock(name='LightingManagerDock'):
    """
    This function creates a dock with the given name.
    It's an example of how we can mix Maya's UI elements with Qt elements
    Args:
        name: The name of the dock to create
    Returns:
        QtWidget.QWidget: The dock's widget
    """
    # delete any conflict dock
    deleteDock(name)
    # name of the dock created
    ctrl = pm.workspaceControl(name, dockToMainWindow=('right', 1), label="Lighting Manager")
    qtCtrl = omui.MQtUtil_findControl(ctrl)

    # conver to something python can understand
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)
    return ptr

def deleteDock(name='LightingManagerDock'):
    """
    A simple function to delete the given dock
    Args:
        name: the name of the dock
    """
    if pm.workspaceControl(name, query=True, exists=True):
        pm.deleteUI(name)