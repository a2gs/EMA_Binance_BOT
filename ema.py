#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

class EMAOffsetQueue:
	offsetx   = int(0)
	topo      = int(0)
	elements  = list()
	element   = float(0.0)

	def __init__(self, offsetX, initValue):
		self.offsetx = offsetX
		self.topo = 0

		self.element = 0.0
		self.elements = []

		self.insertN(initValue)

	def value(self):
		return(self.offsetx)

	def insertN(self, n):
		if self.offsetx == 0:
			self.element = n
		else:
			self.elements.append(n)
   
			if self.topo == self.offsetx:
				self.elements.pop(0)
			else:
				self.topo = self.topo + 1

	def getN(self):
		if self.offsetx == 0:
			return(self.element)
   
		return(self.elements[0])
   
	def getAll(self):
		if self.offsetx == 0:
			return(self.element)
   
		return(self.elements)

# https://dicionariodoinvestidor.com.br/content/o-que-e-media-movel-exponencial-mme/
# https://www.tororadar.com.br/investimento/analise-tecnica/medias-moveis
class ema(EMAOffsetQueue):
	emaValue     = int(0)
	initEmaValue = float(0.0)
	k            = float(0.0)
	offset       = object()

	def __init__(self, emaValueP, ema_initPopulation, offsetValue):

# TODO: throw a exception:
#		if emaValue < len(ema_initPopulation):
#			return False

		self.k = 2 / (emaValueP + 1)
		self.emaValue = emaValueP

		# First 'emaValue's are simple moving avarage
		self.initEmaValue = sum(ema_initPopulation[-emaValueP:]) / emaValueP

		self.offset = EMAOffsetQueue(offsetValue, self.initEmaValue)

		# Other values are EMA calculations
		[self.offset.insertN(self.calculateNewValue(x)) for x in ema_initPopulation[-emaValueP:]]

	def getEMAParams(self):
		return([self.emaValue, self.offset.getN(), self.k, self.offset.value()])

	def insertNewValueAndGetEMA(self, new):
		self.offset.insertN(self.calculateNewValue(new))
		return(self.offset.getN())

	def calculateNewValue(self, new):
		curr = self.offset.getN()
		return(((new - curr) * self.k) + curr)
