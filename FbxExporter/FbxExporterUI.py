"""
documentation: https://doc.qt.io/qtforpython/index.html
TODO: FbxExporterUI
    We need:
        A widget with exportable objects:
            Here we can change exp attr or path attr. preferable with right click.
            RightClick path, add new path
        Export button.
        AddObj button.

"""
from FbxExporter import FbxExporter

from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import maya.api.OpenMaya as OpenMaya
import pymel.core as pm
from functools import partial

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter UI:')
logger.setLevel(logging.DEBUG)

# global var with fbxExporter obj
fbxExporter = FbxExporter.instance()

class FbxExporterUIWidget(QtWidgets.QWidget):
    """
    need: name of object. on click select, able or enable exp attr
    Class of Widgets for element
    BuildUI: construct of the UI
    Refresh info, with callbacks. if True, exportable path.
    """
    # TODO: context menu event for right click: remove paths
    def __init__(self, item):
        super(FbxExporterUIWidget, self).__init__()

        self.item = item

        if not isinstance(self.item, pm.nodetypes.Transform):
            self.item = pm.PyNode(self.item)

        # create actions for context menu
        # self.createActions()
        self.buildUI()

        # change colors background
        # explanation: palette colors: need setAutoFillBackground color, by default false
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Background, QtGui.QColor(40, 180, 255, 30 if self.chBox.isChecked() else 20))
        self.setPalette(palette)

        # context menu policy
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)  # necessary for context menus
        self.AddMenuActions()

    def buildUI(self):
        global fbxExporter

        layout = QtWidgets.QGridLayout(self)
        layout.setMargin(15)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        # chBox
        self.chBox = QtWidgets.QCheckBox(fbxExporter.attrBoolName)
        layout.addWidget(self.chBox, 0, 0)
        self.chBox.setChecked(self.item.attr(fbxExporter.attrBoolName).get())
        self.chBox.toggled.connect(self.chBoxFunc)
        self.chBox.setToolTip('Check to export')

        # middle_Layout: name // path
        middle_widget = QtWidgets.QWidget()
        middle_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        self.middle_layout = QtWidgets.QGridLayout(middle_widget)
        self.middle_layout.setSpacing(2)
        layout.addWidget(middle_widget, 0, 1)

        # name_button
        name_button = QtWidgets.QPushButton(str(self.item))
        self.middle_layout.addWidget(name_button, 0, 0)
        name_button.clicked.connect(lambda: pm.select(self.item))
        name_button.setContentsMargins(0, 0, 0, 0)

        # pathButton
        self._getNumPaths()

        # delButton
        delButton = QtWidgets.QPushButton('X')
        layout.addWidget(delButton, 0, 3)
        delButton.clicked.connect(self.delete)
        delButton.setToolTip('Delete from Fbx Exporter, not from scene')
        delButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)


    def chBoxFunc(self, val):
        self.item.attr(fbxExporter.attrBoolName).set(val)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Background, QtGui.QColor(40, 180, 255, 30 if val else 20))
        self.setPalette(palette)


    def delete(self):
        # delete widget
        global fbxExporter
        self.setVisible(False)
        self.deleteLater()

        # remove item attr
        fbxExporter.removeAttr(self.item)

    # context menu event
    # documentation: https://doc-snapshots.qt.io/qtforpython/PySide2/QtWidgets/QWidget.html?highlight=qwidget#PySide2.QtWidgets.PySide2.QtWidgets.QWidget.contextMenuEvent
    def AddMenuActions(self):
        addExtraPath = QtWidgets.QAction(self)
        addExtraPath.setText('Add Extra Path')
        addExtraPath.triggered.connect(self.addExtraPath)
        self.addAction(addExtraPath)

    def addExtraPath(self):
        global fbxExporter
        # add extra path
        path = getPathFunc(fbxExporter.defaultPath)  # default path
        fbxExporter.addExtraPathAttr(self.item, path)

        # delete all paths, and recreate
        self._getNumPaths()

    def _getNumPaths(self):
        """
        Get the number of paths and create the QPushbuttons for change path
        """
        global fbxExporter

        # delete previous path buttons
        for i in range(1, self.middle_layout.count()):
            widget = self.middle_layout.itemAt(i).widget()
            widget.setVisible(False)
            widget.deleteLater()

        # get paths and create buttons
        pathAttributes = self.item.attr(fbxExporter.attrCompoundName).get()[1:]
        for i, path in enumerate(pathAttributes):
            pathButton = QtWidgets.QPushButton('Path %s' % (i + 1))
            pathButton.setToolTip(path)

            # add context menu to button
            pathButton.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            deletePath = QtWidgets.QAction(pathButton)
            deletePath.triggered.connect(partial(self._deletePath, i+1))
            deletePath.setText('Delete Path')
            pathButton.addAction(deletePath)

            # add buttons to grid
            self.middle_layout.addWidget(pathButton, 0, i+1)
            pathButton.clicked.connect(partial(self._changePath, i + 1))
            pathButton.setContentsMargins(0, 0, 0, 0)

    def _deletePath(self, index):
        global fbxExporter
        # remove path
        fbxExporter.removeExtraPath(self.item, index)

        # populate middle_layout
        self._getNumPaths()


    def _changePath(self, index):
        """
        change path attr path method
        """
        global fbxExporter

        path = getPathFunc(self.item.attr('%s%s' % (fbxExporter.attrPathName, index)).get())
        self.item.attr('%s%s' % (fbxExporter.attrPathName, index)).set(path)

        # search button widget and change tooltip
        # explanation: itemAt returns a PySide2.QtWidgets.QLayoutItem
        # so we need use .widget() to access to the widget
        # documentation: https://doc.qt.io/qtforpython/PySide2/QtWidgets/QLayoutItem.html#PySide2.QtWidgets.QLayoutItem

        self.middle_layout.itemAt(index).widget().setToolTip(path)


