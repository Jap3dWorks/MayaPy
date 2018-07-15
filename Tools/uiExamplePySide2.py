import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm

class className():
    def __init__(self):
        self.varA = 1
        self.varB = 2
        self.varC = None

    def definitionA(self):
        self.varC=self.varA+self.varB

    def definitionB(self, userName):
        if self.varC==None:
            return
        print ('Hi '+ userName + ', thanks for visiting.')
        print ('varC is equal to '+str(self.varC))

# creates instance of this class
cn = className()

####################################
# GUI ##############################
####################################

# srinikom.github.io/pyside-docs/

from PySide2 import QtGui
from PySide2 import QtWidgets
from functools import partial

import maya.OpenMayaUI as mui
import shiboken2

def getMayaWindow():
    pointer = mui.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(long(pointer), QtWidgets.QWidget)

# def className_U1():
objectName = 'pyMyWin'

# check for existing window
if cmds.window("pyMyWin", exists=True):
    cmds.deleteUI("pyMyWin", wnd=True)

# create a window
parent = getMayaWindow()
window = QtWidgets.QMainWindow(parent)
window.setObjectName(objectName)

# create font
font = QtGui.QFont()
font.setPointSize(12)
font.setBold(True)

# create a widget
widget = QtWidgets.QWidget()
window.setCentralWidget(widget)

# create a layout
layout = QtWidgets.QVBoxLayout(widget)  # horizontal QtGui.QHBoxLayout()

# create buttons

# imagePath = cmds/internalVar(upd=True)+'icons/blue_field_background.png'
# button.setStylesheet("background-image: url("+1magePath+"); border:solid black 1px;color.rgb(0,0,0)")

# A+B button
button = QtWidgets.QPushButton("A + B")
layout.addWidget(button)
button.setFont(font)
button.setMinimumSize(200, 40)
button.setMaximumSize(200, 40)
button.setStyleSheet("background-color: rgb(128,128,128); color: rgb(0,0,0)")
button.clicked.connect(partial(cn.definitionA))

#C button
button = QtWidgets.QPushButton("Print C")
layout.addWidget(button)
button.setFont(font)
button.setMinimumSize(200, 40)
button.setMaximumSize(200, 40)
button.setStyleSheet("background-color: rgb(128,128,128); color: rgb(0,0,0)")
button.clicked.connect(partial(cn.definitionB,'Adnan'))

# create close button
closeButton = QtWidgets.QPushButton('Close')
layout.addWidget(closeButton)
closeButton.setFont(font)
closeButton.clicked.connect(window.close)

# show the window
window.show()