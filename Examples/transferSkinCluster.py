"""
Review: Command with args/flags
store position too, for possible vertex index variation
{joint1: [[index, val], [index, influenceNumber,val]], joint2: [[index, influenceNumber,val], [index, influenceNumber,val]]}
store in a class

"""
# ----------------------------------------------------------------------------------------------
#
# transferSkinCluster.py
# v1.43 (160430)
#
# export/import weights of the selected skinCluster
#
# Ingo Clemens
# www.braverabbit.com
#
# Copyright brave rabbit, Ingo Clemens 2012-2015
# All rights reserved.
#
# ----------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# ----------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------
#
#	USE AND MODIFY AT YOUR OWN RISK!!
#
# ----------------------------------------------------------------------------------------------


import os

import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaAnim as OpenMayaAnim

import maya.cmds as cmds
import maya.mel as mel

kPluginCmdName = 'transferSkinCluster'


# --------------------------------------------------------------------------------
# argument flags
# --------------------------------------------------------------------------------

helpFlag = '-h'
helpFlagLong = '-help'

fileFlag = '-f'
fileFlagLong = '-file'

modeFlag = '-m'
modeFlagLong = '-mode'

orderFlag = '-ro'
orderFlagLong = '-reverseOrder'

exclusiveFlag = '-ex'
exclusiveFlagLong = '-exclusive'

helpText = ''
helpText += '\n Description: The command exports and imports the selected skinCluster to/from a file.'
helpText += '\n'
helpText += '\n Flags: transferSkinCluster -h    -help          <n/a>       this message'
helpText += '\n                            -m    -mode          <int>       write (default=0) or read (1)'
helpText += '\n                            -ro   -reverseOrder  <int>       from file (default=0) or reversed (1)'
helpText += '\n                            -f    -file          <string>    the file name for the skinCluster weight data'
helpText += '\n                            -ex   -exclusive     <int>       stores the weight for each influence to a separate file'
helpText += '\n'
helpText += '\n Usage:   Execute the command with the following arguments:'
helpText += '\n Execute: transferSkinCluster -m <mode> -f <file name>;';


# --------------------------------------------------------------------------------
# command
# --------------------------------------------------------------------------------

