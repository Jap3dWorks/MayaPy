# documentation: http://zetcode.com/gui/pysidetutorial/dragdrop/
# documentation: drag and drop: https://doc-snapshots.qt.io/qtforpython/overviews/dnd.html?highlight=drag

import sys
from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import pymel.core as pm

# create custom drag & drop button
class dButton(QtWidgets.QPushButton):
    def __init__(self, title, parent):
        super(dButton, self).__init__(title, parent)

    def mouseMoveEvent(self, e):
        # only drag and drop with right mouse button
        # documentation: QMouseEvents: https://doc-snapshots.qt.io/qtforpython/PySide2/QtGui/QMouseEvent.html#PySide2.QtGui.QMouseEvent
        if e.buttons() != QtCore.Qt.RightButton:
            return
        # documentation: https://doc-snapshots.qt.io/qtforpython/PySide2/QtCore/QMimeData.html?highlight=qmimedata
        # define information than can be stored in the clipboard, and transfered via drag and drop
        mimeData = QtCore.QMimeData()

        # documentation: https://doc-snapshots.qt.io/qtforpython/PySide2/QtGui/QDrag.html#PySide2.QtGui.QDrag
        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        # documentation: https://doc-snapshots.qt.io/qtforpython/PySide2/QtCore/QRect.html#PySide2.QtCore.QRect
        # topLeft() returns the position of the topLeft corner
        drag.setHotSpot(e.globalPos() - self.rect().topLeft())

        dropAction = drag.start(QtCore.Qt.MoveAction)

    # left click normal event
    def mousePressEvent(self, e):
        QtWidgets.QPushButton.mousePressEvent(self, e)  # prepare inherit class too
        # only on left button clicks
        if e.button() == QtCore.Qt.LeftButton:
            print 'press'

class dButtonUI(QtWidgets.QWidget):
    # UI test
    def __init__(self, dock=True):
        if dock:
            parent = getDock()
        else:
            deleteDock()
            try:
                pm.deleteUI('Click or move')
            except:
                pass

            # top level window
            parent = QtWidgets.QDialog(parent=getMayaWindow())
            parent.setObjectName('Click or move')
            parent.setWindowTitle('Click or move')
            # parent.closeEvent(lambda: logger.debug('clossing'))
            # Review: do not work well if not dockable
            # add a layout
            dlgLayout = QtWidgets.QVBoxLayout(parent)
            # dlgLayout.addWidget(self)

        parent.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        super(dButtonUI, self).__init__(parent=parent)
        self.parent().layout().addWidget(self)  # add widget finding preiously the parent
        # delete on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.initUI()

    def initUI(self):
        # no grid
        self.setAcceptDrops(True)  # accept drag and drop, necessary for move buttons

        self.btn = dButton('Button', self)
        self.btn.move(100, 65)

        # review: setGeometry
        self.setGeometry(300, 300, 300, 150)

    def dragEnterEvent(self, e):
        # review, dragEnterEvent
        # types of data widget accepts, p.e plane text or widgets
        e.accept()

    def dropEvent(self, e):
        # unpack dropped data, and handle it in way that is suitable
        # review, dropEvent
        position = e.pos()
        self.btn.move(position)

        e.setDropAction(QtCore.Qt.MoveAction)
        e.accept()


def getDock(name='Click or move Dock'):
    deleteDock(name)

    # Creates and manages the widget used to host windows in a layout
    # which enables docking and stacking windows together
    ctrl = pm.workspaceControl(name, dockToMainWindow=('right', 1), label='Click or move')
    # we need the QT version, MQtUtil_findControl return the qt widget of the named maya control
    qtCtrl = omui.MQtUtil_findControl(ctrl)
    # translate to something python understand
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)

    return ptr

def deleteDock(name = 'Click or move Dock'):
    if pm.workspaceControl(name, query=True, exists=True):
        pm.deleteUI(name)

def getMayaWindow():
    #get maya main window
    win = omui.MQtUtil_mainWindow()
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)

    return ptr