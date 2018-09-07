import os
from maya import cmds
import json
import pprint
"""
implement material merge by name, include materials in dictionary, auto detect
"""
#DIRECTORY = os.path.join(cmds.internalVar(userAppDir = True), 'controllerLibrary')
DIRECTORY = os.path.join('D:\_docs', 'controllerLibrary')


class controllerLibrary(dict):
	
	def createDir(self, directory = DIRECTORY):
		
		#check if directory exist
		if not os.path.exists(directory):
			os.mkdir(directory)
			
	def save(self, name, screenShot = True, directory = DIRECTORY, **info):
		"""
        The save function will save the current scene as a controller
        Args:
            name: the name to save the controller as
            screenshot: Whether or not to save a screenshot
            directory: the directory to save to
            **info: any extra info we might want to store
        """
		self.createDir(directory)
		path = os.path.join(directory, '%s.ma' % name)
		#json path
		infoFile = os.path.join(directory, '%s.json' % name)
		
		#call screenshot method
		if screenShot:
			info ['screenshot'] = self.saveScreenshot(name = name, directory = directory)
			
		info ['name'] = name
		info ['path'] = path
		
		#rename file to what we want in to be saved as
		#cmds.file(rename = path)
		#something selected or not, first we set the path, now we save the file
		if cmds.ls(sl = True):
			cmds.file(path, typ = 'mayaAscii', exportSelected = True, force = True)
		else:
			cmds.file(path, typ = 'mayaAscii', ea=True, force = True) # <--- make a save as not a save
		#controllerLinrary is a dict class so we can store data in ourselves
		#dictionary in a dictionary
		self[name] = info
		
		with open(infoFile, 'w') as f:
			json.dump(info, f, indent = 4)
			
	#find all the controllers in the given directory		
	def find(self, directory = DIRECTORY):
		if not os.path.exists(directory):
			return
			
		files = os.listdir(directory)
		
		mayaFiles = [f for f in files if f.endswith('.ma')]
		for ma in mayaFiles:
			name, ext = os.path.splitext(ma)
			
			#contruct info file name and screenshot name
			infoFile = '%s.json' %name
			screenshot = '%s.jpg' %name
			
			#if info file exist construct path
			if infoFile in files:
				infoFile = os.path.join(directory, infoFile)
				
				with open (infoFile, 'r') as f:
					#json to dictionary
					data = json.load(f)
					
			else:
				data = {}
				
			if screenshot in files:
				data ['screenshot'] = os.path.join(directory, screenshot)
				
			#basic information
			data['name'] = name
			data['path'] = os.path.join(directory, ma)
			
			#save data in self
			self[name] = data
			
			#pprint.pprint(self)
			
	def load(self, name):
		path = self[name]['path']
		cmds.file(path, i=True, usingNamespaces = False)
	
	#save screenshot
	def saveScreenshot(self, name, directory = DIRECTORY):
		path = os.path.join(directory, '%s.jpg' %name)
		cmds.viewFit()
		
		cmds.setAttr('defaultRenderGlobals.imageFormat', 8) #jpgValue
		
		cmds.playblast(completeFilename = path, forceOverwrite = True, format = 'image', width = 200, height = 200, showOrnaments = False,
						startTime = 1, endTime = 1, viewer = False)
						
		return path
		
					
		