class transferSkinCluster(OpenMayaMPx.MPxCommand):
	
	def __init__(self):
		OpenMayaMPx.MPxCommand.__init__(self)
	
	def doIt(self, args):
		
		modeArg = 0
		fileName = ''
		orderArg = 0
		exclusiveArg = 0
		
		# parse the arguments.
		argData = OpenMaya.MArgDatabase(self.syntax(), args)
		
		if argData.isFlagSet(helpFlag):
			self.setResult(helpText)
			return()

		# read flag arguments
		if argData.isFlagSet(modeFlag):
			modeArg = argData.flagArgumentDouble(modeFlag, 0)
		if argData.isFlagSet(orderFlag):
			orderArg = argData.flagArgumentDouble(orderFlag, 0)
		if argData.isFlagSet(exclusiveFlag):
			exclusiveArg = argData.flagArgumentDouble(exclusiveFlag, 0)
		if argData.isFlagSet(fileFlag):
			fileName = argData.flagArgumentString(fileFlag, 0)
		else:
			OpenMaya.MGlobal.displayError(kPluginCmdName + ' needs file name flag.')
			return()
		
		if fileName == '':
			OpenMaya.MGlobal.displayError(kPluginCmdName + ' file name is not specified.')
			return()
		
		if modeArg < 0 or modeArg > 1:
			OpenMaya.MGlobal.displayError(kPluginCmdName + ' mode needs to be set to either 0 for \'write\' or 1 for \'read\'.')
			return()
		
		start = cmds.timerX()
		msgString = ''
		
		result = 0
		if modeArg == 0:
			result = self.writeWeights(fileName, exclusiveArg)
			msgString = 'exported to '
		else:
			result = self.readWeights(fileName, orderArg)
			msgString = 'imported from '
		
		doneTime = cmds.timerX(startTime = start)
		if result == 1:
			OpenMaya.MGlobal.displayInfo('transferSkinCluster command took %.02f seconds' % doneTime)
			OpenMaya.MGlobal.displayInfo('Weights ' + msgString + '\'' + fileName + '\'')


	# --------------------------------------------------------------------------------
	# write the weights file
	# --------------------------------------------------------------------------------

	def writeWeights(self, fileName, exclusive):
		
		# get the current selection
		skinClusterNode = cmds.ls(sl=True, fl=True)
		if len(skinClusterNode) != 0:
				skinClusterNode = skinClusterNode[0]
		else:
			OpenMaya.MGlobal.displayError('Select a skinCluster node to export.')
			return(-1)
		
		# check if it's a skinCluster
		if cmds.nodeType(skinClusterNode) != 'skinCluster':
			OpenMaya.MGlobal.displayError('Selected node is not a skinCluster.')
			return(-1)
		
		# get the MFnSkinCluster
		sel = OpenMaya.MSelectionList()
		OpenMaya.MGlobal.getActiveSelectionList(sel)
		skinClusterObject = OpenMaya.MObject()
		sel.getDependNode(0, skinClusterObject)
		# documentation: MFNSkinCluster: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__cpp_ref_class_m_fn_skin_cluster_html
		skinClusterFn = OpenMayaAnim.MFnSkinCluster(skinClusterObject)
		
		# get the influence objects
		infls = cmds.skinCluster(skinClusterNode, q=True, inf=True)
		if len(infls) == 0:
			OpenMaya.MGlobal.displayError('No influence objects found for skinCluster %s.' % skinClusterNode)
			return(-1)
		
		# get the connected shape node
		shape = cmds.skinCluster(skinClusterNode, q=True, g=True)[0]
		if len(shape) == 0:
			OpenMaya.MGlobal.displayError('No connected shape nodes found.')
			return(-1)
		
		# get the dag path of the shape node
		cmds.select(shape, r=True)
		sel = OpenMaya.MSelectionList()
		OpenMaya.MGlobal.getActiveSelectionList(sel)
		shapeDag = OpenMaya.MDagPath()
		sel.getDagPath(0, shapeDag)
		# create the geometry iterator
		geoIter = OpenMaya.MItGeometry(shapeDag)
		
		# create a pointer object for the influence count of the MFnSkinCluster
		infCount = OpenMaya.MScriptUtil()
		infCountPtr = infCount.asUintPtr()
		OpenMaya.MScriptUtil.setUint(infCountPtr, 0)
		
		value = OpenMaya.MDoubleArray()
		
		#
		# default export to a single skin weights file
		#
		if not exclusive:
			try:
				weightFile = open(fileName, 'wb')
			except:
				OpenMaya.MGlobal.displayError('A file error has occured for file \'' + fileName + '\'.')
				return(-1)
			
			# write all influences and the shape node to the file
			for i in range(0, len(infls), 1):
				weightFile.write(infls[i] + " ")
			weightFile.write(shape + '\n')
			
			weightFile.write(skinClusterNode + '\n')
			
			# write the attributes of the skinCluster node to the file
			result = cmds.getAttr(skinClusterNode + ".normalizeWeights")
			weightFile.write('-nw %s ' % result)
			result = cmds.getAttr(skinClusterNode + ".maxInfluences")
			weightFile.write('-mi %s ' % result)
			result = cmds.getAttr(skinClusterNode + ".dropoff")[0][0]
			weightFile.write('-dr %s\n' % result)
			
			# get the skinCluster weights
			while geoIter.isDone() == False:
				skinClusterFn.getWeights(shapeDag, geoIter.currentItem(), value, infCountPtr)
				for j in range(0, len(infls)):
					if value[j] > 0:
						lineArray = [geoIter.index(), infls[j], j, value[j]]
						weightFile.write(str(lineArray) + '\n')
				geoIter.next()
			
			weightFile.close()
		
		#
		# custom export to individual files
		#
		else:
			cmds.skinCluster(skinClusterNode, e = True, fnw = True);
			dataPath = '%s/%s' % (fileName, skinClusterNode)
			if not os.path.exists(dataPath):
				try:
					os.makedirs(dataPath)
				except:
					OpenMaya.MGlobal.displayError('Unable to create export directory \'' + dataPath + '\'.')
					return(-1)
			
			for j in range(0, len(infls)):
				fileName = '%s/%s.bsw' % (dataPath, infls[j])
				try:
					weightFile = open(fileName, 'wb')
				except:
					OpenMaya.MGlobal.displayError('A file error has occured for file \'' + fileName + '\'.')
					return(-1)
				
				geoIter.reset()
				
				while geoIter.isDone() == False:
					skinClusterFn.getWeights(shapeDag, geoIter.currentItem(), value, infCountPtr)
					line = str(geoIter.index()) + ' ' + str(value[j]) + '\n'
					weightFile.write(line)
					geoIter.next()
				
				weightFile.close()
		
		return(1)
		

	# --------------------------------------------------------------------------------
	# read the weights file
	# --------------------------------------------------------------------------------

	def readWeights( self, fileName, reverseOrder ):
		
		# open the file for reading
		try:
			weightFile = open(fileName, 'rb')
		except:
			OpenMaya.MGlobal.displayError('A file error has occured for file \'' + fileName + '\'.')
			return(-1)
		
		weightData = weightFile.read()
		weightLines = weightData.split('\n')
		weightFile.close()
		
		normalization = 1
		
		# variables for writing a range of influences
		weightString = ''
		inflStart = -1
		inflEnd = -1
		setCount = 0
		writeData = 0
		
		# --------------------------------------------------------------------------------
		# the first line contains the joints and skin shape
		# --------------------------------------------------------------------------------
		objects = weightLines[0]
		items = objects.split(' ')
		shape = items[len(items) - 1]
		
		# --------------------------------------------------------------------------------
		# the second line contains the name of the skin cluster
		# --------------------------------------------------------------------------------
		skinClusterName = weightLines[1]
		
		# --------------------------------------------------------------------------------
		# the third line contains the values for the skin cluster
		# --------------------------------------------------------------------------------
		objects = objects.split(' ')
		if reverseOrder == 1:
			objects = objects[::-1]
			objects.pop(0)
			objects.append(shape)

		# select the influences and the skin shape
		try:
			cmds.select(objects, r = True)
		except:
			weightFile.close()
			return()
		
		# check if the geometry is not already bound
		history = cmds.listHistory(shape, f = 0, bf = 1)
		for h in history:
			if cmds.nodeType(h) == 'skinCluster':
				OpenMaya.MGlobal.displayError(shape + ' is already connected to a skinCluster.')
				return(-1)
		
		# check for the version
		# up to Maya 2012 the bind method flag is not available
		version = mel.eval('getApplicationVersionAsFloat()')
		bindMethod = '-bm 0 '
		if version < 2013:
			bindMethod = '-ih '
		
		# create the new skinCluster
		newSkinCluster = mel.eval('newSkinCluster \"-tsb ' + bindMethod + weightLines[2] + '-omi true -rui false\"')[0]
		cmds.rename(newSkinCluster, skinClusterName)
		
		# get the current normalization and store it
		# it will get re-applied after applying all the weights
		normalization = cmds.getAttr(skinClusterName + '.nw')
		# turn off the normalization to correctly apply the stored skin weights
		cmds.setAttr((skinClusterName + '.nw'), 0)
		# pruning the skin weights to zero is much faster
		# than iterating through all components and setting them to 0
		cmds.skinPercent(skinClusterName, shape, prw = 100, nrm = 0)
		
		# allocate memory for the number of components to set
		weights = eval(weightLines[len(weightLines) - 2])
		# get the index of the last component stored in the weight list
		maxIndex = weights[0]
		cmds.select(skinClusterName, r = True)
		cmdString = 'setAttr -s ' + str(maxIndex + 1) + ' \".wl\"'
		OpenMaya.MGlobal.executeCommand(cmdString)
					
		# --------------------------------------------------------------------------------
		# apply the weight data
		# --------------------------------------------------------------------------------
		
		# timer for timing the read time without the smooth binding
		#start = cmds.timerX()
		
		for l in range(3, len(weightLines) - 1):
			
			weights = eval(weightLines[l])
			weightsNext = ''
			# also get the next line for checking if the component changes
			# but only if it's not the end of the list
			if l < len(weightLines) - 2:
				weightsNext = eval(weightLines[l + 1])
			else:
				weightsNext = weights
				writeData = 1
			
			compIndex = weights[0]
						
			# --------------------------------------------------------------------------------
			# construct the setAttr string
			# i.e. setAttr -s 4 ".wl[9].w[0:3]"  0.0003 0.006 0.496 0.496
			# --------------------------------------------------------------------------------
			
			# start a new range
			if inflStart == -1:
				inflEnd = inflStart = weights[2]
			else:
				# if the current component is the next in line
				if inflEnd == weights[2] - 1:
					inflEnd = weights[2]
				# if influences were dropped because of zero weight
				else:
					# fill the weight string inbetween with zeros
					for x in range(inflEnd + 1, weights[2]):
						weightString += '0 '
						setCount += 1
					inflEnd = weights[2]
				
			# add the weight to the weight string
			weightString += str(weights[3]) + ' '
			# increase the number of weights to be set
			setCount += 1
				
			# if the next line is for the next index set the weights
			if compIndex != weightsNext[0]:
				writeData = 1
				
			if writeData == 1:
				# decide if a range or a single influence index is written
				rangeString = ':' + str(inflEnd)
				if inflEnd == inflStart:
					rangeString = ''
					
				cmdString = 'setAttr -s ' + str(setCount) + ' \".weightList[' + str(compIndex) + '].weights[' + str(inflStart) + rangeString + ']\" ' + weightString
				OpenMaya.MGlobal.executeCommand(cmdString)
					
				# reset and start over
				inflStart = inflEnd = -1
				writeData = 0
				setCount = 0
				weightString = ''
				
		cmds.setAttr((skinClusterName + '.nw'), normalization)
		
		#doneTime = cmds.timerX(startTime = start)
		#OpenMaya.MGlobal.displayInfo('%.02f seconds' % doneTime)
		
		return(1)


