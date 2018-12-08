import maya.cmds as cmds
import Tools.baseWindow
import Tools.Gear

class gearWindow(Tools.baseWindow.baseWindow):
	windowName = 'gearWindow'
	
	def __init__(self):
		#store current gear inside a variable
		self.gear = None
		
	def buildUI(self):
		column = cmds.columnLayout()
		cmds.text(label ='use the slider to modify the number of teeth the gear will have')
		cmds.rowLayout(nc=4)
		
		self.label = cmds.text (label = 10)
		self.slider = cmds.intSlider(min = 5, max = 30, value = 10, step = 1, dragCommand=self.modifyGear)
		cmds.button(label ='Make Gear', command = self.makeGear)
		cmds.button(label ='Reset', command = self.reset)
		
		cmds.setParent(column)
		cmds.rowLayout(nc = 2)
		self.lLength = cmds.text (label = 0.3)
		self.lSlider = cmds.floatSlider(min = 0.01, max = 3.0, value = 0.3, step = 0.01, dragCommand = self.modifyGear)
		
		cmds.setParent(column)
		cmds.button (label ='close', command = self.close)
		
	
	def makeGear(self,*args):
		teeth = cmds.intSlider (self.slider, q = True, value = True)
		
		#makeGear
		self.gear = Tools.Gear.gear()
		
		self.gear.create(teeth = teeth)
		
	def modifyGear(self, *args):
		print args
		teeth = cmds.intSlider(self.slider, q= True, value = True)
		print teeth
		length = cmds.floatSlider(self.lSlider, q=True, value = True)
		print length
		cmds.text(self.label, edit = True, label = teeth)
		cmds.text(self.lLength, edit = True, label =str(length)[0:4])
		
		if self.gear:
			self.gear.changeTeeth(teeth= int(teeth))
			self.gear.changeLength(length = str(length))
		
	def reset(self, *args):
		self.gear = None
		cmds.intSlider(self.slider, edit = True, value = 10)
		cmds.text (self.label, edit = True, label = str(10))
		