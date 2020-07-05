#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import sys

class ema():

	emaRange = object()
	period   = int(0)
	k        = float(0.0)
	offset   = int(0)

	def __init__(self, emaValue : int, emaOffset : int):
		self.emaRange = list() # Queue
		self.period   = emaValue
		self.k        = 2 / (emaValue + 1)
		self.setOffset(emaOffset)

	def load(self, sample : list) -> bool:
		if len(sample) <= self.period:
			return False

		try:
			self.backinsert(sum(sample[0:self.period]) / float(self.period))
		except:
			raise

		[self.calcNewValueInsertAndPop(i) for i in sample[self.period:]]

		return True

	def calcOffset(self, os) -> int: # Return the API (real) offset. Not user EMA requested offset (__init__).
		return -os - 1

	def setOffset(self, emaOffset : int):
		# 0 returns the highest emaRange value. Offset starts counting from the end of python list (-1, right)
		self.offset = self.calcOffset(emaOffset)

	def getOffset(self) -> int:
		return self.calcOffset(self.offset)

	def info(self) -> {}:
		return {'period' : self.period, 'offset' : self.getOffset(), 'current' : self.emaRange[self.offset]}

	def getRange(self) -> []:
		return self.emaRange

	def printData(self):
		print(f'Period: {self.period}\t\tOffset: {self.getOffset()}/{self.offset} (-1 = highest)\t\tCurrent value: {self.getWithOffset()}')
		[print(f"Value {i[1]}: {i[0]}") for i in zip(self.emaRange, range(self.period-1, -1, -1))]

	def get(self, offset : int = 0) -> float:
		try:
			return self.emaRange[self.calcOffset(offset)]
		except:
			raise

	def getWithOffset(self) -> float:
		try:
			return self.emaRange[self.offset]
		except:
			raise

	def backinsert(self, value : float):
		self.emaRange.append(value)

	def frontpop(self) -> float:
		return self.emaRange.pop(0)

	def insertAndPop(self, value : float):
		self.backinsert(value)
		return self.frontpop()

	def calcEMA(self, value : float) -> float:
		return ((value - self.emaRange[-1]) * self.k) + self.emaRange[-1]

	def calcNewValueInsertAndPop(self, newValue : float) -> float:
		newEMA = self.calcEMA(newValue)
		self.backinsert(newEMA)

		if len(self.emaRange) > self.period: # pop a element only queue is full (self.period elements)
			self.frontpop()

		return newEMA

if __name__ == '__main__':

	emaSample = ema(9, 4)

	emaSample.load([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
	emaSample.printData()

	print('-----------')

	print("Inserting value 100")
	emaSample.calcNewValueInsertAndPop(100)
	emaSample.printData()

	print('-----------')

	print(f"Get(): {emaSample.get()} (offset: 0)")
	print(f"Get(2): {emaSample.get(2)}")
	print(f"GetWithOffset(): {emaSample.getWithOffset()}")

	print('-----------')

	emaSample.setOffset(6)
	print("Changing offset to 6")
	print(f"Get(): {emaSample.get()} (offset: 0)")
	print(f"Get(4): {emaSample.get(4)}")
	print(f"GetWithOffset(): {emaSample.getWithOffset()}")