# --------------------------------------------------------------------------------
# define the syntax, needed to make it work with mel and python
# --------------------------------------------------------------------------------

# creator
def cmdCreator():
	return OpenMayaMPx.asMPxPtr(transferSkinCluster())
	
def syntaxCreator():
	syn = OpenMaya.MSyntax()
	syn.addFlag(helpFlag, helpFlagLong);
	syn.addFlag(fileFlag, fileFlagLong, OpenMaya.MSyntax.kString);
	syn.addFlag(modeFlag, modeFlagLong, OpenMaya.MSyntax.kLong);
	syn.addFlag(orderFlag, orderFlagLong, OpenMaya.MSyntax.kLong);
	syn.addFlag(exclusiveFlag, exclusiveFlagLong, OpenMaya.MSyntax.kLong);
	return syn

# initialization
def initializePlugin( mobject ):
	mplugin = OpenMayaMPx.MFnPlugin(mobject, 'Ingo Clemens', '1.42', 'Any')
	try:
		mplugin.registerCommand(kPluginCmdName, cmdCreator, syntaxCreator)
	except:
		sys.stderr.write('Failed to register command: %s\n' % kPluginCmdName)
		raise

def uninitializePlugin( mobject ):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		mplugin.deregisterCommand(kPluginCmdName)
	except:
		sys.stderr.write( 'Failed to unregister command: %s\n' % kPluginCmdName )
		raise


