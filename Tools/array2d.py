class array2d():
	
	def __init__(self, row, col):
		self.array2d = []
		self.row = row
		self.col = col
		for r in range(0,row):
			tempArr = []
			for c in range(0,col):
				tempArr.append (0)
			self.array2d.append(tempArr)
	
	def __str__(self):
		printer = ''
		for r in range(0, self.row):
			for c in range(0, self.col):
				printer = printer + '['+ str(self.array2d[r][c]) + ']'
			printer = printer + '\n'
		return printer