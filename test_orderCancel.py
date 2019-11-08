#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import os, sys
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

try:
	client = Client(os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'), os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'), {"verify": True, "timeout": 20})

	print('--- OPEN ORDERS ---------------------------------------')
	print(client.get_open_orders())

	print('--- CANCEL ORDER --------------------------------------')
	if len(sys.argv) == 3:
		try:
			result = client.cancel_order(symbol=sys.argv[1], orderId=sys.argv[2])
		except BinanceAPIException as e:
			print(f'Binance API exception: {e.status_code} - {e.message}')
			sys.exit(1)

		print(f'Result: {result}')
	else:
		print(f'run: {sys.argv[0]} SYMBOL ORDER_ID');

except BinanceAPIException as e:
	print(f'Binance API exception: {e.status_code} - {e.message}')

except BinanceRequestException as e:
	print(f'Binance request exception: {e.status_code} - {e.message}')

except BinanceWithdrawException as e:
	print(f'Binance withdraw exception: {e.status_code} - {e.message}')
