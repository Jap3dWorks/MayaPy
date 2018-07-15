import maya.cmds as mc

def stackShells():
	shellBox = mc.polyEvaluate(bc2 = True)
	MPU = 0.5 * (shellBox[0][0] + shellBox[0][1])
	MPV = 0.5 * (shellBox[1][0] + shellBox[1][1])
	shells = uvShells()
	for shell in shells:
		shellBox = mc.polyEvaluate(shell, bc2 = True)
		piU = 0.5 * (shellBox[0][0] + shellBox[0][1])
		piV = 0.5 * (shellBox[1][0] + shellBox[1][1])
		posU = MPU - piU
		posV = MPV - piV
		mc.polyEditUV(shell, pu = piU, pv = piV, u = posU, v = posV)

"""
Collect uvShells from  a uv selection in a list
"""
def uvShells():
	"""
		List all the shells based in our uv's selection
		Returns:
			list with list of shells

		"""
	selection = mc.ls (sl = True, fl = True, type = 'float2')
	TotalShells=[]
	
	while len(selection) > 0:
		
		mc.select (selection[0], r=True)
		mc.polySelectConstraint (type = 0x0010, shell = 1, border = 0, mode = 2)
		mc.polySelectConstraint (shell = 0, border = 0, mode = 0)
		shell = mc.ls (sl = True, fl = True)
		mc.select (clear = True)
		
		TotalShells.append(shell)
		
		for delete in shell:
			if delete in selection:
				selection.remove(delete)
				
	return TotalShells
			
"""
orient uv shells in the minim bounding box
"""
def uvShellOrient(Shell=[]):
	if len(Shell) <= 0:
		Shell = mc.ls (sl = True, type = 'float2', fl = True)
	sweepSteps = 8
	iterations = 4
	sweepRange = 90.0
	sweepAngle = (sweepRange / sweepSteps)
	shellBox = mc.polyEvaluate(Shell, bc2 = True)
	piU = 0.5 * (shellBox[0][0] + shellBox[0][1]) #pivot in middle
	piV = 0.5 * (shellBox[1][0] + shellBox[1][1]) #pivot in middle
	oldTotal = 0.0
	newTotal = 0.0
	bestAngle = 0.0
	correctionAngle = 0.0
	
	for i in range (1, (iterations+1)):
		shellBox = mc.polyEvaluate (Shell, bc2 = True)
		oldTotal = (shellBox[0][1] - shellBox[0][0]) + (shellBox[1][1] - shellBox[1][0])
		bestAngle = 0.0
		
		for n in range (1, (sweepSteps)):
			mc.polyEditUV (Shell, pu = piU, pv = piV, r = True, a = sweepAngle)
			shellBox = mc.polyEvaluate (Shell, bc2 = True)
			newTotal = (shellBox[0][1] - shellBox[0][0]) + (shellBox[1][1] - shellBox[1][0])
			
			if newTotal < oldTotal:
				oldTotal = newTotal
				bestAngle = (n * sweepAngle)
				
		correctionAngle = bestAngle - (sweepAngle * (sweepSteps- 1))
		
		if  i != iterations:
			sweepRange = sweepAngle
			sweepAngle = sweepRange / sweepSteps
			correctionAngle -= (sweepRange * 0.5) #center in the best angle range
			
		mc.polyEditUV (Shell, pu = piU, pv = piV, r = True, a = correctionAngle)
				
"""
orient y up the shells
"""
def uvShellUp(Shell=[]):
	if len(Shell) <= 0:
		Shell = mc.ls (sl = True, type = 'float2', fl = True)
	bBox = mc.xform (Shell,ws = True, q = True, bb = True)
	yLen = bBox[4] - bBox[1]
	bLen = (((bBox[3]- bBox[0])**2)+((bBox[5]-bBox[2])**2))**0.5
	oldYMaxVal = bBox[1] #inverse, to guarante the check
	oldYMinVal = bBox[4] #inverse, to guarante the check
	vMax = None
	vMin = None
	shellBox = mc.polyEvaluate(Shell, bc2 = True)
	piU = 0.5 * (shellBox[0][0] + shellBox[0][1])
	piV = 0.5 * (shellBox[1][0] + shellBox[1][1])
	oldVMaxVal = shellBox[1][0]
	oldVMinVal = shellBox[1][1]
	
	for uv in Shell:
		uvPosition = mc.polyEditUV (uv, q = True, v = True)[1]
		Position = mc.xform (uv, q=True, ws = True, t = True)[1]
		
		if Position > oldYMaxVal:
			oldYMaxVal = Position
			oldVMaxVal = uvPosition
			vMax = uv 
			
		if Position < oldYMinVal:
			oldYMinVal = Position
			oldVMinVal = uvPosition
			vMin = uv 
			
	for i in range(0,4):
		shellBox = mc.polyEvaluate (Shell, bc2 = True)
		ulen = shellBox[0][1] - shellBox[0][0]
		vlen = shellBox[1][1] - shellBox[1][0]
		if yLen > bLen and vlen > ulen and oldVMaxVal > oldVMinVal:
			break
		elif yLen <= bLen and vlen <= ulen and oldVMaxVal > oldVMinVal:
			break
		else:
			mc.polyEditUV (Shell, pu = piU, pv = piV, r = True, a = 90)
			oldVMaxVal = mc.polyEditUV (vMax, q = True, v = True)[1]
			oldVMinVal = mc.polyEditUV (vMin, q = True, v = True)[1]