#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import os
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

try:
	client = Client(os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'), os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'), {"verify": True, "timeout": 20})

	closedPrices = client.get_klines(symbol='BNBBTC', interval='1h')[-25-1:-1]

	x = 1
	for i in closedPrices:
		print(f'{x:2}: {i}')
		x=x+1

	print(closedPrices[-3:])

#	print(client.get_server_time())

except BinanceAPIException as e:
	logging.info(f'Binance API exception: {e.status_code} - {e.message}')

except BinanceRequestException as e:
	logging.info(f'Binance request exception: {e.status_code} - {e.message}')

except BinanceWithdrawException as e:
	logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
