#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import os
import ema2
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

try:
	client = Client(os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'), os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'), {"verify": True, "timeout": 20})

	p = 27
	interv = '1w'
	offs = 7
	symb='DASHBTC'

	closedPrices = client.get_klines(symbol=symb, interval=interv)
	lastYetNotClosed = closedPrices[-1]

	lastYetNotClosedPrice = lastYetNotClosed[4]
	lastYetNotClosedTime  = lastYetNotClosed[6]

	lastPrices = []
	[lastPrices.append(float(x[4])) for x in closedPrices[:-1]]

	del closedPrices

	emaS = ema2.ema(p, offs)
	emaS.load(lastPrices)
	emaS.printData()

	print('------------------------------------')

	print(f'Adding last price: {lastYetNotClosedPrice}')

	newV = emaS.calcNewValueIsertAndPop(float(lastYetNotClosedPrice))

	emaS.printData()
	print(f'Current (not offset value) EMA: {newV}')
	print(f'Offset value EMA: {emaS.get()}')

	print('------------------------------------')

	info = emaS.info()
	print(f"Infos: period[{info['period']}] offset[{info['offset']}] current[{info['current']}]")

except BinanceAPIException as e:
	logging.info(f'Binance API exception: {e.status_code} - {e.message}')

except BinanceRequestException as e:
	logging.info(f'Binance request exception: {e.status_code} - {e.message}')

except BinanceWithdrawException as e:
	logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
