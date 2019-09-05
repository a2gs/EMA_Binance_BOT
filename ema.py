#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import sys
import random

def sma(smaValue, population):
	return(sum(population)/smaValue)

def ema(atual, anterior, k):
	return(((atual - anterior) * k) + anterior)

def main(argv):

	print(f'EMA = {argv[1]}')

	random.seed()
	emaRequest = int(argv[1])
	qtdPopulation = emaRequest * 4

	r = random.sample(range(0, 100), qtdPopulation)

	print(f'Population = {r} - Len: [{len(r)}]')

	smaSeedVar = sma(emaRequest, r[:emaRequest])

	k = 2 / (emaRequest + 1)

	print(f'SMA({argv[1]}) = [{smaSeedVar}] | EMA({emaRequest}) | k = {k}')

	seed = smaSeedVar
	emaVar = 0

	for x in range(emaRequest, qtdPopulation):

		emaVar = ema(r[x], seed, k)

		print(f"{x}) atual = [{r[x]}] EMA = [{emaVar}]")	

		seed = emaVar

if __name__ == '__main__':

	if len(sys.argv) != 2:
		print(f"Usage:\n\t{sys.argv[0]} <EMA>\n(population will be EMA * 4)")
		sys.exit(1)

	else:
		main(sys.argv)