melProcs = '''

//----------------------------------------------------------------------------------------------
//
// checking for the skinWeights folder
//
//----------------------------------------------------------------------------------------------

global proc string icTransferSkinClusterCheckDir()
{
	string $weightPath = "data/skinWeights";
	string $workDir = `workspace -q -rd`;
	string $tempDir = `workspace -q -dir`;
	workspace -dir $workDir;

	if (!`filetest -d ($workDir + $weightPath)`)
	{
		string $confirm = `confirmDialog 
					-t "Create Missing Directory"
					-m "Create a 'skinWeights' folder at the current projects data path?"
					-ma center
					-b "OK" -b "Cancel"
					-db "OK" -cb "Cancel" -ds "Cancel"`;
		if ($confirm == "OK")
		{
			workspace -cr $weightPath;
			$workDir += $weightPath + "/";
		}
		else
			$workDir += "data/";
	}
	else
		$workDir += $weightPath + "/";

	print ("// Skin weights directory is set to '" + $workDir + "' //\\n");
	
	workspace -dir $tempDir;
	return $workDir;
}

//----------------------------------------------------------------------------------------------
//
// create the window
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterWindow( string $win )
{
	if (`window -exists $win`)
		deleteUI $win;

	window -t "Import SkinCluster Weights" -w 400 -h 208 -mb 1 $win;
	if (`windowPref -exists $win`)
		windowPref -e -wh 400 208 $win;
	
	menu -l "Help";
	menuItem -l "Rename Help" -c icTransferSkinClusterOpenHelpWindow;
	
	string $form = `formLayout`;
	
	textScrollList -ams 0 -h 120 tsc_weightTSL;
	text -l "\\nJoint Name Mismatch (See Menu > Help for details)" -fn "boldLabelFont" -m 0 tsc_mismatchTitle;
	text -l "\\nRename From File" -al "left" -m 0 tsc_renameSelectionLabel;
	textScrollList -ams 0 -m 0 -sc icTransferSkinClusterRename tsc_influenceTSL;
	text -l "\\nRename" -al "left" -m 0 tsc_replaceLabel;
	checkBox -l "Use Prefix/Suffix" -cc icTransferSkinClusterTogglePrefix -m 0 tsc_prefixCheck;
	textFieldGrp -l "Search" -cw2 50 80 -cl2 "left" "center" -ct2 "both" "both" -m 0 tsc_findField;
	textFieldGrp -l "Replace" -cw2 50 80 -cl2 "left" "center" -ct2 "both" "both" -m 0 tsc_replaceField;
	button -l "Rename And Save" -m 0 tsc_bFindReplace;
	button -l "Import" tsc_bApply;
	
	formLayout 	-e 
				-af tsc_weightTSL top 5
				-af tsc_weightTSL left 5
				-af tsc_weightTSL right 5
				
				-af tsc_mismatchTitle left 5
				-af tsc_mismatchTitle right 5
				-ac tsc_mismatchTitle top 0 tsc_weightTSL
				
				-af tsc_renameSelectionLabel left 5
				-af tsc_renameSelectionLabel right 5
				-ac tsc_renameSelectionLabel top 0 tsc_mismatchTitle
				
				-af tsc_influenceTSL left 5
				-af tsc_influenceTSL right 5
				-ac tsc_influenceTSL top 5 tsc_renameSelectionLabel
				-ac tsc_influenceTSL bottom 0 tsc_replaceLabel
				
				-af tsc_replaceLabel left 5
				-af tsc_replaceLabel right 5
				-ac tsc_replaceLabel bottom 5 tsc_prefixCheck
				
				-af tsc_prefixCheck left 5
				-af tsc_prefixCheck right 5
				-ac tsc_prefixCheck bottom 5 tsc_findField
				
				-af tsc_findField left 5
				-ac tsc_findField bottom 15 tsc_bApply
				
				-ac tsc_replaceField left 10 tsc_findField
				-ac tsc_replaceField bottom 15 tsc_bApply
				
				-af tsc_bFindReplace right 5
				-ac tsc_bFindReplace bottom 15 tsc_bApply
				
				-af tsc_bApply left 5
				-af tsc_bApply right 5
				-af tsc_bApply bottom 5
				
				$form;
}

//----------------------------------------------------------------------------------------------
//
// button callbacks
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterButtonCallback( string $workDir, int $order, string $win )
{
	textScrollList -e -sc ("icTransferSkinClusterCheckJoints \\"" + $workDir + "\\" " + $win) tsc_weightTSL;
	button -e -c ("icTransferSkinClusterReplaceAndSave \\"" + $workDir + "\\"") tsc_bFindReplace;
	button -e -c ("icTransferSkinClusterImportWeight \\"" + $workDir + "\\" " + $order) tsc_bApply;
}

//----------------------------------------------------------------------------------------------
//
// button callbacks
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterTogglePrefix()
{
	if (`checkBox -q -v tsc_prefixCheck`)
	{
		textFieldGrp -e -l "Prefix" tsc_findField;
		textFieldGrp -e -l "Suffix" tsc_replaceField;
	}
	else
	{
		textFieldGrp -e -l "Search" tsc_findField;
		textFieldGrp -e -l "Replace" tsc_replaceField;
	}
		
}

//----------------------------------------------------------------------------------------------
//
// open the help window
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterOpenHelpWindow()
{
	string $win = "icTransferSkinClusterHelpWindow";
	
	if (`window -exists $win`)
		deleteUI $win;

	window -t "Joint Name Mismatch" -w 350 -h 300 $win;
	if (`windowPref -exists $win`)
		windowPref -e -wh 350 300 $win;
	
	rowColumnLayout -co 1 "both" 10;
	text -al "left" -l "\\nIf some or all stored joint names in the weights file don't match\\nthe joint names in the scene you have several rename options:";
	separator -h 10 -style "none";
	text -h 25 -al "left" -l "Rename From File" -fn "boldLabelFont";
	text -al "left" -l "Renames the existing joints in the scene to match the names\\nin the weights file.";
	text -al "left" -l "Select the joint in the scene which should be renamed and select\\nthe item in the list to rename.";
	separator -h 10 -style "none";
	text -h 25 -al "left" -l "Search And Replace" -fn "boldLabelFont";
	text -al "left" -l "Renames the stored joint names in the weights file with a\\nsearch and replace string.";
	text -al "left" -l "This creates a new weights file you can then import.";
	separator -h 10 -style "none";
	text -h 25 -al "left" -l "Add Prefix Or Suffix" -fn "boldLabelFont";
	text -al "left" -l "For adding a prefix or suffix activate the Use Prefix/Suffix option.";
	text -al "left" -l "Use the Prefix field to add a prefix or the Suffix field to append\\na suffix.";
	text -al "left" -l "This creates a new weights file you can then import.";
	separator -h 10 -style "none";
	text -h 25 -al "left" -l "Missing Joints" -fn "boldLabelFont";
	text -al "left" -l "If after renaming some joints are still missing a fast solution is to\\nre-create the missing joints in their previous location and\\nuse them as dummy joints.";
	text -al "left" -l "They only need to serve as skin joints to make the skin cluster work\\nbut have no other functionality.";
	text -al "left" -l "Select an existing joint around the location where the missing joint\\nhas been before, duplicate it and delete any duplicated children.";
	text -al "left" -l "Then rename the joint to match the missing joint name.";
	text -al "left" -l "For duplication you can also use the Duplicate Joint button below.";
	separator -h 10 -style "none";
	button -l "Duplicate Joint" -w 100 -c "duplicate -po";
	separator -h 5 -style "none";
	separator -h 10 -style "none";
	setParent ..;
	
	showWindow $win;
}

//----------------------------------------------------------------------------------------------
//
// check for existing joints
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterCheckJoints( string $workDir, string $win )
{
	textScrollList -e -ra tsc_influenceTSL;
	
	string $selection[] = `textScrollList -q -si tsc_weightTSL`;
	
	int $fileId = `fopen ($workDir + $selection[0]) "r"`;
	string $fileLine = `fgetline $fileId`;
	fclose $fileId;
	
	$fileLine = `substitute "\\n" $fileLine ""`;
	
	string $objs[];
	string $mismatch[];
	tokenize $fileLine " " $objs;
	for ($obj in $objs)
	{
		if (!`objExists $obj`)
			$mismatch[size($mismatch)] = $obj;
	}
	
	int $state = 0;
	
	if (size($mismatch))
	{
		$state = 1;
		
		for ($m in $mismatch)
			textScrollList -e -a $m tsc_influenceTSL;
	}
	
	text -e -m $state tsc_mismatchTitle;
	text -e -m $state tsc_renameSelectionLabel;
	textScrollList -e -m $state tsc_influenceTSL;
	text -e -m $state tsc_replaceLabel;
	textFieldGrp -e -m $state tsc_findField;
	textFieldGrp -e -m $state tsc_replaceField;
	button -e -m $state tsc_bFindReplace;
	checkBox -e -m $state tsc_prefixCheck;
	
	if ($state == 0)
		window -e -h 208 $win;
}

//----------------------------------------------------------------------------------------------
//
// rename the selection
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterRename()
{
	string $selection[] = `textScrollList -q -si tsc_influenceTSL`;
	string $sel[] = `ls -sl -type joint`;
	if (size($sel))
		rename $sel[0] $selection[0];
}

//----------------------------------------------------------------------------------------------
//
// replace the file content with the replace string and save as a new file
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterReplaceAndSave( string $workDir )
{
	string $selection[] = `textScrollList -q -si tsc_weightTSL`;
	
	string $infList[] = `textScrollList -q -ai tsc_influenceTSL`;
	
	string $search = `textFieldGrp -q -tx tsc_findField`;
	string $replace = `textFieldGrp -q -tx tsc_replaceField`;
	int $usePrefix = `checkBox -q -v tsc_prefixCheck`;
	
	int $fileId = `fopen ($workDir + $selection[0]) "r"`;
	string $fileLine = `fgetline $fileId`;
	
	string $fileName = `substitute ".scw" $selection[0] ""`;
	
	int $fileIdNew = `fopen ($workDir + $fileName + "_replaced.scw") "w"`;
	
	int $lineCount = 0;
	
	while (size($fileLine) > 0)
	{
		string $line;
		$line = `substitute "\\n" $fileLine ""`;
		if (!$usePrefix)
		{
			$items = stringToStringArray($line, " ");
			for ($i = 0; $i < size($items) - 1; $i ++)
			{
				for ($inf in $infList)
				{
					if (`gmatch $items[$i] ("*" + $inf + "*")`)
						$items[$i] = substituteAllString($items[$i], $search, $replace);
				}
			}
			$line = stringArrayToString($items, " ");
		}
		else
		{
			if ($lineCount == 0)
			{
				string $items[] = stringToStringArray($line, " ");
				for ($i = 0; $i < size($items) - 1; $i ++)
				{
					for ($inf in $infList)
					{
						if (`gmatch $items[$i] ("*" + $inf + "*")`)
						{
							if ($replace != "")
								$items[$i] = $items[$i] + $replace;
							else if ($search != "")
								$items[$i] = $search + $items[$i];
						}
					}
				}
				$line = stringArrayToString($items, " ");
			}
			else if ($lineCount > 2)
			{
				for ($inf in $infList)
				{
					if (`gmatch $line ("*" + $inf + "*")`)
					{
						if ($replace != "")
							$line = `python("a = eval(\\"" + $line + "\\"); a[1] = a[1] + \\"" + $replace + "\\"; repr(a)")`;
						if ($search != "")
							$line = `python("a = eval(\\"" + $line + "\\"); a[1] = \\"" + $search + "\\" + a[1]; repr(a)")`;
					}
				}
			}
		}
		$line += "\\n";
		
		fprint $fileIdNew $line;
		$fileLine = `fgetline $fileId`;
		
		$lineCount ++;
	}
	
	fclose $fileId;
	fclose $fileIdNew;
	
	string $listItems[] = `textScrollList -q -ai tsc_weightTSL`;
	if (stringArrayFind($fileName + "_replaced.scw", 0, $listItems) == -1)
		textScrollList -e -a ($fileName + "_replaced.scw") tsc_weightTSL;
}

//----------------------------------------------------------------------------------------------
//
// import the selected skinCluster
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterImportWeight( string $workDir, int $order )
{
	string $selection[] = `textScrollList -q -si tsc_weightTSL`;
	if (size($selection[0]))
		transferSkinCluster -m 1 -ro $order -f ($workDir + $selection[0]);
}

//----------------------------------------------------------------------------------------------
//
// find the weight files in the current project
//
//----------------------------------------------------------------------------------------------

global proc string icTransferSkinClusterFindWeights()
{
	string $weightPath = "data/skinWeights";
	string $dirContent[];
	int $exists;
	int $count = 0;

	string $workDir = `workspace -q -rd`;
	if (`filetest -d ($workDir + $weightPath)`)
		$workDir += $weightPath + "/";
	else
		$workDir += "data/";
	$dirContent = `getFileList -fld $workDir`;
	for ($item in $dirContent)
		if (`gmatch $item "*.scw"`)
			textScrollList -e -a $item tsc_weightTSL;

	return $workDir;
}

//----------------------------------------------------------------------------------------------
//
// creating the window
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinClusterImport( int $order )
{
	string $win = "icTransferSkinClusterUI";
	if (`window -exists $win`)
		deleteUI $win;
	icTransferSkinClusterWindow($win);
	string $workDir = `icTransferSkinClusterFindWeights`;
	icTransferSkinClusterButtonCallback( $workDir, $order, $win );
	showWindow $win;
}

//----------------------------------------------------------------------------------------------
//
// find the skinCluster node
//
//----------------------------------------------------------------------------------------------

global proc string[] icTransferSkinClusterFindSkinCluster()
{
	string $return[];
	string $sel[] = `ls -sl -tr`;
	if (!size($sel))
		error ("Select a geometry to export weights.");
	for ($s in $sel)
	{
		string $his[] = `listHistory -f 0 -bf $s`;
		for ($h in $his)
		{
			if (`nodeType $h` == "skinCluster")
				$return[size($return)] = $h;
		}
	}
	return $return;
}

//----------------------------------------------------------------------------------------------
//
// main procedure
//
//----------------------------------------------------------------------------------------------

global proc icTransferSkinCluster( int $mode, int $order )
{
	if ($mode == 0)
	{
		string $workDir = `icTransferSkinClusterCheckDir`;
		string $sc[] = `icTransferSkinClusterFindSkinCluster`;
		for ($s in $sc)
		{
			select -r $s;
			transferSkinCluster -m 0 -f ($workDir + $s + ".scw");
		}
	}
	else
		icTransferSkinClusterImport $order;
}

'''
mel.eval(melProcs)
