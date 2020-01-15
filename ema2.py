#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

class ema:

	emaRange = list() # Queue
	period   = int(0)
	k        = float(0.0)
	offset   = int(0)

	def __init__(self, emaValue : int, emaOffset : int):
		self.period = emaValue
		self.k = 2 / (emaValue + 1)
		self.setOffset(emaOffset)

	def load(self, sample : list) -> bool:
		if len(sample) <= self.period:
			return False

#1		self.emaRange = sample[-self.period:]
#1		self.insertAndPop(sum(self.emaRange) / float(self.period))

		try:
			self.backinsert(sum(sample[0:self.period]) / float(self.period))
		except:
			raise

		for i in sample[self.period:]:
			self.calcNewValueIsertAndPop(i)

		return True

	def setOffset(self, emaOffset : int):
		# 0 returns the highest emaRange value. Offset starts counting from the end of python list (-1, right)
		self.offset = -emaOffset if emaOffset else -1

	def printData(self):
		print(f'Period: {self.period}\t\tOffset: {self.offset} (-1 = highest)\t\tCurrent value: {self.emaRange[self.offset]}')
		print(f'Set: {self.emaRange}')
		print(f'Set lenght: {len(self.emaRange)}')

	def get(self, offset = 0) -> float:
		try:
			return self.emaRange[ self.offset - (offset if offset else 0) ]
		except:
			raise

	def backinsert(self, value : float):
		self.emaRange.append(value)

	def frontpop(self) -> float:
		return self.emaRange.pop(0)

	def insertAndPop(self, value : float):
		self.backinsert(value)
		return self.frontpop()

	def calcNewValueIsertAndPop(self, newValue : float) -> float:
		newEMA = (((newValue - self.emaRange[-1]) * self.k) + self.emaRange[-1])
		self.backinsert(newEMA)

		if len(self.emaRange) >= self.period: # pop a element only queue is full (self.period elements)
			self.frontpop()

		return newEMA

if __name__ == '__main__':

	emaSample = ema(21, 4)

	emaSample.load([1, 2, 3, 4, 5, 6, 7456, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
	emaSample.printData()

	print('-----------')
	emaSample.calcNewValueIsertAndPop(100)
	emaSample.printData()
	print('-----------')

	print(emaSample.get())
	print(emaSample.get(5))

	print('-----------')

	emaSample.setOffset(0)
	print(emaSample.get())
	print(emaSample.get(2))
