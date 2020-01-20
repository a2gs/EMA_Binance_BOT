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

#	closedPrices = client.get_klines(symbol='BNBBTC', interval='1h')[-25-1:-1]

#	closedPrices = client.get_klines(symbol='DASHBTC', interval=interv)[-p-1:-1]
	closedPrices = client.get_klines(symbol='DASHBTC', interval=interv)
	lastYetNotClosed = closedPrices[-1]

	lastYetNotClosedPrice = lastYetNotClosed[4]
	lastYetNotClosedTime  = lastYetNotClosed[6]

#	print(closedPrices)
#	print(lastYetNotClosed)
#	print(float(lastYetNotClosedPrice))
#	print(int(lastYetNotClosedTime))

	lastPrices = []
	[lastPrices.append(float(x[4])) for x in closedPrices[:-1]]

#	print("Prices:")
#	print(lastPrices)
#	print("Prices len:")
#	print(len(lastPrices))

	del closedPrices
#	print('--------------------------------------------------')

	emaS = ema2.ema(p, 0)
	emaS.load(lastPrices)


#	print(client.get_server_time())

#	emaS.printData()

	newV = emaS.calcNewValueIsertAndPop(float(lastYetNotClosedPrice))

#	print(f'--------------------------\nNew EMA value: {newV}')
	emaS.printData()


except BinanceAPIException as e:
	logging.info(f'Binance API exception: {e.status_code} - {e.message}')

except BinanceRequestException as e:
	logging.info(f'Binance request exception: {e.status_code} - {e.message}')

except BinanceWithdrawException as e:
	logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
