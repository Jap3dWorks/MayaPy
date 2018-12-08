import maya.cmds as cmds
"""
	ui constructor baseClass
		windowName = name
"""

class baseWindow(object):
	windowName = 'baseWindow'
	
	def show(self):
		if cmds.window(self.windowName, query=True, exists=True):
			self.close()
	
		cmds.window(self.windowName)
		self.buildUI()
		cmds.showWindow()
		
	def buildUI(self):
		"""
			def Ui here
		"""
		#this method is a placeHolder
		pass
		
	def reset(self, *args):
		#this method is a placeholder
		pass
	
	def close(self, *args):
		cmds.deleteUI(self.windowName)