class FbxExporterUI(QtWidgets.QWidget):
    """
    Fbx Exporter UI V1.0
    need: widget to fill, export button, add and remove buttons.
    addButton: ask for the path. enable multi object
    Class of general ui for FbxExporter
    BuildUI: construct of the UI
    Refresh info on deleting obj, or deleting attr

    We fill the UI of FbxExpUIWidgets objects.
    """
    idCallBack = []
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
        super(FbxExporterUI, self).__init__(parent=parent)
        self.parent().layout().addWidget(self)  # add widget finding preiously the parent
        # delete on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        # when parent is destroyed, child launch close method. we connect the signals.
        parent.destroyed.connect(self.close)

        self.buildUI()
        self.__refresh()

        # callBack
        # todo add callback on duplicate object
        self.idCallBack.append(OpenMaya.MEventMessage.addEventCallback('SceneOpened', self. __refresh))
        self.idCallBack.append(OpenMaya.MEventMessage.addEventCallback('NameChanged', self. __refresh))

    def buildUI(self):
        global fbxExporter

        # general layout
        general_layout = QtWidgets.QGridLayout(self)
        general_layout.setAlignment(QtCore.Qt.AlignHCenter)
        general_layout.setMargin(0)

        # create upper grid, widgets // visible checkbox
        upper_Widget = QtWidgets.QWidget()
        upper_layout = QtWidgets.QGridLayout(upper_Widget)
        general_layout.addWidget(upper_Widget, 0, 0)

        # fill upper Grid

        # check box visibility
        checkVi_widget = QtWidgets.QWidget()
        checkVi_Layout = QtWidgets.QGridLayout(checkVi_widget)
        upper_layout.addWidget(checkVi_widget, 0, 0)
        # checkBox
        cvCheckBox = QtWidgets.QCheckBox('Visible only')
        cvCheckBox.setChecked(True)
        cvCheckBox.setToolTip('Export only visible objects')
        checkVi_Layout.addWidget(cvCheckBox, 0, 0)
        checkVi_Layout.setSpacing(0)
        checkVi_Layout.setMargin(0)
        # Add button
        addButton = QtWidgets.QPushButton('Add')
        checkVi_Layout.addWidget(addButton, 0, 1)
        addButton.clicked.connect(self.add)
        addButton.setToolTip('Add objects to export, only transform nodes')
        # Export Button
        exportButton = QtWidgets.QPushButton('export')
        exportButton.clicked.connect(lambda: fbxExporter.export(cvCheckBox.isChecked()))
        checkVi_Layout.addWidget(exportButton, 0, 2)
        exportButton.setToolTip('Export FBX')

        # container
        container_widget = QtWidgets.QWidget()

        self.container_layout = QtWidgets.QVBoxLayout(container_widget)
        self.container_layout.setAlignment(QtCore.Qt.AlignTop)
        self.container_layout.setSpacing(0)
        self.container_layout.setMargin(0)
        # self.container_layout.addStretch(10)
        # now set that our widget have an scroll, this is a scroll area
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setAlignment(QtCore.Qt.AlignJustify)
        # Apply to scrollWidget
        scrollArea.setWidget(container_widget)
        upper_layout.addWidget(scrollArea, 1, 0)

    def add(self):
        """
        add attributes and refresh the container
        """
        global fbxExporter
        # add attributes // this method refresh the list
        path = getPathFunc(fbxExporter.defaultPath)
        logger.debug('Default path: %s , %s' % (path, fbxExporter.defaultPath))
        fbxExporter.addAttributes(path)

        # refresh container
        self.__refresh()

    def __refresh(self, *args):
        """
        Refresh container, for add and remove options, or change attributes
        """
        fbxExporter.constructList()

        global fbxExporter
        # private method for refresh list
        # clear container
        while self.container_layout.count():
            widget = self.container_layout.takeAt(0).widget()
            widget.setVisible(False)
            widget.deleteLater()

        # fill container
        # TODO: can be a good idea, change background color when active export of widget
        for i, item in enumerate(fbxExporter):
            # create on delete callback per obj
            mSelectionList = OpenMaya.MSelectionList().add(str(item))
            mObject = mSelectionList.getDependNode(0)
            # if item already has a callback, do nothing
            if not len(OpenMaya.MMessage.nodeCallbacks(mObject)):
                logger.debug('New remove callback Callback: %s' % item)
                self.idCallBack.append(OpenMaya.MModelMessage.addNodeRemovedFromModelCallback(mObject, self. __refresh))
            mSelectionList.clear()  # review: try without clear

            # create Widget
            widget = FbxExporterUIWidget(item)
            self.container_layout.addWidget(widget)

    # when close event, delete callbacks
    def closeEvent(self, event):
        for i, val in enumerate(self.idCallBack):
            # Event callback
            try:
                OpenMaya.MMessage.removeCallback(val)
                logger.debug('MMessage Callback removed: %s' % i)
            except:
                pass

def getPathFunc(defaultPath):
    pathWin = QtWidgets.QFileDialog.getExistingDirectory(parent=getMayaWindow(), caption='FBX exporter browser', dir=defaultPath)
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

def deleteDock(name = 'FbxExporterUIDock'):
    if pm.workspaceControl(name, query=True, exists=True):
        pm.deleteUI(name)

def getMayaWindow():
    #get maya main window
    win = omui.MQtUtil_mainWindow()
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)

    return ptr

"""
from FbxExporter import FbxExporterUI
from FbxExporter import FbxExporter
reload(FbxExporter)
reload(FbxExporterUI)
ui = FbxExporterUI.FbxExporterUI(True)
"""