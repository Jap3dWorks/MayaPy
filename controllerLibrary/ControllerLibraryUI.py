from PySide2 import QtWidgets, QtCore, QtGui
from controllerLibrary import ControllerLibrary
#reload (ControllerLibrary)
from maya import cmds
import pprint

class controllerLibraryUI(QtWidgets.QDialog):
	def __init__(self):
		#get init superClass, then add new functionalities
		super(controllerLibraryUI, self).__init__()
		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) #stay always on top
		self.setWindowTitle('Controller Library UI')
		
		#store library in a variable
		self.library = ControllerLibrary.controllerLibrary()
		self.buildUI()
		
	def buildUI(self):
		
		#basic box to our class
		layout = QtWidgets.QVBoxLayout(self)
		
		saveWidget = QtWidgets.QWidget()
		saveLayout = QtWidgets.QHBoxLayout(saveWidget)
		layout.addWidget(saveWidget)
		
		self.saveNameField = QtWidgets.QLineEdit()
		saveLayout.addWidget(self.saveNameField)
		#save button
		saveBtn = QtWidgets.QPushButton('save')
		saveBtn.clicked.connect(self.save)
		saveLayout.addWidget(saveBtn)
		
		size = 64
		self.listWidget = QtWidgets.QListWidget()
		self.listWidget.setViewMode(QtWidgets.QListWidget.IconMode)
		self.listWidget.setIconSize(QtCore.QSize(size, size))
		#ajust position on resize
		self.listWidget.setResizeMode(QtWidgets.QListWidget.Adjust)
		#grid size litle larger
		self.listWidget.setGridSize(QtCore.QSize(size+12, size+12))
		layout.addWidget(self.listWidget)
		
		btnWidget = QtWidgets.QWidget()
		btnLayout = QtWidgets.QHBoxLayout(btnWidget)
		layout.addWidget(btnWidget)
		
		#buttons
		importBtn = QtWidgets.QPushButton('Import')
		importBtn.clicked.connect(self.load)
		btnLayout.addWidget(importBtn)
		
		refreshBtn = QtWidgets.QPushButton('Refresh')
		refreshBtn.clicked.connect(self.populate)
		btnLayout.addWidget(refreshBtn)
		
		closeBtn = QtWidgets.QPushButton('Close')
		closeBtn.clicked.connect(self.close)
		btnLayout.addWidget(closeBtn)
		
		self.populate()
		
	def load(self):
		currentItem = self.listWidget.currentItem()
		
		if not currentItem:
			return
			
		name = currentItem.text()
		self.library.load(name)
		
	def save(self):
		name = self.saveNameField.text()
		if not name.strip():
			cmds.warning('You must give a name!')
			return
		self.library.save(name=name)
		self.populate()
		self.saveNameField.setText('')

	def populate(self):
		self.listWidget.clear()
		self.library.find()
		#library class (Controller library class) is a dictionary 
		for name, info in self.library.items():
			item = QtWidgets.QListWidgetItem(name)
			item.setToolTip(pprint.pformat(info))
			screenshot = info.get('screenshot')
			
			if screenshot:
				icon = QtGui.QIcon(screenshot)
				item.setIcon(icon)
			
			self.listWidget.addItem(item)
			
	def showUI():
		#create instance of our ui
		ui=controllerLibraryUI()
		
		ui.show()
		return ui